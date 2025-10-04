from .battery_base import BaseBattery

class PowerPlantBESS(BaseBattery):
    def __init__(self, capacity_kwh, rated_voltage, rated_power_kw, plant_id, grid_connected=True):
        super().__init__(capacity_kwh, rated_voltage, rated_power_kw)
        self.id = plant_id+'_BESS'
        self.grid_connected = grid_connected

    def connect_to_grid(self):
        self.grid_connected = True
        self.mode = "grid-connected"

    def disconnect_from_grid(self):
        self.grid_connected = False
        self.mode = "islanded"