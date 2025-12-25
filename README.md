# Smart Shelf Monitoring System

AIOT 智慧零售系統 - 智慧監控與補貨系統

## Demo

[![Watch the demo](https://img.youtube.com/vi/raYe3EbU5T8/0.jpg)](https://www.youtube.com/shorts/raYe3EbU5T8)


[Download Demo Video](output/monitor_test2_1.mp4)

## Features
- **YOLOv10 Object Detection**: Identifies products on shelves.
- **Stock Monitoring**: Tracks real-time stock levels.
- **Gap Detection**: Identifies gaps between products to estimate restocking needs.
- **Streamlit Dashboard**:
    - **Video Resizing**: Optimize performance on low-end devices/cloud.
    - **Real-time Stats**: View stock counts and alerts.

## Usage
```bash
streamlit run app.py
```

## How It Works (系統原理)

本系統結合 **YOLOv10 物件偵測** 與 **幾何邏輯運算**，實現自動化的貨架監控與補貨提醒。

### 1. Zone Definition (貨架區域定義)
- 使用 `zone_creator.py` 工具，讓用戶在畫面上直接框選特定商品的「貨架區域 (Zone)」。
- 每個區域會被賦予一個唯一的 ID 與商品名稱 (例如: Coke, Water)。
- 系統會自動記錄該區域的座標 `(x1, y1, x2, y2)` 並儲存於 `config.json`，作為後續監控的基準。

### 2. Shelf Gap Detection (貨架空缺偵測)
系統在 `zone_monitor.py` 與 `app.py` 中執行以下即時運算：

1.  **物件偵測 (Object Detection)**: 使用 YOLOv10 模型偵測畫面中所有的商品。
2.  **區域過濾 (Zone Filtering)**: 只保留中心點落在「貨架區域」內的商品。
3.  **動態寬度計算 (Dynamic Width Calculation)**: 
    - 系統會即時計算該區域內所有偵測到的商品平均寬度 (`Avg Width`)。
    - 這使得系統能適應不同大小的商品，無需手動設定尺寸。
4.  **間隙判定 (Gap Logic)**:
    - 系統會檢查相鄰商品之間的距離 (以及商品與左右邊界的距離)。
    - 若 **間隙距離 > 平均寬度 × 係數 (預設 0.8)**，則判定該位置有一個或多個缺貨空位。
    - 缺貨位置會被標示為 **紅色虛線框**。

### 3. Anti-Occlusion (防遮擋機制)
為了避免顧客經過或手部遮擋導致誤判為「缺貨」，系統內建防遮擋機制：
- 系統維護每個區域的 **歷史數量 (History Buffer)** (預設 30 幀)。
- 若當前偵測數量 **突然驟降** (例如低於歷史平均的 60%)，且歷史數據充足，系統會判定為 **"BLOCKED" (視線受阻)**。
- 此時會顯示黃色警告，並暫停計算缺貨，直到視野恢復正常。

### 4. Dashbroad Monitoring (儀表板監控)
Streamlit 儀表板提供視覺化監控：
- **Stock (現貨)**: 綠色實線框，即時顯示架上數量。
- **Missing (缺貨)**: 紅色虛線框，顯示該區域需要補貨的數量。
- **Status (狀態)**: 
    - 🟢 **監控中**: 系統運作正常。
    - ⚠️ **視線受阻**: 偵測到遮擋，暫停計數。
