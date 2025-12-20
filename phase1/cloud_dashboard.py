"""Cloud dashboard subscriber that renders smart shelf status with gap alerts."""
import json
import os
from datetime import datetime
from typing import Any, Dict, Iterable

import colorama
import paho.mqtt.client as mqtt

BROKER_HOST = "broker.emqx.io"
BROKER_PORT = 1883
TOPIC = "smart_retail/group3/shelf"
BAR_CAPACITY = 6
LOW_STOCK_THRESHOLD = 3

colorama.init(autoreset=True)


def format_timestamp(ts: str) -> str:
    try:
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ts


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def sanitize_details(details: Any) -> Dict[str, int]:
    if isinstance(details, dict):
        sanitized: Dict[str, int] = {}
        for key, value in details.items():
            try:
                sanitized[str(key)] = max(0, int(value))
            except (TypeError, ValueError):
                continue
        return sanitized
    return {}


def draw_bar(count: int) -> str:
    filled = min(max(count, 0), BAR_CAPACITY)
    return "■" * filled + "." * (BAR_CAPACITY - filled)


def render_dashboard(payload: Dict[str, Any]) -> None:
    clear_screen()

    timestamp = format_timestamp(str(payload.get("timestamp", "")))
    device = payload.get("device_id", "Unknown Device")
    status_msg = payload.get("status", "")

    gaps = 0
    try:
        gaps = int(payload.get("gaps", 0))
    except (TypeError, ValueError):
        gaps = 0

    details = sanitize_details(payload.get("details"))
    if not details:
        count = payload.get("count")
        if isinstance(count, int):
            details = {"Zone A": max(0, count)}

    low_stock_zones = [zone for zone, value in details.items() if value <= LOW_STOCK_THRESHOLD]
    has_low_stock = bool(low_stock_zones)

    status_warning = gaps > 0 or has_low_stock
    if gaps > 0:
        overall_color = colorama.Fore.RED
        overall_state = "WARNING"
    elif has_low_stock:
        overall_color = colorama.Fore.YELLOW
        overall_state = "WARNING"
    else:
        overall_color = colorama.Fore.GREEN
        overall_state = "NORMAL"

    print(colorama.Style.BRIGHT + "Smart Retail Monitor")
    print(f"Updated: {timestamp}")
    print(f"Device: {device}")
    if status_msg:
        print(f"Status Msg: {status_msg}")
    print()

    if details:
        print("Zones:")
        for zone, value in details.items():
            color = colorama.Fore.GREEN if value > LOW_STOCK_THRESHOLD else colorama.Fore.YELLOW
            bar = draw_bar(value)
            print(f"  {zone:<12} {color}{bar} {value}/{BAR_CAPACITY}")
    else:
        print("Zones: (no data)")

    print()
    if gaps > 0:
        print(colorama.Fore.RED + colorama.Style.BRIGHT + "🚨 GAP DETECTED! Restock Needed!")
        print(colorama.Fore.RED + f"Detected gaps: {gaps}")
    else:
        print(colorama.Fore.GREEN + "✅ Shelf Organized")

    print()
    print(overall_color + f"Overall Status: {overall_state}")
    if low_stock_zones:
        zones = ", ".join(low_stock_zones)
        print(colorama.Fore.YELLOW + f"Low stock zones: {zones}")


def on_connect(client: mqtt.Client, userdata, flags, rc):  # type: ignore[override]
    if rc == 0:
        print("[dashboard] Connected to MQTT broker. Waiting for messages...")
        client.subscribe(TOPIC, qos=1)
    else:
        print(f"[dashboard] Failed to connect, return code {rc}")


def on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:  # type: ignore[override]
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except json.JSONDecodeError:
        print(f"[dashboard] Received malformed payload: {msg.payload}")
        return

    render_dashboard(payload)


def main() -> None:
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER_HOST, BROKER_PORT)
    except Exception as exc:  # noqa: BLE001
        print(f"[dashboard] Connection error: {exc}")
        return

    print("[dashboard] Listening on topic smart_retail/group3/shelf")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("[dashboard] Stopping dashboard")


if __name__ == "__main__":
    main()
