from consumers.consumer_base import ConsumerBase
import json

class Industry(ConsumerBase):
    def __init__(self, demand_function, industry_type, shift_hours, machinery, id, efficiency=0.85, voltage=415):
        super().__init__(demand_function, efficiency, voltage)
        self.industry_type = industry_type
        self.shift_hours = shift_hours  # e.g. [(8,16), (16,24)]
        self.machinery = machinery      # dict of machines and rated power
        self.id = id

    def get_demand(self, time):
        """Industry demand depends on active shifts + machinery."""
        base_demand = super().get_demand(time)
        active_shift = any(start <= time.hour < end for start, end in self.shift_hours)
        machine_demand = sum(self.machinery.values()) if active_shift else 0
        total_demand = base_demand + machine_demand
        self.power = total_demand
        return total_demand
    
    def publish_state(self, sim_time=None):
        """Publish MQTT state with industry-specific sensor data."""
        topic = f"consumers/{self.id}/state"
        
        # Use provided simulation time or last known time
        if sim_time is not None:
            self.simulation_time = sim_time
            
        from format_time import format_simulation_time
        time_str = format_simulation_time(self.simulation_time)
        
        # Get industry-specific sensor data
        sensor_data = self.sensor_collector.get_consumer_sensor_data(
            self.simulation_time,
            "industry",
            abs(self.power)
        )
        
        state = {
            "device_id": self.id,
            "power": self.power,
            "current": self.current,
            "voltage": self.voltage,
            "simulated_time": time_str,
            "industry_type": self.industry_type,
            "shift_hours": self.shift_hours,
            "machinery": self.machinery,
            # Add all sensor data
            **sensor_data
        }
        self.mqtt_client.publish(topic, json.dumps(state))