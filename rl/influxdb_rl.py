import numpy as np
from pathlib import Path
from typing import Dict, List
from stable_baselines3 import DQN
import requests
import json
from influxdb_client_3 import InfluxDBClient3, Point
from datetime import datetime, timedelta

# --- InfluxDB v3 Enterprise Config ---
# For InfluxDB v3, specify the full URL without protocol (client adds it)
# If using HTTP (non-TLS), you may need to adjust settings
influx_url = "http://10.122.147.28:8181"
token = "apiv3_MnT56_WfZMg4x80uVKDLD_Cjx9jz2tFMCnHISROUdTQAFlpFaSaY0Xl_kFxYfUpI0rITlNe3RDmrom0FXQQ_Rg"
database = "test_1_data"
org = "team fusion"
bucket = "test_1_data"

# Initialize InfluxDB v3 client
# Try without TLS first (use flight_client_options to disable TLS if needed)
try:
    client = InfluxDBClient3(
        host=influx_url,
        token=token,
        org=org,
        database=bucket  # v3 uses 'database' instead of 'bucket'
    )
except Exception as e:
    print(f"Failed to connect with TLS disabled. Error: {e}")
    print("Trying with HTTP protocol...")
    # If the above fails, try with explicit HTTP
    client = InfluxDBClient3(
        host=host,
        port=port,
        token=token,
        database=database,
        org="",  # May be required even if empty
        flight_client_options={
            "disable_server_verification": True,
        }
    )


def log_rl_action(action_id, action_name, reasoning, timestamp=None):
    """
    Log RL agent's action and reasoning to the 'rl_actions' measurement in InfluxDB v3.

    Args:
        action_id (int): The predicted action ID (0-7).
        action_name (str): Name of the action (e.g., 'Charge', 'Discharge').
        reasoning (str): AI-generated reasoning for the action.
        timestamp (datetime, optional): Timestamp for the log. Defaults to current UTC time.
    """
    try:
        # Use provided timestamp or current UTC time
        timestamp_dt = timestamp if timestamp else datetime.utcnow()

        # Create point for RL actions
        point = {
            "measurement": "rl_actions",
            "tags": {
                "action_name": action_name
            },
            "fields": {
                "action_id": action_id,
                "reasoning": str(reasoning)
            },
            "time": timestamp_dt
        }

        # Write to InfluxDB v3
        client.write(record=point)
        print(f"✓ Logged RL action to InfluxDB: {action_name} (ID: {action_id})")

    except Exception as e:
        print(f"❌ Error logging RL action to InfluxDB: {e}")


def map_value(value, source_min, source_max, target_min, target_max):
    """
    Map a value from source range to target range using linear interpolation
    """
    if source_max == source_min:
        return target_min

    # Normalize to 0-1 range
    normalized = (value - source_min) / (source_max - source_min)
    # Clamp to 0-1
    normalized = max(0.0, min(1.0, normalized))
    # Map to target range
    mapped = target_min + normalized * (target_max - target_min)
    return mapped


def query_latest_renewable_gen():
    """Query latest total renewable generation using SQL"""
    query = """
    SELECT current_output
    FROM generation_state
    WHERE time >= now() - INTERVAL '1 hour'
      AND current_output > 0.0
    ORDER BY time DESC
    LIMIT 100
    """
    try:
        table = client.query(query=query)
        df = table.to_pandas()

        if not df.empty and 'current_output' in df.columns:
            total = df['current_output'].sum()
            return total if total > 0 else 0.0
        return 0.0
    except Exception as e:
        print(f"Error querying renewable_gen: {e}")
        return 0.0


def query_latest_battery_soc():
    """Query latest weighted average battery SOC using SQL"""
    query = """
    SELECT device_id, soc, remaining_capacity
    FROM batteries_state
    WHERE device_id LIKE '%BESS%'
    AND time >= now() - INTERVAL '1 hour'
    AND remaining_capacity > 0.0
    ORDER BY time DESC

    """
    try:
        table = client.query(query=query)
        df = table.to_pandas()

        if df.empty:
            return 50.0

        # Get latest record per device
        df_latest = df.groupby('device_id').first().reset_index()

        # Calculate weighted average
        df_latest = df_latest[df_latest['remaining_capacity'] > 0]
        if df_latest.empty:
            return 50.0

        total_weighted = (df_latest['soc'] * df_latest['remaining_capacity']).sum()
        total_capacity = df_latest['remaining_capacity'].sum()

        if total_capacity > 0:
            return total_weighted / total_capacity
        return 50.0
    except Exception as e:
        print(f"Error querying battery_soc: {e}")
        return 50.0


