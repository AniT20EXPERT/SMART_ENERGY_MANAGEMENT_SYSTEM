from .generation_base import GenerationBase
import json
import random

class WindPowerPlant(GenerationBase):
    def __init__(self, capacity_kW, location, rotor_diameter_m, rated_voltage=690.0):
        super().__init__(capacity_kW, location, generation_function=self.wind_generation_function)
        self.rotor_diameter_m = rotor_diameter_m
        self.rated_voltage = rated_voltage  # AC voltage for wind turbines (typically 690V)
        self.current_voltage = rated_voltage
        self.current_current = 0.0
        self.generation_type = "wind"  # Set generation type for cost calculation

    def wind_generation_function(self, wind_speed_m_s=0, **kwargs):
        """Compute wind output (simplified cubic law, capped at capacity)"""
        rated_speed = 12.0  # m/s for rated output
        normalized_speed = min(wind_speed_m_s / rated_speed, 1.0)
        return self.capacity_kW * (normalized_speed ** 3)
    
    def calculate_electrical_parameters(self):
        """Calculate voltage and current based on current output and wind conditions"""
        if self.current_output <= 0:
            self.current_voltage = 0.0
            self.current_current = 0.0
            return
        
        # Get current wind speed from sensor data
        if hasattr(self, 'sensor_collector') and self.simulation_time:
            try:
                sensor_data = self.sensor_collector.get_generation_sensor_data(
                    self.simulation_time, "wind", abs(self.current_output)
                )
                wind_speed = sensor_data.get('wind_speed', 5.0)  # Default to 5 m/s
            except:
                wind_speed = 5.0
        else:
            wind_speed = 5.0
        
        # Calculate voltage based on wind speed (voltage increases with wind speed)
        wind_factor = min(wind_speed / 12.0, 1.0)  # Normalize to 12 m/s rated wind speed
        voltage_factor = 0.6 + (0.4 * wind_factor)  # Voltage varies from 60% to 100% of rated
        self.current_voltage = self.rated_voltage * voltage_factor
        
        # Add some realistic variation (±3% for wind turbines)
        voltage_variation = random.uniform(-0.03, 0.03)
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
        """Publish MQTT state with wind-specific sensor data."""
        topic = f"generation/{self.id}/state"
        
        # Use provided simulation time or last known time
        if sim_time is not None:
            self.simulation_time = sim_time
            
        from format_time import format_simulation_time
        time_str = format_simulation_time(self.simulation_time)
        
        # Calculate electrical parameters (voltage and current)
        self.calculate_electrical_parameters()
        
        # Get wind-specific sensor data
        sensor_data = self.sensor_collector.get_generation_sensor_data(
            self.simulation_time,
            "wind",
            abs(self.current_output)
        )
        
        # Get cost data
        cost_data = self.get_total_costs()
        
        state = {
            "device_id": self.id,
            "current_output": self.current_output,
            "capacity_kW": self.capacity_kW,
            "location": self.location,
            "simulated_time": time_str,
            "rotor_diameter_m": self.rotor_diameter_m,
            # Electrical parameters
            "voltage": self.current_voltage,
            "current": self.current_current,
            "rated_voltage": self.rated_voltage,
            # Add cost data
            **cost_data,
            # Add all sensor data
            **sensor_data
        }
        self.mqtt_client.publish(topic, json.dumps(state))
        
        # Also publish to generation_state topic for database aggregation
        generation_state = {
            "device_id": self.id,
            "current_output": self.current_output,
            "time": time_str,
            "device_type": "wind"
        }
        self.mqtt_client.publish("generation_state", json.dumps(generation_state))