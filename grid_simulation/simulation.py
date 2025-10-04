# Imports for batteries
from batteries.battery_base import BaseBattery
from batteries.ev_battery import EVBattery
from batteries.grid_bess import GridBESS
from batteries.power_plant_bess import PowerPlantBESS

# Imports for consumers
from consumers.consumer_base import ConsumerBase
from consumers.ev_charging_station import EVChargingStation
from consumers.ev import ElectricVehicle
from consumers.house import House
from consumers.industry import Industry

# Imports for generation
from generation.generation_base import GenerationBase
from generation.external import external_generation_function
from generation.solar_power_plant import SolarPowerPlant
from generation.wind_power_plant import WindPowerPlant

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

# More realistic generation functions
def solar_generation_factor(time, latitude=35.0):
    """Calculate solar generation factor based on time, season, and weather"""
    # Day of year for seasonal variation (1 to 365)
    day_of_year = time.timetuple().tm_yday
    
    # Seasonal variation (more sunlight in summer)
    seasonal_factor = 1.0 + 0.2 * math.cos(2 * math.pi * (day_of_year - 172) / 365)
    
    # Diurnal variation (peaks at solar noon ~12:00)
    hour = time.hour + time.minute / 60.0
    solar_angle = math.sin(math.pi * (hour - 6) / 12) if 6 <= hour < 18 else 0
    
    # Weather impact (random cloud cover effect)
    weather_factor = random.uniform(0.7, 1.0)  # Simulates cloud cover variability
    
    # Combine factors
    return max(0, solar_angle * seasonal_factor * weather_factor * 0.9)

def wind_generation_factor(time):
    """Calculate wind generation factor with temporal correlation"""
    # Base wind speed with daily variation
    hour = time.hour
    daily_variation = 1.0 + 0.3 * math.sin(2 * math.pi * hour / 24)
    
    # Add some random fluctuation with persistence
    base_speed = random.uniform(4.0, 12.0)
    persistence = 0.8  # Wind speed correlation between time steps
    if hasattr(wind_generation_factor, 'last_speed'):
        base_speed = persistence * wind_generation_factor.last_speed + (1 - persistence) * base_speed
    wind_generation_factor.last_speed = base_speed
    
    # Convert to power output (simplified cubic relationship)
    wind_speed = base_speed * daily_variation
    # Wind turbine power curve: 0 below 3 m/s, max at 12 m/s, cut-out at 25 m/s
    if wind_speed < 3 or wind_speed > 25:
        return 0.0
    elif wind_speed < 12:
        return ((wind_speed - 3) / 9) ** 3
    else:
        return 1.0

# Define simple demand functions
def house_demand_function(time):
    hour = time.hour
    if 18 <= hour < 22:
        return 5.0
    elif 0 <= hour < 6:
        return 1.0
    else:
        return 2.5

def industry_demand_function(time):
    hour = time.hour
    if 8 <= hour < 18:
        return 100.0
    return 20.0

def ev_demand_function(time):
    hour = time.hour
    if 17 <= hour < 23:
        return 7.2
    return 3.6

class PowerRoutingManager:
    """Manages power routing decisions from RL agent (MQTT)"""
    def __init__(self):
        # Default routing: equal distribution
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
        """Update routing configuration from RL agent"""
        self.routing_config.update(new_config)
    
    def get_routing(self):
        """Get current routing configuration"""
        return self.routing_config.copy()

class DynamicEVManager:
    """Manages dynamic EV arrivals and departures"""
    def __init__(self, evs, charging_stations):
        self.all_evs = evs
        self.charging_stations = charging_stations
        self.available_evs = evs.copy()  # EVs not currently at stations
        self.connected_evs = []  # EVs currently at stations
    
    def simulate_arrivals_departures(self, current_time):
        """Simulate random EV arrivals and departures"""
        hour = current_time.hour
        
        # Higher arrival probability during peak hours (17-23)
        arrival_prob = 0.3 if 17 <= hour < 23 else 0.1
        departure_prob = 0.2 if 6 <= hour < 10 else 0.05
        
        # Handle arrivals
        num_arrivals = int(len(self.available_evs) * arrival_prob)
        for _ in range(num_arrivals):
            if self.available_evs:
                ev = random.choice(self.available_evs)
                station = random.choice(self.charging_stations)
                if station.connect_ev(ev):
                    ev.plug_in()
                    self.available_evs.remove(ev)
                    self.connected_evs.append(ev)
        
        # Handle departures
        num_departures = int(len(self.connected_evs) * departure_prob)
        evs_to_remove = []
        for _ in range(num_departures):
            if self.connected_evs:
                ev = random.choice(self.connected_evs)
                # Find and disconnect from station
                for station in self.charging_stations:
                    if ev in station.connected_evs:
                        # Disconnect EV from station
                        station.connected_evs.remove(ev)
                        ev.unplug()
                        evs_to_remove.append(ev)
                        self.available_evs.append(ev)
                        break
        
        for ev in evs_to_remove:
            if ev in self.connected_evs:
                self.connected_evs.remove(ev)

