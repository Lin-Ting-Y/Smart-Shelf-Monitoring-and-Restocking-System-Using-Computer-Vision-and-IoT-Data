"""Mock edge publisher that simulates smart shelf inventory events."""
import json
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

BROKER_HOST = "broker.emqx.io"
BROKER_PORT = 1883
TOPIC = "smart_retail/group3/shelf"
PUBLISH_INTERVAL_SECONDS = 2
CAPACITY = 10
LOW_STOCK_THRESHOLD = 3  # aligns with 30% of capacity


def build_payload() -> dict:
    """Return a randomized inventory payload with 80/20 normal-to-low distribution."""
    if random.random() < 0.8:
        current_stock = random.randint(LOW_STOCK_THRESHOLD + 1, CAPACITY)
    else:
        current_stock = random.randint(0, LOW_STOCK_THRESHOLD)
    empty_slots = CAPACITY - current_stock
    return {
        "device_id": "jetson_mock_01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "product_id": "Coke",
        "capacity": CAPACITY,
        "current_stock": current_stock,
        "empty_slots": empty_slots,
    }


def on_connect(client: mqtt.Client, userdata, flags, rc):  # type: ignore[override]
    if rc == 0:
        print("[publisher] Connected to MQTT broker")
    else:
        print(f"[publisher] Failed to connect, return code {rc}")


def main() -> None:
    client = mqtt.Client()
    client.on_connect = on_connect

    while True:
        try:
            client.connect(BROKER_HOST, BROKER_PORT)
            break
        except Exception as exc:  # noqa: BLE001 - surface connection errors
            print(f"[publisher] Connection error: {exc}. Retrying in 5s...")
            time.sleep(5)

    client.loop_start()

    try:
        while True:
            payload = build_payload()
            message = json.dumps(payload)
            result = client.publish(TOPIC, message, qos=1)
            status = result[0]
            if status == mqtt.MQTT_ERR_SUCCESS:
                print(f"[publisher] Published: {message}")
            else:
                print(f"[publisher] Publish failed with status {status}")
            time.sleep(PUBLISH_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("[publisher] Stopping publisher")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
