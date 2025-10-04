import os
import json
import time
import dotenv
import paho.mqtt.client as mqtt
from datetime import datetime
from influxdb_client_3 import InfluxDBClient3, Point, WritePrecision, WriteOptions

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
        
        self.batch_size = 5000  # Number of points to collect before writing
        self.points_buffer = []

        # Configure write options for batching
        from influxdb_client_3 import InfluxDBClient3, WriteOptions

        write_options = WriteOptions(
            batch_size=10_000,        # buffer more points before writing
            flush_interval=10_000,    # flush every 10 seconds (less frequent writes)
            jitter_interval=2_000,    # spread out flushes to avoid bursts
            retry_interval=30_000,    # wait 30s before retrying failed writes
        )


        # Initialize InfluxDB client with write options
        self.influx_client = InfluxDBClient3(
            host=self.influx_host,
            token=self.influx_token,
            org=self.influx_org,
            write_options=write_options
        )

        # Initialize MQTT client
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.connect(self.broker, self.port, 60)
        self.mqtt_client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected to MQTT broker with result code {rc}")
        self.mqtt_client.subscribe("#")
        print("Subscribed to all topics (#)")

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            topic = msg.topic
            # print(f"Received data on {topic}: {data}")

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
                    print(f"Published routing update for {device_id}: {routing_update}")
                else:
                    print("Invalid routing data received")
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
            device_id = data.pop("device_id", topic.split("/")[-1])

            # Determine timestamp from simulated_time
            sim_time = data.pop("simulated_time", None)
            timestamp_dt = None
            if sim_time is not None:
                try:
                    # If ISO string, parse directly
                    if isinstance(sim_time, str):
                        # Remove 'Z' suffix if present for parsing
                        sim_time_clean = sim_time.rstrip('Z')
                        timestamp_dt = datetime.fromisoformat(sim_time_clean)
                    # If numeric (int/float), treat as epoch seconds
                    elif isinstance(sim_time, (int, float)):
                        timestamp_dt = datetime.fromtimestamp(sim_time)
                    else:
                        timestamp_dt = datetime.utcnow()
                except Exception:
                    timestamp_dt = datetime.utcnow()
            else:
                timestamp_dt = datetime.utcnow()

            # Create InfluxDB point
            point = Point(measurement) \
                .tag("device_id", device_id) \
                .tag("topic", topic) \
                .time(timestamp_dt, write_precision=WritePrecision.MS)

            # Add remaining fields
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    point = point.field(key, float(value))
                elif isinstance(value, (str, bool)):
                    point = point.field(key, value)

            # Add point to buffer
            self.points_buffer.append(point)

            # Write when buffer reaches batch size
            if len(self.points_buffer) >= self.batch_size:
                self.influx_client.write(
                    database=self.influx_bucket,
                    record=self.points_buffer
                )
                print(f"Written batch of {len(self.points_buffer)} points to InfluxDB")
                self.points_buffer.clear()

        except Exception as e:
            print(f"Error processing message on topic {msg.topic}: {e}")

    def update_grid_routing(self, device_id, input_source_id, output_source_id):
        routing_data = {
            "device_id": device_id,
            "input_source_id": input_source_id,
            "output_source_id": output_source_id
        }
        self.mqtt_client.publish(self.routing_topic, json.dumps(routing_data))
        print(f"Sent routing update for {device_id}: {routing_data}")


def main():
    logger = DataLogger()
    print("DataLogger running... Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Stopping DataLogger...")
        logger.mqtt_client.loop_stop()
        logger.mqtt_client.disconnect()
        logger.influx_client.close()


if __name__ == "__main__":
    main()