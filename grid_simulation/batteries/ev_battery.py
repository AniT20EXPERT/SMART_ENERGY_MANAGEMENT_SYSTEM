from .battery_base import BaseBattery

class EVBattery(BaseBattery):
    def __init__(self, capacity_kwh, rated_voltage, rated_power_kw, vehicle_id):
        super().__init__(capacity_kwh, rated_voltage, rated_power_kw)
        self.id = vehicle_id+'_battery'   # EV-specific identifier