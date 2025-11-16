# Streamlit 界面使用指南

## 版本：v1.0.0
## 日期：2025-01-27

---

## 📋 概述

`book_reader_streamlit.py` 是一個使用 Streamlit 構建的 Web 界面，用於替代原本的 OpenCV 顯示界面。它提供了：

1. **相機即時預覽**：實時顯示 USB 相機畫面
2. **OCR 結果列表**：按日期時間顯示所有 OCR 辨識結果
3. **OCR 文字內容**：顯示每張圖片的 OCR 辨識文字

---

## 🚀 快速開始

### 1. 安裝依賴

確保已安裝 Streamlit：

```bash
pip install streamlit
```

### 2. 運行應用程式

```bash
cd example_bookReader
streamlit run book_reader_streamlit.py
```

應用程式會在瀏覽器中自動打開，預設地址為 `http://localhost:8501`

---

## 🎯 功能說明

### 1. 相機即時預覽

- **位置**：左側主區域
- **功能**：實時顯示 USB 相機畫面
- **控制**：
  - **"Enable Camera Preview"**：啟用/關閉相機預覽
  - **"Auto Refresh Preview"**：啟用/關閉自動刷新（僅在啟用預覽時顯示）
  - **"🔄 Refresh Preview"**：手動刷新預覽按鈕（僅在關閉自動刷新時顯示）
  - **"🔧 Reset Camera"**：重置相機連接按鈕（用於修復 F5 刷新後相機無法使用的問題）

**刷新模式**：
- **自動刷新模式**（預設）：頁面每 0.2 秒自動刷新一次，提供即時預覽
- **手動刷新模式**：關閉自動刷新後，點擊「刷新預覽」按鈕才會更新畫面

### 2. OCR 辨識

#### **手動觸發**

1. 點擊側邊欄中的 "📸 Capture & OCR" 按鈕
2. 系統會自動：
   - 拍攝當前相機畫面
   - 執行 OCR 辨識
   - 將結果添加到歷史記錄

#### **自訂 Prompt**

在側邊欄的 "Custom Prompt" 文字框中輸入自訂的 OCR prompt，留空則使用預設 prompt。

### 3. OCR 結果歷史

- **位置**：右側主區域
- **顯示方式**：按日期時間倒序排列（最新的在最上面）
- **內容**：
  - 拍攝的圖片縮圖
  - OCR 辨識的文字內容
  - 時間戳和狀態

#### **結果狀態**

- ✅ **completed**：OCR 辨識成功
- ⚠️ **skipped**：跳過 OCR（圖像不包含文字）
- ❌ **error**：OCR 辨識失敗

#### **操作**

- **展開/摺疊**：點擊結果標題展開查看詳情
- **清除所有結果**：點擊 "🗑️ Clear All Results" 按鈕

---

## 📁 文件結構

### 數據存儲

- **OCR 結果**：`ocr_results.json`
  - 格式：JSON 數組
  - 內容：所有 OCR 辨識結果
  - 限制：保留最近 100 條記錄

- **拍攝圖片**：`captured_images/`
  - 格式：`capture_YYYYMMDD_HHMMSS.jpg`
  - 路徑：由 `config.ini` 中的 `image_save_path` 設定

---

## ⚙️ 配置說明

### config.ini 設定

所有設定都從 `config.ini` 讀取，主要設定包括：

#### **[CAMERA]**
- `camera_device`: USB 相機裝置編號（預設：0）
- `frame_width`: 拍攝解析度寬度（預設：1280）
- `frame_height`: 拍攝解析度高度（預設：720）
- `save_captured_image`: 是否儲存拍攝的圖片（預設：true）
- `image_save_path`: 圖片儲存路徑（預設：captured_images）

#### **[API]**
- `api_url`: DeepSeek-OCR API 伺服器位址
- `ocr_endpoint`: OCR API 端點（預設：/ocr）
- `request_timeout`: 請求超時時間（秒）

#### **[OCR]**
- `prompt`: 預設 OCR prompt

#### **[OPENAI]**
- `enable_preanalysis`: 是否啟用 OpenAI 預分析
- `model`: OpenAI 模型名稱

---

## 🔧 技術細節

### 相機預覽實現

```python
def get_camera_frame(self):
    """從 USB Camera 讀取一幀影像"""
    cap = cv2.VideoCapture(self.camera_device)
    # ... 讀取並返回影像
```

- 使用 OpenCV 讀取相機畫面
- 自動轉換 BGR 到 RGB 格式供 Streamlit 顯示
- 自動刷新（約 10 FPS）

### OCR 結果存儲

```python
def add_ocr_result(self, frame, result):
    """添加 OCR 結果到列表"""
    # 保存圖片
    # 添加到結果列表
    # 保存到 JSON 文件
```

- 結果存儲在內存中（`self.ocr_results`）
- 同時保存到 JSON 文件（`ocr_results.json`）
- 自動限制結果數量（最多 100 條）

### 數據格式

```json
{
  "id": "20250127_123456",
  "datetime": "2025-01-27 12:34:56",
  "status": "completed",
  "text": "OCR 辨識的文字內容...",
  "image_path": "captured_images/capture_20250127_123456.jpg"
}
```

