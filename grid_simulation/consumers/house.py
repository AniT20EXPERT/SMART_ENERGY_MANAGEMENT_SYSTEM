from consumers.consumer_base import ConsumerBase

class House(ConsumerBase):
    def __init__(self, demand_function, num_occupants, appliances, id, efficiency=0.95, voltage=230):
        super().__init__(demand_function, efficiency, voltage)
        self.num_occupants = num_occupants
        self.appliances = appliances  # dict of appliances and rated power
        self.id = id

    def get_demand(self, time):
        """House demand = base demand function + appliance usage."""
        base_demand = super().get_demand(time)
        appliance_demand = sum(self.appliances.values())
        total_demand = base_demand + appliance_demand
        self.power = total_demand
        return total_demand
