# Change: Add YOLOv7 Training Automation Manager

## Why
Model training currently requires manual setup of YOLOv7, dataset retrieval, and command execution. Automating these tasks reduces onboarding friction and ensures consistent runs across environments.

## What Changes
- Introduce a standalone Python orchestrator (`train_manager.py`) that clones YOLOv7, installs dependencies, downloads weights, and kicks off training in one step
- Integrate Roboflow dataset retrieval with an easily configurable API key placeholder
- Embed guardrails so reruns skip completed steps and resume quickly

## Impact
- Affected specs: model-training
- Affected code: phase2/train_manager.py, documentation for training workflow
