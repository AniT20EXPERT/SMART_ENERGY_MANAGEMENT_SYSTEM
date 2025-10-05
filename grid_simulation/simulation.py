# Imports for batteries
from batteries.battery_base import BaseBattery
from batteries.ev_battery import EVBattery
from batteries.grid_bess import GridBESS
from batteries.power_plant_bess import PowerPlantBESS

# Imports for consumers
from consumers.consumer_base import ConsumerBase
from consumers.ev import ElectricVehicle
from consumers.house import House
from consumers.industry import Industry
from consumers.ev_charging_station import EVChargingStation
# Imports for generation
from generation.generation_base import GenerationBase
from generation.external import external_generation_function
from generation.solar_power_plant import SolarPowerPlant
from generation.wind_power_plant import WindPowerPlant

# Import sensor system
from sensors import SensorDataCollector

# Import cost calculator
from cost_calculator import CostCalculator

# Imports for grid
from grid.grid_base import GridBase
from grid.inverter import Inverter
from grid.substation import Substation
from grid.transformer import Transformer

# Additional standard library imports
from datetime import datetime, timedelta
import random
import math
import time
import threading
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.animation import FuncAnimation

# More realistic generation functions with smooth transitions
def solar_generation_factor(time, latitude=35.0):
    """Calculate solar generation factor based on time, season, and weather"""
    day_of_year = time.timetuple().tm_yday
    seasonal_factor = 1.0 + 0.2 * math.cos(2 * math.pi * (day_of_year - 172) / 365)
    hour = time.hour + time.minute / 60.0
    solar_angle = math.sin(math.pi * (hour - 6) / 12) if 6 <= hour < 18 else 0
    
    # Much smoother weather variation with higher persistence
    if not hasattr(solar_generation_factor, 'last_weather'):
        solar_generation_factor.last_weather = 0.85
    
    # Very high persistence (0.98) for smooth transitions
    target_weather = random.gauss(0.85, 0.05)  # Gaussian distribution around 0.85
    target_weather = max(0.7, min(1.0, target_weather))  # Clamp to reasonable range
    solar_generation_factor.last_weather = (
        0.98 * solar_generation_factor.last_weather + 0.02 * target_weather
    )
    
    return max(0, solar_angle * seasonal_factor * solar_generation_factor.last_weather * 0.9)

def wind_generation_factor(time):
    """Calculate wind generation factor with temporal correlation"""
    hour = time.hour + time.minute / 60.0
    daily_variation = 1.0 + 0.2 * math.sin(2 * math.pi * hour / 24)
    
    # Initialize with reasonable starting wind speed
    if not hasattr(wind_generation_factor, 'last_speed'):
        wind_generation_factor.last_speed = 8.0
    
    # Very high persistence (0.95) for smooth wind speed changes
    target_speed = random.gauss(8.0, 2.0)  # Gaussian around 8 m/s
    target_speed = max(3.0, min(15.0, target_speed))
    wind_generation_factor.last_speed = (
        0.95 * wind_generation_factor.last_speed + 0.05 * target_speed
    )
    
    wind_speed = wind_generation_factor.last_speed * daily_variation
    
    if wind_speed < 3 or wind_speed > 25:
        return 0.0
    elif wind_speed < 12:
        return ((wind_speed - 3) / 9) ** 3
    else:
        return 1.0

# Smooth demand functions with gradual transitions
def smooth_transition(hour, minute, peak_start, peak_end, peak_value, base_value, transition_hours=2):
    """Helper to create smooth transitions between demand levels"""
    time_decimal = hour + minute / 60.0
    
    # Morning ramp-up
    if peak_start - transition_hours <= time_decimal < peak_start:
        progress = (time_decimal - (peak_start - transition_hours)) / transition_hours
        return base_value + (peak_value - base_value) * (0.5 - 0.5 * math.cos(math.pi * progress))
    # Evening ramp-down
    elif peak_end <= time_decimal < peak_end + transition_hours:
        progress = (time_decimal - peak_end) / transition_hours
        return peak_value - (peak_value - base_value) * (0.5 - 0.5 * math.cos(math.pi * progress))
    # Peak period
    elif peak_start <= time_decimal < peak_end:
        return peak_value
    # Base period
    else:
        return base_value

