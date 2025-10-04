from .generation_base import GenerationBase

class SolarPowerPlant(GenerationBase):
    def __init__(self, capacity_kW, location, panel_area_m2):
        super().__init__(capacity_kW, location, generation_function=self.solar_generation_function)
        self.panel_area_m2 = panel_area_m2

    def solar_generation_function(self, sunlight_factor=1.0, **kwargs):
        """Compute solar output based on sunlight factor (0 to 1) using instance capacity"""
        return self.capacity_kW * sunlight_factor