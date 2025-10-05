# Corrected Weighted SoC Queries for InfluxDB

Based on your actual database schema, here are the corrected queries using the proper field names.

## Database Schema Analysis
From your error message, the available fields are:
- `soc` - State of Charge percentage
- `remaining_capacity` - Remaining capacity (instead of `capacity_kwh`)
- `device_id` - Device identifier
- `device_type` - Type of device
- `power` - Current power
- `voltage` - Voltage
- `current` - Current
- And many sensor fields...

## 1. Overall Weighted SoC for All Batteries

```sql
SELECT 
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as weighted_soc_percentage
FROM batteries_state 
WHERE remaining_capacity > 0
  AND soc IS NOT NULL
GROUP BY time(1m)
```

## 2. Grid BESS Weighted SoC

```sql
SELECT 
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as grid_bess_weighted_soc
FROM batteries_state 
WHERE remaining_capacity > 0
  AND soc IS NOT NULL
  AND device_id =~ /.*GridBESS.*/
GROUP BY time(1m)
```

## 3. Solar Plant BESS Weighted SoC

```sql
SELECT 
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as solar_bess_weighted_soc
FROM batteries_state 
WHERE remaining_capacity > 0
  AND soc IS NOT NULL
  AND device_id =~ /.*Solar.*/
GROUP BY time(1m)
```

## 4. Wind Plant BESS Weighted SoC

```sql
SELECT 
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as wind_bess_weighted_soc
FROM batteries_state 
WHERE remaining_capacity > 0
  AND soc IS NOT NULL
  AND device_id =~ /.*Wind.*/
GROUP BY time(1m)
```

## 5. Combined Solar and Wind BESS Weighted SoC

```sql
SELECT 
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as renewable_bess_weighted_soc
FROM batteries_state 
WHERE remaining_capacity > 0
  AND soc IS NOT NULL
  AND (device_id =~ /.*Solar.*/ OR device_id =~ /.*Wind.*/)
GROUP BY time(1m)
```

## 6. All BESS (Grid + Solar + Wind) Weighted SoC

```sql
SELECT 
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as all_bess_weighted_soc
FROM batteries_state 
WHERE remaining_capacity > 0
  AND soc IS NOT NULL
  AND (device_id =~ /.*GridBESS.*/ OR device_id =~ /.*Solar.*/ OR device_id =~ /.*Wind.*/)
GROUP BY time(1m)
```

## 7. Real-time Overall Weighted SoC (Latest Values)

```sql
SELECT 
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as current_weighted_soc
FROM (
  SELECT 
    soc, 
    remaining_capacity,
    ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY time DESC) as rn
  FROM batteries_state 
  WHERE remaining_capacity > 0
    AND soc IS NOT NULL
    AND time >= now() - 5m
) 
WHERE rn = 1
```

## 8. Device Type Breakdown with Weighted SoC

```sql
SELECT 
  CASE 
    WHEN device_id =~ /.*GridBESS.*/ THEN 'Grid BESS'
    WHEN device_id =~ /.*Solar.*/ THEN 'Solar BESS'
    WHEN device_id =~ /.*Wind.*/ THEN 'Wind BESS'
    WHEN device_id =~ /.*EV.*/ THEN 'EV Battery'
    ELSE 'Other'
  END as battery_type,
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as weighted_soc,
  SUM(remaining_capacity) as total_remaining_capacity,
  COUNT(*) as battery_count
FROM batteries_state 
WHERE remaining_capacity > 0
  AND soc IS NOT NULL
  AND time >= now() - 1h
GROUP BY battery_type, time(1m)
ORDER BY time, total_remaining_capacity DESC
```

## 9. Grafana Dashboard Query

```sql
SELECT 
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as "Weighted SoC %"
FROM batteries_state 
WHERE $timeFilter
  AND remaining_capacity > 0
  AND soc IS NOT NULL
GROUP BY time($__interval)
ORDER BY time
```

## 10. Alert Query (Low SoC Detection)

```sql
SELECT 
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as weighted_soc
FROM batteries_state 
WHERE remaining_capacity > 0
  AND soc IS NOT NULL
  AND time >= now() - 1m
HAVING weighted_soc < 20
```

## 11. Historical Weighted SoC Trends

```sql
SELECT 
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as weighted_soc_trend
FROM batteries_state 
WHERE remaining_capacity > 0
  AND soc IS NOT NULL
  AND time >= now() - 24h
GROUP BY time(5m)
ORDER BY time
```

## 12. Detailed Battery Information

```sql
SELECT 
  device_id,
  soc,
  remaining_capacity,
  soc * remaining_capacity as weighted_contribution,
  power,
  voltage,
  current,
  mode
FROM batteries_state 
WHERE remaining_capacity > 0
  AND soc IS NOT NULL
  AND time >= now() - 1h
ORDER BY time DESC, remaining_capacity DESC
```

## 13. Capacity-Weighted SoC by Device Type (Latest)

```sql
SELECT 
  CASE 
    WHEN device_id =~ /.*GridBESS.*/ THEN 'Grid BESS'
    WHEN device_id =~ /.*Solar.*/ THEN 'Solar BESS'
    WHEN device_id =~ /.*Wind.*/ THEN 'Wind BESS'
    ELSE 'Other'
  END as battery_type,
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as weighted_soc,
  SUM(remaining_capacity) as total_capacity,
  AVG(soc) as avg_soc,
  MIN(soc) as min_soc,
  MAX(soc) as max_soc
FROM batteries_state 
WHERE remaining_capacity > 0
  AND soc IS NOT NULL
  AND time >= now() - 5m
GROUP BY battery_type
ORDER BY total_capacity DESC
```

## Key Changes Made

1. **Field Name**: Changed `capacity_kwh` to `remaining_capacity`
2. **Time Filtering**: Added proper time filtering for better performance
3. **Device Filtering**: Used regex patterns to identify different battery types
4. **Error Handling**: Added NULL checks for both `soc` and `remaining_capacity`

## Usage Notes

- Replace `time(1m)` with your desired grouping interval
- Adjust time ranges (`now() - 1h`, `now() - 24h`, etc.) as needed
- Use `$timeFilter` for Grafana dashboards
- Modify device ID patterns based on your actual naming convention

## Testing

Start with the simple query to verify it works:

```sql
SELECT 
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as weighted_soc_percentage
FROM batteries_state 
WHERE remaining_capacity > 0
  AND soc IS NOT NULL
  AND time >= now() - 1h
GROUP BY time(1m)
LIMIT 10
```
