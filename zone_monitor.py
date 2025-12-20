import cv2
import json
import argparse
import sys
from pathlib import Path
import numpy as np
import time
from collections import deque  # 新增：用來記錄歷史數據
from ultralytics import YOLO
import paho.mqtt.client as mqtt

# ==========================================
# 參數設定
# ==========================================
GAP_FACTOR = 0.8        # 間隙判定係數
CONFIDENCE_THRESHOLD = 0.3 

# --- 防遮擋 (Anti-Occlusion) 設定 ---
HISTORY_LEN = 30        # 參考過去多少幀的數據 (30幀約等於1秒)
DROP_RATIO = 0.6        # 驟降比例 (當前數量 < 平均數量 * 0.6 視為被遮擋)
# ----------------------------------

# MQTT 設定
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "smart_retail/amber/shelf"

# ==========================================

def load_config(config_path):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            print(f"✅ 成功載入設定檔: {config_path}")
            return json.load(f)
    except Exception as e:
        print(f"⚠️ 無法讀取設定檔: {e}，請確認是否已建立 config.json")
        sys.exit(1)

def draw_dashed_rect(img, pt1, pt2, color, thickness=2, style='dotted'):
    points = [pt1, (pt2[0], pt1[1]), pt2, (pt1[0], pt2[1])]
    for i in range(4):
        p1 = points[i]
        p2 = points[(i+1)%4]
        cv2.line(img, p1, p2, color, thickness)