class GridTopology:
    """Manages dynamic grid connections"""
    def __init__(self):
        self.connections = {}  # {source_id: {target_id: enabled}}
    
    def add_connection(self, source_id, target_id, enabled=True):
        """Add a connection between nodes"""
        if source_id not in self.connections:
            self.connections[source_id] = {}
        self.connections[source_id][target_id] = enabled
    
    def enable_connection(self, source_id, target_id):
        """Enable a connection"""
        if source_id in self.connections and target_id in self.connections[source_id]:
            self.connections[source_id][target_id] = True
    
    def disable_connection(self, source_id, target_id):
        """Disable a connection"""
        if source_id in self.connections and target_id in self.connections[source_id]:
            self.connections[source_id][target_id] = False
    
    def is_connected(self, source_id, target_id):
        """Check if connection is enabled"""
        return self.connections.get(source_id, {}).get(target_id, False)
    
    def get_active_connections(self):
        """Get all active connections"""
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
        self.power_flows = {}  # {(source, target): power_kw}
        
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
        
        # Add topology connection
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
        """Route power based on RL agent decisions and topology"""
        routing = self.routing_manager.get_routing()
        self.power_flows = {}
        
        # Calculate total power from each source type
        solar_power = sum(self.supply_sources.get(p.id, 0) for p in solar_plants)
        wind_power = sum(self.supply_sources.get(p.id, 0) for p in wind_plants)
        bess_power = sum(bess.remaining_capacity * 0.1 for bess, _ in self.bess_list if bess.soc > 0)
        
        # Calculate demands by type
        house_demand = sum(h.get_demand(current_time) for h in houses)
        industry_demand = sum(i.get_demand(current_time) for i in industries)
        station_demand = sum(s.get_demand(current_time) for s in charging_stations)
        
        # Route solar power
        if solar_power > 0 and self.topology.is_connected('Grid', 'Substation'):
            solar_to_houses = solar_power * routing['solar_to_houses']
            solar_to_industries = solar_power * routing['solar_to_industries']
            solar_to_stations = solar_power * routing['solar_to_stations']
            
            for p in solar_plants:
                self.power_flows[(p.id, 'Grid')] = self.supply_sources.get(p.id, 0)
            
            self.power_flows[('Grid', 'Houses')] = solar_to_houses
            self.power_flows[('Grid', 'Industries')] = solar_to_industries
            self.power_flows[('Grid', 'Stations')] = solar_to_stations
        
        # Route wind power
        if wind_power > 0 and self.topology.is_connected('Grid', 'Substation'):
            wind_to_houses = wind_power * routing['wind_to_houses']
            wind_to_industries = wind_power * routing['wind_to_industries']
            wind_to_stations = wind_power * routing['wind_to_stations']
            
            for p in wind_plants:
                self.power_flows[(p.id, 'Grid')] = self.supply_sources.get(p.id, 0)
    
    def simulate_step(self, current_time, solar_plants, wind_plants, houses, industries, charging_stations, duration_h):
        # Reset supply
        for key in self.supply_sources:
            self.supply_sources[key] = 0.0
        self.total_supply = 0.0
        self.total_demand = 0.0
        
        # Calculate total demand
        total_house_demand = sum(house.get_demand(current_time) for house in houses)
        total_industry_demand = sum(industry.get_demand(current_time) for industry in industries)
        total_station_demand = sum(station.get_demand(current_time) for station in charging_stations)
        self.total_demand = total_house_demand + total_industry_demand + total_station_demand
        
        # Generate power (only if connected to grid)
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
        
        # Apply substation / transformer efficiencies
        for sub in self.substations:
            self.total_supply *= sub.efficiency
            for key in self.supply_sources:
                self.supply_sources[key] *= sub.efficiency
        
        for trans in self.transformers:
            self.total_supply *= trans.efficiency
            for key in self.supply_sources:
                self.supply_sources[key] *= trans.efficiency
        
        # Handle BESS charging/discharging
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
        
        # Route power to consumers
        self.route_power_to_consumers(solar_plants, wind_plants, houses, industries, charging_stations, current_time)

