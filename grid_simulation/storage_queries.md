# Battery Storage Queries for InfluxDB

Based on your existing query structure, here are different variations to get total storage information.

## 1. Total Storage Capacity (Sum of All Remaining Capacity)

```sql
SELECT 
  time,
  SUM(remaining_capacity) as total_storage_kWh,
  SUM(CASE WHEN power > 0 THEN power ELSE 0 END) as total_charging_kW,
  SUM(CASE WHEN power < 0 THEN ABS(power) ELSE 0 END) as total_discharging_kW
FROM batteries_state 
WHERE remaining_capacity > 0
GROUP BY time
ORDER BY time
```

## 2. Total Storage with Weighted SoC

```sql
SELECT 
  time,
  SUM(remaining_capacity) as total_storage_kWh,
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as weighted_soc_percentage,
  SUM(CASE WHEN power > 0 THEN power ELSE 0 END) as total_charging_kW,
  SUM(CASE WHEN power < 0 THEN ABS(power) ELSE 0 END) as total_discharging_kW
FROM batteries_state 
WHERE remaining_capacity > 0
  AND soc IS NOT NULL
GROUP BY time
ORDER BY time
```

## 3. Storage by Battery Type

```sql
SELECT 
  time,
  CASE 
    WHEN device_id =~ /.*GridBESS.*/ THEN 'Grid BESS'
    WHEN device_id =~ /.*Solar.*/ THEN 'Solar BESS'
    WHEN device_id =~ /.*Wind.*/ THEN 'Wind BESS'
    WHEN device_id =~ /.*EV.*/ THEN 'EV Battery'
    ELSE 'Other'
  END as battery_type,
  SUM(remaining_capacity) as storage_kWh,
  SUM(CASE WHEN power > 0 THEN power ELSE 0 END) as charging_kW,
  SUM(CASE WHEN power < 0 THEN ABS(power) ELSE 0 END) as discharging_kW
FROM batteries_state 
WHERE remaining_capacity > 0
GROUP BY time, battery_type
ORDER BY time, storage_kWh DESC
```

## 4. Total Storage with Individual Battery Details

```sql
SELECT 
  time,
  device_id,
  remaining_capacity as storage_kWh,
  soc as soc_percentage,
  CASE WHEN power > 0 THEN power ELSE 0 END as charging_kW,
  CASE WHEN power < 0 THEN ABS(power) ELSE 0 END as discharging_kW,
  mode
FROM batteries_state 
WHERE remaining_capacity > 0
ORDER BY time, remaining_capacity DESC
```

## 5. Storage Summary with Statistics

```sql
SELECT 
  time,
  SUM(remaining_capacity) as total_storage_kWh,
  AVG(remaining_capacity) as avg_storage_per_battery,
  MIN(remaining_capacity) as min_storage,
  MAX(remaining_capacity) as max_storage,
  COUNT(*) as active_batteries,
  SUM(CASE WHEN power > 0 THEN power ELSE 0 END) as total_charging_kW,
  SUM(CASE WHEN power < 0 THEN ABS(power) ELSE 0 END) as total_discharging_kW
FROM batteries_state 
WHERE remaining_capacity > 0
GROUP BY time
ORDER BY time
```

## 6. Storage Efficiency (Charging vs Discharging)

```sql
SELECT 
  time,
  SUM(remaining_capacity) as total_storage_kWh,
  SUM(CASE WHEN power > 0 THEN power ELSE 0 END) as total_charging_kW,
  SUM(CASE WHEN power < 0 THEN ABS(power) ELSE 0 END) as total_discharging_kW,
  SUM(CASE WHEN power > 0 THEN power ELSE 0 END) - SUM(CASE WHEN power < 0 THEN ABS(power) ELSE 0 END) as net_charging_kW,
  CASE 
    WHEN SUM(CASE WHEN power > 0 THEN power ELSE 0 END) > 0 
    THEN SUM(CASE WHEN power < 0 THEN ABS(power) ELSE 0 END) / SUM(CASE WHEN power > 0 THEN power ELSE 0 END) * 100
    ELSE 0 
  END as discharge_efficiency_percentage
FROM batteries_state 
WHERE remaining_capacity > 0
GROUP BY time
ORDER BY time
```

