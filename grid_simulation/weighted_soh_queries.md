# Weighted Average SoH Queries for InfluxDB

Based on your database schema, here are corrected queries for calculating weighted average SoH and addressing maximum capacity parameters.

## Database Schema Analysis

From your previous error message, the available fields are:
- `remaining_capacity` - Current remaining capacity (not `power_capacity`)
- `soc` - State of Charge percentage
- `soh` - State of Health percentage
- `voltage`, `current`, `power` - Electrical parameters
- `device_id` - Device identifier

**Note**: There's no `power_capacity` field in your schema. You should use `remaining_capacity` or calculate maximum capacity from other fields.

## 1. Corrected Weighted Average SoH (Using remaining_capacity)

```sql
SELECT 
  SUM("soh" * "remaining_capacity") / SUM("remaining_capacity") as weighted_avg_soh
FROM (
  SELECT 
    "soh",
    "remaining_capacity",
    ROW_NUMBER() OVER (PARTITION BY "device_id" ORDER BY "time" DESC) as rn
  FROM "batteries_state" 
  WHERE "time" >= $__timeFrom 
    AND "time" <= $__timeTo
    AND "soh" IS NOT NULL
    AND "remaining_capacity" > 0
    AND "device_id" LIKE '%BESS%'
) t
WHERE rn = 1;
```

## 2. Weighted Average SoH with Maximum Capacity Calculation

```sql
-- Calculate maximum capacity from SoC and remaining capacity
SELECT 
  SUM("soh" * ("remaining_capacity" / ("soc" / 100.0))) / SUM("remaining_capacity" / ("soc" / 100.0)) as weighted_avg_soh,
  SUM("remaining_capacity") as total_remaining_capacity,
  SUM("remaining_capacity" / ("soc" / 100.0)) as total_max_capacity
FROM (
  SELECT 
    "soh",
    "remaining_capacity",
    "soc",
    ROW_NUMBER() OVER (PARTITION BY "device_id" ORDER BY "time" DESC) as rn
  FROM "batteries_state" 
  WHERE "time" >= $__timeFrom 
    AND "time" <= $__timeTo
    AND "soh" IS NOT NULL
    AND "remaining_capacity" > 0
    AND "soc" > 0
    AND "device_id" LIKE '%BESS%'
) t
WHERE rn = 1;
```

## 3. Weighted Average SoH by Battery Type

```sql
SELECT 
  CASE 
    WHEN "device_id" LIKE '%GridBESS%' THEN 'Grid BESS'
    WHEN "device_id" LIKE '%Solar%' THEN 'Solar BESS'
    WHEN "device_id" LIKE '%Wind%' THEN 'Wind BESS'
    ELSE 'Other BESS'
  END as battery_type,
  SUM("soh" * "remaining_capacity") / SUM("remaining_capacity") as weighted_avg_soh,
  SUM("remaining_capacity") as total_remaining_capacity,
  COUNT(*) as battery_count
FROM (
  SELECT 
    "soh",
    "remaining_capacity",
    "device_id",
    ROW_NUMBER() OVER (PARTITION BY "device_id" ORDER BY "time" DESC) as rn
  FROM "batteries_state" 
  WHERE "time" >= $__timeFrom 
    AND "time" <= $__timeTo
    AND "soh" IS NOT NULL
    AND "remaining_capacity" > 0
    AND "device_id" LIKE '%BESS%'
) t
WHERE rn = 1
GROUP BY battery_type
ORDER BY weighted_avg_soh DESC;
```

## 4. Weighted Average SoH with Capacity Statistics

```sql
SELECT 
  SUM("soh" * "remaining_capacity") / SUM("remaining_capacity") as weighted_avg_soh,
  SUM("remaining_capacity") as total_remaining_capacity,
  AVG("soh") as simple_avg_soh,
  MIN("soh") as min_soh,
  MAX("soh") as max_soh,
  COUNT(*) as battery_count
FROM (
  SELECT 
    "soh",
    "remaining_capacity",
    ROW_NUMBER() OVER (PARTITION BY "device_id" ORDER BY "time" DESC) as rn
  FROM "batteries_state" 
  WHERE "time" >= $__timeFrom 
    AND "time" <= $__timeTo
    AND "soh" IS NOT NULL
    AND "remaining_capacity" > 0
    AND "device_id" LIKE '%BESS%'
) t
WHERE rn = 1;
```

