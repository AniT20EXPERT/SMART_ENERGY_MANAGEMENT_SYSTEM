#!/usr/bin/env python3
"""
SoC Query Generator for InfluxDB
Generates queries to calculate weighted State of Charge (SoC) for different battery types.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class SoCQueryGenerator:
    """Generate InfluxDB queries for battery SoC analysis"""
    
    def __init__(self, measurement: str = "batteries_state"):
        self.measurement = measurement
        self.base_conditions = [
            "remaining_capacity > 0",
            "soc IS NOT NULL"
        ]
    
    def generate_weighted_soc_query(self, 
                                  time_range: str = "1h",
                                  group_interval: str = "1m",
                                  device_filter: Optional[str] = None,
                                  alias: str = "weighted_soc") -> str:
        """
        Generate a weighted SoC query
        
        Args:
            time_range: Time range for data (e.g., "1h", "24h", "7d")
            group_interval: Grouping interval (e.g., "1m", "5m", "1h")
            device_filter: Optional device ID filter (regex pattern)
            alias: Alias for the result column
        """
        conditions = self.base_conditions.copy()
        conditions.append(f"time >= now() - {time_range}")
        
        if device_filter:
            conditions.append(f"device_id =~ /{device_filter}/")
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
SELECT 
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as {alias}
FROM {self.measurement} 
WHERE {where_clause}
GROUP BY time({group_interval})
ORDER BY time
"""
        return query.strip()
    
    def generate_device_breakdown_query(self, 
                                      time_range: str = "1h",
                                      group_interval: str = "1m") -> str:
        """Generate a query that breaks down SoC by device type"""
        conditions = self.base_conditions.copy()
        conditions.append(f"time >= now() - {time_range}")
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
SELECT 
  CASE 
    WHEN device_id =~ /.*GridBESS.*/ THEN 'Grid BESS'
    WHEN device_id =~ /.*Solar.*/ THEN 'Solar BESS'
    WHEN device_id =~ /.*Wind.*/ THEN 'Wind BESS'
    WHEN device_id =~ /.*EV.*/ THEN 'EV Battery'
    ELSE 'Other'
  END as battery_type,
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as weighted_soc,
  SUM(remaining_capacity) as total_capacity,
  COUNT(*) as battery_count
FROM {self.measurement} 
WHERE {where_clause}
GROUP BY battery_type, time({group_interval})
ORDER BY time, total_capacity DESC
"""
        return query.strip()
    
    def generate_realtime_query(self, time_window: str = "5m") -> str:
        """Generate a query for real-time weighted SoC"""
        conditions = self.base_conditions.copy()
        conditions.append(f"time >= now() - {time_window}")
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
SELECT 
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as current_weighted_soc
FROM (
  SELECT 
    soc, 
    remaining_capacity,
    ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY time DESC) as rn
  FROM {self.measurement} 
  WHERE {where_clause}
) 
WHERE rn = 1
"""
        return query.strip()
    
    def generate_alert_query(self, threshold: float = 20.0, time_window: str = "1m") -> str:
        """Generate a query for SoC alerts"""
        conditions = self.base_conditions.copy()
        conditions.append(f"time >= now() - {time_window}")
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
SELECT 
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as weighted_soc
FROM {self.measurement} 
WHERE {where_clause}
HAVING weighted_soc < {threshold}
"""
        return query.strip()
    
    def generate_grafana_query(self, time_filter: str = "$timeFilter") -> str:
        """Generate a Grafana-compatible query"""
        conditions = self.base_conditions.copy()
        conditions.append(f"{time_filter}")
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
SELECT 
  SUM(soc * remaining_capacity) / SUM(remaining_capacity) as "Weighted SoC %"
FROM {self.measurement} 
WHERE {where_clause}
GROUP BY time($__interval)
ORDER BY time
"""
        return query.strip()
    
    def generate_all_queries(self) -> Dict[str, str]:
        """Generate all standard queries"""
        queries = {
            "overall_weighted_soc": self.generate_weighted_soc_query(
                time_range="1h", 
                group_interval="1m",
                alias="overall_weighted_soc"
            ),
            "grid_bess_soc": self.generate_weighted_soc_query(
                time_range="1h",
                group_interval="1m", 
                device_filter=".*GridBESS.*",
                alias="grid_bess_weighted_soc"
            ),
            "solar_bess_soc": self.generate_weighted_soc_query(
                time_range="1h",
                group_interval="1m",
                device_filter=".*Solar.*", 
                alias="solar_bess_weighted_soc"
            ),
            "wind_bess_soc": self.generate_weighted_soc_query(
                time_range="1h",
                group_interval="1m",
                device_filter=".*Wind.*",
                alias="wind_bess_weighted_soc"
            ),
            "renewable_bess_soc": self.generate_weighted_soc_query(
                time_range="1h",
                group_interval="1m",
                device_filter=".*Solar.*|.*Wind.*",
                alias="renewable_bess_weighted_soc"
            ),
            "device_breakdown": self.generate_device_breakdown_query(
                time_range="1h",
                group_interval="1m"
            ),
            "realtime_soc": self.generate_realtime_query(time_window="5m"),
            "alert_low_soc": self.generate_alert_query(threshold=20.0),
            "grafana_dashboard": self.generate_grafana_query()
        }
        return queries
    
    def save_queries_to_file(self, filename: str = "generated_soc_queries.sql"):
        """Save all queries to a SQL file"""
        queries = self.generate_all_queries()
        
        with open(filename, 'w') as f:
            f.write("-- Generated SoC Queries for InfluxDB\n")
            f.write(f"-- Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"-- Measurement: {self.measurement}\n\n")
            
            for name, query in queries.items():
                f.write(f"-- {name.replace('_', ' ').title()}\n")
                f.write(query)
                f.write("\n\n")
        
        print(f"Queries saved to {filename}")
    
    def print_query(self, query_name: str):
        """Print a specific query"""
        queries = self.generate_all_queries()
        if query_name in queries:
            print(f"-- {query_name.replace('_', ' ').title()}")
            print(queries[query_name])
        else:
            print(f"Query '{query_name}' not found. Available queries:")
            for name in queries.keys():
                print(f"  - {name}")

def main():
    """Main function to demonstrate query generation"""
    generator = SoCQueryGenerator()
    
    print("SoC Query Generator for InfluxDB")
    print("=" * 50)
    
    # Generate and display some key queries
    print("\n1. Overall Weighted SoC (1 hour, 1-minute intervals):")
    print(generator.generate_weighted_soc_query())
    
    print("\n2. Grid BESS Weighted SoC:")
    print(generator.generate_weighted_soc_query(device_filter=".*GridBESS.*"))
    
    print("\n3. Real-time Weighted SoC:")
    print(generator.generate_realtime_query())
    
    print("\n4. Device Breakdown:")
    print(generator.generate_device_breakdown_query())
    
    print("\n5. Grafana Dashboard Query:")
    print(generator.generate_grafana_query())
    
    # Save all queries to file
    generator.save_queries_to_file()
    
    print("\n" + "=" * 50)
    print("All queries generated successfully!")
    print("Use these queries in your InfluxDB client or Grafana dashboard.")

if __name__ == "__main__":
    main()
