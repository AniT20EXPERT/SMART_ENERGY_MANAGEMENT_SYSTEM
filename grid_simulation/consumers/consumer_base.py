import json
import paho.mqtt.client as mqtt
from format_time import format_simulation_time
from sensors import SensorDataCollector

class ConsumerBase:
    """Base class for consumer components"""
    
    def __init__(self, demand_function, efficiency=1.0, voltage=230, current=0.0, power=0.0,
                 device_id="consumer_default"):
        self.calculate_demand = demand_function  # Function(time) -> demand (kW)
        self.efficiency = efficiency
        self.voltage = voltage
        self.current = current
        self.power = power
        self.simulation_time = None

        # MQTT client
        self.id = device_id
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect("localhost", 1883, 60)
        self.mqtt_client.loop_start()
        
        # Sensor data collector
        self.sensor_collector = SensorDataCollector(location=f"consumer_{device_id}")

    def get_demand(self, sim_time):
        """Return current demand in kW (after efficiency), using simulated time."""
        demand_kw = self.calculate_demand(sim_time)
        net_demand = demand_kw / self.efficiency if self.efficiency > 0 else demand_kw
        self.power = net_demand
        self.current = (self.power * 1000) / self.voltage  # Convert kW to A
        self.simulation_time = sim_time

        # Publish state with simulated time
        self.publish_state()

        return net_demand

    def publish_state(self, sim_time=None):
        """Publish MQTT state including simulation time in RFC3339 format."""
        topic = f"consumers/{self.id}/state"
        
        # Use provided simulation time or last known time
        if sim_time is not None:
            self.simulation_time = sim_time
            
        time_str = format_simulation_time(self.simulation_time)
        
        # Get sensor data
        sensor_data = self.sensor_collector.get_consumer_sensor_data(
            self.simulation_time,
            "generic",
            abs(self.power)
        )
        
        state = {
            "device_id": self.id,
            "power": self.power,
            "current": self.current,
            "voltage": self.voltage,
            "simulated_time": time_str,
            # Add all sensor data
            **sensor_data
        }
        self.mqtt_client.publish(topic, json.dumps(state))