import json
import paho.mqtt.client as mqtt
from format_time import format_simulation_time
from sensors import SensorDataCollector
from cost_calculator import CostCalculator
class GenerationBase:
    """Base class for all generation units using a generation function"""

    def __init__(self, capacity_kW, location, generation_function=None,
                 device_id="generation_default"):
        """
        generation_function: a callable that returns power in kW
        """
        self.capacity_kW = capacity_kW
        self.location = location
        self.current_output = 0.0
        self.generation_function = generation_function  # default None
        self.simulation_time = None

        # MQTT client
        self.id = device_id
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect("localhost", 1883, 60)
        self.mqtt_client.loop_start()
        
        # Sensor data collector
        self.sensor_collector = SensorDataCollector(location=location)
        
        # Cost calculator
        self.cost_calculator = CostCalculator()
        
        # Cost tracking
        self.total_generation_cost = 0.0
        self.current_operation_cost = 0.0
        self.generation_type = "unknown"  # Will be set by subclasses

    def generate(self, sim_time=None, **kwargs):
        """
        Generate power using the generation function
        kwargs are passed to the function (e.g., sunlight, wind speed)
        """
        if self.generation_function is None:
            raise NotImplementedError("No generation function provided")

        output = self.generation_function(**kwargs)
        # limit output to max capacity
        self.current_output = min(output, self.capacity_kW)
        
        if sim_time is not None:
            self.simulation_time = sim_time

        # Calculate generation cost (assuming 1 hour duration for cost calculation)
        if self.current_output > 0:
            generation_cost_data = self.cost_calculator.calculate_generation_cost(
                self.current_output, self.generation_type, sim_time
            )
            self.current_operation_cost = generation_cost_data["total_cost_inr"]
            self.total_generation_cost += self.current_operation_cost

        # Publish state with simulated time
        self.publish_state()

        return self.current_output

    def get_current_output(self):
        return self.current_output

    def get_total_costs(self):
        """Get total cost breakdown for this generation unit"""
        return {
            "total_generation_cost_inr": round(self.total_generation_cost, 2),
            "current_operation_cost_inr": round(self.current_operation_cost, 2),
            "generation_type": self.generation_type,
            "currency": "INR"
        }

    def publish_state(self, sim_time=None):
        """Publish MQTT state including simulation time in RFC3339 format."""
        topic = f"generation/{self.id}/state"
        
        # Use provided simulation time or last known time
        if sim_time is not None:
            self.simulation_time = sim_time
            
        time_str = format_simulation_time(self.simulation_time)
        
        # Get sensor data
        sensor_data = self.sensor_collector.get_all_sensor_data(
            self.simulation_time,
            "generation",
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
            "device_type": "generation"
        }
        self.mqtt_client.publish("generation_state", json.dumps(generation_state))