def house_demand_function(time):
    """Smooth house demand with gradual transitions"""
    return smooth_transition(
        time.hour, time.minute,
        peak_start=18, peak_end=22,
        peak_value=50.0,  # Scaled up from 5.0
        base_value=15.0,  # Scaled up from 1.5
        transition_hours=1.5
    )

def industry_demand_function(time):
    """Smooth industry demand with gradual transitions"""
    return smooth_transition(
        time.hour, time.minute,
        peak_start=8, peak_end=18,
        peak_value=800.0,  # Scaled up from 100.0
        base_value=150.0,  # Scaled up from 20.0
        transition_hours=1
    )

def ev_demand_function(time):
    """Smooth EV demand with gradual transitions"""
    return smooth_transition(
        time.hour, time.minute,
        peak_start=17, peak_end=23,
        peak_value=60.0,  # Scaled up from 7.2
        base_value=25.0,  # Scaled up from 3.6
        transition_hours=1.5
    )

def station_demand_function(time):
    """Smooth station demand with gradual transitions"""
    return smooth_transition(
        time.hour, time.minute,
        peak_start=17, peak_end=23,
        peak_value=120.0,  # Scaled up from 15.0
        base_value=60.0,   # Scaled up from 8.0
        transition_hours=1.5
    )
    
class PowerRoutingManager:
    """Manages power routing decisions from RL agent (MQTT)"""
    def __init__(self):
        self.routing_config = {
            'solar_to_houses': 0.33,
            'solar_to_industries': 0.33,
            'solar_to_stations': 0.34,
            'wind_to_houses': 0.33,
            'wind_to_industries': 0.33,
            'wind_to_stations': 0.34,
            'bess_to_houses': 0.33,
            'bess_to_industries': 0.33,
            'bess_to_stations': 0.34,
        }
    
    def update_routing(self, new_config):
        self.routing_config.update(new_config)
    
    def get_routing(self):
        return self.routing_config.copy()

class DynamicEVManager:
    """Manages dynamic EV arrivals and departures"""
    def __init__(self, evs, charging_stations):
        self.all_evs = evs
        self.charging_stations = charging_stations
        self.available_evs = evs.copy()
        self.connected_evs = []
    
    def simulate_arrivals_departures(self, current_time):
        hour = current_time.hour
        arrival_prob = 0.3 if 17 <= hour < 23 else 0.1
        departure_prob = 0.2 if 6 <= hour < 10 else 0.05
        
        # Probabilistic per EV for smoother changes
        for ev in list(self.available_evs):
            if random.random() < arrival_prob:
                station = random.choice(self.charging_stations)
                if station.connect_ev(ev):
                    ev.plug_in()
                    self.available_evs.remove(ev)
                    self.connected_evs.append(ev)
        
        for ev in list(self.connected_evs):
            if random.random() < departure_prob:
                for station in self.charging_stations:
                    if ev in station.connected_evs:
                        station.connected_evs.remove(ev)
                        ev.unplug()
                        self.connected_evs.remove(ev)
                        self.available_evs.append(ev)
                        break

class GridTopology:
    """Manages dynamic grid connections"""
    def __init__(self):
        self.connections = {}
    
    def add_connection(self, source_id, target_id, enabled=True):
        if source_id not in self.connections:
            self.connections[source_id] = {}
        self.connections[source_id][target_id] = enabled
    
    def enable_connection(self, source_id, target_id):
        if source_id in self.connections and target_id in self.connections[source_id]:
            self.connections[source_id][target_id] = True
    
    def disable_connection(self, source_id, target_id):
        if source_id in self.connections and target_id in self.connections[source_id]:
            self.connections[source_id][target_id] = False
    
    def is_connected(self, source_id, target_id):
        return self.connections.get(source_id, {}).get(target_id, False)
    
    def get_active_connections(self):
        active = []
        for source, targets in self.connections.items():
            for target, enabled in targets.items():
                if enabled:
                    active.append((source, target))
        return active

