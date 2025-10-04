from .grid_base import GridBase

class Substation(GridBase):
    """Substation steps up/down voltage and routes power"""
    
    def __init__(self, efficiency, input_source_id, output_source_id, voltage_level_kV):
        super().__init__(efficiency, input_source_id, output_source_id)
        self.voltage_level_kV = voltage_level_kV
