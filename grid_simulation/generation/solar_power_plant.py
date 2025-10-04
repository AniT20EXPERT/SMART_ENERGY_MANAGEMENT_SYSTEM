from .generation_base import GenerationBase
import json
import random

class SolarPowerPlant(GenerationBase):
    def __init__(self, capacity_kW, location, panel_area_m2, rated_voltage=600.0):
        super().__init__(capacity_kW, location, generation_function=self.solar_generation_function)
        self.panel_area_m2 = panel_area_m2
        self.rated_voltage = rated_voltage  # DC voltage at maximum power point
        self.current_voltage = rated_voltage
        self.current_current = 0.0

    def solar_generation_function(self, sunlight_factor=1.0, **kwargs):
        """Compute solar output based on sunlight factor (0 to 1) using instance capacity"""
        return self.capacity_kW * sunlight_factor
    
    def calculate_electrical_parameters(self):
        """Calculate voltage and current based on current output and irradiance"""
        if self.current_output <= 0:
            self.current_voltage = 0.0
            self.current_current = 0.0
            return
        
        # Get current irradiance from sensor data
        if hasattr(self, 'sensor_collector') and self.simulation_time:
            try:
                sensor_data = self.sensor_collector.get_generation_sensor_data(
                    self.simulation_time, "solar", abs(self.current_output)
                )
                irradiance = sensor_data.get('irradiance', 1000.0)  # Default to 1000 W/m²
            except:
                irradiance = 1000.0
        else:
            irradiance = 1000.0
        
        # Calculate voltage based on irradiance (voltage decreases slightly with lower irradiance)
        irradiance_factor = min(irradiance / 1000.0, 1.0)  # Normalize to 1000 W/m²
        voltage_factor = 0.7 + (0.3 * irradiance_factor)  # Voltage varies from 70% to 100% of rated
        self.current_voltage = self.rated_voltage * voltage_factor
        
        # Add some realistic variation (±2%)
        voltage_variation = random.uniform(-0.02, 0.02)
        self.current_voltage *= (1 + voltage_variation)
        
        # Calculate current from power and voltage
        if self.current_voltage > 0:
            self.current_current = (self.current_output * 1000) / self.current_voltage  # Convert kW to W
        else:
            self.current_current = 0.0
        
        # Ensure voltage and current are within reasonable bounds
        self.current_voltage = max(0, min(self.current_voltage, self.rated_voltage * 1.1))
        self.current_current = max(0, self.current_current)
    
    def publish_state(self, sim_time=None):
        """Publish MQTT state with solar-specific sensor data."""
        topic = f"generation/{self.id}/state"
        
        # Use provided simulation time or last known time
        if sim_time is not None:
            self.simulation_time = sim_time
            
        from format_time import format_simulation_time
        time_str = format_simulation_time(self.simulation_time)
        
        # Calculate electrical parameters (voltage and current)
        self.calculate_electrical_parameters()
        
        # Get solar-specific sensor data
        sensor_data = self.sensor_collector.get_generation_sensor_data(
            self.simulation_time,
            "solar",
            abs(self.current_output)
        )
        
        state = {
            "device_id": self.id,
            "current_output": self.current_output,
            "capacity_kW": self.capacity_kW,
            "location": self.location,
            "simulated_time": time_str,
            "panel_area_m2": self.panel_area_m2,
            # Electrical parameters
            "voltage": self.current_voltage,
            "current": self.current_current,
            "rated_voltage": self.rated_voltage,
            # Add all sensor data
            **sensor_data
        }
        self.mqtt_client.publish(topic, json.dumps(state))
        
        # Also publish to generation_state topic for database aggregation
        generation_state = {
            "device_id": self.id,
            "current_output": self.current_output,
            "time": time_str,
            "device_type": "solar"
        }
        self.mqtt_client.publish("generation_state", json.dumps(generation_state))