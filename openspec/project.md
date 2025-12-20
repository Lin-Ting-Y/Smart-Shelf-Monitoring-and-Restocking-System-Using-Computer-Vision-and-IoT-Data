# Project Context

## Purpose
Prototype a smart retail shelf that reports inventory levels over MQTT, triggers cloud-side alerts, and prepares for future vision-based counting so stakeholders can validate the end-to-end pipeline before investing in production hardware.

## Tech Stack
- Python 3.10+ for all edge and cloud scripts
- paho-mqtt for broker communication (broker.emqx.io for demos)
- PyTorch + YOLOv7 + OpenCV for vision inference (Phase 2/3)
- Google Colab for model training workflows
- NVIDIA Jetson Nano (target hardware for Phase 3)

## Project Conventions

### Code Style
Follow PEP 8 with automated formatting via `black` where possible. Use descriptive function names and docstrings for non-trivial routines.

### Architecture Patterns
Event-driven pipeline: edge (publisher) → MQTT broker → cloud/dashboard subscriber. Vision inference replaces mock publisher once validated. Separate modules per deployment stage (mock edge, cloud dashboard, laptop inference, Jetson deployment).

### Testing Strategy
Unit-test data formatting and alert threshold logic with `pytest`. For MQTT flows, rely on integration smoke tests using the public broker and mocked payloads. Vision components validated with recorded demo videos.

### Git Workflow
Trunk-based with short-lived feature branches named `feature/<change-id>`. Conventional commit prefixes (`feat`, `fix`, `docs`, etc.) tied to OpenSpec change IDs in the body.

## Domain Context
Retail shelf monitoring focusing on beverage products (initially Coke). Inventory is represented as total capacity vs detected stock count. Alerts trigger when available stock falls to 30% or lower (≤3 items when capacity is 10).

## Important Constraints
- Public MQTT broker is non-authenticated; avoid transmitting sensitive data.
- Edge scripts must tolerate intermittent network connectivity and retry on publish failure.
- Demo should operate on commodity laptops before migrating to Jetson.
- Vision model must run at ≥10 FPS on laptop to ensure timely alerts.

## External Dependencies
- MQTT broker: `broker.emqx.io` (port 1883)
- Roboflow Universe datasets (retail bottles/SKU-110K) for training
- Google Drive for persisting trained weights in Colab
- OpenCV video capture devices or prerecorded demo footage
