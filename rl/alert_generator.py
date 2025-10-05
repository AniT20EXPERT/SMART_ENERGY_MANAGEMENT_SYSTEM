import time
from datetime import datetime, timedelta
from typing import List, Dict, Set
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import pyarrow as pa
from influxdb_client_3 import InfluxDBClient3




class RenewableEnergyAlertMonitor:
    """
    Monitors renewable energy systems and battery storage for critical alerts.
    Queries InfluxDB every 10 seconds and maintains an active alert list.
    """

    def __init__(self, influx_url: str, token: str, org: str, bucket: str):
        """
        Initialize the alert monitor with InfluxDB connection.

        Args:
            influx_url: InfluxDB server URL
            token: Authentication token
            org: Organization name
            bucket: Bucket name for reading/writing data
        """
        self.client = InfluxDBClient3(
            host=influx_url,
            token=token,
            org=org,
            database=bucket  # v3 uses 'database' instead of 'bucket'
        )

        self.org = org
        self.bucket = bucket
        # Alert tracking
        self.active_alerts: List[Dict[str, str]] = []
        self.alert_keys: Set[str] = set()
        self.previous_alert_keys: Set[str] = set()  # Track previous state

        # Store previous readings for comparison
        self.previous_readings = {
            'generation': {},  # device_id -> output
            'batteries': {},  # device_id -> {soc, soh, temp}
            'ev_batteries': {}  # device_id -> temp
        }

        # Alert definitions
        self.alert_definitions = {
            'solar_output_drop': {
                'alert_name_desc': 'Solar power plant output dropped by 40% or more',
                'recommendation': 'Check for cloud cover, panel soiling, or inverter faults; verify system connections'
            },
            'wind_output_drop': {
                'alert_name_desc': 'Wind power plant output dropped by 40% or more',
                'recommendation': 'Check wind speed conditions, turbine blade pitch, and yaw system functionality'
            },
            'battery_soh_critical': {
                'alert_name_desc': 'Battery state of health below 30% - replacement needed',
                'recommendation': 'Schedule immediate battery replacement; degraded capacity affects reliability'
            },
            'battery_soc_low': {
                'alert_name_desc': 'Battery state of charge below 20% - critically low',
                'recommendation': 'Initiate charging immediately; prolonged low SOC may cause permanent damage'
            },
            'battery_temp_high': {
                'alert_name_desc': 'Battery temperature exceeded 55°C - thermal runaway risk',
                'recommendation': 'Activate cooling systems immediately; disconnect if temperature continues rising'
            },
            'ev_thermal_critical': {
                'alert_name_desc': 'EV battery thermal load exceeded 60°C - critical overheating',
                'recommendation': 'Reduce charging rate immediately; inspect cooling system and ventilation'
            }
        }

    def query_generation_devices(self) -> List[Dict[str, any]]:
        sql = """
        SELECT device_id, current_output, time
        FROM generation_state
        WHERE time > now() - interval '1 minute'
          AND current_output IS NOT NULL
        ORDER BY device_id, time DESC
        """
        try:
            table: pa.Table = self.client.query(sql)
            if table.num_rows == 0:
                return []

            records = table.to_pydict()  # dict of lists
            devices = []
            seen_devices = set()

            for i in range(len(records['device_id'])):
                device_id = records['device_id'][i]
                if device_id in seen_devices:
                    continue
                seen_devices.add(device_id)

                current_output = float(records['current_output'][i])
                timestamp = records['time'][i]

                if "solar" in device_id.lower() or "pv" in device_id.lower():
                    device_type = "solar"
                elif "wind" in device_id.lower() or "wt" in device_id.lower():
                    device_type = "wind"
                else:
                    device_type = "unknown"

                prev_output = self.previous_readings["generation"].get(device_id)

                devices.append({
                    "device_id": device_id,
                    "current_output": current_output,
                    "prev_output": prev_output,
                    "time": timestamp,
                    "device_type": device_type
                })

                self.previous_readings["generation"][device_id] = current_output

            return devices
        except Exception as e:
            print(f"Error querying generation devices: {e}")
            return []

    def query_batteries(self) -> List[Dict[str, any]]:
        sql = """
        SELECT device_id, soc, soh, temperature, time
        FROM batteries_state
        WHERE device_id LIKE '%BESS%'
          AND time > now() - interval '1 minute'
        ORDER BY device_id, time DESC
        """
        try:
            table: pa.Table = self.client.query(sql)
            if table.num_rows == 0:
                return []

            records = table.to_pydict()
            batteries = []
            seen_devices = set()

            for i in range(len(records['device_id'])):
                device_id = records['device_id'][i]
                if device_id in seen_devices:
                    continue
                seen_devices.add(device_id)

                soc = float(records['soc'][i])
                soh = float(records['soh'][i])
                temp = float(records['temperature'][i])
                timestamp = records['time'][i]

                # Get previous readings from cache
                prev_readings = self.previous_readings['batteries'].get(device_id, {})
                prev_soc = prev_readings.get('soc')
                prev_soh = prev_readings.get('soh')
                prev_temp = prev_readings.get('temperature')

                batteries.append({
                    "device_id": device_id,
                    "soc": soc,
                    "soh": soh,
                    "temperature": temp,
                    "prev_soc": prev_soc,
                    "prev_soh": prev_soh,
                    "prev_temperature": prev_temp,
                    "time": timestamp
                })

                # Update cache
                self.previous_readings['batteries'][device_id] = {
                    'soc': soc,
                    'soh': soh,
                    'temperature': temp
                }

            return batteries
        except Exception as e:
            print(f"Error querying batteries: {e}")
            return []

    def query_ev_batteries(self) -> List[Dict[str, any]]:
        sql = """
        SELECT device_id, temperature, time
        FROM batteries_state
        WHERE device_id LIKE '%EV%'
          AND time > now() - interval '1 minute'
          AND temperature IS NOT NULL
        ORDER BY device_id, time DESC
        """
        try:
            table: pa.Table = self.client.query(sql)
            if table.num_rows == 0:
                return []

            records = table.to_pydict()
            ev_batteries = []
            seen_devices = set()

            for i in range(len(records['device_id'])):
                device_id = records['device_id'][i]
                if device_id in seen_devices:
                    continue
                seen_devices.add(device_id)

                temperature = float(records['temperature'][i])
                timestamp = records['time'][i]
                prev_temp = self.previous_readings['ev_batteries'].get(device_id)
                temp_change = temperature - prev_temp if prev_temp is not None else None

                ev_batteries.append({
                    "device_id": device_id,
                    "temperature": temperature,
                    "prev_temperature": prev_temp,
                    "temp_change": temp_change,
                    "time": timestamp
                })

                self.previous_readings['ev_batteries'][device_id] = temperature

            return ev_batteries
        except Exception as e:
            print(f"Error querying EV batteries: {e}")
            return []
    def check_generation_alerts(self, device_data: List[Dict]) -> List[Dict[str, str]]:
        """Check for solar and wind power plant output drop alerts."""
        alerts = []

        for device in device_data:
            device_id = device['device_id']
            device_type = device.get('device_type', 'unknown')
            current_output = float(device['current_output'])
            prev_output = device['prev_output']

            # Skip if no previous reading
            if prev_output is None:
                continue

            prev_output = float(prev_output)

            if prev_output > 0:
                drop_percentage = ((prev_output - current_output) / prev_output) * 100

                if drop_percentage >= 40:
                    # Determine alert type based on device type
                    if device_type == 'solar':
                        alert_type = 'solar_output_drop'
                        alert_prefix = 'solar'
                    elif device_type == 'wind':
                        alert_type = 'wind_output_drop'
                        alert_prefix = 'wind'
                    else:
                        alert_type = 'solar_output_drop'  # Default fallback
                        alert_prefix = 'generation'

                    alert_key = f"{alert_prefix}_{device_id}"
                    alert = {
                        'alert_key': alert_key,
                        'asset_id': device_id,
                        'alert_type': alert_type,
                        'device_type': device_type,
                        'alert_name_desc': f"{self.alert_definitions[alert_type]['alert_name_desc']} - {device_id}",
                        'recommendation': self.alert_definitions[alert_type]['recommendation'],
                        'severity': 'high',
                        'current_value': f"{current_output:.1f} kW",
                        'previous_value': f"{prev_output:.1f} kW",
                        'drop_percentage': f"{drop_percentage:.1f}%",
                        'timestamp': device['time'].isoformat() if hasattr(device['time'], 'isoformat') else str(
                            device['time'])
                    }
                    alerts.append(alert)

        return alerts

    def check_battery_alerts(self, battery_data: List[Dict]) -> List[Dict[str, str]]:
        """Check for battery system alerts (SOH, SOC, temperature)."""
        alerts = []

        for battery in battery_data:
            device_id = battery['device_id']
            soh = float(battery['soh'])
            soc = float(battery['soc'])
            temp = float(battery['temperature'])

            # SOH check (below 30%)
            if soh < 0.30:
                alert_key = f"battery_soh_{device_id}"
                alert = {
                    'alert_key': alert_key,
                    'asset_id': device_id,
                    'alert_type': 'battery_soh_critical',
                    'alert_name_desc': f"{self.alert_definitions['battery_soh_critical']['alert_name_desc']} - {device_id}",
                    'recommendation': self.alert_definitions['battery_soh_critical']['recommendation'],
                    'severity': 'critical',
                    'current_value': f"SOH: {soh * 100:.1f}%",
                    'previous_value': f"SOH: {float(battery['prev_soh']) * 100:.1f}%" if battery['prev_soh'] else "N/A",
                    'timestamp': battery['time'].isoformat() if hasattr(battery['time'], 'isoformat') else str(
                        battery['time'])
                }
                alerts.append(alert)

            # SOC check (below 20%)
            if soc < 0.20:
                alert_key = f"battery_soc_{device_id}"
                alert = {
                    'alert_key': alert_key,
                    'asset_id': device_id,
                    'alert_type': 'battery_soc_low',
                    'alert_name_desc': f"{self.alert_definitions['battery_soc_low']['alert_name_desc']} - {device_id}",
                    'recommendation': self.alert_definitions['battery_soc_low']['recommendation'],
                    'severity': 'high',
                    'current_value': f"SOC: {soc * 100:.1f}%",
                    'previous_value': f"SOC: {float(battery['prev_soc']) * 100:.1f}%" if battery['prev_soc'] else "N/A",
                    'timestamp': battery['time'].isoformat() if hasattr(battery['time'], 'isoformat') else str(
                        battery['time'])
                }
                alerts.append(alert)

            # Temperature check (above 55°C)
            if temp > 55:
                alert_key = f"battery_temp_{device_id}"
                alert = {
                    'alert_key': alert_key,
                    'asset_id': device_id,
                    'alert_type': 'battery_temp_high',
                    'alert_name_desc': f"{self.alert_definitions['battery_temp_high']['alert_name_desc']} - {device_id}",
                    'recommendation': self.alert_definitions['battery_temp_high']['recommendation'],
                    'severity': 'critical',
                    'current_value': f"Temperature: {temp:.1f}°C",
                    'previous_value': f"Temperature: {float(battery['prev_temperature']):.1f}°C" if battery[
                        'prev_temperature'] else "N/A",
                    'timestamp': battery['time'].isoformat() if hasattr(battery['time'], 'isoformat') else str(
                        battery['time'])
                }
                alerts.append(alert)

        return alerts

    def check_ev_battery_alerts(self, ev_data: List[Dict]) -> List[Dict[str, str]]:
        """Check for EV battery thermal load alerts (above 60°C)."""
        alerts = []

        for ev_battery in ev_data:
            device_id = ev_battery['device_id']
            thermal_load = float(ev_battery['temperature'])

            if thermal_load > 60:
                alert_key = f"ev_thermal_{device_id}"

                temp_change_str = "N/A"
                if ev_battery['temp_change'] is not None:
                    change = float(ev_battery['temp_change'])
                    temp_change_str = f"+{change:.1f}°C" if change > 0 else f"{change:.1f}°C"

                alert = {
                    'alert_key': alert_key,
                    'asset_id': device_id,
                    'alert_type': 'ev_thermal_critical',
                    'alert_name_desc': f"{self.alert_definitions['ev_thermal_critical']['alert_name_desc']} - {device_id}",
                    'recommendation': self.alert_definitions['ev_thermal_critical']['recommendation'],
                    'severity': 'critical',
                    'current_value': f"Thermal Load: {thermal_load:.1f}°C",
                    'previous_value': f"Thermal Load: {float(ev_battery['prev_temperature']):.1f}°C" if ev_battery[
                        'prev_temperature'] else "N/A",
                    'temp_change': temp_change_str,
                    'timestamp': ev_battery['time'].isoformat() if hasattr(ev_battery['time'], 'isoformat') else str(
                        ev_battery['time'])
                }
                alerts.append(alert)

        return alerts

    def update_alert_list(self, new_alerts: List[Dict[str, str]]):
        """
        Update the active alerts list.
        Add new alerts and remove alerts that are no longer occurring.
        """
        # Get current alert keys from new alerts
        new_alert_keys = {alert['alert_key'] for alert in new_alerts}

        # Remove alerts that are no longer occurring
        self.active_alerts = [
            alert for alert in self.active_alerts
            if alert['alert_key'] in new_alert_keys
        ]

        # Add new alerts (avoid duplicates)
        current_keys = {alert['alert_key'] for alert in self.active_alerts}
        for alert in new_alerts:
            if alert['alert_key'] not in current_keys:
                self.active_alerts.append(alert)

        # Update the tracking set
        self.alert_keys = new_alert_keys

    def write_alerts_to_influxdb(self) -> bool:
        """
        Write current active alerts to InfluxDB alerts measurement.
        Only writes if there are changes from previous state.
        Returns True if write occurred, False otherwise.
        """
        timestamp = datetime.utcnow()

        # Check if alert state has changed
        current_alert_keys = set(self.alert_keys)

        # Determine if we need to write
        alerts_changed = current_alert_keys != self.previous_alert_keys

        if not alerts_changed:
            print(f"[InfluxDB Write] No changes in alert state - skipping write")
            return False

        # Update previous state
        self.previous_alert_keys = current_alert_keys.copy()

        if not self.active_alerts:
            # Create point for cleared alerts
            point = {
                "measurement": "alerts",
                "tags": {
                    "status": "cleared"
                },
                "fields": {
                    "count": 0,
                    "message": "All alerts cleared"
                },
                "time": timestamp
            }

            try:
                self.client.write(record=point)
                print(f"[InfluxDB Write] All alerts cleared - written at {timestamp.isoformat()}")
                return True
            except Exception as e:
                print(f"[InfluxDB Write Error] {e}")
                return False

        # Write each alert
        points = []
        for alert in self.active_alerts:
            fields = {
                "alert_name_desc": alert['alert_name_desc'],
                "recommendation": alert['recommendation'],
                "current_value": alert['current_value'],
                "previous_value": alert.get('previous_value', 'N/A')
            }

            # Add optional fields if they exist
            if 'drop_percentage' in alert:
                fields["drop_percentage"] = alert['drop_percentage']
            if 'temp_change' in alert:
                fields["temp_change"] = alert['temp_change']

            point = {
                "measurement": "alerts",
                "tags": {
                    "alert_type": alert['alert_type'],
                    "asset_id": alert['asset_id'],
                    "severity": alert['severity']
                },
                "fields": fields,
                "time": timestamp
            }
            points.append(point)

        try:
            # Write all points at once (batch write)
            self.client.write(record=points)
            print(f"[InfluxDB Write] {len(points)} alerts written at {timestamp.isoformat()}")
            return True
        except Exception as e:
            print(f"[InfluxDB Write Error] {e}")
            return False

    def monitor_cycle(self):
        """
        Single monitoring cycle - query data, check alerts, update list, write to DB.
        """
        print(f"\n{'=' * 80}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting monitoring cycle...")
        print(f"{'=' * 80}")

        # Query all data sources
        generation_data = self.query_generation_devices()
        battery_data = self.query_batteries()
        ev_data = self.query_ev_batteries()

        print(f"Data Retrieved:")
        print(f"  - Generation Devices: {len(generation_data)}")
        print(f"  - Batteries (BESS): {len(battery_data)}")
        print(f"  - EV Batteries: {len(ev_data)}")

        # Check for alerts
        all_alerts = []
        all_alerts.extend(self.check_generation_alerts(generation_data))
        all_alerts.extend(self.check_battery_alerts(battery_data))
        all_alerts.extend(self.check_ev_battery_alerts(ev_data))

        # Update alert list
        self.update_alert_list(all_alerts)

        # Display current alerts
        print(f"\nActive Alerts: {len(self.active_alerts)}")
        if self.active_alerts:
            for i, alert in enumerate(self.active_alerts, 1):
                print(f"\n  Alert {i}:")
                print(f"    {alert['alert_name_desc']}")
                print(f"    Recommendation: {alert['recommendation']}")
                print(f"    Severity: {alert['severity'].upper()}")
                print(f"    Current: {alert['current_value']}")
                if 'previous_value' in alert:
                    print(f"    Previous: {alert['previous_value']}")
                if 'drop_percentage' in alert:
                    print(f"    Drop: {alert['drop_percentage']}")
                if 'temp_change' in alert:
                    print(f"    Change: {alert['temp_change']}")
        else:
            print("  No active alerts - All systems nominal")

        # Write to InfluxDB only if alerts changed
        write_occurred = self.write_alerts_to_influxdb()
        if write_occurred:
            print(f"Alert state changed - data written to InfluxDB")

        print(f"\n{'=' * 80}\n")

    def start_monitoring(self, interval_seconds: int = 10):
        """
        Start continuous monitoring with specified interval.

        Args:
            interval_seconds: Time between monitoring cycles (default: 10)
        """
        print(f"Starting Renewable Energy Alert Monitor")
        print(f"Monitoring interval: {interval_seconds} seconds")
        # print(f"InfluxDB: {self.client.url}")
        print(f"Bucket: {self.bucket}")

        try:
            while True:
                self.monitor_cycle()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")
            self.client.close()
        except Exception as e:
            print(f"\n\nError occurred: {str(e)}")
            import traceback
            traceback.print_exc()
            self.client.close()
            raise


# Example usage
if __name__ == "__main__":
    # Initialize monitor
    monitor = RenewableEnergyAlertMonitor(
        influx_url="http://10.122.147.28:8181",
        token="apiv3_MnT56_WfZMg4x80uVKDLD_Cjx9jz2tFMCnHISROUdTQAFlpFaSaY0Xl_kFxYfUpI0rITlNe3RDmrom0FXQQ_Rg",
        org="team fusion",
        bucket="test_1_data"
    )

    # Start monitoring (queries every 10 seconds)
    monitor.start_monitoring(interval_seconds=10)