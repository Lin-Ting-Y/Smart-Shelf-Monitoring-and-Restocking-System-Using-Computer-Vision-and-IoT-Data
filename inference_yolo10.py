"""YOLOv10 inference with dynamic gap detection and zone-aware MQTT updates."""
from __future__ import annotations

import json
import sys
import time
from collections import deque
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np
import paho.mqtt.client as mqtt
from ultralytics import YOLO

BROKER_HOST = "broker.emqx.io"
BROKER_PORT = 1883
TOPIC = "smart_retail/group3/shelf"

MODEL_PATH = Path("models/best.pt")
PUBLISH_INTERVAL_SECONDS = 1.0
CONFIDENCE_THRESHOLD = 0.15
WINDOW_NAME = "YOLOv10 Shelf Monitor"
VIDEO_SOURCE_DEFAULT: int | str = 0  # overridden by CLI argument
GAP_FACTOR = 0.8
STATUS_LABEL = "Tracking"
ZONE_LEFT_LABEL = "Product A"
ZONE_RIGHT_LABEL = "Product B"
OUTPUT_DIR = Path("outputs")
OCCLUSION_WINDOW = 30
OCCLUSION_DROP_RATIO = 0.6
IGNORE_ZONES: list[tuple[int, int]] = [(310, 360)]
SHELF_START_X = 50
SHELF_END_X = 600


def ensure_model_exists(model_path: Path) -> None:
    if not model_path.exists():
        raise FileNotFoundError(f"Expected model weights at {model_path} (see Task 2.1)")


def resolve_video_source() -> int | str:
    if len(sys.argv) <= 1:
        return VIDEO_SOURCE_DEFAULT
    candidate = Path(sys.argv[1])
    if not candidate.exists():
        raise FileNotFoundError(f"Video file not found: {candidate}")
    return str(candidate)


def extract_detections(result) -> list[tuple[float, float, float, float, float]]:
    boxes = []
    for box in result.boxes:
        conf = float(box.conf.item())
        if conf < CONFIDENCE_THRESHOLD:
            continue
        x1, y1, x2, y2 = map(float, box.xyxy[0].tolist())
        boxes.append((x1, y1, x2, y2, conf))
    return boxes


def classify_detections(
    boxes: list[tuple[float, float, float, float, float]],
    divider_x: float,
) -> tuple[list[tuple[float, float, float, float, float, str]], dict[str, int]]:
    classified: list[tuple[float, float, float, float, float, str]] = []
    counts = {ZONE_LEFT_LABEL: 0, ZONE_RIGHT_LABEL: 0}
    for x1, y1, x2, y2, conf in boxes:
        center_x = (x1 + x2) / 2
        label = ZONE_LEFT_LABEL if center_x < divider_x else ZONE_RIGHT_LABEL
        counts[label] += 1
        classified.append((x1, y1, x2, y2, conf, label))
    return classified, counts


def draw_product_boxes(
    frame,
    boxes: list[tuple[float, float, float, float, float, str]],
) -> None:
    for x1, y1, x2, y2, conf, label in boxes:
        p1 = (int(x1), int(y1))
        p2 = (int(x2), int(y2))
        cv2.rectangle(frame, p1, p2, (0, 200, 0), 2)
        cv2.putText(
            frame,
            f"{label} {conf:.2f}",
            (p1[0], max(p1[1] - 10, 15)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 200, 0),
            1,
        )