class GridVisualizer:
    """Real-time grid visualization in separate thread"""
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
        """Build the network graph structure"""
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
        
        # Aggregate consumers
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
        """Calculate structured layout positions"""
        self.pos = {}
        layer_gap = 2.5
        
        # Generators at top
        gen_nodes = [p.id for p in self.solar_plants] + [p.id for p in self.wind_plants]
        for i, node in enumerate(gen_nodes):
            self.pos[node] = (i * 1.5, layer_gap * 4)
        
        self.pos["Grid"] = (len(gen_nodes) * 0.75, layer_gap * 3)
        
        for i, sub in enumerate(self.grid.substations):
            self.pos[sub.id] = (i * 2, layer_gap * 2)
        
        for i, trans in enumerate(self.grid.transformers):
            self.pos[trans.id] = (i * 2, layer_gap * 1)
        
        # Consumer aggregates
        self.pos["Houses"] = (0, 0)
        self.pos["Industries"] = (2, 0)
        self.pos["Stations"] = (4, 0)
        
        # BESS near their source
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
        """Update visualization with current power flows"""
        if not self.running:
            return
        
        self.ax.clear()
        self.build_graph()
        
        # Color map
        color_map = {
            "grid": "gray", "solar": "gold", "wind": "skyblue",
            "house": "lightgreen", "industry": "orange",
            "station": "violet", "bess": "brown",
            "substation": "blue", "transformer": "green",
        }
        
        node_colors = [color_map.get(self.G.nodes[n].get("type", "grid"), "grey") for n in self.G.nodes]
        
        # Draw nodes
        nx.draw_networkx_nodes(self.G, self.pos, node_color=node_colors, 
                              node_size=800, ax=self.ax, edgecolors="black", linewidths=2)
        
        # Draw edges
        nx.draw_networkx_edges(self.G, self.pos, ax=self.ax, arrows=True, 
                              arrowsize=15, edge_color="gray", width=2)
        
        # Draw labels with offset (above nodes)
        label_pos = {k: (v[0], v[1] + 0.3) for k, v in self.pos.items()}
        nx.draw_networkx_labels(self.G, label_pos, font_size=7, ax=self.ax)
        
        # Draw power flow values on edges
        edge_labels = {}
        for (u, v) in self.G.edges():
            power = self.grid.power_flows.get((u, v), 0)
            if power > 0:
                edge_labels[(u, v)] = f"{power:.1f}kW"
        
        nx.draw_networkx_edge_labels(self.G, self.pos, edge_labels, 
                                     font_size=6, ax=self.ax)
        
        # Draw SoC on battery nodes
        for bess, _ in self.grid.bess_list:
            if bess.id in self.pos:
                x, y = self.pos[bess.id]
                self.ax.text(x, y - 0.5, f"SoC: {bess.soc:.1f}%", 
                           fontsize=6, ha='center', 
                           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        self.ax.set_title(f"Grid Power Flow (Supply: {self.grid.total_supply:.1f}kW, Demand: {self.grid.total_demand:.1f}kW)")
        self.ax.axis("off")
    
    def start(self):
        """Start visualization in separate thread"""
        def run_viz():
            self.fig, self.ax = plt.subplots(figsize=(16, 10))
            ani = FuncAnimation(self.fig, self.update_plot, interval=1000, cache_frame_data=False)
            plt.show()
        
        viz_thread = threading.Thread(target=run_viz, daemon=True)
        viz_thread.start()
    
    def stop(self):
        """Stop visualization"""
        self.running = False

# [Previous imports and classes remain unchanged]

def main():
    grid = Grid()
    
    # Create 5 Solar Power Plants
    solar_plants = []
    for i in range(5):
        capacity = random.uniform(500, 2000)
        plant = SolarPowerPlant(
            capacity_kW=capacity,
            location=f"SolarSite_{i+1}",
            panel_area_m2=capacity*5
        )
        inverter = Inverter(efficiency=0.98, input_source_id=None, output_source_id=None, inverter_type="DC-AC")
        bess = PowerPlantBESS(
            capacity_kwh=random.uniform(200, 800),
            rated_voltage=400,
            rated_power_kw=random.uniform(100, 400),
            plant_id=f"SolarSite_{i+1}"
        )
        grid.add_power_plant(plant, inverter, bess)
        solar_plants.append(plant)
    
    # Create 3 Wind Power Plants
    wind_plants = []
    for i in range(3):
        capacity = random.uniform(1000, 3000)
        plant = WindPowerPlant(
            capacity_kW=capacity,
            location=f"WindSite_{i+1}",
            rotor_diameter_m=random.uniform(50, 100)
        )
        inverter = Inverter(efficiency=0.98, input_source_id=None, output_source_id=None, inverter_type="DC-AC")
        bess = PowerPlantBESS(
            capacity_kwh=random.uniform(400, 1200),
            rated_voltage=400,
            rated_power_kw=random.uniform(200, 600),
            plant_id=f"WindSite_{i+1}"
        )
        grid.add_power_plant(plant, inverter, bess)
        wind_plants.append(plant)
    
    # Create grid-level BESS
    grid_bess = GridBESS(capacity_kwh=5000, rated_voltage=400, rated_power_kw=1000)
    grid.add_grid_bess(grid_bess)
    
    # Add substation and transformer
    substation = Substation(efficiency=0.99, input_source_id='generation', output_source_id='distribution', voltage_level_kV=11)
    grid.add_substation(substation)
    transformer = Transformer(efficiency=0.97, input_source_id='high_voltage', output_source_id='low_voltage', rated_power_kVA=10000)
    grid.add_transformer(transformer)
    
    # Create 100 Houses
    houses = []
    for i in range(100):
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
    
    # Create 100 Industries
    industries = []
    for i in range(100):
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
    
    # Create 10 EV Charging Stations
    charging_stations = []
    for i in range(10):
        station = EVChargingStation(
            demand_function=house_demand_function,
            num_ports=random.randint(4, 10),
            max_power_kw=50.0,
            id=f"Station_{i+1}",
            efficiency=0.95,
            voltage=400
        )
        charging_stations.append(station)
    
    # Create 1000 Electric Vehicles with Batteries
    evs = []
    for i in range(1000):
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
    
    # Initialize dynamic EV manager
    ev_manager = DynamicEVManager(evs, charging_stations)
    
    # Connect some initial EVs
    for ev in evs[:50]:
        station = random.choice(charging_stations)
        if station.connect_ev(ev):
            ev.plug_in()
            ev_manager.available_evs.remove(ev)
            ev_manager.connected_evs.append(ev)
    
    # Start visualization
    visualizer = GridVisualizer(grid, solar_plants, wind_plants, houses, industries, charging_stations, evs)
    visualizer.start()
    
    # Simulation loop
    current_time = datetime(2025, 10, 4, 10, 0)
    real_start = time.time()
    sim_step_minutes = 60  # 1 hour simulation steps
    sim_step_seconds = sim_step_minutes * 60
    scale = 120  # 1 hour sim time = 30 seconds real time
    publish_interval_sim_min = 60  # Changed to 60 minutes to match sim_step_minutes
    publish_interval_steps = max(1, publish_interval_sim_min // sim_step_minutes)  # Ensure no division by zero
    step_count = 0
    duration_h = sim_step_minutes / 60.0
    
    print("Starting enhanced EMS simulation with:")
    print("- Real-time power flow visualization")
    print("- Dynamic EV arrivals/departures")
    print("- Power routing per consumer type")
    print("- Topology-aware grid connections")
    print("\nSimulation will run for 10 minutes real-time...")
    
    while True:
        real_now = time.time()
        real_elapsed = real_now - real_start
        if real_elapsed >= 10 * 60:
            break
        
        print(f"\n{'='*60}")
        print(f"Simulation at time: {current_time}")
        
        # Simulate EV dynamics
        ev_manager.simulate_arrivals_departures(current_time)
        print(f"EVs at stations: {len(ev_manager.connected_evs)}, Available: {len(ev_manager.available_evs)}")
        
        # Run grid simulation
        grid.simulate_step(current_time, solar_plants, wind_plants, houses, industries, charging_stations, duration_h)
        print(f"Supply: {grid.total_supply:.2f} kW, Demand: {grid.total_demand:.2f} kW")
        
        # Example: Dynamically disable/enable connections (simulate grid events)
        if step_count == 10:
            print("Simulating grid event: Disabling SolarSite_1 connection")
            grid.topology.disable_connection('SolarSite_1', 'Grid')
        if step_count == 20:
            print("Re-enabling SolarSite_1 connection")
            grid.topology.enable_connection('SolarSite_1', 'Grid')
        
        # Charge connected EVs
        for station in charging_stations:
            for ev in station.connected_evs:
                ev.charge_ev(current_time, duration_h=duration_h)
        
        step_count += 1
        if step_count % publish_interval_steps == 0:
            # Publish all devices
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
        
        # Advance simulated time
        current_time += timedelta(minutes=sim_step_minutes)
        
        # Sleep for corresponding real time
        real_sleep = sim_step_seconds / scale
        time.sleep(real_sleep)
    
    print("\nSimulation complete!")
    visualizer.stop()

if __name__ == '__main__':
    main()