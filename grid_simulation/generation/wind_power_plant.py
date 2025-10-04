from .generation_base import GenerationBase

class WindPowerPlant(GenerationBase):
    def __init__(self, capacity_kW, location, rotor_diameter_m):
        super().__init__(capacity_kW, location, generation_function=self.wind_generation_function)
        self.rotor_diameter_m = rotor_diameter_m

    def wind_generation_function(self, wind_speed_m_s=0, **kwargs):
        """Compute wind output (simplified cubic law, capped at capacity)"""
        rated_speed = 12.0  # m/s for rated output
        normalized_speed = min(wind_speed_m_s / rated_speed, 1.0)
        return self.capacity_kW * (normalized_speed ** 3)