def query_latest_battery_soh():
    """Query latest weighted average battery SOH for BESS devices using SQL"""
    query = """
    SELECT device_id, soh, remaining_capacity, soc
    FROM batteries_state
    WHERE time >= now() - INTERVAL '1 hour'
      AND device_id LIKE 'BESS%'
      AND remaining_capacity > 0.0
      AND soc > 0.0
    ORDER BY time DESC
    """
    try:
        table = client.query(query=query)
        df = table.to_pandas()

        if df.empty:
            return 85.0

        # Get latest record per device
        df_latest = df.groupby('device_id').first().reset_index()

        # Calculate weighted average by nominal capacity
        df_latest['weight'] = df_latest['remaining_capacity'] / (df_latest['soc'] / 100.0)
        total_weighted = (df_latest['soh'] * df_latest['weight']).sum()
        total_weight = df_latest['weight'].sum()

        if total_weight > 0:
            return total_weighted / total_weight
        return 85.0
    except Exception as e:
        print(f"Error querying battery_soh: {e}")
        return 85.0


def query_latest_ev_demand():
    """Query latest total EV power demand using SQL"""
    query = """
    SELECT power
    FROM batteries_state
    WHERE time >= now() - INTERVAL '1 hour'
      AND device_id LIKE 'EV%'
      AND power > 0.0
    ORDER BY time DESC
    LIMIT 100
    """
    try:
        table = client.query(query=query)
        df = table.to_pandas()

        if not df.empty and 'power' in df.columns:
            total = df['power'].sum()
            return total if total > 0 else 5.0
        return 5.0
    except Exception as e:
        print(f"Error querying ev_demand: {e}")
        return 5.0


def query_latest_load_demand():
    """Query latest total load consumption using SQL"""
    query = """
    SELECT power
    FROM consumers_state
    WHERE time >= now() - INTERVAL '1 hour'
      AND power > 0.0
    ORDER BY time DESC
    LIMIT 100
    """
    try:
        table = client.query(query=query)
        df = table.to_pandas()

        if not df.empty and 'power' in df.columns:
            total = df['power'].sum()
            return total if total > 0 else 10.0
        return 10.0
    except Exception as e:
        print(f"Error querying load_demand: {e}")
        return 10.0


