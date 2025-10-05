# SoH (State of Health) Queries for InfluxDB

Here are different variations to get the latest SoH of all batteries, including grid and power plant batteries.

## 1. Latest SoH for All Batteries (Simple)

```sql
SELECT 
  "soh", 
  "time", 
  "device_id"
FROM "batteries_state" 
WHERE "time" >= $__timeFrom 
  AND "time" <= $__timeTo
  AND "soh" IS NOT NULL
ORDER BY "time" DESC
```

## 2. Latest SoH for Each Battery (Most Recent Value per Device)

```sql
SELECT 
  "soh", 
  "time", 
  "device_id"
FROM (
  SELECT 
    "soh",
    "time",
    "device_id",
    ROW_NUMBER() OVER (PARTITION BY "device_id" ORDER BY "time" DESC) as rn
  FROM "batteries_state" 
  WHERE "time" >= $__timeFrom 
    AND "time" <= $__timeTo
    AND "soh" IS NOT NULL
) 
WHERE rn = 1
ORDER BY "soh" DESC
```

## 3. Latest SoH with Battery Type Classification

```sql
SELECT 
  "soh", 
  "time", 
  "device_id",
  CASE 
    WHEN "device_id" =~ /.*GridBESS.*/ THEN 'Grid BESS'
    WHEN "device_id" =~ /.*Solar.*/ THEN 'Solar BESS'
    WHEN "device_id" =~ /.*Wind.*/ THEN 'Wind BESS'
    WHEN "device_id" =~ /.*EV.*/ THEN 'EV Battery'
    ELSE 'Other'
  END as battery_type
FROM (
  SELECT 
    "soh",
    "time",
    "device_id",
    ROW_NUMBER() OVER (PARTITION BY "device_id" ORDER BY "time" DESC) as rn
  FROM "batteries_state" 
  WHERE "time" >= $__timeFrom 
    AND "time" <= $__timeTo
    AND "soh" IS NOT NULL
) 
WHERE rn = 1
ORDER BY battery_type, "soh" DESC
```

## 4. Latest SoH for Grid and Power Plant Batteries Only

```sql
SELECT 
  "soh", 
  "time", 
  "device_id",
  CASE 
    WHEN "device_id" =~ /.*GridBESS.*/ THEN 'Grid BESS'
    WHEN "device_id" =~ /.*Solar.*/ THEN 'Solar BESS'
    WHEN "device_id" =~ /.*Wind.*/ THEN 'Wind BESS'
  END as battery_type
FROM (
  SELECT 
    "soh",
    "time",
    "device_id",
    ROW_NUMBER() OVER (PARTITION BY "device_id" ORDER BY "time" DESC) as rn
  FROM "batteries_state" 
  WHERE "time" >= $__timeFrom 
    AND "time" <= $__timeTo
    AND "soh" IS NOT NULL
    AND ("device_id" =~ /.*GridBESS.*/ OR "device_id" =~ /.*Solar.*/ OR "device_id" =~ /.*Wind.*/)
) 
WHERE rn = 1
ORDER BY battery_type, "soh" DESC
```

## 5. Latest SoH with Additional Battery Information

```sql
SELECT 
  "soh", 
  "time", 
  "device_id",
  "remaining_capacity",
  "soc",
  "voltage",
  "current",
  "temperature",
  CASE 
    WHEN "device_id" =~ /.*GridBESS.*/ THEN 'Grid BESS'
    WHEN "device_id" =~ /.*Solar.*/ THEN 'Solar BESS'
    WHEN "device_id" =~ /.*Wind.*/ THEN 'Wind BESS'
    WHEN "device_id" =~ /.*EV.*/ THEN 'EV Battery'
    ELSE 'Other'
  END as battery_type
FROM (
  SELECT 
    "soh",
    "time",
    "device_id",
    "remaining_capacity",
    "soc",
    "voltage",
    "current",
    "temperature",
    ROW_NUMBER() OVER (PARTITION BY "device_id" ORDER BY "time" DESC) as rn
  FROM "batteries_state" 
  WHERE "time" >= $__timeFrom 
    AND "time" <= $__timeTo
    AND "soh" IS NOT NULL
) 
WHERE rn = 1
ORDER BY "soh" DESC
```

## 6. SoH Statistics by Battery Type

