# Change: Add SKU-110K Local Training Automation

## Why
Roboflow-based downloads may not suit offline or bandwidth-constrained environments. Providing a standalone script that sources a public SKU-110K subset and performs conversion enables fully local training workflows.

## What Changes
- Introduce `train_sku_local.py` to fetch a lightweight SKU retail dataset without Roboflow
- Convert source annotations into YOLO format, generate train/val splits, and wire in YOLOv7 training commands
- Document usage steps and dataset assumptions for contributors operating without hosted services

## Impact
- Affected specs: model-training
- Affected code: train_sku_local.py, supporting documentation