## 7. Real-time Storage Status

```sql
SELECT 
  time,
  SUM(remaining_capacity) as total_storage_kWh,
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as weighted_soc_percentage,
  SUM(CASE WHEN power > 0 THEN power ELSE 0 END) as total_charging_kW,
  SUM(CASE WHEN power < 0 THEN ABS(power) ELSE 0 END) as total_discharging_kW,
  SUM(CASE WHEN mode = 'charging' THEN 1 ELSE 0 END) as batteries_charging,
  SUM(CASE WHEN mode = 'discharging' THEN 1 ELSE 0 END) as batteries_discharging,
  SUM(CASE WHEN mode = 'idle' THEN 1 ELSE 0 END) as batteries_idle
FROM batteries_state 
WHERE remaining_capacity > 0
  AND soc IS NOT NULL
GROUP BY time
ORDER BY time
```

## 8. Storage Utilization Rate

```sql
SELECT 
  time,
  SUM(remaining_capacity) as current_storage_kWh,
  -- Assuming you have a total_capacity field or can calculate it
  -- SUM(total_capacity) as total_capacity_kWh,
  -- SUM(remaining_capacity) / SUM(total_capacity) * 100 as utilization_percentage,
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as weighted_soc_percentage,
  SUM(CASE WHEN power > 0 THEN power ELSE 0 END) as total_charging_kW,
  SUM(CASE WHEN power < 0 THEN ABS(power) ELSE 0 END) as total_discharging_kW
FROM batteries_state 
WHERE remaining_capacity > 0
  AND soc IS NOT NULL
GROUP BY time
ORDER BY time
```

## 9. Grafana Dashboard Query

```sql
SELECT 
  time,
  SUM(remaining_capacity) as "Total Storage (kWh)",
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as "Weighted SoC %",
  SUM(CASE WHEN power > 0 THEN power ELSE 0 END) as "Charging (kW)",
  SUM(CASE WHEN power < 0 THEN ABS(power) ELSE 0 END) as "Discharging (kW)"
FROM batteries_state 
WHERE $timeFilter
  AND remaining_capacity > 0
  AND soc IS NOT NULL
GROUP BY time($__interval)
ORDER BY time
```

## 10. Storage Trends Over Time

```sql
SELECT 
  time,
  SUM(remaining_capacity) as total_storage_kWh,
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as weighted_soc_percentage,
  SUM(CASE WHEN power > 0 THEN power ELSE 0 END) as total_charging_kW,
  SUM(CASE WHEN power < 0 THEN ABS(power) ELSE 0 END) as total_discharging_kW,
  -- Calculate storage change rate
  SUM(CASE WHEN power > 0 THEN power ELSE 0 END) - SUM(CASE WHEN power < 0 THEN ABS(power) ELSE 0 END) as net_storage_change_kW
FROM batteries_state 
WHERE remaining_capacity > 0
  AND soc IS NOT NULL
  AND time >= now() - 24h
GROUP BY time(5m)
ORDER BY time
```

## Key Fields Explained

- **`remaining_capacity`**: Current stored energy in kWh
- **`soc`**: State of Charge percentage (0-100%)
- **`power`**: Positive = charging, Negative = discharging
- **`mode`**: Battery operation mode (charging, discharging, idle)

## Usage Recommendations

1. **For Real-time Monitoring**: Use query #7
2. **For Historical Analysis**: Use query #10
3. **For Grafana Dashboards**: Use query #9
4. **For Detailed Breakdown**: Use query #3 or #4
5. **For Efficiency Analysis**: Use query #6

Choose the query that best fits your specific use case!
