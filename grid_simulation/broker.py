import os
import json
import time
import dotenv
import paho.mqtt.client as mqtt
from datetime import datetime
from influxdb_client_3 import InfluxDBClient3, Point, WritePrecision

class DataLogger:
    def __init__(self):
        # Load environment variables
        dotenv.load_dotenv()

        # MQTT configuration
        self.broker = os.getenv("MQTT_BROKER", "localhost")
        self.port = int(os.getenv("MQTT_PORT", 1883))
        self.routing_topic = os.getenv("ROUTING_TOPIC", "grid/routing")

        # InfluxDB configuration
        self.influx_host = os.getenv("INFLUX_HOST")
        self.influx_token = os.getenv("INFLUX_TOKEN")
        self.influx_org = os.getenv("INFLUX_ORG")
        self.influx_bucket = os.getenv("INFLUX_BUCKET")
        
        self.batch_size = 10000  # Reduced for more frequent writes
        self.points_buffer = []
        self.last_write_time = time.time()
        self.write_interval = 0.1  # Force write every 5 seconds

        # Initialize InfluxDB client (no write options for v3 client)
        self.influx_client = InfluxDBClient3(
            host=self.influx_host,
            token=self.influx_token,
            org=self.influx_org
        )

        # Initialize MQTT client with better error handling
        self.mqtt_client = mqtt.Client(client_id="datalogger_" + str(int(time.time())))
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect
        
        # Connect with retry logic
        self.connect_mqtt()

    def connect_mqtt(self):
        """Connect to MQTT broker with retry logic"""
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                print(f"Attempting to connect to MQTT broker at {self.broker}:{self.port} (attempt {attempt + 1}/{max_retries})")
                self.mqtt_client.connect(self.broker, self.port, 60)
                self.mqtt_client.loop_start()
                return
            except Exception as e:
                print(f"Failed to connect: {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print("Max retries reached. Please check your MQTT broker.")
                    raise

    def on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection"""
        if rc == 0:
            print(f"✓ Connected to MQTT broker successfully")
            # Subscribe to all topics
            self.mqtt_client.subscribe("#")
            print("✓ Subscribed to all topics (#)")
        else:
            print(f"✗ Failed to connect to MQTT broker with result code {rc}")
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorized"
            }
            print(f"  Error: {error_messages.get(rc, 'Unknown error')}")

    def on_disconnect(self, client, userdata, rc):
        """Callback for MQTT disconnection"""
        if rc != 0:
            print(f"✗ Unexpected disconnection from MQTT broker (code: {rc})")
            print("  Attempting to reconnect...")
            try:
                self.connect_mqtt()
            except Exception as e:
                print(f"  Reconnection failed: {e}")

    def on_message(self, client, userdata, msg):
        """Callback for incoming MQTT messages"""
        try:
            data = json.loads(msg.payload.decode())
            topic = msg.topic
            
            # Show message count every 100 messages
            if not hasattr(self, 'message_count'):
                self.message_count = 0
            self.message_count += 1
            if self.message_count % 100 == 0:
                print(f"Processed {self.message_count} messages, buffer: {len(self.points_buffer)} points")

            # Routing updates handled separately
            if topic == self.routing_topic:
                device_id = data.get("device_id")
                input_source_id = data.get("input_source_id")
                output_source_id = data.get("output_source_id")
                if device_id and input_source_id and output_source_id:
                    routing_update = {
                        "input_source_id": input_source_id,
                        "output_source_id": output_source_id
                    }
                    self.mqtt_client.publish(f"devices/{device_id}/routing", json.dumps(routing_update))
                    print(f"Published routing update for {device_id}")
                return

            # Determine measurement based on topic prefix
            prefix = topic.split("/")[0]
            measurement_map = {
                "batteries": "batteries_state",
                "generation": "generation_state",
                "consumers": "consumers_state",
                "grid": "grid_state",
                "devices": "devices_state"
            }
            measurement = measurement_map.get(prefix, "unknown_state")

            # Extract device id from payload or topic
            device_id = data.pop("device_id", topic.split("/")[-2] if len(topic.split("/")) > 1 else "unknown")

            # Determine timestamp from simulated_time
            sim_time = data.pop("simulated_time", None)
            
            # Remove reserved InfluxDB column names from data
            reserved_fields = ['time', '_time', '_measurement', '_field', '_value']
            for field in reserved_fields:
                if field in data:
                    # Rename to avoid conflict
                    data[f"data_{field}"] = data.pop(field)
            timestamp_dt = None
            if sim_time is not None:
                try:
                    if isinstance(sim_time, str):
                        # Handle ISO format with or without 'Z'
                        sim_time_clean = sim_time.replace('Z', '+00:00')
                        timestamp_dt = datetime.fromisoformat(sim_time_clean)
                    elif isinstance(sim_time, (int, float)):
                        timestamp_dt = datetime.fromtimestamp(sim_time)
                    else:
                        timestamp_dt = datetime.utcnow()
                except Exception as e:
                    print(f"Warning: Failed to parse timestamp '{sim_time}': {e}")
                    timestamp_dt = datetime.utcnow()
            else:
                timestamp_dt = datetime.utcnow()

            # Create InfluxDB point
            point = Point(measurement) \
                .tag("device_id", device_id) \
                .tag("topic", topic) \
                .time(timestamp_dt, write_precision=WritePrecision.MS)

            # Add remaining fields (handle nested dicts and lists)
            for key, value in data.items():
                try:
                    if isinstance(value, (int, float)):
                        point = point.field(key, float(value))
                    elif isinstance(value, bool):
                        point = point.field(key, value)
                    elif isinstance(value, str):
                        point = point.field(key, value)
                    elif isinstance(value, (dict, list)):
                        # Convert complex types to JSON strings
                        point = point.field(key, json.dumps(value))
                except Exception as e:
                    print(f"Warning: Failed to add field '{key}': {e}")

            # Add point to buffer
            self.points_buffer.append(point)

            # Write when buffer reaches batch size OR time interval exceeded
            current_time = time.time()
            if len(self.points_buffer) >= self.batch_size or \
               (current_time - self.last_write_time) >= self.write_interval:
                self.flush_buffer()

        except json.JSONDecodeError as e:
            print(f"JSON decode error on topic {msg.topic}: {e}")
        except Exception as e:
            print(f"Error processing message on topic {msg.topic}: {e}")

    def flush_buffer(self):
        """Write buffered points to InfluxDB"""
        if not self.points_buffer:
            return
        
        try:
            self.influx_client.write(
                database=self.influx_bucket,
                record=self.points_buffer
            )
            print(f"✓ Written {len(self.points_buffer)} points to InfluxDB")
            self.points_buffer.clear()
            self.last_write_time = time.time()
        except Exception as e:
            print(f"✗ Error writing to InfluxDB: {e}")
            # Keep buffer for retry on next attempt
            if len(self.points_buffer) > 1000:
                print(f"  Warning: Buffer size exceeded 1000, clearing old data")
                self.points_buffer = self.points_buffer[-500:]

    def update_grid_routing(self, device_id, input_source_id, output_source_id):
        """Manually publish routing update"""
        routing_data = {
            "device_id": device_id,
            "input_source_id": input_source_id,
            "output_source_id": output_source_id
        }
        self.mqtt_client.publish(self.routing_topic, json.dumps(routing_data))
        print(f"Sent routing update for {device_id}")

    def close(self):
        """Cleanup and close connections"""
        print("\nShutting down DataLogger...")
        # Flush remaining buffer
        if self.points_buffer:
            print(f"Flushing {len(self.points_buffer)} remaining points...")
            self.flush_buffer()
        
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        self.influx_client.close()
        print("✓ DataLogger stopped cleanly")


def main():
    logger = None
    try:
        logger = DataLogger()
        print("\n" + "="*60)
        print("DataLogger running... Press Ctrl+C to stop.")
        print("="*60 + "\n")

        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nReceived interrupt signal...")
    except Exception as e:
        print(f"\nFatal error: {e}")
    finally:
        if logger:
            logger.close()


if __name__ == "__main__":
    main()