```sql
SELECT 
  CASE 
    WHEN "device_id" =~ /.*GridBESS.*/ THEN 'Grid BESS'
    WHEN "device_id" =~ /.*Solar.*/ THEN 'Solar BESS'
    WHEN "device_id" =~ /.*Wind.*/ THEN 'Wind BESS'
    WHEN "device_id" =~ /.*EV.*/ THEN 'EV Battery'
    ELSE 'Other'
  END as battery_type,
  AVG("soh") as avg_soh,
  MIN("soh") as min_soh,
  MAX("soh") as max_soh,
  COUNT(*) as battery_count
FROM (
  SELECT 
    "soh",
    "device_id",
    ROW_NUMBER() OVER (PARTITION BY "device_id" ORDER BY "time" DESC) as rn
  FROM "batteries_state" 
  WHERE "time" >= $__timeFrom 
    AND "time" <= $__timeTo
    AND "soh" IS NOT NULL
) 
WHERE rn = 1
GROUP BY battery_type
ORDER BY avg_soh DESC
```

## 7. SoH Alert Query (Batteries with Low SoH)

```sql
SELECT 
  "soh", 
  "time", 
  "device_id",
  CASE 
    WHEN "device_id" =~ /.*GridBESS.*/ THEN 'Grid BESS'
    WHEN "device_id" =~ /.*Solar.*/ THEN 'Solar BESS'
    WHEN "device_id" =~ /.*Wind.*/ THEN 'Wind BESS'
    WHEN "device_id" =~ /.*EV.*/ THEN 'EV Battery'
    ELSE 'Other'
  END as battery_type
FROM (
  SELECT 
    "soh",
    "time",
    "device_id",
    ROW_NUMBER() OVER (PARTITION BY "device_id" ORDER BY "time" DESC) as rn
  FROM "batteries_state" 
  WHERE "time" >= $__timeFrom 
    AND "time" <= $__timeTo
    AND "soh" IS NOT NULL
) 
WHERE rn = 1
  AND "soh" < 80  -- Alert if SoH below 80%
ORDER BY "soh" ASC
```

## 8. SoH Trend Over Time (Latest Values)

```sql
SELECT 
  "time",
  AVG("soh") as avg_soh,
  MIN("soh") as min_soh,
  MAX("soh") as max_soh,
  COUNT(*) as battery_count
FROM (
  SELECT 
    "soh",
    "time",
    "device_id",
    ROW_NUMBER() OVER (PARTITION BY "device_id" ORDER BY "time" DESC) as rn
  FROM "batteries_state" 
  WHERE "time" >= $__timeFrom 
    AND "time" <= $__timeTo
    AND "soh" IS NOT NULL
) 
WHERE rn = 1
GROUP BY "time"
ORDER BY "time"
```

## 9. Grafana Dashboard Query (Latest SoH)

```sql
SELECT 
  "soh" as "SoH %", 
  "time", 
  "device_id" as "Device ID"
FROM (
  SELECT 
    "soh",
    "time",
    "device_id",
    ROW_NUMBER() OVER (PARTITION BY "device_id" ORDER BY "time" DESC) as rn
  FROM "batteries_state" 
  WHERE $__timeFilter
    AND "soh" IS NOT NULL
) 
WHERE rn = 1
ORDER BY "soh" DESC
```

## 10. Real-time SoH Monitoring

```sql
SELECT 
  "soh", 
  "time", 
  "device_id",
  "remaining_capacity",
  "soc",
  CASE 
    WHEN "device_id" =~ /.*GridBESS.*/ THEN 'Grid BESS'
    WHEN "device_id" =~ /.*Solar.*/ THEN 'Solar BESS'
    WHEN "device_id" =~ /.*Wind.*/ THEN 'Wind BESS'
    ELSE 'Other'
  END as battery_type
FROM "batteries_state" 
WHERE "time" >= now() - 5m
  AND "soh" IS NOT NULL
ORDER BY "time" DESC, "soh" DESC
```

## Key Features Explained

- **`ROW_NUMBER() OVER (PARTITION BY "device_id" ORDER BY "time" DESC)`**: Gets the most recent record for each device
- **`WHERE rn = 1`**: Filters to only the latest record per device
- **Battery Type Classification**: Categorizes batteries by their device ID patterns
- **SoH Filtering**: `"soh" IS NOT NULL` ensures we only get valid SoH values

## Recommended Queries

1. **For Latest SoH of All Batteries**: Use query #2 or #5
2. **For Grid and Power Plant Only**: Use query #4
3. **For Grafana Dashboard**: Use query #9
4. **For SoH Alerts**: Use query #7
5. **For Statistics**: Use query #6

Choose the query that best fits your specific monitoring needs!
