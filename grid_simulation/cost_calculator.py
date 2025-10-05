import json
import os
from datetime import datetime, time
from typing import Dict, Any, Optional

class CostCalculator:
    """Utility class for calculating costs across all grid operations"""
    
    def __init__(self, config_path: str = "cost_config.json"):
        """Initialize cost calculator with configuration file"""
        self.config_path = config_path
        self.cost_config = self._load_cost_config()
        
    def _load_cost_config(self) -> Dict[str, Any]:
        """Load cost configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Cost config file {self.config_path} not found. Using default costs.")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            print(f"Error parsing cost config file: {e}. Using default costs.")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default cost configuration if file is not found"""
        return {
            "cost_config": {
                "currency": "INR",
                "unit": "per_kWh",
                "costs": {
                    "battery_operations": {
                        "charging_cost_per_kwh": 6.50,
                        "discharging_cost_per_kwh": 0.50,
                        "storage_cost_per_kwh_hour": 0.10
                    },
                    "generation": {
                        "solar_generation_cost_per_kwh": 2.50,
                        "wind_generation_cost_per_kwh": 3.20,
                        "external_grid_cost_per_kwh": 8.00
                    },
                    "grid_operations": {
                        "transmission_cost_per_kwh": 0.80,
                        "distribution_cost_per_kwh": 1.20,
                        "substation_cost_per_kwh": 0.30
                    },
                    "consumer_operations": {
                        "house_consumption_cost_per_kwh": 7.50,
                        "industry_consumption_cost_per_kwh": 6.80,
                        "ev_charging_cost_per_kwh": 8.50
                    }
                },
                "time_of_day_multipliers": {
                    "peak_hours": {"start": "18:00", "end": "22:00", "multiplier": 1.5},
                    "off_peak_hours": {"start": "22:00", "end": "06:00", "multiplier": 0.7},
                    "normal_hours": {"multiplier": 1.0}
                },
                "seasonal_adjustments": {
                    "summer": {"months": ["April", "May", "June", "July", "August", "September"], "multiplier": 1.2},
                    "winter": {"months": ["October", "November", "December", "January", "February", "March"], "multiplier": 0.9}
                }
            }
        }
    
    def _get_time_multiplier(self, current_time: Optional[datetime] = None) -> float:
        """Calculate time-of-day multiplier based on current time"""
        if current_time is None:
            current_time = datetime.now()
        
        current_hour = current_time.hour
        current_minute = current_time.minute
        current_time_str = f"{current_hour:02d}:{current_minute:02d}"
        
        # Check peak hours (18:00-22:00)
        if "18:00" <= current_time_str <= "22:00":
            return self.cost_config["cost_config"]["time_of_day_multipliers"]["peak_hours"]["multiplier"]
        
        # Check off-peak hours (22:00-06:00)
        if current_time_str >= "22:00" or current_time_str <= "06:00":
            return self.cost_config["cost_config"]["time_of_day_multipliers"]["off_peak_hours"]["multiplier"]
        
        # Normal hours
        return self.cost_config["cost_config"]["time_of_day_multipliers"]["normal_hours"]["multiplier"]
    
    def _get_seasonal_multiplier(self, current_time: Optional[datetime] = None) -> float:
        """Calculate seasonal multiplier based on current time"""
        if current_time is None:
            current_time = datetime.now()
        
        current_month = current_time.strftime("%B")
        
        # Check summer months
        summer_months = self.cost_config["cost_config"]["seasonal_adjustments"]["summer"]["months"]
        if current_month in summer_months:
            return self.cost_config["cost_config"]["seasonal_adjustments"]["summer"]["multiplier"]
        
        # Winter months
        return self.cost_config["cost_config"]["seasonal_adjustments"]["winter"]["multiplier"]
    
    def calculate_battery_charging_cost(self, energy_kwh: float, duration_h: float, 
                                      current_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Calculate cost for battery charging operation"""
        base_cost_per_kwh = self.cost_config["cost_config"]["costs"]["battery_operations"]["charging_cost_per_kwh"]
        time_multiplier = self._get_time_multiplier(current_time)
        seasonal_multiplier = self._get_seasonal_multiplier(current_time)
        
        total_multiplier = time_multiplier * seasonal_multiplier
        cost_per_kwh = base_cost_per_kwh * total_multiplier
        total_cost = energy_kwh * cost_per_kwh
        
        return {
            "operation": "battery_charging",
            "energy_kwh": energy_kwh,
            "duration_h": duration_h,
            "base_cost_per_kwh": base_cost_per_kwh,
            "time_multiplier": time_multiplier,
            "seasonal_multiplier": seasonal_multiplier,
            "final_cost_per_kwh": cost_per_kwh,
            "total_cost_inr": round(total_cost, 2),
            "currency": "INR"
        }
    
    def calculate_battery_discharging_cost(self, energy_kwh: float, duration_h: float,
                                         current_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Calculate cost for battery discharging operation"""
        base_cost_per_kwh = self.cost_config["cost_config"]["costs"]["battery_operations"]["discharging_cost_per_kwh"]
        time_multiplier = self._get_time_multiplier(current_time)
        seasonal_multiplier = self._get_seasonal_multiplier(current_time)
        
        total_multiplier = time_multiplier * seasonal_multiplier
        cost_per_kwh = base_cost_per_kwh * total_multiplier
        total_cost = energy_kwh * cost_per_kwh
        
        return {
            "operation": "battery_discharging",
            "energy_kwh": energy_kwh,
            "duration_h": duration_h,
            "base_cost_per_kwh": base_cost_per_kwh,
            "time_multiplier": time_multiplier,
            "seasonal_multiplier": seasonal_multiplier,
            "final_cost_per_kwh": cost_per_kwh,
            "total_cost_inr": round(total_cost, 2),
            "currency": "INR"
        }
    
    def calculate_battery_storage_cost(self, energy_kwh: float, duration_h: float,
                                     current_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Calculate cost for battery storage operation"""
        base_cost_per_kwh_hour = self.cost_config["cost_config"]["costs"]["battery_operations"]["storage_cost_per_kwh_hour"]
        time_multiplier = self._get_time_multiplier(current_time)
        seasonal_multiplier = self._get_seasonal_multiplier(current_time)
        
        total_multiplier = time_multiplier * seasonal_multiplier
        cost_per_kwh_hour = base_cost_per_kwh_hour * total_multiplier
        total_cost = energy_kwh * duration_h * cost_per_kwh_hour
        
        return {
            "operation": "battery_storage",
            "energy_kwh": energy_kwh,
            "duration_h": duration_h,
            "base_cost_per_kwh_hour": base_cost_per_kwh_hour,
            "time_multiplier": time_multiplier,
            "seasonal_multiplier": seasonal_multiplier,
            "final_cost_per_kwh_hour": cost_per_kwh_hour,
            "total_cost_inr": round(total_cost, 2),
            "currency": "INR"
        }
    
    def calculate_generation_cost(self, energy_kwh: float, generation_type: str,
                                current_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Calculate cost for power generation"""
        cost_key = f"{generation_type}_generation_cost_per_kwh"
        base_cost_per_kwh = self.cost_config["cost_config"]["costs"]["generation"][cost_key]
        time_multiplier = self._get_time_multiplier(current_time)
        seasonal_multiplier = self._get_seasonal_multiplier(current_time)
        
        total_multiplier = time_multiplier * seasonal_multiplier
        cost_per_kwh = base_cost_per_kwh * total_multiplier
        total_cost = energy_kwh * cost_per_kwh
        
        return {
            "operation": f"{generation_type}_generation",
            "energy_kwh": energy_kwh,
            "base_cost_per_kwh": base_cost_per_kwh,
            "time_multiplier": time_multiplier,
            "seasonal_multiplier": seasonal_multiplier,
            "final_cost_per_kwh": cost_per_kwh,
            "total_cost_inr": round(total_cost, 2),
            "currency": "INR"
        }
    
    def calculate_grid_operation_cost(self, energy_kwh: float, operation_type: str,
                                    current_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Calculate cost for grid operations (transmission, distribution, substation)"""
        cost_key = f"{operation_type}_cost_per_kwh"
        base_cost_per_kwh = self.cost_config["cost_config"]["costs"]["grid_operations"][cost_key]
        time_multiplier = self._get_time_multiplier(current_time)
        seasonal_multiplier = self._get_seasonal_multiplier(current_time)
        
        total_multiplier = time_multiplier * seasonal_multiplier
        cost_per_kwh = base_cost_per_kwh * total_multiplier
        total_cost = energy_kwh * cost_per_kwh
        
        return {
            "operation": f"grid_{operation_type}",
            "energy_kwh": energy_kwh,
            "base_cost_per_kwh": base_cost_per_kwh,
            "time_multiplier": time_multiplier,
            "seasonal_multiplier": seasonal_multiplier,
            "final_cost_per_kwh": cost_per_kwh,
            "total_cost_inr": round(total_cost, 2),
            "currency": "INR"
        }
    
    def calculate_consumer_cost(self, energy_kwh: float, consumer_type: str,
                              current_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Calculate cost for consumer operations"""
        cost_key = f"{consumer_type}_consumption_cost_per_kwh"
        base_cost_per_kwh = self.cost_config["cost_config"]["costs"]["consumer_operations"][cost_key]
        time_multiplier = self._get_time_multiplier(current_time)
        seasonal_multiplier = self._get_seasonal_multiplier(current_time)
        
        total_multiplier = time_multiplier * seasonal_multiplier
        cost_per_kwh = base_cost_per_kwh * total_multiplier
        total_cost = energy_kwh * cost_per_kwh
        
        return {
            "operation": f"{consumer_type}_consumption",
            "energy_kwh": energy_kwh,
            "base_cost_per_kwh": base_cost_per_kwh,
            "time_multiplier": time_multiplier,
            "seasonal_multiplier": seasonal_multiplier,
            "final_cost_per_kwh": cost_per_kwh,
            "total_cost_inr": round(total_cost, 2),
            "currency": "INR"
        }
    
    def calculate_external_grid_cost(self, energy_kwh: float, 
                                   current_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Calculate cost for taking power from external grid"""
        return self.calculate_generation_cost(energy_kwh, "external_grid", current_time)