class Grid:
    def __init__(self):
        self.supply_sources = {}
        self.bess_list = []
        self.inverters = {}
        self.transformers = []
        self.substations = []
        self.total_supply = 0.0
        self.total_demand = 0.0
        self.topology = GridTopology()
        self.routing_manager = PowerRoutingManager()
        self.cost_calculator = CostCalculator()
        self.total_external_grid_cost = 0.0
        self.current_external_grid_cost = 0.0
        self.power_flows = {}
        
    def add_power_plant(self, plant, inverter, bess=None):
        plant.id = plant.location
        inverter.input_source_id = plant.id
        inverter.output_source_id = 'grid'
        if bess:
            bess.plant_id = plant.id
            bess.id = f"BESS_{plant.id}"
            self.bess_list.append((bess, plant.id))
        self.supply_sources[plant.id] = 0.0
        self.inverters[plant.id] = inverter
        self.topology.add_connection(plant.id, 'Grid')
    
    def add_grid_bess(self, bess):
        if not hasattr(bess, 'id'):
            bess.id = 'GridBESS'
        self.bess_list.append((bess, 'grid'))
    
    def add_substation(self, substation):
        if not hasattr(substation, 'id'):
            substation.id = 'Substation'
        self.substations.append(substation)
        self.topology.add_connection('Grid', substation.id)
    
    def add_transformer(self, transformer):
        if not hasattr(transformer, 'id'):
            transformer.id = 'Transformer'
        self.transformers.append(transformer)
        for sub in self.substations:
            self.topology.add_connection(sub.id, transformer.id)
    
    def route_power_to_consumers(self, solar_plants, wind_plants, houses, industries, charging_stations, current_time):
        routing = self.routing_manager.get_routing()
        self.power_flows = {}
        solar_power = sum(self.supply_sources.get(p.id, 0) for p in solar_plants)
        wind_power = sum(self.supply_sources.get(p.id, 0) for p in wind_plants)
        bess_power = sum(bess.remaining_capacity * 0.1 for bess, _ in self.bess_list if bess.soc > 0)
        house_demand = sum(h.get_demand(current_time) for h in houses)
        industry_demand = sum(i.get_demand(current_time) for i in industries)
        station_demand = sum(s.get_demand(current_time) for s in charging_stations)
        if solar_power > 0 and self.topology.is_connected('Grid', 'Substation'):
            solar_to_houses = solar_power * routing['solar_to_houses']
            solar_to_industries = solar_power * routing['solar_to_industries']
            solar_to_stations = solar_power * routing['solar_to_stations']
            for p in solar_plants:
                self.power_flows[(p.id, 'Grid')] = self.supply_sources.get(p.id, 0)
            self.power_flows[('Grid', 'Houses')] = solar_to_houses
            self.power_flows[('Grid', 'Industries')] = solar_to_industries
            self.power_flows[('Grid', 'Stations')] = solar_to_stations
        if wind_power > 0 and self.topology.is_connected('Grid', 'Substation'):
            wind_to_houses = wind_power * routing['wind_to_houses']
            wind_to_industries = wind_power * routing['wind_to_industries']
            wind_to_stations = wind_power * routing['wind_to_stations']
            for p in wind_plants:
                self.power_flows[(p.id, 'Grid')] = self.supply_sources.get(p.id, 0)
    
    def simulate_step(self, current_time, solar_plants, wind_plants, houses, industries, charging_stations, duration_h):
        for key in self.supply_sources:
            self.supply_sources[key] = 0.0
        self.total_supply = 0.0
        self.total_demand = 0.0
        total_house_demand = sum(house.get_demand(current_time) for house in houses)
        total_industry_demand = sum(industry.get_demand(current_time) for industry in industries)
        total_station_demand = sum(station.get_demand(current_time) for station in charging_stations)
        total_ev_demand = sum(ev.get_demand(current_time) for station in charging_stations for ev in station.connected_evs)
        self.total_demand = total_house_demand + total_industry_demand + total_station_demand + total_ev_demand
        for plant in solar_plants:
            if self.topology.is_connected(plant.id, 'Grid'):
                raw_output = plant.generate(sunlight_factor=solar_generation_factor(current_time), sim_time=current_time)
                inverter = self.inverters[plant.id]
                output = inverter.transfer_power(raw_output, current_time=current_time)
                self.supply_sources[plant.id] = output
                self.total_supply += output
        for plant in wind_plants:
            if self.topology.is_connected(plant.id, 'Grid'):
                raw_output = plant.generate(wind_speed=wind_generation_factor(current_time), sim_time=current_time)
                inverter = self.inverters[plant.id]
                output = inverter.transfer_power(raw_output, current_time=current_time)
                self.supply_sources[plant.id] = output
                self.total_supply += output
        for sub in self.substations:
            self.total_supply *= sub.efficiency
            for key in self.supply_sources:
                self.supply_sources[key] *= sub.efficiency
        for trans in self.transformers:
            self.total_supply *= trans.efficiency
            for key in self.supply_sources:
                self.supply_sources[key] *= trans.efficiency
        net_power = self.total_supply - self.total_demand
        for bess, connected_to in self.bess_list:
            if net_power > 0 and bess.soc < 100:
                charge_power = min(net_power, bess.max_charge_power_kw, (bess.capacity_kwh - bess.remaining_capacity) / duration_h)
                bess.charge(charge_power, duration_h, sim_time=current_time)
                net_power -= charge_power
            elif net_power < 0 and bess.soc > 0:
                discharge_power = min(-net_power, bess.max_discharge_power_kw, bess.remaining_capacity / duration_h)
                bess.discharge(discharge_power, duration_h, sim_time=current_time)
                net_power += discharge_power
            if bess.remaining_capacity > 0:
                bess.calculate_storage_cost(duration_h, current_time)
        if net_power < 0:
            external_power_needed = abs(net_power)
            external_cost_data = self.cost_calculator.calculate_external_grid_cost(
                external_power_needed, current_time
            )
            self.current_external_grid_cost = external_cost_data["total_cost_inr"]
            self.total_external_grid_cost += self.current_external_grid_cost
            self.publish_external_grid_cost(current_time, external_power_needed, external_cost_data)
        self.route_power_to_consumers(solar_plants, wind_plants, houses, industries, charging_stations, current_time)

    def publish_external_grid_cost(self, current_time, power_kw, cost_data):
        import json
        import paho.mqtt.client as mqtt
        from format_time import format_simulation_time
        mqtt_client = mqtt.Client()
        mqtt_client.connect("localhost", 1883, 60)
        mqtt_client.loop_start()
        time_str = format_simulation_time(current_time)
        external_grid_state = {
            "device_id": "external_grid",
            "simulated_time": time_str,
            "power_imported_kw": power_kw,
            "current_operation_cost_inr": cost_data["total_cost_inr"],
            "total_external_grid_cost_inr": round(self.total_external_grid_cost, 2),
            "base_cost_per_kwh": cost_data["base_cost_per_kwh"],
            "time_multiplier": cost_data["time_multiplier"],
            "seasonal_multiplier": cost_data["seasonal_multiplier"],
            "final_cost_per_kwh": cost_data["final_cost_per_kwh"],
            "currency": "INR",
            "operation_type": "external_grid_import"
        }
        mqtt_client.publish("grid/external_grid/cost", json.dumps(external_grid_state))
        mqtt_client.loop_stop()

