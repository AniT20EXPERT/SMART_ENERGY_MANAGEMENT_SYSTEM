from consumers.consumer_base import ConsumerBase
import json

class EVChargingStation(ConsumerBase):
    def __init__(self, demand_function, num_ports, max_power_kw, id, efficiency=0.95, voltage=400):
        super().__init__(demand_function, efficiency, voltage)
        self.num_ports = num_ports
        self.max_power_kw = max_power_kw
        self.connected_evs = []
        self.id = id

    def connect_ev(self, ev):
        if len(self.connected_evs) < self.num_ports:
            self.connected_evs.append(ev)
            return True
        return False
    
    def disconnect_ev(self, ev):
        """Disconnect an EV from this charging station."""
        if ev in self.connected_evs:
            self.connected_evs.remove(ev)
            return True
        return False

    def get_demand(self, time):
        """Station demand = sum of all connected EVs + base demand function."""
        base_demand = super().get_demand(time)
        ev_demand = sum(ev.get_demand(time) for ev in self.connected_evs)
        total_demand = min(base_demand + ev_demand, self.max_power_kw)
        self.power = total_demand
        return total_demand
    
    def publish_state(self, sim_time=None):
        """Publish MQTT state with EV charging station-specific sensor data."""
        topic = f"consumers/{self.id}/state"
        
        # Use provided simulation time or last known time
        if sim_time is not None:
            self.simulation_time = sim_time
            
        from format_time import format_simulation_time
        time_str = format_simulation_time(self.simulation_time)
        
        # Get EV charging station-specific sensor data
        sensor_data = self.sensor_collector.get_consumer_sensor_data(
            self.simulation_time,
            "ev_charging",
            abs(self.power)
        )
        
        state = {
            "device_id": self.id,
            "power": self.power,
            "current": self.current,
            "voltage": self.voltage,
            "simulated_time": time_str,
            "num_ports": self.num_ports,
            "max_power_kw": self.max_power_kw,
            "connected_evs_count": len(self.connected_evs),
            "connected_ev_ids": [ev.id for ev in self.connected_evs],
            # Add all sensor data
            **sensor_data
        }
        self.mqtt_client.publish(topic, json.dumps(state))