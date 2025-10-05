#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced sensor data collection.
This script shows the comprehensive sensor data now being sent by all grid components.
"""

import json
from datetime import datetime
from sensors import SensorDataCollector
from batteries.battery_base import BaseBattery
from consumers.house import House
from generation.solar_power_plant import SolarPowerPlant
from generation.wind_power_plant import WindPowerPlant

def test_sensor_data():
    """Test the enhanced sensor data collection"""
    print("Testing Enhanced Sensor Data Collection")
    print("=" * 50)
    
    # Create a test time
    test_time = datetime(2025, 10, 4, 12, 0)  # Noon on a sunny day
    
    # Test sensor collector directly
    print("\n1. Testing SensorDataCollector directly:")
    sensor_collector = SensorDataCollector("test_location")
    
    # Test general sensor data
    general_data = sensor_collector.get_all_sensor_data(test_time, "test_device", 100.0)
    print(f"General sensor data keys: {len(general_data)}")
    print(f"Sample data: irradiance={general_data['irradiance']:.1f} W/m², "
          f"wind_speed={general_data['wind_speed']:.1f} m/s, "
          f"temperature={general_data['temperature']:.1f}°C")
    
    # Test battery sensor data
    battery_data = sensor_collector.get_battery_sensor_data(test_time, 50.0)
    print(f"\nBattery sensor data keys: {len(battery_data)}")
    print(f"Battery-specific: battery_temperature={battery_data['battery_temperature']:.1f}°C, "
          f"thermal_runaway_risk={battery_data['thermal_runaway_risk']:.1f}")
    
    # Test solar generation sensor data
    solar_data = sensor_collector.get_generation_sensor_data(test_time, "solar", 200.0)
    print(f"\nSolar sensor data keys: {len(solar_data)}")
    print(f"Solar-specific: panel_temperature={solar_data['panel_temperature']:.1f}°C, "
          f"panel_soiling={solar_data['panel_soiling']:.1f}%, "
          f"tracking_angle={solar_data['tracking_angle']:.1f}°")
    
    # Test wind generation sensor data
    wind_data = sensor_collector.get_generation_sensor_data(test_time, "wind", 150.0)
    print(f"\nWind sensor data keys: {len(wind_data)}")
    print(f"Wind-specific: rotor_speed={wind_data['rotor_speed']:.1f} RPM, "
          f"blade_angle={wind_data['blade_angle']:.1f}°, "
          f"nacelle_direction={wind_data['nacelle_direction']:.1f}°")
    
    # Test house consumer sensor data
    house_data = sensor_collector.get_consumer_sensor_data(test_time, "house", 5.0)
    print(f"\nHouse sensor data keys: {len(house_data)}")
    print(f"House-specific: indoor_temperature={house_data['indoor_temperature']:.1f}°C, "
          f"hvac_status={house_data['hvac_status']}, "
          f"occupancy_detected={house_data['occupancy_detected']}")
    
    # Test industry consumer sensor data
    industry_data = sensor_collector.get_consumer_sensor_data(test_time, "industry", 50.0)
    print(f"\nIndustry sensor data keys: {len(industry_data)}")
    print(f"Industry-specific: production_line_status={industry_data['production_line_status']}, "
          f"shift_active={industry_data['shift_active']}, "
          f"safety_alarms={industry_data['safety_alarms']}")
    
    # Test EV charging sensor data
    ev_data = sensor_collector.get_consumer_sensor_data(test_time, "ev_charging", 7.2)
    print(f"\nEV charging sensor data keys: {len(ev_data)}")
    print(f"EV charging-specific: charging_power={ev_data['charging_power']:.1f} kW, "
          f"connector_status={ev_data['connector_status']}, "
          f"charging_efficiency={ev_data['charging_efficiency']:.3f}")

def test_device_publish_states():
    """Test the actual device publish states with sensor data"""
    print("\n\n2. Testing Device Publish States with Sensor Data:")
    print("=" * 50)
    
    test_time = datetime(2025, 10, 4, 12, 0)
    
    # Create a battery
    battery = BaseBattery(
        capacity_kwh=100.0,
        rated_voltage=400.0,
        rated_power_kw=50.0,
        device_id="test_battery"
    )
    battery.charge(25.0, 1.0, test_time)
    
    # Create a house
    def house_demand(time):
        return 5.0
    
    house = House(
        demand_function=house_demand,
        num_occupants=3,
        appliances={"lighting": 0.5, "hvac": 2.0, "appliances": 1.0},
        id="test_house"
    )
    house.get_demand(test_time)
    
    # Create a solar plant
    solar_plant = SolarPowerPlant(
        capacity_kW=500.0,
        location="test_solar_site",
        panel_area_m2=2500.0
    )
    solar_plant.generate(sim_time=test_time, sunlight_factor=0.8)
    
    # Create a wind plant
    wind_plant = WindPowerPlant(
        capacity_kW=1000.0,
        location="test_wind_site",
        rotor_diameter_m=80.0
    )
    wind_plant.generate(sim_time=test_time, wind_speed_m_s=8.0)
    
    print("Devices created and simulated. Check MQTT topics for enhanced sensor data:")
    print("- batteries/test_battery/state")
    print("- consumers/test_house/state") 
    print("- generation/test_solar_site/state")
    print("- generation/test_wind_site/state")
    print("\nEach message now includes comprehensive sensor data!")

def show_sensor_data_structure():
    """Show the structure of sensor data being sent"""
    print("\n\n3. Sensor Data Structure:")
    print("=" * 50)
    
    sensor_collector = SensorDataCollector("demo_location")
    test_time = datetime(2025, 10, 4, 12, 0)
    
    # Get sample data
    sample_data = sensor_collector.get_all_sensor_data(test_time, "demo_device", 100.0)
    
    print("Environmental Sensors:")
    env_keys = ['irradiance', 'wind_speed', 'temperature', 'humidity', 'pressure', 
                'cloud_cover', 'precipitation', 'visibility']
    for key in env_keys:
        if key in sample_data:
            print(f"  - {key}: {sample_data[key]}")
    
    print("\nGrid Sensors:")
    grid_keys = ['grid_frequency', 'voltage_quality', 'power_quality']
    for key in grid_keys:
        if key in sample_data:
            print(f"  - {key}: {sample_data[key]}")
    
    print("\nEquipment Sensors:")
    equip_keys = ['vibration', 'noise_level', 'maintenance_indicators']
    for key in equip_keys:
        if key in sample_data:
            print(f"  - {key}: {sample_data[key]}")
    
    print("\nMetadata:")
    meta_keys = ['location', 'device_type', 'sensor_timestamp']
    for key in meta_keys:
        if key in sample_data:
            print(f"  - {key}: {sample_data[key]}")

if __name__ == "__main__":
    test_sensor_data()
    test_device_publish_states()
    show_sensor_data_structure()
    
    print("\n" + "=" * 50)
    print("Enhanced sensor data collection is now active!")
    print("All battery, consumer, and generation data now includes:")
    print("- Environmental sensors (irradiance, wind speed, temperature, etc.)")
    print("- Grid sensors (frequency, power quality, voltage quality)")
    print("- Equipment sensors (vibration, noise, maintenance indicators)")
    print("- Device-specific sensors (battery temperature, panel soiling, etc.)")
    print("=" * 50)
