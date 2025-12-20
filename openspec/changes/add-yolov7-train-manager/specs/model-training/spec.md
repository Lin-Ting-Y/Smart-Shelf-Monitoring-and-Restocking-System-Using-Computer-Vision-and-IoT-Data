## ADDED Requirements
### Requirement: Automated YOLOv7 Training Orchestration
The system SHALL provide a single entry-point script that prepares the YOLOv7 training environment, retrieves datasets, and launches training runs without manual intervention.

#### Scenario: Fresh environment bootstrap
- **GIVEN** `train_manager.py` runs in a directory without the `yolov7` repository, weights, or datasets
- **WHEN** the script executes
- **THEN** it clones the YOLOv7 repository, installs requirements, downloads pretrained weights, retrieves the configured dataset, and starts the training process

#### Scenario: Idempotent rerun
- **GIVEN** `train_manager.py` runs in a directory where the repository, weights, and dataset already exist
- **WHEN** the script executes
- **THEN** it skips completed steps and directly launches the YOLOv7 training command using the existing assets
