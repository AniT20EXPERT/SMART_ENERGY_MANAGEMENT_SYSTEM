"""
Sensor data collection and management for grid simulation.
Provides environmental and equipment sensor data for all grid components.
"""

import random
import math
from datetime import datetime
from typing import Dict, Any, Optional

class EnvironmentalSensors:
    """Environmental sensor data collection"""
    
    def __init__(self, location: str = "default"):
        self.location = location
        self.base_irradiance = 1000.0  # W/m²
        self.base_wind_speed = 5.0     # m/s
        self.base_temperature = 25.0  # °C
        self.base_humidity = 60.0     # %
        self.base_pressure = 1013.25  # hPa
        
    def get_irradiance(self, time: datetime, cloud_cover: float = 0.0) -> float:
        """Get solar irradiance in W/m²"""
        if time is None:
            return 0.0
        
        # Day of year for seasonal variation
        day_of_year = time.timetuple().tm_yday
        
        # Hour of day for diurnal variation
        hour = time.hour + time.minute / 60.0
        
        # Solar angle calculation (simplified)
        solar_angle = math.sin(math.pi * (hour - 6) / 12) if 6 <= hour < 18 else 0
        
        # Seasonal variation
        seasonal_factor = 1.0 + 0.3 * math.cos(2 * math.pi * (day_of_year - 172) / 365)
        
        # Cloud cover effect (cloud_cover is 0-100%, so divide by 100)
        cloud_factor = 1.0 - (cloud_cover / 100.0 * 0.7)
        
        # Random weather variation
        weather_factor = random.uniform(0.8, 1.2)
        
        irradiance = self.base_irradiance * solar_angle * seasonal_factor * cloud_factor * weather_factor
        return max(0, irradiance)
    
    def get_wind_speed(self, time: datetime, base_speed: float = None) -> float:
        """Get wind speed in m/s"""
        if time is None:
            return self.base_wind_speed
            
        if base_speed is None:
            base_speed = self.base_wind_speed
            
        # Daily variation
        hour = time.hour
        daily_variation = 1.0 + 0.4 * math.sin(2 * math.pi * hour / 24)
        
        # Random fluctuation with persistence
        persistence = 0.8
        if hasattr(self, '_last_wind_speed'):
            base_speed = persistence * self._last_wind_speed + (1 - persistence) * base_speed
        self._last_wind_speed = base_speed
        
        # Add random variation
        wind_speed = base_speed * daily_variation * random.uniform(0.7, 1.3)
        return max(0, wind_speed)
    
    def get_temperature(self, time: datetime) -> float:
        """Get ambient temperature in °C"""
        if time is None:
            return self.base_temperature
            
        # Daily temperature cycle
        hour = time.hour + time.minute / 60.0
        daily_cycle = 1.0 + 0.3 * math.sin(2 * math.pi * (hour - 6) / 24)
        
        # Seasonal variation
        day_of_year = time.timetuple().tm_yday
        seasonal_cycle = 1.0 + 0.2 * math.cos(2 * math.pi * (day_of_year - 172) / 365)
        
        temperature = self.base_temperature * daily_cycle * seasonal_cycle
        temperature += random.uniform(-2, 2)  # Random variation
        
        return temperature
    
    def get_humidity(self, time: datetime) -> float:
        """Get relative humidity in %"""
        if time is None:
            return self.base_humidity
            
        # Inverse relationship with temperature
        temp = self.get_temperature(time)
        humidity = self.base_humidity * (1.0 - (temp - self.base_temperature) / 50.0)
        humidity += random.uniform(-10, 10)
        return max(0, min(100, humidity))
    
    def get_pressure(self, time: datetime) -> float:
        """Get atmospheric pressure in hPa"""
        if time is None:
            return self.base_pressure
            
        # Small daily variation
        hour = time.hour
        daily_variation = 1.0 + 0.01 * math.sin(2 * math.pi * hour / 24)
        
        pressure = self.base_pressure * daily_variation
        pressure += random.uniform(-5, 5)
        
        return pressure
    
    def get_cloud_cover(self, time: datetime) -> float:
        """Get cloud cover percentage (0-100%)"""
        if time is None:
            return 50.0  # Default cloud cover
            
        # Random but persistent cloud cover
        if not hasattr(self, '_cloud_cover'):
            self._cloud_cover = random.uniform(0, 100)
        
        # Gradual changes
        change = random.uniform(-5, 5)
        self._cloud_cover = max(0, min(100, self._cloud_cover + change))
        
        return self._cloud_cover
    
    def get_precipitation(self, time: datetime) -> float:
        """Get precipitation rate in mm/h"""
        if time is None:
            return 0.0
            
        cloud_cover = self.get_cloud_cover(time)
        if cloud_cover > 80:
            return random.uniform(0, 10)  # Light to moderate rain
        elif cloud_cover > 50:
            return random.uniform(0, 2)   # Light drizzle
        else:
            return 0.0
    
    def get_visibility(self, time: datetime) -> float:
        """Get visibility in km"""
        if time is None:
            return 10.0  # Default visibility
            
        precipitation = self.get_precipitation(time)
        humidity = self.get_humidity(time)
        
        # Reduced visibility due to precipitation and humidity
        visibility = 10.0  # Base visibility
        visibility *= (1.0 - precipitation / 20.0)  # Rain reduces visibility
        visibility *= (1.0 - (humidity - 50) / 200.0)  # High humidity reduces visibility
        
        return max(0.1, visibility)

