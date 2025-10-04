import json
import paho.mqtt.client as mqtt
from datetime import datetime
from format_time import format_simulation_time

class GridBase:
    """Base class for grid components"""

    def __init__(self, efficiency, input_source_id, output_source_id,
                 device_id="grid_default"):
        """
        efficiency: float (0 to 1) representing conversion efficiency
        input_source_id: ID of the input source (battery, generation, or grid)
        output_source_id: ID of the output destination
        """
        if not 0 <= efficiency <= 1:
            raise ValueError("Efficiency must be between 0 and 1")
        self.efficiency = efficiency
        self.input_source_id = input_source_id
        self.output_source_id = output_source_id

        # Feature parameters
        self.power_in = 0.0
        self.power_out = 0.0
        self.simulation_time = None  # latest simulation time

        # MQTT client
        self.id = device_id
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect("localhost", 1883, 60)
        self.mqtt_client.loop_start()

    def transfer_power(self, input_power_kW, current_time=None):
        """Transfer power with efficiency loss."""
        if input_power_kW is None or input_power_kW < 0:
            self.power_in = None
            self.power_out = None
        else:
            self.power_in = input_power_kW
            self.power_out = input_power_kW * self.efficiency

        if current_time is not None:
            self.simulation_time = current_time

        self.publish_state()
        return self.power_out

    def publish_state(self, sim_time=None):
        """Publish MQTT state including simulation time in RFC3339 format."""
        # Map device_id to corresponding Grafana panel topics
        topic_mapping = {
            "grid_default": "grid/default/state",
            "total_consumption": "grid/total_consumption/state",
            "active_alerts": "grid/active_alerts_count/state",
            "power_balance": "grid/power_flow_balance/state",
            "system_health": "grid/system_health_index/state",
            "total_generation": "grid/total_power_generation/state",
            "total_storage": "grid/total_storage_soc/state"
        }
        topic = topic_mapping.get(self.id, f"grid/{self.id}/state")

        # Update simulation time if provided
        if sim_time is not None:
            self.simulation_time = sim_time

        time_str = format_simulation_time(self.simulation_time)

        state = {
            "device_id": self.id,
            "simulated_time": time_str,
            "efficiency": self.efficiency,
            "input_source_id": self.input_source_id,
            "output_source_id": self.output_source_id,
            "power_in": self.power_in,
            "power_out": self.power_out
        }

        # Set state to None if no data to indicate "No data" in Grafana
        if self.power_in is None and self.power_out is None:
            state = {"device_id": self.id, "status": "No data"}

        self.mqtt_client.publish(topic, json.dumps(state))