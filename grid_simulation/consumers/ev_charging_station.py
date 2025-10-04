from consumers.consumer_base import ConsumerBase

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