def detect_gaps_in_zone(boxes, zone_coords):
    zx1, zy1, zx2, zy2 = zone_coords
    
    # 如果 boxes 是空的，由主程式決定是否回傳空，這裡單純處理邏輯
    if len(boxes) < 1:
        return [(zx1, zy1, zx2, zy2)], 0

    sorted_boxes = sorted(boxes, key=lambda b: b[0])
    widths = [b[2] - b[0] for b in sorted_boxes]
    avg_width = float(np.mean(widths))
    
    gaps = []

    # 左邊界
    first_box = sorted_boxes[0]
    left_gap = first_box[0] - zx1
    if left_gap > avg_width * GAP_FACTOR:
        missing_count = int(left_gap // avg_width)
        for i in range(missing_count):
            gx1 = int(zx1 + i * avg_width)
            gx2 = int(gx1 + avg_width)
            gaps.append((gx1, int(first_box[1]), gx2, int(first_box[3])))

    # 中間
    for i in range(len(sorted_boxes) - 1):
        curr_box = sorted_boxes[i]
        next_box = sorted_boxes[i+1]
        gap_size = next_box[0] - curr_box[2]
        if gap_size > avg_width * GAP_FACTOR:
            missing_count = int(gap_size // avg_width)
            for k in range(missing_count):
                gx1 = int(curr_box[2] + k * avg_width)
                gx2 = int(gx1 + avg_width)
                gy1 = min(curr_box[1], next_box[1])
                gy2 = max(curr_box[3], next_box[3])
                gaps.append((gx1, int(gy1), gx2, int(gy2)))

    # 右邊界
    last_box = sorted_boxes[-1]
    right_gap = zx2 - last_box[2]
    if right_gap > avg_width * GAP_FACTOR:
        missing_count = int(right_gap // avg_width)
        for i in range(missing_count):
            gx1 = int(last_box[2] + i * avg_width)
            gx2 = int(gx1 + avg_width)
            if gx2 > zx2: break 
            gaps.append((gx1, int(last_box[1]), gx2, int(last_box[3])))

    return gaps, avg_width

def run_monitor(args):
    config = load_config(args.config)
    zones = config.get('zones', [])
    
    print(f"🚀 載入模型: {args.weights}")
    model = YOLO(args.weights)
    
    # 建立每個區域的歷史紀錄器 { 'zone_id': deque([10, 10, 9...]) }
    zone_histories = {zone['id']: deque(maxlen=HISTORY_LEN) for zone in zones}

    client = mqtt.Client()
    try:
        client.connect(MQTT_BROKER, MQTT_PORT)
        client.loop_start()
        print("📡 MQTT 連線成功")
    except:
        print("⚠️ MQTT 連線失敗 (可忽略)")

    source = int(args.source) if args.source.isdigit() else args.source
    cap = cv2.VideoCapture(source)

    video_writer = None
    output_path = Path(args.output) if getattr(args, "output", None) else None
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    while True:
        ret, frame = cap.read()
        if not ret: break

        results = model(frame, verbose=False)
        detections = results[0].boxes.data.tolist()

        mqtt_payload = {"total_gaps": 0, "details": {}}

        for zone in zones:
            zid = zone['id']
            p_name = zone['product']
            zx1, zy1, zx2, zy2 = zone['coords']
            
            # 畫出區域框 (黃色)
            cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), (0, 255, 255), 1)

            # 3.1 找出區域內的物體
            zone_boxes = []
            for det in detections:
                x1, y1, x2, y2, conf, cls = det
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                if zx1 < center_x < zx2 and zy1 < center_y < zy2:
                    zone_boxes.append([x1, y1, x2, y2])
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)

            current_count = len(zone_boxes)
            
            # =========================================================
            # 🔥 新增：防遮擋機制 (Anti-Occlusion Logic)
            # =========================================================
            history = zone_histories[zid]
            
            # 計算歷史平均 (避免除以零)
            avg_count = sum(history) / len(history) if len(history) > 0 else current_count
            
            # 判斷是否被遮擋：
            # 條件1: 歷史數據要足夠 (至少累積 10 幀，避免剛開機就誤判)
            # 條件2: 當前數量 < 平均數量 * 0.6 (驟降 40% 以上)
            is_blocked = False
            if len(history) > 10 and current_count < avg_count * DROP_RATIO:
                is_blocked = True
            
            # 更新歷史數據 (如果被遮擋，就不要把這個異常低的數字寫入歷史，以免拉低平均)
            if not is_blocked:
                history.append(current_count)
            # =========================================================

            if is_blocked:
                # ⚠️ 狀態：被遮擋
                # 顯示黃色警告，不計算缺貨，不畫紅框
                warning_text = "VIEW BLOCKED"
                text_size, _ = cv2.getTextSize(warning_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
                # 在區域中央顯示警告
                center_x_zone = (zx1 + zx2) // 2 - text_size[0] // 2
                center_y_zone = (zy1 + zy2) // 2
                
                cv2.rectangle(frame, (center_x_zone-5, center_y_zone-25), 
                             (center_x_zone + text_size[0]+5, center_y_zone+5), (0, 255, 255), -1)
                cv2.putText(frame, warning_text, (center_x_zone, center_y_zone), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
                
                # MQTT 狀態傳送 Blocked
                mqtt_payload["details"][p_name] = {"status": "blocked"}

            else:
                # ✅ 狀態：正常 (執行缺貨偵測)
                gaps, avg_w = detect_gaps_in_zone(zone_boxes, [zx1, zy1, zx2, zy2])
                
                for gx1, gy1, gx2, gy2 in gaps:
                    draw_dashed_rect(frame, (gx1, gy1), (gx2, gy2), (0, 0, 255), 2)
                    cv2.putText(frame, "EMPTY", (gx1, gy1+20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

                stock_count = current_count
                gap_count = len(gaps)
                mqtt_payload["details"][p_name] = {"stock": stock_count, "missing": gap_count}
                mqtt_payload["total_gaps"] += gap_count
                
                info_text = f"{p_name}: {stock_count}"
                cv2.putText(frame, info_text, (zx1, zy1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)


        if output_path and video_writer is None:
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            height, width = frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            video_writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        if video_writer is not None:
            video_writer.write(frame)

        cv2.imshow('Smart Gap Monitor', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    if video_writer is not None:
        video_writer.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default='config.json')
    parser.add_argument('--weights', type=str, default='best.pt')
    parser.add_argument('--source', type=str, default='0')
    parser.add_argument('--output', type=str, help='輸出影片路徑')
    args = parser.parse_args()
    run_monitor(args)