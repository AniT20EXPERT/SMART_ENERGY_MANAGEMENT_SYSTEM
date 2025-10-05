from consumers.consumer_base import ConsumerBase
import json
class House(ConsumerBase):
    def __init__(self, demand_function, num_occupants, appliances, id, efficiency=0.95, voltage=230):
        super().__init__(demand_function, efficiency, voltage, device_id=id)
        self.num_occupants = num_occupants
        self.appliances = appliances  # dict of appliances and rated power
        self.consumer_type = "house"  # Set consumer type for cost calculation

    def get_demand(self, time):
        """House demand = base demand function + appliance usage."""
        base_demand = super().get_demand(time)
        appliance_demand = sum(self.appliances.values())
        total_demand = base_demand + appliance_demand
        self.power = total_demand
        return total_demand
    
    def publish_state(self, sim_time=None):
        """Publish MQTT state with house-specific sensor data."""
        topic = f"consumers/{self.id}/state"
        
        # Use provided simulation time or last known time
        if sim_time is not None:
            self.simulation_time = sim_time
            
        from format_time import format_simulation_time
        time_str = format_simulation_time(self.simulation_time)
        
        # Get house-specific sensor data
        sensor_data = self.sensor_collector.get_consumer_sensor_data(
            self.simulation_time,
            "house",
            abs(self.power)
        )
        
        # Get cost data
        cost_data = self.get_total_costs()
        
        state = {
            "device_id": self.id,
            "power": self.power,
            "current": self.current,
            "voltage": self.voltage,
            "simulated_time": time_str,
            "num_occupants": self.num_occupants,
            "appliances": self.appliances,
            # Add cost data
            **cost_data,
            # Add all sensor data
            **sensor_data
        }
        self.mqtt_client.publish(topic, json.dumps(state))