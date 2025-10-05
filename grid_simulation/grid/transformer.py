from .grid_base import GridBase

class Transformer(GridBase):
    """Transformer steps voltage up or down"""
    
    def __init__(self, efficiency, input_source_id, output_source_id, rated_power_kVA):
        super().__init__(efficiency, input_source_id, output_source_id)
        self.rated_power_kVA = rated_power_kVA
        self.operation_type = "transmission"  # Set operation type for cost calculation
