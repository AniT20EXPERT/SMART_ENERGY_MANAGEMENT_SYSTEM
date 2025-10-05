import json
import paho.mqtt.client as mqtt
from format_time import format_simulation_time
from sensors import SensorDataCollector
from cost_calculator import CostCalculator

class BaseBattery:
    def __init__(self, capacity_kwh, rated_voltage, rated_power_kw,
                 max_charge_power_kw=None, max_discharge_power_kw=None,
                 charge_efficiency=0.95, discharge_efficiency=0.95,
                 device_id="battery_default"):
        # Configuration parameters
        self.capacity_kwh = capacity_kwh
        self.rated_voltage = rated_voltage
        self.rated_power_kw = rated_power_kw
        self.max_charge_power_kw = max_charge_power_kw if max_charge_power_kw else rated_power_kw
        self.max_discharge_power_kw = max_discharge_power_kw if max_discharge_power_kw else rated_power_kw
        self.charge_efficiency = charge_efficiency
        self.discharge_efficiency = discharge_efficiency

        # Feature parameters (initial values)
        self.soc = 100.0                  # %
        self.soh = 100.0                  # %
        self.voltage = rated_voltage      # V
        self.current = 0.0                # A
        self.power = 0.0                  # kW (+ve charging, -ve discharging)
        self.temperature = 25.0           # °C
        self.internal_resistance = 0.05   # Ω
        self.remaining_capacity = capacity_kwh  # kWh
        self.cycle_count = 0
        self.mode = "idle"                # idle, charging, discharging
        self.simulation_time = None

        # MQTT client
        self.id = device_id
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect("localhost", 1883, 60)
        self.mqtt_client.loop_start()
        
        # Sensor data collector
        self.sensor_collector = SensorDataCollector(location=f"battery_{device_id}")
        
        # Cost calculator
        self.cost_calculator = CostCalculator()
        
        # Cost tracking
        self.total_charging_cost = 0.0
        self.total_discharging_cost = 0.0
        self.total_storage_cost = 0.0
        self.current_operation_cost = 0.0

    def _update_operating_conditions(self, power_kw, duration_h, charging=True):
        """Internal helper to update dynamic parameters."""
        # Current (I = P/V) [kW -> W conversion]
        self.current = (abs(power_kw) * 1000) / max(self.voltage, 1e-6)

        # Temperature rise: proportional to I^2 * R
        heat_generated = (self.current ** 2) * self.internal_resistance * duration_h / 3600
        self.temperature += 0.01 * heat_generated  # scaled factor

        # Voltage adjustment due to internal resistance
        if charging:
            self.voltage = self.rated_voltage + (self.current * self.internal_resistance)
        else:
            self.voltage = self.rated_voltage - (self.current * self.internal_resistance)

        if self.voltage < 0:
            self.voltage = 0

        # SOH degradation (very simplified)
        self.soh -= 0.0001 * abs(power_kw) * duration_h
        if self.soh < 0:
            self.soh = 0

    def charge(self, power_kw, duration_h, sim_time=None):
        """Charge the battery with given power (kW) for duration (h)."""
        if power_kw > self.max_charge_power_kw:
            power_kw = self.max_charge_power_kw  # enforce charge limit

        # Apply charging efficiency
        energy_added = power_kw * duration_h * self.charge_efficiency
        self.remaining_capacity = min(self.capacity_kwh, self.remaining_capacity + energy_added)
        self.soc = (self.remaining_capacity / self.capacity_kwh) * 100
        self.mode = "charging"
        self.power = power_kw
        self.simulation_time = sim_time

        # Calculate charging cost
        charging_cost_data = self.cost_calculator.calculate_battery_charging_cost(
            energy_added, duration_h, sim_time
        )
        self.current_operation_cost = charging_cost_data["total_cost_inr"]
        self.total_charging_cost += self.current_operation_cost

        # Update feature parameters
        self._update_operating_conditions(power_kw, duration_h, charging=True)

        # Publish state
        self.publish_state(sim_time)

    def discharge(self, power_kw, duration_h, sim_time=None):
        """Discharge the battery with given power (kW) for duration (h)."""
        if power_kw > self.max_discharge_power_kw:
            power_kw = self.max_discharge_power_kw  # enforce discharge limit

        # Apply discharging efficiency
        energy_removed = power_kw * duration_h / self.discharge_efficiency
        self.remaining_capacity = max(0.0, self.remaining_capacity - energy_removed)
        self.soc = (self.remaining_capacity / self.capacity_kwh) * 100
        self.mode = "discharging"
        self.power = -power_kw
        self.cycle_count += 1 if self.remaining_capacity == 0 else 0
        self.simulation_time = sim_time

        # Calculate discharging cost
        discharging_cost_data = self.cost_calculator.calculate_battery_discharging_cost(
            energy_removed, duration_h, sim_time
        )
        self.current_operation_cost = discharging_cost_data["total_cost_inr"]
        self.total_discharging_cost += self.current_operation_cost

        # Update feature parameters
        self._update_operating_conditions(power_kw, duration_h, charging=False)

        # Publish state
        self.publish_state(sim_time)

    def calculate_storage_cost(self, duration_h, sim_time=None):
        """Calculate storage cost for the current energy stored"""
        if self.remaining_capacity > 0:
            storage_cost_data = self.cost_calculator.calculate_battery_storage_cost(
                self.remaining_capacity, duration_h, sim_time
            )
            self.current_operation_cost = storage_cost_data["total_cost_inr"]
            self.total_storage_cost += self.current_operation_cost
            return storage_cost_data
        return None

    def get_total_costs(self):
        """Get total cost breakdown for this battery"""
        return {
            "total_charging_cost_inr": round(self.total_charging_cost, 2),
            "total_discharging_cost_inr": round(self.total_discharging_cost, 2),
            "total_storage_cost_inr": round(self.total_storage_cost, 2),
            "total_operation_cost_inr": round(self.total_charging_cost + self.total_discharging_cost + self.total_storage_cost, 2),
            "current_operation_cost_inr": round(self.current_operation_cost, 2),
            "currency": "INR"
        }

    def publish_state(self, sim_time=None):
        """Publish MQTT state including simulation time in RFC3339 format."""
        topic = f"batteries/{self.id}/state"

        # Use provided simulation time or last known time
        if sim_time is not None:
            self.simulation_time = sim_time

        time_str = format_simulation_time(self.simulation_time)

        # Get sensor data
        sensor_data = self.sensor_collector.get_battery_sensor_data(
            self.simulation_time, 
            abs(self.power)
        )

        # Get cost data
        cost_data = self.get_total_costs()

        state = {
            "device_id": self.id,
            "simulated_time": time_str,
            "soc": self.soc,
            "soh": self.soh,
            "voltage": self.voltage,
            "current": self.current,
            "power": self.power,
            "temperature": self.temperature,
            "remaining_capacity": self.remaining_capacity,
            "cycle_count": self.cycle_count,
            "mode": self.mode,
            # Add cost data
            **cost_data,
            # Add all sensor data
            **sensor_data
        }

        self.mqtt_client.publish(topic, json.dumps(state))
        
        # Also publish to generation_state topic when discharging (generating power)
        if self.power < 0:  # Negative power means discharging (generating)
            generation_state = {
                "device_id": self.id,
                "current_output": abs(self.power),  # Positive value for generation
                "time": time_str,
                "device_type": "bess"
            }
            self.mqtt_client.publish("generation_state", json.dumps(generation_state))

