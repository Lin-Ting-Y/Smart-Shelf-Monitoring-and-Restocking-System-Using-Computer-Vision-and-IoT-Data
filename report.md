# Smart Shelf Monitoring and Restocking System

Demo: [https://smart-shelf-monitoring.streamlit.app/](https://smart-shelf-monitoring.streamlit.app/)

## 使用流程

### 1. 產生區域設定檔
- 執行 `zone_creator.py`，用滑鼠在影片畫面上框選每個貨架區域。
- 每框一個區域，依指示輸入商品名稱。
- 按 `s` 鍵儲存，會產生 `config.json`。
- 範例指令：
  ```
  python zone_creator.py --source <影片檔名或攝影機編號>
  ```

### 2. 啟動/部署 Streamlit 監控介面
- 本地端：
  ```
  streamlit run app.py
  ```
- 雲端部署：直接開啟 [Streamlit App Demo](https://smart-shelf-monitoring.streamlit.app/)

### 3. 操作說明
- 進入監控頁面後：
  1. 上傳監控影片（支援 mp4/avi）
  2. 調整 YOLO 信心度與間隙判定係數（可選）
  3. 勾選「啟動推論」開始監控
  4. 介面會即時顯示各區域現貨、缺貨、狀態
- 若出現「找不到 config.json」請先回到步驟 1 產生設定檔
- 若出現「找不到 best.pt」請確認模型檔已放在 `models/best.pt`

## 依賴
- 需安裝 requirements.txt 內所有套件
- 建議使用 Python 3.11

---

如有問題請參考原始碼註解或聯絡作者。
