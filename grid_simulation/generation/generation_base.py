import json
import paho.mqtt.client as mqtt
from format_time import format_simulation_time
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

        # Publish state with simulated time
        self.publish_state()

        return self.current_output

    def get_current_output(self):
        return self.current_output

    def publish_state(self, sim_time=None):
        """Publish MQTT state including simulation time in RFC3339 format."""
        topic = f"generation/{self.id}/state"
        
        # Use provided simulation time or last known time
        if sim_time is not None:
            self.simulation_time = sim_time
            
        time_str = format_simulation_time(self.simulation_time)
        
        state = {
            "device_id": self.id,
            "current_output": self.current_output,
            "capacity_kW": self.capacity_kW,
            "location": self.location,
            "simulated_time": time_str
        }
        self.mqtt_client.publish(topic, json.dumps(state))