def detect_gaps_for_row(
    row_boxes: list[tuple[float, float, float, float, float]],
    gap_factor: float,
    frame_width: int,
) -> tuple[list[tuple[int, int, int, int]], float]:
    if len(row_boxes) < 2:
        return [], 0.0

    sorted_boxes = sorted(row_boxes, key=lambda b: b[0])
    widths = [b[2] - b[0] for b in sorted_boxes]
    avg_width = float(np.mean(widths)) if widths else 0.0
    if avg_width <= 0:
        return [], 0.0

    gaps: list[tuple[int, int, int, int]] = []

    # Check head gap against shelf start anchor
    first_box = sorted_boxes[0]
    gap_left = first_box[0] - SHELF_START_X
    if gap_left > avg_width * gap_factor:
        num_missing = max(int(round(gap_left / avg_width)), 1)
        for index in range(num_missing):
            left = int(first_box[0] - (index + 1) * avg_width)
            right = int(left + avg_width)
            if right <= SHELF_START_X:
                break
            mid_x = (left + right) / 2
            if any(start <= mid_x <= end for start, end in IGNORE_ZONES):
                continue
            top = int(first_box[1])
            bottom = int(first_box[3])
            gaps.append((max(int(SHELF_START_X), left), top, right, bottom))

    for current, nxt in zip(sorted_boxes, sorted_boxes[1:]):
        gap_start = current[2]
        gap_end = nxt[0]
        gap_size = gap_end - gap_start
        if gap_size <= avg_width * gap_factor:
            continue

        num_missing = max(int(round(gap_size / avg_width)), 1)
        for index in range(num_missing):
            left = int(gap_start + index * avg_width)
            right = int(left + avg_width)
            if right > frame_width:
                break
            mid_x = (left + right) / 2
            if any(start <= mid_x <= end for start, end in IGNORE_ZONES):
                continue
            top = int(min(current[1], nxt[1]))
            bottom = int(max(current[3], nxt[3]))
            gaps.append((left, top, right, bottom))

    # Check tail gap against shelf end anchor
    last_box = sorted_boxes[-1]
    gap_right = SHELF_END_X - last_box[2]
    if gap_right > avg_width * gap_factor:
        num_missing = max(int(round(gap_right / avg_width)), 1)
        for index in range(num_missing):
            left = int(last_box[2] + index * avg_width)
            right = int(left + avg_width)
            if left >= SHELF_END_X:
                break
            mid_x = (left + right) / 2
            if any(start <= mid_x <= end for start, end in IGNORE_ZONES):
                continue
            top = int(last_box[1])
            bottom = int(last_box[3])
            gaps.append((left, top, min(int(SHELF_END_X), right), bottom))

    return gaps, avg_width