class GridSensors:
    """Grid-level sensor data collection"""
    
    def __init__(self):
        self.base_frequency = 50.0  # Hz
        self.base_voltage = 230.0   # V
        
    def get_frequency(self, time: datetime, load_factor: float = 1.0) -> float:
        """Get grid frequency in Hz"""
        if time is None:
            return self.base_frequency
            
        # Frequency varies with load
        frequency = self.base_frequency * (1.0 - (load_factor - 1.0) * 0.01)
        frequency += random.uniform(-0.1, 0.1)  # Small random variation
        return frequency
    
    def get_voltage_quality(self, time: datetime) -> Dict[str, float]:
        """Get voltage quality metrics"""
        return {
            'voltage_harmonics': random.uniform(0.5, 3.0),  # THD %
            'voltage_flicker': random.uniform(0.1, 1.0),    # Pst
            'power_factor': random.uniform(0.85, 0.98),   # Power factor
            'voltage_imbalance': random.uniform(0.1, 2.0)  # %
        }
    
    def get_power_quality(self, time: datetime) -> Dict[str, float]:
        """Get power quality metrics"""
        return {
            'total_harmonic_distortion': random.uniform(1.0, 5.0),  # THD %
            'flicker_severity': random.uniform(0.1, 2.0),           # Pst
            'interruption_count': random.randint(0, 3),             # Count
            'sag_count': random.randint(0, 5),                     # Count
            'swell_count': random.randint(0, 2)                    # Count
        }

class EquipmentSensors:
    """Equipment-specific sensor data collection"""
    
    def __init__(self, equipment_type: str = "generic"):
        self.equipment_type = equipment_type
        
    def get_vibration(self, time: datetime, operating_power: float = 0.0) -> float:
        """Get vibration level in mm/s"""
        # Vibration increases with operating power
        base_vibration = 0.5
        power_factor = operating_power / 1000.0  # Normalize to kW
        vibration = base_vibration + power_factor * 0.1
        vibration += random.uniform(-0.1, 0.1)
        return max(0, vibration)
    
    def get_noise_level(self, time: datetime, operating_power: float = 0.0) -> float:
        """Get noise level in dB"""
        # Noise increases with operating power
        base_noise = 45.0
        power_factor = operating_power / 1000.0
        noise = base_noise + power_factor * 10.0
        noise += random.uniform(-2, 2)
        return max(30, noise)
    
    def get_maintenance_indicators(self, time: datetime) -> Dict[str, Any]:
        """Get maintenance-related sensor data"""
        return {
            'operating_hours': random.uniform(1000, 10000),
            'maintenance_due': random.choice([True, False]),
            'wear_level': random.uniform(0, 100),  # %
            'efficiency_degradation': random.uniform(0, 5),  # %
            'alarm_count': random.randint(0, 3)
        }

