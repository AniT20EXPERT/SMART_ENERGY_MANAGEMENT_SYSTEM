from .generation_base import GenerationBase

def external_generation_function(capacity_kW, requested_power_kW=0, **kwargs):
    """External source provides requested power up to max capacity"""
    return min(requested_power_kW, capacity_kW)

class ExternalSource(GenerationBase):
    def __init__(self, capacity_kW, location, source_name):
        super().__init__(capacity_kW, location, generation_function=external_generation_function)
        self.source_name = source_name