def draw_dashed_rectangle(
    frame,
    box: tuple[int, int, int, int],
    color: tuple[int, int, int],
    dash_length: int = 10,
) -> None:
    left, top, right, bottom = box
    segments = [
        ((left, top), (right, top)),
        ((right, top), (right, bottom)),
        ((right, bottom), (left, bottom)),
        ((left, bottom), (left, top)),
    ]
    for start, end in segments:
        total_length = np.hypot(end[0] - start[0], end[1] - start[1])
        if total_length == 0:
            continue
        steps = max(int(total_length // dash_length), 1)
        for idx in range(0, steps, 2):
            fraction_start = idx / steps
            fraction_end = min((idx + 1) / steps, 1.0)
            p_start = (
                int(start[0] + (end[0] - start[0]) * fraction_start),
                int(start[1] + (end[1] - start[1]) * fraction_start),
            )
            p_end = (
                int(start[0] + (end[0] - start[0]) * fraction_end),
                int(start[1] + (end[1] - start[1]) * fraction_end),
            )
            cv2.line(frame, p_start, p_end, color, 2)


def publish_inventory(
    client: mqtt.Client,
    total: int,
    zone_counts: dict[str, int],
    gap_count: int,
    status: str,
) -> None:
    payload = {
        "total": total,
        "details": {
            ZONE_LEFT_LABEL: zone_counts.get(ZONE_LEFT_LABEL, 0),
            ZONE_RIGHT_LABEL: zone_counts.get(ZONE_RIGHT_LABEL, 0),
        },
        "gaps": gap_count,
        "status": status,
    }
    message = json.dumps(payload)
    result = client.publish(TOPIC, message, qos=1)
    if result.rc != mqtt.MQTT_ERR_SUCCESS:
        print(f"[inference] Publish failed with status {result.rc}")


def cluster_rows(
    boxes: Iterable[tuple[float, float, float, float, float]],
    y_threshold: float,
) -> list[list[tuple[float, float, float, float, float]]]:
    rows: list[list[tuple[float, float, float, float, float]]] = []
    centers: list[float] = []

    for box in sorted(boxes, key=lambda b: (b[1] + b[3]) / 2):
        center_y = (box[1] + box[3]) / 2
        for idx, current_center in enumerate(centers):
            if abs(center_y - current_center) <= y_threshold:
                rows[idx].append(box)
                centers[idx] = (current_center * (len(rows[idx]) - 1) + center_y) / len(rows[idx])
                break
        else:
            rows.append([box])
            centers.append(center_y)

    return rows


def main() -> None:
    ensure_model_exists(MODEL_PATH)

    print(f"[inference] Loading YOLOv10 weights from {MODEL_PATH}")
    model = YOLO(str(MODEL_PATH))
    print(f"[inference] model.names -> {model.names}")

    try:
        source = resolve_video_source()
    except FileNotFoundError as exc:
        print(f"[inference] {exc}")
        sys.exit(1)

    if isinstance(source, str):
        print(f"[inference] Playing video source {source}")
    else:
        print("[inference] Initializing webcam feed")

    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        print("[inference] Unable to open video source")
        sys.exit(1)

    client = mqtt.Client()

    print(f"[inference] Connecting to MQTT broker at {BROKER_HOST}:{BROKER_PORT}")
    client.connect(BROKER_HOST, BROKER_PORT)
    client.loop_start()

    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    if fps <= 0:
        fps = 30.0
    writer: cv2.VideoWriter | None = None
    output_path: Path | None = None
    recent_counts: deque[int] = deque(maxlen=OCCLUSION_WINDOW)
    last_avg_width = 0.0

    last_publish_time = 0.0
    try:
        while True:
            success, frame = capture.read()
            if not success:
                print("[inference] Video stream ended or frame grab failed")
                break

            if writer is None:
                height, width = frame.shape[:2]
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                if isinstance(source, str):
                    stem = Path(source).stem
                else:
                    stem = f"webcam_{int(time.time())}"
                output_path = OUTPUT_DIR / f"{stem}_annotated.mp4"
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
                if not writer.isOpened():
                    print(f"[inference] Failed to open writer at {output_path}")
                    writer = None
                else:
                    print(f"[inference] Writing annotated video to {output_path}")

            results = model.predict(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)
            if not results:
                continue

            result = results[0]
            detections = extract_detections(result)
            height, width = frame.shape[:2]
            divider_x = width / 2
            classified_boxes, zone_counts = classify_detections(detections, divider_x)
            draw_product_boxes(frame, classified_boxes)

            detected_count = len(detections)
            recent_counts.append(detected_count)
            avg_count = float(sum(recent_counts)) / len(recent_counts) if recent_counts else float(detected_count)
            occlusion_ready = len(recent_counts) >= max(5, OCCLUSION_WINDOW // 3)
            occluded = occlusion_ready and avg_count > 0 and detected_count < avg_count * OCCLUSION_DROP_RATIO

            gap_boxes: list[tuple[int, int, int, int]] = []
            if not occluded:
                avg_widths: list[float] = []
                row_clusters = cluster_rows(detections, y_threshold=50.0)
                for row in row_clusters:
                    if not row:
                        continue
                    row_gaps, row_avg_width = detect_gaps_for_row(row, GAP_FACTOR, width)
                    gap_boxes.extend(row_gaps)
                    if row_avg_width > 0:
                        avg_widths.append(row_avg_width)
                        center_y = int(sum((box[1] + box[3]) / 2 for box in row) / len(row))
                        cv2.line(frame, (0, center_y), (width, center_y), (100, 100, 255), 1)
                    for gap_box in row_gaps:
                        draw_dashed_rectangle(frame, gap_box, (0, 0, 255))

                for start, end in IGNORE_ZONES:
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (int(start), 0), (int(end), height), (80, 80, 80), -1)
                    alpha = 0.15
                    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

                avg_width = float(np.mean(avg_widths)) if avg_widths else 0.0
                if avg_width > 0:
                    last_avg_width = avg_width
            else:
                avg_width = last_avg_width

            gap_count = len(gap_boxes)
            status_text = STATUS_LABEL if not occluded else "Blocked"
            cv2.putText(
                frame,
                f"Detections: {detected_count}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                frame,
                status_text,
                (10, 65),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 0),
                2,
            )
            cv2.putText(
                frame,
                f"Avg W: {avg_width:.1f}px",
                (10, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (200, 200, 200),
                2,
            )

            if occluded:
                warning_text = "⚠️ VIEW BLOCKED / RESTOCKING"
                text_size, _ = cv2.getTextSize(warning_text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)
                text_x = max((width - text_size[0]) // 2, 10)
                text_y = max((height + text_size[1]) // 2, text_size[1] + 10)
                cv2.putText(
                    frame,
                    warning_text,
                    (text_x, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.2,
                    (0, 255, 255),
                    3,
                )

            now = time.time()
            if now - last_publish_time >= PUBLISH_INTERVAL_SECONDS:
                if not occluded:
                    publish_inventory(client, detected_count, zone_counts, gap_count, STATUS_LABEL)
                else:
                    publish_inventory(client, detected_count, zone_counts, 0, "Blocked")
                last_publish_time = now

            if writer is not None:
                writer.write(frame)

            cv2.imshow(WINDOW_NAME, frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("[inference] Quit signal received")
                break
    except KeyboardInterrupt:
        print("[inference] Interrupted by user")
    finally:
        client.loop_stop()
        client.disconnect()
        capture.release()
        if writer is not None:
            writer.release()
            if output_path is not None:
                print(f"[inference] Saved annotated video to {output_path}")
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
