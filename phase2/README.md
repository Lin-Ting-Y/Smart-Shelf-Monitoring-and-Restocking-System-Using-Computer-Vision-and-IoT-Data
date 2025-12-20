# Phase 2 — YOLOv7 Training Automation

`train_manager.py` automates repository setup, dependency installation, dataset retrieval via Roboflow, and kicks off YOLOv7 training.

`train_sku_local.py` provides an offline-friendly alternative that sources a lightweight retail dataset (or synthesizes one) and launches YOLOv8 through the Ultralytics package without Roboflow.

## Configure secrets

Edit the constants at the top of `train_manager.py`:

- `ROBOFLOW_API_KEY`
- `ROBOFLOW_WORKSPACE`
- `ROBOFLOW_PROJECT`
- `ROBOFLOW_VERSION`

## Run training

```bash
python train_manager.py
```

The script will:

1. Clone `WongKinYiu/yolov7` if missing.
2. Install dependencies from `yolov7/requirements.txt` and ensure `roboflow` is available.
3. Download `yolov7_training.pt` weights if absent.
4. Download the specified dataset in YOLOv7 format (stored under `datasets/`).
5. Launch `yolov7/train.py` with batch size 16 for 50 epochs, saving results under `runs/train/run_retail`.

### Offline retail demo

Use this path when Roboflow access is unavailable or bandwidth is limited.

```bash
python train_sku_local.py
```

The script will:

1. Ensure the `ultralytics` package (YOLOv8) is installed, upgrading `pip` only when needed.
2. Fetch a compact public dataset of bottles/cans/packages and convert labels to YOLO format. If the download fails, it generates a synthetic dataset so training can still proceed.
3. Create `data.yaml` pointing to the prepared train/val splits.
4. Detect GPU availability (defaulting to CPU when CUDA is unavailable).
5. Launch YOLOv8 with batch size 8 for 10 epochs to validate the end-to-end workflow quickly.

## Troubleshooting

- If the dataset download renames the folder differently, update `ROBOFLOW_PROJECT` and rerun.
- For GPU selection, adjust the `--device` argument inside the script (default `0`).
- Use a virtual environment to avoid polluting global Python packages.
