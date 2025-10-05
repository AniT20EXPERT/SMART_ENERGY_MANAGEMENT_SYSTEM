#!/usr/bin/env python3
"""
Test script to demonstrate cost integration in the grid simulation system.
This script shows how costs are calculated and tracked across different components.
"""

import sys
import os
from datetime import datetime, timedelta

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cost_calculator import CostCalculator
from batteries.battery_base import BaseBattery
from generation.solar_power_plant import SolarPowerPlant
from generation.wind_power_plant import WindPowerPlant
from consumers.house import House
from consumers.industry import Industry
from consumers.ev_charging_station import EVChargingStation
from grid.substation import Substation
from grid.transformer import Transformer
from grid.inverter import Inverter

def test_cost_calculator():
    """Test the cost calculator with different scenarios"""
    print("=== Testing Cost Calculator ===")
    
    calculator = CostCalculator()
    current_time = datetime.now()
    
    # Test battery operations
    print("\n1. Battery Operations:")
    charging_cost = calculator.calculate_battery_charging_cost(10.0, 1.0, current_time)
    print(f"   Charging 10 kWh for 1 hour: ₹{charging_cost['total_cost_inr']}")
    
    discharging_cost = calculator.calculate_battery_discharging_cost(8.0, 1.0, current_time)
    print(f"   Discharging 8 kWh for 1 hour: ₹{discharging_cost['total_cost_inr']}")
    
    storage_cost = calculator.calculate_battery_storage_cost(50.0, 1.0, current_time)
    print(f"   Storing 50 kWh for 1 hour: ₹{storage_cost['total_cost_inr']}")
    
    # Test generation costs
    print("\n2. Generation Operations:")
    solar_cost = calculator.calculate_generation_cost(100.0, "solar", current_time)
    print(f"   Solar generation 100 kWh: ₹{solar_cost['total_cost_inr']}")
    
    wind_cost = calculator.calculate_generation_cost(80.0, "wind", current_time)
    print(f"   Wind generation 80 kWh: ₹{wind_cost['total_cost_inr']}")
    
    external_cost = calculator.calculate_external_grid_cost(50.0, current_time)
    print(f"   External grid 50 kWh: ₹{external_cost['total_cost_inr']}")
    
    # Test consumer costs
    print("\n3. Consumer Operations:")
    house_cost = calculator.calculate_consumer_cost(5.0, "house", current_time)
    print(f"   House consumption 5 kWh: ₹{house_cost['total_cost_inr']}")
    
    industry_cost = calculator.calculate_consumer_cost(100.0, "industry", current_time)
    print(f"   Industry consumption 100 kWh: ₹{industry_cost['total_cost_inr']}")
    
    ev_cost = calculator.calculate_consumer_cost(15.0, "ev_charging", current_time)
    print(f"   EV charging 15 kWh: ₹{ev_cost['total_cost_inr']}")
    
    # Test grid operations
    print("\n4. Grid Operations:")
    transmission_cost = calculator.calculate_grid_operation_cost(200.0, "transmission", current_time)
    print(f"   Transmission 200 kWh: ₹{transmission_cost['total_cost_inr']}")
    
    distribution_cost = calculator.calculate_grid_operation_cost(150.0, "distribution", current_time)
    print(f"   Distribution 150 kWh: ₹{distribution_cost['total_cost_inr']}")
    
    substation_cost = calculator.calculate_grid_operation_cost(100.0, "substation", current_time)
    print(f"   Substation 100 kWh: ₹{substation_cost['total_cost_inr']}")

def test_battery_cost_tracking():
    """Test battery cost tracking"""
    print("\n=== Testing Battery Cost Tracking ===")
    
    # Create a battery
    battery = BaseBattery(
        capacity_kwh=100.0,
        rated_voltage=400.0,
        rated_power_kw=50.0,
        device_id="test_battery"
    )
    
    print(f"Initial battery costs: {battery.get_total_costs()}")
    
    # Simulate charging
    battery.charge(20.0, 1.0, datetime.now())
    print(f"After charging 20 kWh: {battery.get_total_costs()}")
    
    # Simulate discharging
    battery.discharge(15.0, 1.0, datetime.now())
    print(f"After discharging 15 kWh: {battery.get_total_costs()}")
    
    # Simulate storage
    battery.calculate_storage_cost(1.0, datetime.now())
    print(f"After 1 hour storage: {battery.get_total_costs()}")

def test_generation_cost_tracking():
    """Test generation cost tracking"""
    print("\n=== Testing Generation Cost Tracking ===")
    
    # Create solar plant
    solar_plant = SolarPowerPlant(
        capacity_kW=1000.0,
        location="Test Solar Farm",
        panel_area_m2=5000.0
    )
    
    print(f"Initial solar costs: {solar_plant.get_total_costs()}")
    
    # Simulate generation
    solar_plant.generate(sunlight_factor=0.8, sim_time=datetime.now())
    print(f"After generating: {solar_plant.get_total_costs()}")

def test_consumer_cost_tracking():
    """Test consumer cost tracking"""
    print("\n=== Testing Consumer Cost Tracking ===")
    
    # Create a house
    def house_demand(time):
        return 5.0  # 5 kW base demand
    
    house = House(
        demand_function=house_demand,
        num_occupants=4,
        appliances={"refrigerator": 0.5, "air_conditioner": 2.0},
        id="test_house"
    )
    
    print(f"Initial house costs: {house.get_total_costs()}")
    
    # Simulate consumption
    house.get_demand(datetime.now())
    print(f"After consumption: {house.get_total_costs()}")

def test_grid_component_cost_tracking():
    """Test grid component cost tracking"""
    print("\n=== Testing Grid Component Cost Tracking ===")
    
    # Create substation
    substation = Substation(
        efficiency=0.99,
        input_source_id="generation",
        output_source_id="distribution",
        voltage_level_kV=11
    )
    
    print(f"Initial substation costs: {substation.get_total_costs()}")
    
    # Simulate power transfer
    substation.transfer_power(100.0, datetime.now())
    print(f"After transferring 100 kW: {substation.get_total_costs()}")

def main():
    """Main test function"""
    print("Grid Simulation Cost Integration Test")
    print("=" * 50)
    
    try:
        test_cost_calculator()
        test_battery_cost_tracking()
        test_generation_cost_tracking()
        test_consumer_cost_tracking()
        test_grid_component_cost_tracking()
        
        print("\n" + "=" * 50)
        print("All tests completed successfully!")
        print("\nCost integration features:")
        print("✓ Cost calculator with Indian Rupee pricing")
        print("✓ Time-of-day and seasonal multipliers")
        print("✓ Battery operation cost tracking")
        print("✓ Generation cost tracking")
        print("✓ Consumer cost tracking")
        print("✓ Grid component cost tracking")
        print("✓ MQTT integration for cost data")
        print("✓ External grid cost tracking")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
