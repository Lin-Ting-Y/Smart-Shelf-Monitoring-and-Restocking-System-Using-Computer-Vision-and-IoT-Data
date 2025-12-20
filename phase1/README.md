# Phase 1 — Mock Data Pipeline

This phase validates MQTT transport and alert behavior without depending on cameras or trained models.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install paho-mqtt colorama
```

## Scripts

- `mock_edge.py` — Publishes randomized inventory payloads every two seconds to `smart_retail/group3/shelf` on `broker.emqx.io`.
- `cloud_dashboard.py` — Subscribes to the same topic and renders formatted status updates with color-coded alerts.

## Run the demo

1. Start the dashboard subscriber:

   ```bash
   python cloud_dashboard.py
   ```

2. In another terminal, launch the mock publisher:

   ```bash
   python mock_edge.py
   ```

3. Observe green "Status OK" messages for normal stock and red "🚨 RESTOCK ALERT!" messages when stock is ≤3.

Press `Ctrl+C` in each terminal to stop the scripts.
