# Cost Integration Summary

This document summarizes the cost integration features added to the grid simulation system.

## Overview

The system now includes comprehensive cost tracking for all battery operations, generation, and grid interactions. All costs are calculated in Indian Rupees (INR) and include time-of-day and seasonal multipliers for realistic pricing.

## Files Added/Modified

### New Files
- `cost_config.json` - Configuration file with Indian Rupee costs and multipliers
- `cost_calculator.py` - Utility class for calculating costs across all operations
- `test_cost_integration.py` - Test script to demonstrate cost integration
- `COST_INTEGRATION_SUMMARY.md` - This documentation file

### Modified Files
- `batteries/battery_base.py` - Added cost tracking for charging, discharging, and storage
- `generation/generation_base.py` - Added cost tracking for power generation
- `generation/solar_power_plant.py` - Set generation type and integrated cost data
- `generation/wind_power_plant.py` - Set generation type and integrated cost data
- `generation/external.py` - Set generation type and integrated cost data
- `grid/grid_base.py` - Added cost tracking for grid operations
- `grid/substation.py` - Set operation type for cost calculation
- `grid/transformer.py` - Set operation type for cost calculation
- `grid/inverter.py` - Set operation type for cost calculation
- `consumers/consumer_base.py` - Added cost tracking for consumption
- `consumers/house.py` - Set consumer type and integrated cost data
- `consumers/industry.py` - Set consumer type and integrated cost data
- `consumers/ev_charging_station.py` - Set consumer type and integrated cost data
- `simulation.py` - Added external grid cost tracking and storage cost calculations

## Cost Configuration

### Base Costs (per kWh)
- **Battery Operations:**
  - Charging: ₹6.50/kWh
  - Discharging: ₹0.50/kWh
  - Storage: ₹0.10/kWh/hour

- **Generation:**
  - Solar: ₹2.50/kWh
  - Wind: ₹3.20/kWh
  - External Grid: ₹8.00/kWh

- **Grid Operations:**
  - Transmission: ₹0.80/kWh
  - Distribution: ₹1.20/kWh
  - Substation: ₹0.30/kWh

- **Consumer Operations:**
  - House: ₹7.50/kWh
  - Industry: ₹6.80/kWh
  - EV Charging: ₹8.50/kWh

### Time-of-Day Multipliers
- **Peak Hours (18:00-22:00):** 1.5x
- **Off-Peak Hours (22:00-06:00):** 0.7x
- **Normal Hours:** 1.0x

### Seasonal Adjustments
- **Summer (Apr-Sep):** 1.2x
- **Winter (Oct-Mar):** 0.9x

## MQTT Integration

All cost data is automatically published via MQTT topics:

### Battery Topics
- `batteries/{device_id}/state` - Includes cost data for charging, discharging, storage

### Generation Topics
- `generation/{device_id}/state` - Includes cost data for power generation
- `generation_state` - Aggregated generation data with costs

### Consumer Topics
- `consumers/{device_id}/state` - Includes cost data for consumption

### Grid Topics
- `grid/{device_id}/state` - Includes cost data for grid operations
- `grid/external_grid/cost` - External grid import costs

## Cost Data Structure

Each MQTT message includes the following cost fields:

```json
{
  "total_charging_cost_inr": 65.00,
  "total_discharging_cost_inr": 4.00,
  "total_storage_cost_inr": 5.00,
  "total_operation_cost_inr": 74.00,
  "current_operation_cost_inr": 13.00,
  "currency": "INR",
  "time_multiplier": 1.5,
  "seasonal_multiplier": 1.2,
  "final_cost_per_kwh": 9.36
}
```

## Usage Examples

### Battery Operations
```python
# Charging cost is automatically calculated
battery.charge(20.0, 1.0, current_time)

# Discharging cost is automatically calculated
battery.discharge(15.0, 1.0, current_time)

# Storage cost is calculated separately
battery.calculate_storage_cost(1.0, current_time)

# Get total costs
costs = battery.get_total_costs()
```

### Generation Operations
```python
# Generation cost is automatically calculated
solar_plant.generate(sunlight_factor=0.8, sim_time=current_time)

# Get total costs
costs = solar_plant.get_total_costs()
```

### Consumer Operations
```python
# Consumption cost is automatically calculated
house.get_demand(current_time)

# Get total costs
costs = house.get_total_costs()
```

## Dashboard Integration

The cost data is designed to be easily integrated into dashboards:

1. **Real-time Cost Monitoring:** All MQTT topics include current operation costs
2. **Historical Cost Tracking:** Total costs are accumulated over time
3. **Cost Breakdown:** Separate tracking for different operation types
4. **Time-based Analysis:** Cost multipliers for different time periods
5. **Seasonal Analysis:** Cost adjustments for different seasons

## Testing

Run the test script to verify cost integration:

```bash
cd grid_simulation
python test_cost_integration.py
```

This will demonstrate:
- Cost calculator functionality
- Battery cost tracking
- Generation cost tracking
- Consumer cost tracking
- Grid component cost tracking

## Benefits

1. **Comprehensive Cost Tracking:** Every operation in the grid has associated costs
2. **Realistic Pricing:** Indian Rupee costs with time-of-day and seasonal adjustments
3. **Dashboard Ready:** All cost data is available via MQTT for dashboard integration
4. **Modular Design:** Easy to modify costs via configuration file
5. **Detailed Breakdown:** Separate tracking for different cost components
6. **Real-time Updates:** Costs are calculated and published in real-time

## Future Enhancements

Potential future improvements:
- Dynamic pricing based on market conditions
- Carbon cost tracking
- Maintenance cost integration
- Revenue tracking for generation
- Cost optimization algorithms
- Historical cost analysis and reporting