## 5. Weighted Average SoH with Maximum Capacity (Alternative Method)

```sql
-- Using power field as a proxy for capacity (if power represents rated capacity)
SELECT 
  SUM("soh" * ABS("power")) / SUM(ABS("power")) as weighted_avg_soh
FROM (
  SELECT 
    "soh",
    "power",
    ROW_NUMBER() OVER (PARTITION BY "device_id" ORDER BY "time" DESC) as rn
  FROM "batteries_state" 
  WHERE "time" >= $__timeFrom 
    AND "time" <= $__timeTo
    AND "soh" IS NOT NULL
    AND "power" IS NOT NULL
    AND "device_id" LIKE '%BESS%'
) t
WHERE rn = 1;
```

## 6. Comprehensive Weighted SoH Analysis

```sql
SELECT 
  SUM("soh" * "remaining_capacity") / SUM("remaining_capacity") as weighted_avg_soh,
  SUM("remaining_capacity") as total_remaining_capacity,
  SUM("remaining_capacity" / ("soc" / 100.0)) as estimated_max_capacity,
  AVG("soh") as simple_avg_soh,
  MIN("soh") as min_soh,
  MAX("soh") as max_soh,
  COUNT(*) as battery_count,
  -- Calculate capacity utilization
  SUM("remaining_capacity") / SUM("remaining_capacity" / ("soc" / 100.0)) * 100 as capacity_utilization_percent
FROM (
  SELECT 
    "soh",
    "remaining_capacity",
    "soc",
    ROW_NUMBER() OVER (PARTITION BY "device_id" ORDER BY "time" DESC) as rn
  FROM "batteries_state" 
  WHERE "time" >= $__timeFrom 
    AND "time" <= $__timeTo
    AND "soh" IS NOT NULL
    AND "remaining_capacity" > 0
    AND "soc" > 0
    AND "device_id" LIKE '%BESS%'
) t
WHERE rn = 1;
```

## 7. Real-time Weighted SoH (Latest Values)

```sql
SELECT 
  SUM("soh" * "remaining_capacity") / SUM("remaining_capacity") as current_weighted_avg_soh
FROM (
  SELECT 
    "soh",
    "remaining_capacity",
    ROW_NUMBER() OVER (PARTITION BY "device_id" ORDER BY "time" DESC) as rn
  FROM "batteries_state" 
  WHERE "time" >= now() - 5m
    AND "soh" IS NOT NULL
    AND "remaining_capacity" > 0
    AND "device_id" LIKE '%BESS%'
) t
WHERE rn = 1;
```

## 8. Grafana Dashboard Query

```sql
SELECT 
  SUM("soh" * "remaining_capacity") / SUM("remaining_capacity") as "Weighted Avg SoH %"
FROM (
  SELECT 
    "soh",
    "remaining_capacity",
    ROW_NUMBER() OVER (PARTITION BY "device_id" ORDER BY "time" DESC) as rn
  FROM "batteries_state" 
  WHERE $__timeFilter
    AND "soh" IS NOT NULL
    AND "remaining_capacity" > 0
    AND "device_id" LIKE '%BESS%'
) t
WHERE rn = 1;
```

## Key Corrections Made

1. **Field Name**: Changed `power_capacity` to `remaining_capacity` (actual field in your schema)
2. **Added NULL Checks**: `"remaining_capacity" > 0` and `"soh" IS NOT NULL`
3. **Maximum Capacity Calculation**: Used `remaining_capacity / (soc / 100.0)` to estimate max capacity
4. **Added Safety Checks**: `"soc" > 0` to avoid division by zero

## About Maximum Value Parameters

**Answer**: There's no explicit `maximum_capacity` or `power_capacity` field in your current schema. However, you can:

1. **Calculate it**: `remaining_capacity / (soc / 100.0)` = maximum capacity
2. **Use power field**: If `power` represents rated capacity
3. **Add it to your data model**: Include a `max_capacity` field in future data collection

## Recommended Query

Use **Query #1** for the simplest weighted average, or **Query #6** for comprehensive analysis including capacity utilization.

The weighted average calculation is now correct and will give you the capacity-weighted SoH across all BESS batteries.