def get_test_iot_data(db_data=None):
    """
    Query IoT data from InfluxDB v3 and map to model's expected ranges
    """
    # Query raw values from InfluxDB
    raw_renewable = query_latest_renewable_gen()  # 0-4500
    raw_battery_soc = query_latest_battery_soc()  # 0-100
    raw_battery_soh = query_latest_battery_soh()  # 0-100
    raw_ev_demand = query_latest_ev_demand()  # 0-110
    raw_load_demand = query_latest_load_demand()  # 0-448

    # Map to model's expected ranges
    # renewable_gen: 0-4500 -> 0-80
    mapped_renewable = map_value(raw_renewable, 0, 4500, 0.0, 80.0)

    # battery_soc: 0-100 -> 0-1
    mapped_soc = map_value(raw_battery_soc, 0, 100, 0.0, 1.0)

    # battery_soh: 0-100 -> 0.7-0.95
    mapped_soh = map_value(raw_battery_soh, 0, 100, 0.7, 0.95)

    # ev_demand: 0-110 -> 5-50
    mapped_ev = map_value(raw_ev_demand, 0, 110, 5.0, 50.0)

    # load_demand: 0-448 -> 10-93
    mapped_load = map_value(raw_load_demand, 0, 448, 10.0, 93.0)

    # Calculate current time step (0-95 for 96 steps in a day)
    current_hour = datetime.now().hour
    current_minute = datetime.now().minute
    # Convert to 15-min intervals: hour*4 + minute//15
    time_step = (current_hour * 4) + (current_minute // 15)
    time_step = min(95, max(0, time_step))  # Clamp to 0-95

    # For predicted values, use current values as approximation
    # In production, you might have separate forecasting queries
    predicted_demand_next = mapped_load
    predicted_renewable_next = mapped_renewable

    print(f"\n=== Data Mapping ===")
    print(f"Renewable: {raw_renewable:.1f} kW -> {mapped_renewable:.1f} kW")
    print(f"Battery SOC: {raw_battery_soc:.1f}% -> {mapped_soc:.3f}")
    print(f"Battery SOH: {raw_battery_soh:.1f}% -> {mapped_soh:.3f}")
    print(f"EV Demand: {raw_ev_demand:.1f} kW -> {mapped_ev:.1f} kW")
    print(f"Load Demand: {raw_load_demand:.1f} kW -> {mapped_load:.1f} kW")
    print(f"Time Step: {time_step} (Hour: {current_hour}:{current_minute:02d})")
    print(f"===================\n")

    return {
        "time_step": time_step,
        "renewable_gen": mapped_renewable,
        "battery_soc": mapped_soc,
        "battery_soh": mapped_soh,
        "ev_demand": mapped_ev,
        "load_demand": mapped_load,
        # Hard-coded values
        "grid_price_buy": 8,
        "grid_price_sell": 8,
        "ev_rul": 0.9,
        "emission_factor": 0.45,
        "predicted_demand_next": predicted_demand_next,
        "predicted_renewable_next": predicted_renewable_next
    }


def iot_scenario_to_state(
        scenario: Dict,
        max_renewable: float = 300,
        max_load: float = 200,
        max_ev: float = 50,
        max_price: float = 10
) -> np.ndarray:
    """
    Convert IoT test scenario to environment state vector
    """
    hour = scenario['time_step'] / 4.0  # 15-min timesteps (4 per hour)
    hour_rad = (hour / 24.0) * 2 * np.pi

    state = np.array([
        scenario['time_step'] / 96.0,  # Normalize to 0-1 (96 timesteps per day)
        scenario['renewable_gen'] / max_renewable,
        scenario['load_demand'] / max_load,
        scenario['ev_demand'] / max_ev,
        scenario['battery_soc'],
        scenario['battery_soh'],
        scenario['grid_price_buy'] / max_price,
        scenario['grid_price_sell'] / max_price,
        scenario['grid_price_sell'] / scenario['grid_price_buy'],
        scenario['emission_factor'],
        scenario['predicted_demand_next'] / max_load,
        scenario['predicted_renewable_next'] / max_renewable,
        np.sin(hour_rad),
        np.cos(hour_rad),
        scenario['ev_rul']
    ], dtype=np.float32)

    return state


def test_iot_scenarios_dqn(model_path: str,
                           test_data,
                           verbose: bool = True) -> Dict:
    """
    Test a DQN model on a single IoT scenario
    """
    model = DQN.load(Path(model_path))

    if verbose:
        print(f"\n{'=' * 80}")
        print(f"IoT Test Case - DQN Model")
        print(f"Model: {model_path}")
        print(f"{'=' * 80}\n")

    action_names = ['Idle', 'Export', 'Charge', 'Discharge',
                    'Buy', 'Sell', 'EV+', 'EV-']

    scenario = test_data
    state = iot_scenario_to_state(scenario)
    action, _ = model.predict(state, deterministic=True)
    action_id = int(action)

    predicted_name = action_names[action_id]

    result = {
        'predicted_action': f"{predicted_name} ({action_id})",
        'action_id': action_id,
        'action_name': predicted_name,
        'context': {
            'renewable': scenario['renewable_gen'],
            'load': scenario['load_demand'],
            'ev': scenario['ev_demand'],
            'soc': scenario['battery_soc'],
            'soh': scenario['battery_soh'],
            'price_buy': scenario['grid_price_buy'],
            'price_sell': scenario['grid_price_sell'],
            'time_step': scenario['time_step']
        }
    }

    if verbose:
        print(f"✓ Predicted Action: {predicted_name} (ID: {action_id})")
        print(f"  Context: Renewable={scenario['renewable_gen']:.1f}kW, "
              f"Load={scenario['load_demand']:.1f}kW, "
              f"EV={scenario['ev_demand']:.1f}kW, "
              f"SOC={scenario['battery_soc']:.2f}")

    return result


def run_ai(action_id, iot_data):
    """
    Get AI explanation for the chosen action
    """
    model = "mistral:latest"
    action_descriptions = {
        0: "Idle - No proactive move → rely on natural balance (renewables + grid), maintain natural balance",
        1: "Export - Use renewables to meet load; export surplus to grid",
        2: "Charge - Prioritize storing energy (from renewables if possible): Charge battery with available renewable energy",
        3: "Discharge - Use stored energy to meet demand and reduce imports: Discharge battery to meet load",
        4: "Grid Buy - Buy electricity from grid to meet load",
        5: "Grid Sell - Sell battery energy to grid (if profitable)",
        6: "EV+ - Prioritize EV charging to Aggressively satisfy EV demand (even if costly)",
        7: "EV- - Slow down EV charging to save resources"
    }

    prompt = f"""
You are an expert energy management AI assistant powered by reinforcement learning. 
You are given the following information about the current state of a smart EMS system:

1. IoT Data (current state):
{iot_data}

2. Action ids and its corresponding Descriptions:
{action_descriptions}

3. RL Agent's action id Choice for each reading of iot data:
{action_id}

Task:
- Explain why the RL agent chose the given action, considering the current IoT data.
- Highlight potential future outcomes, and reasoning behind the choice.
- You answer must always be in favour of the RL agent's action.
- Avoid using exact numbers in your answers, rather use quantifying words like high, low, moderate, etc.
- Keep the answer short, sweet and concise.
- Output in the following JSON format:
  {{
    "action_id": {action_id},
    "reasoning": "<detailed human-readable explanation>"
  }}
    """

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.1,
                "num_predict": 1500
            },
            timeout=90
        )

        if response.status_code == 200:
            return response.json().get("response", "")
        else:
            return f"Error calling Ollama: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"


