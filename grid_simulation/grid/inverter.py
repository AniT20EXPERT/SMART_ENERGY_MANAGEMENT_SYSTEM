from .grid_base import GridBase

class Inverter(GridBase):
    """Inverter converts DC to AC or vice versa"""
    
    def __init__(self, efficiency, input_source_id, output_source_id, inverter_type="DC-AC"):
        super().__init__(efficiency, input_source_id, output_source_id)
        self.inverter_type = inverter_type