class SensorDataCollector:
    """Main sensor data collection class"""
    
    def __init__(self, location: str = "default"):
        self.environmental = EnvironmentalSensors(location)
        self.grid = GridSensors()
        self.equipment = EquipmentSensors()
        self.location = location
        
    def get_all_sensor_data(self, time: datetime, device_type: str = "generic", 
                           operating_power: float = 0.0, load_factor: float = 1.0) -> Dict[str, Any]:
        """Get comprehensive sensor data for any device"""
        
        # Environmental data
        cloud_cover = self.environmental.get_cloud_cover(time)
        sensor_data = {
            # Environmental sensors
            'irradiance': self.environmental.get_irradiance(time, cloud_cover),
            'wind_speed': self.environmental.get_wind_speed(time),
            'temperature': self.environmental.get_temperature(time),
            'humidity': self.environmental.get_humidity(time),
            'pressure': self.environmental.get_pressure(time),
            'cloud_cover': cloud_cover,
            'precipitation': self.environmental.get_precipitation(time),
            'visibility': self.environmental.get_visibility(time),
            
            # Grid sensors
            'grid_frequency': self.grid.get_frequency(time, load_factor),
            'voltage_quality': self.grid.get_voltage_quality(time),
            'power_quality': self.grid.get_power_quality(time),
            
            # Equipment sensors
            'vibration': self.equipment.get_vibration(time, operating_power),
            'noise_level': self.equipment.get_noise_level(time, operating_power),
            'maintenance_indicators': self.equipment.get_maintenance_indicators(time),
            
            # Location and metadata
            'location': self.location,
            'device_type': device_type,
            'sensor_timestamp': time.isoformat() + 'Z'
        }
        
        return sensor_data
    
    def get_battery_sensor_data(self, time: datetime, operating_power: float = 0.0) -> Dict[str, Any]:
        """Get sensor data specifically for battery systems"""
        base_data = self.get_all_sensor_data(time, "battery", operating_power)
        
        # Battery-specific sensors
        base_data.update({
            'battery_temperature': self.environmental.get_temperature(time) + random.uniform(-5, 15),
            'cooling_system_status': random.choice(['active', 'idle', 'fault']),
            'thermal_runaway_risk': random.uniform(0, 10),  # Risk score
            'electrolyte_level': random.uniform(80, 100),   # %
            'cell_imbalance': random.uniform(0, 5)          # mV
        })
        
        return base_data
    
    def get_generation_sensor_data(self, time: datetime, generation_type: str, 
                                  operating_power: float = 0.0) -> Dict[str, Any]:
        """Get sensor data specifically for generation systems"""
        base_data = self.get_all_sensor_data(time, f"generation_{generation_type}", operating_power)
        
        if generation_type == "solar":
            base_data.update({
                'panel_temperature': self.environmental.get_temperature(time) + random.uniform(10, 30),
                'panel_soiling': random.uniform(0, 20),  # %
                'tracking_angle': random.uniform(-45, 45),  # degrees
                'inverter_efficiency': random.uniform(0.92, 0.98)
            })
        elif generation_type == "wind":
            base_data.update({
                'rotor_speed': random.uniform(10, 30),  # RPM
                'blade_angle': random.uniform(0, 90),   # degrees
                'nacelle_direction': random.uniform(0, 360),  # degrees
                'turbine_efficiency': random.uniform(0.85, 0.95)
            })
        
        return base_data
    
    def get_consumer_sensor_data(self, time: datetime, consumer_type: str, 
                                operating_power: float = 0.0) -> Dict[str, Any]:
        """Get sensor data specifically for consumer systems"""
        base_data = self.get_all_sensor_data(time, f"consumer_{consumer_type}", operating_power)
        
        if consumer_type == "house":
            base_data.update({
                'indoor_temperature': self.environmental.get_temperature(time) + random.uniform(-5, 5),
                'hvac_status': random.choice(['heating', 'cooling', 'idle']),
                'appliance_count': random.randint(5, 15),
                'occupancy_detected': random.choice([True, False])
            })
        elif consumer_type == "industry":
            base_data.update({
                'production_line_status': random.choice(['active', 'idle', 'maintenance']),
                'shift_active': random.choice([True, False]),
                'equipment_count': random.randint(10, 50),
                'safety_alarms': random.randint(0, 2)
            })
        elif consumer_type == "ev_charging":
            base_data.update({
                'charging_power': operating_power,
                'connector_status': random.choice(['connected', 'disconnected', 'fault']),
                'charging_efficiency': random.uniform(0.88, 0.95),
                'session_duration': random.uniform(0, 480)  # minutes
            })
        
        return base_data
