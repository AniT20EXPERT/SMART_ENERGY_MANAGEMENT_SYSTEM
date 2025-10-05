# Battery SoC Queries for InfluxDB

This document contains InfluxDB queries to calculate overall weighted State of Charge (SoC) for different battery types in the grid simulation system.

## Query Structure

All queries assume data is stored in InfluxDB with the following structure:
- **Measurement**: `batteries_state`
- **Fields**: `soc`, `remaining_capacity`, `capacity_kwh`
- **Tags**: `device_id`, `device_type` (battery type)

## 1. Overall Weighted SoC for All Batteries

```sql
-- Calculate overall weighted SoC for all batteries
SELECT 
  SUM(soc * capacity_kwh) / SUM(capacity_kwh) as weighted_soc_percentage
FROM batteries_state 
WHERE time >= now() - 1h
  AND capacity_kwh > 0
  AND soc IS NOT NULL
GROUP BY time(1m)
```

## 2. Grid BESS Weighted SoC

```sql
-- Calculate weighted SoC for Grid BESS only
SELECT 
  SUM(soc * capacity_kwh) / SUM(capacity_kwh) as grid_bess_weighted_soc
FROM batteries_state 
WHERE time >= now() - 1h
  AND device_id =~ /.*GridBESS.*/
  AND capacity_kwh > 0
  AND soc IS NOT NULL
GROUP BY time(1m)
```

## 3. Solar Plant BESS Weighted SoC

```sql
-- Calculate weighted SoC for Solar Plant BESS
SELECT 
  SUM(soc * capacity_kwh) / SUM(capacity_kwh) as solar_bess_weighted_soc
FROM batteries_state 
WHERE time >= now() - 1h
  AND device_id =~ /.*Solar.*/
  AND capacity_kwh > 0
  AND soc IS NOT NULL
GROUP BY time(1m)
```

## 4. Wind Plant BESS Weighted SoC

```sql
-- Calculate weighted SoC for Wind Plant BESS
SELECT 
  SUM(soc * capacity_kwh) / SUM(capacity_kwh) as wind_bess_weighted_soc
FROM batteries_state 
WHERE time >= now() - 1h
  AND device_id =~ /.*Wind.*/
  AND capacity_kwh > 0
  AND soc IS NOT NULL
GROUP BY time(1m)
```

## 5. Combined Solar and Wind BESS Weighted SoC

```sql
-- Calculate weighted SoC for combined Solar and Wind BESS
SELECT 
  SUM(soc * capacity_kwh) / SUM(capacity_kwh) as renewable_bess_weighted_soc
FROM batteries_state 
WHERE time >= now() - 1h
  AND (device_id =~ /.*Solar.*/ OR device_id =~ /.*Wind.*/)
  AND capacity_kwh > 0
  AND soc IS NOT NULL
GROUP BY time(1m)
```

## 6. All BESS (Grid + Solar + Wind) Weighted SoC

```sql
-- Calculate weighted SoC for all BESS systems
SELECT 
  SUM(soc * capacity_kwh) / SUM(capacity_kwh) as all_bess_weighted_soc
FROM batteries_state 
WHERE time >= now() - 1h
  AND (device_id =~ /.*GridBESS.*/ OR device_id =~ /.*Solar.*/ OR device_id =~ /.*Wind.*/)
  AND capacity_kwh > 0
  AND soc IS NOT NULL
GROUP BY time(1m)
```

## 7. Detailed Breakdown by Battery Type

```sql
-- Detailed breakdown showing individual and weighted SoC
SELECT 
  device_id,
  soc,
  capacity_kwh,
  soc * capacity_kwh as weighted_contribution
FROM batteries_state 
WHERE time >= now() - 1h
  AND capacity_kwh > 0
  AND soc IS NOT NULL
ORDER BY time DESC, capacity_kwh DESC
```

## 8. Real-time Overall Weighted SoC (Latest Values)

```sql
-- Get the most recent weighted SoC for all batteries
SELECT 
  SUM(soc * capacity_kwh) / SUM(capacity_kwh) as current_weighted_soc
FROM (
  SELECT 
    soc, 
    capacity_kwh,
    ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY time DESC) as rn
  FROM batteries_state 
  WHERE time >= now() - 5m
    AND capacity_kwh > 0
    AND soc IS NOT NULL
) 
WHERE rn = 1
```

## 9. Historical Weighted SoC Trends

```sql
-- Historical trend of weighted SoC over the last 24 hours
SELECT 
  SUM(soc * capacity_kwh) / SUM(capacity_kwh) as weighted_soc_trend
FROM batteries_state 
WHERE time >= now() - 24h
  AND capacity_kwh > 0
  AND soc IS NOT NULL
GROUP BY time(5m)
ORDER BY time
```

## 10. Capacity-Weighted SoC with Device Type Breakdown

```sql
-- Weighted SoC broken down by device type
SELECT 
  CASE 
    WHEN device_id =~ /.*GridBESS.*/ THEN 'Grid BESS'
    WHEN device_id =~ /.*Solar.*/ THEN 'Solar BESS'
    WHEN device_id =~ /.*Wind.*/ THEN 'Wind BESS'
    ELSE 'Other'
  END as battery_type,
  SUM(soc * capacity_kwh) / SUM(capacity_kwh) as weighted_soc,
  SUM(capacity_kwh) as total_capacity
FROM batteries_state 
WHERE time >= now() - 1h
  AND capacity_kwh > 0
  AND soc IS NOT NULL
GROUP BY battery_type, time(1m)
```

## 11. Grafana Dashboard Query (Continuous)

```sql
-- For Grafana dashboard - continuous monitoring
SELECT 
  SUM(soc * capacity_kwh) / SUM(capacity_kwh) as "Weighted SoC %"
FROM batteries_state 
WHERE $timeFilter
  AND capacity_kwh > 0
  AND soc IS NOT NULL
GROUP BY time($__interval)
ORDER BY time
```

## 12. Alert Query (Low SoC Detection)

```sql
-- Alert when overall weighted SoC drops below threshold
SELECT 
  SUM(soc * capacity_kwh) / SUM(capacity_kwh) as weighted_soc
FROM batteries_state 
WHERE time >= now() - 1m
  AND capacity_kwh > 0
  AND soc IS NOT NULL
HAVING weighted_soc < 20  -- Alert if below 20%
```

## Usage Notes

### For Grafana Dashboards:
1. Use query #11 for continuous monitoring
2. Set up alerts using query #12
3. Create separate panels for different battery types using queries #2-6

### For Real-time Monitoring:
1. Use query #8 for current status
2. Use query #7 for detailed breakdown
3. Use query #9 for historical trends

### For Analysis:
1. Use query #10 for capacity analysis
2. Modify time ranges as needed (1h, 24h, 7d, etc.)
3. Adjust grouping intervals based on data frequency

## Expected Results

The queries will return:
- **Weighted SoC percentage** (0-100%)
- **Time series data** for trend analysis
- **Device-specific breakdowns** for detailed monitoring
- **Capacity-weighted calculations** for accurate representation

## Performance Optimization

For better performance with large datasets:
1. Create indexes on `device_id` and `time`
2. Use appropriate time ranges
3. Consider data retention policies
4. Use continuous queries for pre-aggregated data
