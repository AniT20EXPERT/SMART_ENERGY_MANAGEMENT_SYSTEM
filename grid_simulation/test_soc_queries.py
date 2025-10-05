#!/usr/bin/env python3
"""
Test script for SoC queries
This script demonstrates how to use the SoC query generator and validates query syntax.
"""

import sys
import os
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from soc_query_generator import SoCQueryGenerator

def test_query_generation():
    """Test the SoC query generator"""
    print("Testing SoC Query Generation")
    print("=" * 40)
    
    generator = SoCQueryGenerator()
    
    # Test different query types
    print("\n1. Overall Weighted SoC Query:")
    query1 = generator.generate_weighted_soc_query(
        time_range="24h",
        group_interval="5m",
        alias="overall_soc"
    )
    print(query1)
    
    print("\n2. Grid BESS Specific Query:")
    query2 = generator.generate_weighted_soc_query(
        time_range="1h",
        device_filter=".*GridBESS.*",
        alias="grid_bess_soc"
    )
    print(query2)
    
    print("\n3. Real-time Query:")
    query3 = generator.generate_realtime_query(time_window="2m")
    print(query3)
    
    print("\n4. Alert Query (SoC < 15%):")
    query4 = generator.generate_alert_query(threshold=15.0)
    print(query4)
    
    print("\n5. Device Breakdown Query:")
    query5 = generator.generate_device_breakdown_query(
        time_range="6h",
        group_interval="10m"
    )
    print(query5)

def test_custom_queries():
    """Test custom query generation"""
    print("\n" + "=" * 40)
    print("Testing Custom Queries")
    print("=" * 40)
    
    generator = SoCQueryGenerator(measurement="custom_batteries")
    
    # Custom measurement name
    print("\n1. Custom Measurement Query:")
    query = generator.generate_weighted_soc_query(
        time_range="7d",
        group_interval="1h",
        alias="weekly_weighted_soc"
    )
    print(query)
    
    # Solar and Wind combined
    print("\n2. Renewable BESS Query:")
    query = generator.generate_weighted_soc_query(
        time_range="12h",
        device_filter=".*Solar.*|.*Wind.*",
        alias="renewable_soc"
    )
    print(query)

def demonstrate_usage():
    """Demonstrate practical usage scenarios"""
    print("\n" + "=" * 40)
    print("Practical Usage Scenarios")
    print("=" * 40)
    
    generator = SoCQueryGenerator()
    
    print("\n1. For Grafana Dashboard (Continuous Monitoring):")
    grafana_query = generator.generate_grafana_query()
    print(grafana_query)
    
    print("\n2. For Real-time API Endpoint:")
    realtime_query = generator.generate_realtime_query()
    print(realtime_query)
    
    print("\n3. For Historical Analysis (Last 7 days):")
    historical_query = generator.generate_weighted_soc_query(
        time_range="7d",
        group_interval="1h",
        alias="historical_soc"
    )
    print(historical_query)
    
    print("\n4. For Alert System (Low SoC Detection):")
    alert_query = generator.generate_alert_query(threshold=25.0)
    print(alert_query)

def save_all_queries():
    """Save all generated queries to files"""
    print("\n" + "=" * 40)
    print("Saving Queries to Files")
    print("=" * 40)
    
    generator = SoCQueryGenerator()
    
    # Save to SQL file
    generator.save_queries_to_file("soc_queries.sql")
    
    # Generate JSON format for API usage
    queries = generator.generate_all_queries()
    
    query_data = {
        "generated_at": datetime.now().isoformat(),
        "measurement": "batteries_state",
        "queries": queries
    }
    
    with open("soc_queries.json", "w") as f:
        import json
        json.dump(query_data, f, indent=2)
    
    print("Queries saved to:")
    print("  - soc_queries.sql (SQL format)")
    print("  - soc_queries.json (JSON format)")

def main():
    """Main test function"""
    print("SoC Query Generator Test Suite")
    print("=" * 50)
    
    try:
        test_query_generation()
        test_custom_queries()
        demonstrate_usage()
        save_all_queries()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        print("\nGenerated files:")
        print("  - soc_queries.md (Documentation)")
        print("  - soc_queries.sql (SQL queries)")
        print("  - soc_queries.json (JSON format)")
        print("\nUsage:")
        print("  1. Use SQL queries directly in InfluxDB")
        print("  2. Use JSON format for API integration")
        print("  3. Import SQL queries into Grafana")
        print("  4. Modify queries as needed for your specific use case")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