# ========================================
# Main execution block
# ========================================
if __name__ == "__main__":
    import time

    prev_id = None
    cached_ai_res = None
    first_run = True

    print("Starting continuous monitoring loop (Ctrl+C to stop)...\n")
    print(f"Connected to InfluxDB v3 Enterprise at {influx_url}")
    print(f"Database: {database}\n")

    try:
        while True:
            # Get data from InfluxDB and map to model ranges
            input_data = get_test_iot_data()

            # Run DQN model prediction
            res = test_iot_scenarios_dqn(
                "./models/DQN_20251005_005912/best_model/best_model.zip",
                input_data,
                verbose=True
            )

            predicted_id = res['action_id']

            # Generate AI explanation and log on first run or when action changes
            if first_run or predicted_id != prev_id:
                if not first_run:
                    print(f"\n🔄 Action changed from {prev_id} to {predicted_id}")
                else:
                    print(f"\n🚀 Initial action: {predicted_id}")
                    first_run = False

                prev_id = predicted_id

                # Get AI explanation
                print("Generating AI explanation...")
                ai_response = run_ai(predicted_id, input_data)

                try:
                    cached_ai_res = json.loads(ai_response)
                    print("\n=== AI Explanation ===")
                    print(f"Action: {res['action_name']} (ID: {predicted_id})")
                    print(f"Reasoning: {cached_ai_res['reasoning']}")
                    print("=" * 50)

                    # Log to InfluxDB
                    log_rl_action(
                        action_id=predicted_id,
                        action_name=res['action_name'],
                        reasoning=cached_ai_res['reasoning']
                    )

                except json.JSONDecodeError:
                    print(f"\nRaw AI Response:\n{ai_response}")
                    cached_ai_res = {
                        "action_id": predicted_id,
                        "reasoning": ai_response
                    }
                    # Log to InfluxDB even with raw response
                    log_rl_action(
                        action_id=predicted_id,
                        action_name=res['action_name'],
                        reasoning=ai_response
                    )
            else:
                # Action unchanged, display cached explanation
                if cached_ai_res:
                    print(f"\n✓ Action unchanged: {res['action_name']} (ID: {predicted_id})")
                    print(f"Cached Reasoning: {cached_ai_res['reasoning'][:100]}...")
                else:
                    print(f"\n✓ Action unchanged: {res['action_name']} (ID: {predicted_id})")

            print(f"\nWaiting 5 seconds before next check...\n")
            time.sleep(5)

    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring stopped by user")
        print("Final state:")
        if cached_ai_res:
            print(f"  Last Action: ID {prev_id}")
            print(f"  Last Reasoning: {cached_ai_res['reasoning']}")
    except Exception as e:
        print(f"\n❌ Error in monitoring loop: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Close InfluxDB client on exit
        print("Closing InfluxDB connection...")
        client.close()