from .generation_base import GenerationBase
import json
import random

def external_generation_function(capacity_kW, requested_power_kW=0, **kwargs):
    """External source provides requested power up to max capacity"""
    return min(requested_power_kW, capacity_kW)

class ExternalSource(GenerationBase):
    def __init__(self, capacity_kW, location, source_name, rated_voltage=11000.0):
        super().__init__(capacity_kW, location, generation_function=external_generation_function)
        self.source_name = source_name
        self.rated_voltage = rated_voltage  # Grid voltage (typically 11kV, 33kV, or 132kV)
        self.current_voltage = rated_voltage
        self.current_current = 0.0
    
    def calculate_electrical_parameters(self):
        """Calculate voltage and current based on current output and grid conditions"""
        if self.current_output <= 0:
            self.current_voltage = 0.0
            self.current_current = 0.0
            return
        
        # Grid voltage is relatively stable but can vary slightly
        # Base voltage on load factor (higher load = slightly lower voltage)
        load_factor = min(self.current_output / self.capacity_kW, 1.0) if self.capacity_kW > 0 else 0.0
        voltage_factor = 0.95 + (0.05 * (1.0 - load_factor))  # Voltage drops slightly with higher load
        self.current_voltage = self.rated_voltage * voltage_factor
        
        # Add some realistic grid variation (±1% for grid sources)
        voltage_variation = random.uniform(-0.01, 0.01)
        self.current_voltage *= (1 + voltage_variation)
        
        # Calculate current from power and voltage
        if self.current_voltage > 0:
            self.current_current = (self.current_output * 1000) / self.current_voltage  # Convert kW to W
        else:
            self.current_current = 0.0
        
        # Ensure voltage and current are within reasonable bounds
        self.current_voltage = max(0, min(self.current_voltage, self.rated_voltage * 1.05))
        self.current_current = max(0, self.current_current)
    
    def publish_state(self, sim_time=None):
        """Publish MQTT state with external grid-specific sensor data."""
        topic = f"generation/{self.id}/state"
        
        # Use provided simulation time or last known time
        if sim_time is not None:
            self.simulation_time = sim_time
            
        from format_time import format_simulation_time
        time_str = format_simulation_time(self.simulation_time)
        
        # Calculate electrical parameters (voltage and current)
        self.calculate_electrical_parameters()
        
        # Get sensor data
        sensor_data = self.sensor_collector.get_all_sensor_data(
            self.simulation_time,
            "generation",
            abs(self.current_output)
        )
        
        state = {
            "device_id": self.id,
            "current_output": self.current_output,
            "capacity_kW": self.capacity_kW,
            "location": self.location,
            "simulated_time": time_str,
            "source_name": self.source_name,
            # Electrical parameters
            "voltage": self.current_voltage,
            "current": self.current_current,
            "rated_voltage": self.rated_voltage,
            # Add all sensor data
            **sensor_data
        }
        self.mqtt_client.publish(topic, json.dumps(state))
