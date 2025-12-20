## ADDED Requirements
### Requirement: Offline SKU Dataset Training Automation
The system SHALL ship a single-command workflow that downloads a publicly hosted retail dataset, converts annotations to YOLO format, and launches YOLOv8 training via the Ultralytics package without Roboflow dependencies.

#### Scenario: Fresh offline setup
- **GIVEN** `train_sku_local.py` runs in an environment without the dataset present
- **WHEN** the script executes
- **THEN** it fetches the dataset archive from the public URL, extracts it, converts annotations, prepares train/val splits, generates `data.yaml`, installs Ultralytics if needed, and starts YOLOv8 training

#### Scenario: Subsequent rerun
- **GIVEN** `train_sku_local.py` reruns after assets were already downloaded and converted
- **WHEN** the script executes
- **THEN** it skips redundant downloads/conversions and resumes YOLOv8 training with the existing YOLO-formatted dataset
