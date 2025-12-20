import streamlit as st
import cv2
import json
import numpy as np
import tempfile
import os
import time
from collections import deque
from ultralytics import YOLO

# ==========================================
# 頁面設定
# ==========================================
st.set_page_config(page_title="AIOT 智慧零售系統", layout="wide")

# ==========================================
# 共用函式庫
# ==========================================

# 設定基礎路徑 (確保與 app.py 同目錄)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_asset_path(filename):
    return os.path.join(BASE_DIR, filename)

def load_config(filename='config.json'):
    path = get_asset_path(filename)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def draw_dashed_rect(img, pt1, pt2, color, thickness=2):
    points = [pt1, (pt2[0], pt1[1]), pt2, (pt1[0], pt2[1])]
    for i in range(4):
        p1 = points[i]
        p2 = points[(i+1)%4]
        cv2.line(img, p1, p2, color, thickness)

def detect_gaps_in_zone(boxes, zone_coords, gap_factor):
    zx1, zy1, zx2, zy2 = zone_coords
    if len(boxes) < 1:
        return [(zx1, zy1, zx2, zy2)], 0

    sorted_boxes = sorted(boxes, key=lambda b: b[0])
    widths = [b[2] - b[0] for b in sorted_boxes]
    avg_width = float(np.mean(widths))
    
    if avg_width == 0: return [], 0
    
    gaps = []
    # 左邊界
    first_box = sorted_boxes[0]
    left_gap = first_box[0] - zx1
    if left_gap > avg_width * gap_factor:
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
        if gap_size > avg_width * gap_factor:
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
    if right_gap > avg_width * gap_factor:
        missing_count = int(right_gap // avg_width)
        for i in range(missing_count):
            gx1 = int(last_box[2] + i * avg_width)
            gx2 = int(gx1 + avg_width)
            if gx2 > zx2:
                break
            gaps.append((gx1, int(last_box[1]), gx2, int(last_box[3])))

    return gaps, avg_width

# ==========================================
# 主介面開始
# ==========================================

st.title("🥤 AIOT 智慧零售 - 智慧監控")
st.markdown("依賴既有的 `config.json` 與 `models/best.pt`，僅提供監控執行介面。")

config = load_config('config.json')

col_setup, col_dashboard = st.columns([1, 4])

with col_setup:
    st.subheader("⚙️ 參數控制")

    if config:
        st.success(f"已載入 {len(config.get('zones', []))} 個區域設定")
        with st.expander("查看區域設定"):
            st.json(config)
    else:
        st.error("找不到 config.json，請先透過既有工具建立設定檔。")

    monitor_file = st.file_uploader("選擇監控影片", type=['mp4', 'avi'], key="monitor_upload")

    st.markdown("---")
    conf_thres = st.slider("YOLO 信心度", 0.1, 1.0, 0.3)
    gap_factor = st.slider("間隙判定係數", 0.5, 1.5, 0.8)

    st.markdown("---")
    run_btn = st.checkbox("🚀 啟動推論", value=False)

    if not run_btn:
        st.info("準備好後請勾選啟動")

with col_dashboard:
    monitor_placeholder = st.empty()
    stats_container = st.empty()

if run_btn:
    if not config:
        st.error("❌ 找不到 config.json！請先建立設定檔後再啟動監控。")
        st.stop()
    if monitor_file is None:
        st.warning("請先選擇監控影片再勾選啟動。")
        st.stop()

    try:
        model_path = get_asset_path('models/best.pt')
        model = YOLO(model_path)
    except Exception:
        st.error(f"❌ 找不到 best.pt 模型檔 (路徑: {get_asset_path('models/best.pt')})。")
        st.stop()

    # 處理影片
    tfile_mon = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile_mon.write(monitor_file.read())
    tfile_mon.close()

    video_path_mon = tfile_mon.name
    cap = cv2.VideoCapture(video_path_mon)

    history_len = 30
    zone_histories = {zone['id']: deque(maxlen=history_len) for zone in config.get('zones', [])}

    while cap.isOpened() and run_btn:
        ret, frame = cap.read()
        if not ret:
            st.warning("影片播放結束")
            break

        results = model(frame, conf=conf_thres, verbose=False)
        detections = results[0].boxes.data.tolist()

        zones = config.get('zones', [])
        current_stats = {}

        for zone in zones:
            zid = zone['id']
            p_name = zone['product']
            zx1, zy1, zx2, zy2 = zone['coords']

            cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), (0, 255, 255), 1)

            zone_boxes = []
            for det in detections:
                x1, y1, x2, y2, conf, cls = det
                cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                if zx1 < cx < zx2 and zy1 < cy < zy2:
                    zone_boxes.append([x1, y1, x2, y2])
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)

            current_count = len(zone_boxes)
            history = zone_histories[zid]
            avg_count = sum(history) / len(history) if len(history) > 0 else current_count

            is_blocked = False
            if len(history) > 10 and current_count < avg_count * 0.6:
                is_blocked = True

            if not is_blocked:
                history.append(current_count)

            if is_blocked:
                cv2.putText(frame, "BLOCKED", (zx1, zy1 + 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)
                status_text = "⚠️ 視線受阻"
                gap_count = 0
            else:
                gaps, _ = detect_gaps_in_zone(zone_boxes, [zx1, zy1, zx2, zy2], gap_factor)
                for gx1, gy1, gx2, gy2 in gaps:
                    draw_dashed_rect(frame, (gx1, gy1), (gx2, gy2), (0, 0, 255), 2)
                status_text = "🟢 監控中"
                gap_count = len(gaps)

            current_stats[p_name] = {"stock": current_count, "gap": gap_count, "status": status_text}

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        monitor_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)

        with stats_container.container():
            if len(current_stats) > 0:
                cols = st.columns(len(current_stats))
                for idx, (pname, data) in enumerate(current_stats.items()):
                    with cols[idx]:
                        with st.container(border=True):
                            st.markdown(f"**{pname}**")
                            c1, c2 = st.columns(2)
                            c1.metric("現貨", data['stock'])
                            c2.metric("缺貨", data['gap'], delta_color="inverse")
                            if data['status'] == "⚠️ 視線受阻":
                                st.warning(data['status'])
                            else:
                                st.caption(data['status'])

        time.sleep(0.01)

    cap.release()

    try:
        os.unlink(video_path_mon)
    except Exception:
        pass