---

## 📊 界面布局

```
┌─────────────────────────────────────────────────────────┐
│  📖 Book Reader OCR System                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │                  │  │                          │  │
│  │  📷 Camera       │  │  📋 OCR Results History  │  │
│  │  Preview         │  │                          │  │
│  │                  │  │  📄 2025-01-27 12:34:56  │  │
│  │  [Live Preview]  │  │  └─ Image                │  │
│  │                  │  │  └─ OCR Text             │  │
│  │                  │  │                          │  │
│  │  [Capture & OCR] │  │  📄 2025-01-27 12:30:12  │  │
│  │                  │  │  └─ ...                  │  │
│  └──────────────────┘  └──────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  ⚙️ Settings                                     │  │
│  │  ☑ Enable Camera Preview                        │  │
│  │                                                  │  │
│  │  OCR Settings                                   │  │
│  │  Custom Prompt: [________________]              │  │
│  │                                                  │  │
│  │  [📸 Capture & OCR]                             │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 🐛 故障排除

### 問題 1：無法讀取相機畫面

**錯誤訊息**：
```
無法讀取相機畫面
```

**解決方法**：
1. **檢查相機連接**：確認相機是否正確連接
2. **檢查設定**：確認 `config.ini` 中的 `camera_device` 設定正確
3. **檢查權限**：`ls -l /dev/video*`
4. **重置相機**：點擊「🔧 Reset Camera」按鈕重置相機連接
5. **F5 刷新問題**：如果按 F5 刷新後相機無法使用，點擊「🔧 Reset Camera」按鈕修復

---

### 問題 2：OCR API 連接失敗

**錯誤訊息**：
```
OCR API 請求失敗
```

**解決方法**：
1. 檢查 `config.ini` 中的 `api_url` 設定
2. 確認 OCR API 服務正在運行
3. 檢查網路連接

---

### 問題 3：Streamlit 自動刷新過快

**現象**：頁面不斷刷新，影響使用

**解決方法**：
1. 關閉 "Enable Camera Preview" 開關（完全停止刷新）
2. 關閉 "Auto Refresh Preview" 開關（停止自動刷新，改為手動刷新）
3. 使用 "🔄 Refresh Preview" 按鈕手動更新預覽畫面

**新增功能**：
- ✅ **自動刷新開關**：可以控制是否自動刷新預覽畫面
- ✅ **手動刷新按鈕**：關閉自動刷新後，可以手動點擊按鈕更新預覽

---

## 📌 注意事項

1. **相機資源**：確保只有一個應用程式在使用相機
2. **結果數量**：系統自動限制為最近 100 條記錄
3. **圖片存儲**：定期清理 `captured_images/` 目錄以節省空間
4. **效能**：相機預覽會持續刷新，可能影響效能

---

## 🔄 與原版 book_reader.py 的差異

| 功能 | book_reader.py | book_reader_streamlit.py |
|------|---------------|--------------------------|
| 顯示界面 | OpenCV 視窗 | Streamlit Web 界面 |
| GPIO 支援 | ✅ 支援 | ❌ 不支援 |
| 音訊播放 | ✅ 支援 | ❌ 不支援 |
| 相機預覽 | OpenCV 視窗 | Streamlit 網頁 |
| OCR 結果 | 終端機輸出 | Web 界面顯示 |
| 結果歷史 | ❌ 無 | ✅ 有（JSON 存儲） |
| 圖片列表 | ❌ 無 | ✅ 有（按時間排序） |

---

## 📚 相關文件

- [配置說明](CONFIGURATION.md)
- [安裝指南](INSTALLATION.md)
- [故障排除](TROUBLESHOOTING.md)
- [自動刷新機制說明](../../README/STREAMLIT_REFRESH_OPTIMIZATION.md)
- [F5 刷新相機問題修復](../../README/STREAMLIT_CAMERA_REFRESH_FIX.md)
- [Streamlit 替代方案建議](../../README/STREAMLIT_ALTERNATIVE_SOLUTIONS.md)

## ⚠️ 重要提醒

**Streamlit 多進程架構限制**：
- Streamlit 使用多進程架構，F5 刷新時會創建新進程
- 舊進程可能仍然佔用相機資源，導致新進程無法初始化相機
- 這是 Streamlit 架構的根本限制，難以完全解決

**建議**：
- 如果**不需要 Web 界面**，建議使用 `book_reader.py`（OpenCV 視窗版本）
- 如果**需要 Web 界面**，建議考慮遷移到 Flask + WebSocket/SSE
- 詳細說明請參考：[Streamlit 替代方案建議](../../README/STREAMLIT_ALTERNATIVE_SOLUTIONS.md)

---

## 版本資訊

- **版本**：v1.2.0
- **日期**：2025-11-12
- **更新**：
  - 新增自動刷新控制功能
  - 修復 F5 刷新後相機無法使用的問題
  - 新增手動重置相機按鈕
- **作者**：AI Assistant

---

**結論**：Streamlit 界面提供了更友好的 Web 界面，方便查看和管理 OCR 辨識結果，適合需要圖形化界面的使用場景。

