from consumers.consumer_base import ConsumerBase
from batteries.battery_base import BaseBattery

class ElectricVehicle(ConsumerBase):
    def __init__(self, demand_function, battery: BaseBattery, id,
                 efficiency=0.9, voltage=400, current=0.0, power=0.0):
        # Initialize base consumer attributes
        super().__init__(demand_function, efficiency, voltage, current, power)

        # Attach a battery
        self.battery = battery
        self.charging_status = "idle"   # idle, charging, discharging (for V2G)
        self.connected = False          # whether EV is plugged in at a charging station
        self.id = id

    def plug_in(self):
        """Connect EV to charging station / grid."""
        self.connected = True

    def unplug(self):
        """Disconnect EV."""
        self.connected = False
        self.charging_status = "idle"

    def charge_ev(self, time, duration_h=1.0):
        """
        Simulate EV charging from grid/charging station.
        Uses demand function to get required charging demand.
        """
        if not self.connected:
            return 0.0

        # Get required demand from ConsumerBase
        demand_kw = self.get_demand(time)

        # Charge the battery
        self.battery.charge(demand_kw, duration_h, sim_time=time)      # Charging rate needs to vary, or recalculate charging requirements at every time step
        self.charging_status = "charging"
        return demand_kw