class GridVisualizer:
    def __init__(self, grid, solar_plants, wind_plants, houses, industries, charging_stations, evs):
        self.grid = grid
        self.solar_plants = solar_plants
        self.wind_plants = wind_plants
        self.houses = houses
        self.industries = industries
        self.charging_stations = charging_stations
        self.evs = evs
        self.G = nx.DiGraph()
        self.pos = {}
        self.fig = None
        self.ax = None
        self.running = True
        
    def build_graph(self):
        self.G.clear()
        def add_node_safe(node_id, node_type):
            if node_id not in self.G.nodes:
                self.G.add_node(node_id, type=node_type)
        add_node_safe("Grid", "grid")
        for plant in self.solar_plants:
            add_node_safe(plant.id, "solar")
            if self.grid.topology.is_connected(plant.id, 'Grid'):
                self.G.add_edge(plant.id, "Grid")
        for plant in self.wind_plants:
            add_node_safe(plant.id, "wind")
            if self.grid.topology.is_connected(plant.id, 'Grid'):
                self.G.add_edge(plant.id, "Grid")
        for sub in self.grid.substations:
            add_node_safe(sub.id, "substation")
            if self.grid.topology.is_connected('Grid', sub.id):
                self.G.add_edge("Grid", sub.id)
        for trans in self.grid.transformers:
            add_node_safe(trans.id, "transformer")
            for sub in self.grid.substations:
                if self.grid.topology.is_connected(sub.id, trans.id):
                    self.G.add_edge(sub.id, trans.id)
        add_node_safe("Houses", "house")
        add_node_safe("Industries", "industry")
        add_node_safe("Stations", "station")
        for trans in self.grid.transformers:
            self.G.add_edge(trans.id, "Houses")
            self.G.add_edge(trans.id, "Industries")
            self.G.add_edge(trans.id, "Stations")
        for bess, connected_to in self.grid.bess_list:
            add_node_safe(bess.id, "bess")
            conn = "Grid" if connected_to == "grid" else connected_to
            self.G.add_edge(conn, bess.id)
        self.calculate_layout()
    
    def calculate_layout(self):
        self.pos = {}
        layer_gap = 2.5
        gen_nodes = [p.id for p in self.solar_plants] + [p.id for p in self.wind_plants]
        for i, node in enumerate(gen_nodes):
            self.pos[node] = (i * 1.5, layer_gap * 4)
        self.pos["Grid"] = (len(gen_nodes) * 0.75, layer_gap * 3)
        for i, sub in enumerate(self.grid.substations):
            self.pos[sub.id] = (i * 2, layer_gap * 2)
        for i, trans in enumerate(self.grid.transformers):
            self.pos[trans.id] = (i * 2, layer_gap * 1)
        self.pos["Houses"] = (0, 0)
        self.pos["Industries"] = (2, 0)
        self.pos["Stations"] = (4, 0)
        offset = len(gen_nodes) * 1.5 + 1
        for bess, connected_to in self.grid.bess_list:
            conn = "Grid" if connected_to == "grid" else connected_to
            if conn in self.pos:
                x, y = self.pos[conn]
                self.pos[bess.id] = (x + 0.8, y - 0.5)
            else:
                self.pos[bess.id] = (offset, 1)
                offset += 1
    
    def update_plot(self, frame):
        if not self.running:
            return
        self.ax.clear()
        self.build_graph()
        color_map = {
            "grid": "gray", "solar": "gold", "wind": "skyblue",
            "house": "lightgreen", "industry": "orange",
            "station": "violet", "bess": "brown",
            "substation": "blue", "transformer": "green",
        }
        node_colors = [color_map.get(self.G.nodes[n].get("type", "grid"), "grey") for n in self.G.nodes]
        nx.draw_networkx_nodes(self.G, self.pos, node_color=node_colors, 
                              node_size=800, ax=self.ax, edgecolors="black", linewidths=2)
        nx.draw_networkx_edges(self.G, self.pos, ax=self.ax, arrows=True, 
                              arrowsize=15, edge_color="gray", width=2)
        label_pos = {k: (v[0], v[1] + 0.3) for k, v in self.pos.items()}
        nx.draw_networkx_labels(self.G, label_pos, font_size=7, ax=self.ax)
        edge_labels = {}
        for (u, v) in self.G.edges():
            power = self.grid.power_flows.get((u, v), 0)
            if power > 0:
                edge_labels[(u, v)] = f"{power:.1f}kW"
        nx.draw_networkx_edge_labels(self.G, self.pos, edge_labels, 
                                     font_size=6, ax=self.ax)
        for bess, _ in self.grid.bess_list:
            if bess.id in self.pos:
                x, y = self.pos[bess.id]
                self.ax.text(x, y - 0.5, f"SoC: {bess.soc:.1f}%", 
                           fontsize=6, ha='center', 
                           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        self.ax.set_title(f"Grid Power Flow (Supply: {self.grid.total_supply:.1f}kW, Demand: {self.grid.total_demand:.1f}kW)")
        self.ax.axis("off")
    
    def start(self):
        def run_viz():
            self.fig, self.ax = plt.subplots(figsize=(16, 10))
            ani = FuncAnimation(self.fig, self.update_plot, interval=1000, cache_frame_data=False)
            plt.show()
        viz_thread = threading.Thread(target=run_viz, daemon=True)
        viz_thread.start()
    
    def stop(self):
        self.running = False

# Modified main function with adjusted scale and scaled component counts/capacities

def main():
    grid = Grid()
    solar_plants = []
    for i in range(2):
        capacity = random.uniform(200, 500)  # Scaled down while keeping relative min-max proportion
        plant = SolarPowerPlant(
            capacity_kW=capacity,
            location=f"SolarSite_{i+1}",
            panel_area_m2=capacity*5,
            rated_voltage=600.0
        )
        inverter = Inverter(efficiency=0.98, input_source_id=None, output_source_id=None, inverter_type="DC-AC")
        bess = PowerPlantBESS(
            capacity_kwh=random.uniform(100, 300),  # Scaled
            rated_voltage=400,
            rated_power_kw=random.uniform(50, 150),  # Scaled
            plant_id=f"SolarSite_{i+1}"
        )
        grid.add_power_plant(plant, inverter, bess)
        solar_plants.append(plant)
    wind_plants = []
    for i in range(1):
        capacity = random.uniform(300, 800)  # Scaled
        plant = WindPowerPlant(
            capacity_kW=capacity,
            location=f"WindSite_{i+1}",
            rotor_diameter_m=random.uniform(50, 100),
            rated_voltage=690.0
        )
        inverter = Inverter(efficiency=0.98, input_source_id=None, output_source_id=None, inverter_type="DC-AC")
        bess = PowerPlantBESS(
            capacity_kwh=random.uniform(150, 400),  # Scaled
            rated_voltage=400,
            rated_power_kw=random.uniform(75, 200),  # Scaled
            plant_id=f"WindSite_{i+1}"
        )
        grid.add_power_plant(plant, inverter, bess)
        wind_plants.append(plant)
    grid_bess = GridBESS(capacity_kwh=1000, rated_voltage=400, rated_power_kw=200)  # Scaled
    grid.add_grid_bess(grid_bess)
    substation = Substation(efficiency=0.99, input_source_id='generation', output_source_id='distribution', voltage_level_kV=11)
    grid.add_substation(substation)
    transformer = Transformer(efficiency=0.97, input_source_id='high_voltage', output_source_id='low_voltage', rated_power_kVA=5000)  # Scaled
    grid.add_transformer(transformer)
    houses = []
    for i in range(20):  # Increased count for scaling
        appliances = {
            "lighting": 0.5,
            "hvac": random.uniform(1.0, 3.0),
            "appliances": random.uniform(0.5, 1.5)
        }
        house = House(
            demand_function=house_demand_function,
            num_occupants=random.randint(1, 5),
            appliances=appliances,
            id=f"House_{i+1}",
            efficiency=0.95,
            voltage=230
        )
        houses.append(house)
    industries = []
    for i in range(5):  # Increased count for scaling
        machinery = {
            "motor": random.uniform(10, 50),
            "equipment": random.uniform(20, 100)
        }
        industry = Industry(
            demand_function=industry_demand_function,
            industry_type="manufacturing",
            shift_hours=[(8, 16), (16, 24)],
            machinery=machinery,
            id=f"Industry_{i+1}",
            efficiency=0.85,
            voltage=415
        )
        industries.append(industry)
    charging_stations = []
    for i in range(3):  # Increased count for scaling
        station = EVChargingStation(
            demand_function=station_demand_function,
            num_ports=random.randint(4, 10),
            max_power_kw=50.0,
            id=f"Station_{i+1}",
            efficiency=0.95,
            voltage=400
        )
        charging_stations.append(station)
    evs = []
    for i in range(30):  # Increased count for scaling
        battery = EVBattery(
            capacity_kwh=random.uniform(40, 100),
            rated_voltage=400,
            rated_power_kw=7.2,
            vehicle_id=f"EV_{i+1}"
        )
        ev = ElectricVehicle(
            demand_function=ev_demand_function,
            battery=battery,
            id=f"EV_{i+1}",
            efficiency=0.9,
            voltage=400
        )
        evs.append(ev)
    ev_manager = DynamicEVManager(evs, charging_stations)
    for ev in evs[:10]:  # Adjusted initial connections
        station = random.choice(charging_stations)
        if station.connect_ev(ev):
            ev.plug_in()
            ev_manager.available_evs.remove(ev)
            ev_manager.connected_evs.append(ev)
    visualizer = GridVisualizer(grid, solar_plants, wind_plants, houses, industries, charging_stations, evs)
    visualizer.start()
    # --- Simulation timing setup ---
    current_time = datetime(2025, 10, 4, 6, 0)  # Start at 6:00 AM
    real_start = time.time()

    sim_step_minutes = 15           # 1-minute steps for fine resolution
    sim_step_seconds = sim_step_minutes * 60
    scale = 240                   # 1 sim hour = 30 real seconds (3600/30 = 120)
    publish_interval_sim_min = 2   # Publish every 1 simulated minute
    publish_interval_steps = max(1, publish_interval_sim_min // sim_step_minutes)

    step_count = 0
    duration_h = sim_step_minutes / 60.0
    simulation_days = 10           # 10-day simulation
    total_sim_hours = simulation_days * 24
    total_sim_steps = total_sim_hours * (60 // sim_step_minutes)

    max_real_time_minutes = 48    # Adjusted for 10 days (10*24*60/120/60 = 48 minutes)

    print("Starting enhanced EMS simulation with:")
    print("- Real-time power flow visualization")
    print("- Dynamic EV arrivals/departures")
    print("- Power routing per consumer type")
    print("- Topology-aware grid connections")
    print(f"- {simulation_days} days simulation time ({total_sim_hours} hours)")
    print(f"- {sim_step_minutes}-minute time steps")
    print(f"- Maximum {max_real_time_minutes} minutes real-time")
    print(f"- Total simulation steps: {total_sim_steps}")
    while step_count < total_sim_steps:
        real_now = time.time()
        real_elapsed = real_now - real_start
        if real_elapsed >= max_real_time_minutes * 60:
            print(f"\nReal-time limit reached ({max_real_time_minutes} minutes). Stopping simulation.")
            break
        progress_percent = (step_count / total_sim_steps) * 100
        real_time_elapsed = real_elapsed / 60
        if step_count % (publish_interval_steps * 2) == 0:
            print(f"\n{'='*60}")
            print(f"Progress: {progress_percent:.1f}% | Step: {step_count}/{total_sim_steps}")
            print(f"Simulation time: {current_time.strftime('%Y-%m-%d %H:%M')}")
            print(f"Real time elapsed: {real_time_elapsed:.1f} minutes")
        ev_manager.simulate_arrivals_departures(current_time)
        grid.simulate_step(current_time, solar_plants, wind_plants, houses, industries, charging_stations, duration_h)
        if step_count == total_sim_steps // 7:
            print("Day 1: Simulating grid event - Disabling SolarSite_1 connection")
            grid.topology.disable_connection('SolarSite_1', 'Grid')
        elif step_count == total_sim_steps // 7 * 2:
            print("Day 2: Re-enabling SolarSite_1 connection")
            grid.topology.enable_connection('SolarSite_1', 'Grid')
        elif step_count == total_sim_steps // 7 * 4:
            print("Day 4: Simulating maintenance - Disabling WindSite_1 connection")
            grid.topology.disable_connection('WindSite_1', 'Grid')
        elif step_count == total_sim_steps // 7 * 5:
            print("Day 5: Re-enabling WindSite_1 connection")
            grid.topology.enable_connection('WindSite_1', 'Grid')
        for station in charging_stations:
            for ev in station.connected_evs:
                ev.charge_ev(current_time, duration_h=duration_h)
        step_count += 1
        if step_count % publish_interval_steps == 0:
            for plant in solar_plants + wind_plants:
                plant.publish_state(current_time)
            for bess, _ in grid.bess_list:
                bess.publish_state(current_time)
            for inv in grid.inverters.values():
                inv.publish_state(current_time)
            for sub in grid.substations:
                sub.publish_state(current_time)
            for trans in grid.transformers:
                trans.publish_state(current_time)
            for house in houses:
                house.publish_state(current_time)
            for ind in industries:
                ind.publish_state(current_time)
            for station in charging_stations:
                station.publish_state(current_time)
            for ev in evs:
                ev.publish_state(current_time)
                ev.battery.publish_state(current_time)
        current_time += timedelta(minutes=sim_step_minutes)
        real_sleep = sim_step_seconds / scale
        time.sleep(real_sleep)
    final_real_time = (time.time() - real_start) / 60
    final_sim_time = current_time
    print(f"\n{'='*60}")
    print("SIMULATION COMPLETE!")
    print(f"Final simulation time: {final_sim_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"Total real time: {final_real_time:.1f} minutes")
    print(f"Total simulation steps: {step_count}")
    print(f"Simulation speed: {step_count / final_real_time:.1f} steps/minute")
    print("="*60)
    visualizer.stop()

if __name__ == '__main__':
    main()