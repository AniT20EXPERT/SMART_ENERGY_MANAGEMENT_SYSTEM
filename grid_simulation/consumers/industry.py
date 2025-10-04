from consumers.consumer_base import ConsumerBase

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
