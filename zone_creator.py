import cv2
import json
import os
import argparse

# ==========================================
# 參數設定
# ==========================================
OUTPUT_FILE = 'config.json'
# ==========================================

# 全域變數
drawing = False
ix, iy = -1, -1
current_rect = None
zones = []
zone_counter = 1

def mouse_callback(event, x, y, flags, param):
    global ix, iy, drawing, current_rect

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix, iy = x, y
        current_rect = None

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            current_rect = (ix, iy, x, y)

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        current_rect = (ix, iy, x, y)

def save_config(zones, width, height):
    data = {
        "description": "Shelf Area Config",
        "resolution": [width, height],
        "zones": zones
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"\n✅ 設定檔已儲存至: {os.path.abspath(OUTPUT_FILE)}")
    print(f"   共包含 {len(zones)} 個區域")

def main(args):
    global zones, zone_counter, current_rect
    
    source = args.source
    if source.isdigit():
        source = int(source)
    
    print(f"📂 正在開啟來源: {source}")
    cap = cv2.VideoCapture(source)
    
    if not cap.isOpened():
        print(f"❌ 無法開啟影片/鏡頭: {source}")
        return

    # 取得原始解析度
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"ℹ️ 來源解析度: {width} x {height}")

    window_name = 'Zone Creator'
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1024, 600)
    cv2.setMouseCallback(window_name, mouse_callback)

    print("="*50)
    print(f"🎯 區域標記工具 (Zone Creator)")
    print("="*50)
    print("💡 視窗可自由縮放，配合 p 暫停來慢慢標記。")
    print("1. [滑鼠拖拉] 畫出 '整排貨架' 的大範圍")
    print("2. [終端機] 輸入名稱 (如: Coke)")
    print("3. [按 p] 暫停/繼續播放")
    print("4. [按 s] 存檔")
    print("="*50)

    paused = False
    frame = None

    while True:
        if not paused:
            ret, next_frame = cap.read()
            if not ret:
                if isinstance(source, str):
                    print("影片播放結束，已自動回到開頭。")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                break
            frame = next_frame
        elif frame is None:
            # 尚未讀到畫面就按暫停，直接跳過一次迴圈
            paused = False
            continue

        display_frame = frame.copy()

        for z in zones:
            x1, y1, x2, y2 = z['coords']
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(display_frame, z['product'], (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        if current_rect:
            x1, y1, x2, y2 = current_rect
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 255), 2)

        cv2.imshow(window_name, display_frame)
        
        delay = 1 if paused else (30 if isinstance(source, str) else 1)
        key = cv2.waitKey(delay) & 0xFF

        # 輸入邏輯
        if not drawing and current_rect is not None:
            x1, y1, x2, y2 = current_rect
            # 確保座標順序正確
            xmin, xmax = sorted([x1, x2])
            ymin, ymax = sorted([y1, y2])
            
            # 防呆：避免點一下變成一個點
            if (xmax - xmin) > 10 and (ymax - ymin) > 10:
                # 暫停畫面
                temp = display_frame.copy()
                cv2.rectangle(temp, (xmin, ymin), (xmax, ymax), (0, 255, 255), 2)
                cv2.imshow(window_name, temp)
                cv2.waitKey(1)
                
                print(f"\n[區域 {zone_counter}]")
                product_name = input(f"請輸入整排商品名稱 (例如 Coke): ").strip()
                
                if not product_name:
                    product_name = f"Row_{zone_counter}"
                
                new_zone = {
                    "id": f"zone_{zone_counter}",
                    "product": product_name,
                    "coords": [xmin, ymin, xmax, ymax]
                }
                zones.append(new_zone)
                print(f"👍 已新增: {product_name}")
                zone_counter += 1
            current_rect = None

        if key == ord('p'):
            paused = not paused
            state = "已暫停" if paused else "繼續播放"
            print(f"⏯️ {state}")
        elif key == ord('q'):
            break
        elif key == ord('z') and zones:
            removed = zones.pop()
            print(f"↩️ 已移除: {removed['product']}")
            zone_counter -= 1
        elif key == ord('s'):
            save_config(zones, width, height)
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=str, default='0')
    args = parser.parse_args()
    
    main(args)