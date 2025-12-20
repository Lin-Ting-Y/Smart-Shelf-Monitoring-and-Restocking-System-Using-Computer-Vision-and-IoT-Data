# Change: Add Mock Smart Shelf Phase 1 Pipeline

## Why
We need to validate MQTT data flow and alert logic before integrating cameras or deploying to Jetson hardware. A mock publisher and dashboard ensure the end-to-end pipeline works with realistic payloads.

## What Changes
- Create a Python mock edge publisher that emits randomized stock payloads over MQTT every two seconds
- Implement a cloud dashboard subscriber that formats updates and surfaces restock alerts when inventory drops to 30% capacity or lower
- Document dependencies and installation command for quick onboarding across contributors

## Impact
- Affected specs: mock-smart-shelf
- Affected code: mock_edge.py, cloud_dashboard.py, supporting setup instructions
