# Flask Web 界面使用指南

## 版本：v1.0.0
## 日期：2025-11-12

---

## 📋 概述

`book_reader_flask.py` 是一個使用 Flask 構建的 Web 界面，用於替代 Streamlit 版本。它提供了：

1. **相機即時預覽**：使用 Server-Sent Events (SSE) 實現真正的即時串流
2. **OCR 辨識**：拍攝照片並執行 OCR 辨識
3. **自訂 Prompt**：可以輸入自訂的 OCR prompt，每次 OCR 時都會附加
4. **OCR 結果歷史**：按日期時間顯示所有 OCR 辨識結果

---

## 🚀 快速開始

### 1. 安裝依賴

確保已安裝 Flask 和相關套件：

```bash
cd example_bookReader
pip install Flask flask-cors
```

或使用 requirements.txt：

```bash
pip install -r requirements.txt
```

### 2. 運行應用程式

```bash
python3 book_reader_flask.py
```

應用程式會在瀏覽器中自動打開，預設地址為 `http://localhost:8502`

---

## 🎯 功能說明

### 1. 左側固定 Sidebar

#### **相機設定**
- **設備顯示**：顯示當前使用的相機設備編號
- **啟用預覽**：開關相機即時預覽功能

#### **OCR 設定**
- **自訂 Prompt**：文字輸入框，可以輸入自訂的 OCR prompt
  - 預設值：`這是一本繁體中文書的內頁screen, 請OCR 並用繁體中文輸出結果。`
  - 可以隨時修改，修改後的 prompt 會立即生效
  - 如果清空文字框，系統會使用 `config.ini` 中的預設 prompt
- **提示**：此 prompt 會附加到每次 OCR 請求，傳遞給 DeepSeek-OCR API

#### **操作按鈕**
- **📸 拍攝 & OCR**：拍攝當前相機畫面並執行 OCR 辨識
- **🔧 重置相機**：重置相機連接（用於修復相機問題）

#### **結果操作**
- **🗑️ 清除所有結果**：清除所有 OCR 結果歷史記錄

### 2. 主內容區域

#### **左側：相機預覽**
- **即時預覽**：顯示 USB 相機的即時畫面（約 30 FPS）
- **錯誤訊息**：如果無法讀取相機，顯示錯誤訊息
- **OCR 結果顯示**：拍攝後顯示 OCR 辨識結果

#### **右側：OCR 結果歷史**
- **結果列表**：按日期時間倒序排列（最新的在最上面）
- **結果內容**：
  - 拍攝的圖片縮圖
  - OCR 辨識的文字內容
  - 時間戳和狀態
- **結果狀態**：
  - ✅ **成功**：OCR 辨識成功
  - ⚠️ **跳過**：跳過 OCR（圖像不包含文字）
  - ❌ **失敗**：OCR 辨識失敗

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

### 檔案結構

```
example_bookReader/
├── book_reader_flask.py      # Flask 應用程式主檔案
├── templates/
│   └── book_reader.html      # HTML 模板
├── static/
│   ├── css/
│   │   └── book_reader.css   # CSS 樣式
│   └── js/
│       └── book_reader.js    # JavaScript 邏輯
├── config.ini                 # 設定檔
└── ocr_results.json           # OCR 結果存儲
```

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
  - 預設值：`這是一本繁體中文書的內頁screen, 請OCR 並用繁體中文輸出結果。`
  - 如果使用者沒有輸入自訂 prompt 或清空了文字框，則使用此預設值
  - 此 prompt 會附加到每次 OCR 請求中，傳遞給 DeepSeek-OCR API

#### **[OPENAI]**
- `enable_preanalysis`: 是否啟用 OpenAI 預分析
- `model`: OpenAI 模型名稱

---

## 🔧 技術細節

### 相機預覽實現

使用 **Server-Sent Events (SSE)** 實現即時串流：

```python
@app.route('/api/camera/stream')
def camera_stream():
    def generate():
        while True:
            frame = reader.get_camera_frame()
            if frame is not None:
                # 編碼為 base64
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                yield f"data: {json.dumps({'frame': frame_base64})}\n\n"
            time.sleep(0.033)  # 約 30 FPS
    
    return Response(generate(), mimetype='text/event-stream')
```

**優點**：
- ✅ 單進程架構，資源管理簡單
- ✅ 真正的即時串流（約 30 FPS）
- ✅ 沒有 Streamlit 的多進程問題

### OCR Prompt 處理

**重要**：每次執行 OCR 時，prompt 都會附加到 DeepSeek-OCR API 請求中。

**Prompt 優先順序**：
1. **使用者輸入的 prompt**（sidebar 中的文字框）
   - 如果使用者有輸入文字，優先使用使用者的 prompt
2. **OpenAI 預分析的 prompt**（如果啟用）
   - 如果啟用了 OpenAI 預分析功能，且圖像包含文字，會使用 AI 生成的 prompt
3. **預設 prompt**（config.ini 中的設定）
   - 如果使用者沒有輸入或清空了文字框，使用 `config.ini` 中的預設 prompt

**實現邏輯**：
```python
# 優先順序：user_prompt > custom_prompt > 預設 prompt
prompt_to_use = None
if user_prompt and user_prompt.strip():
    prompt_to_use = user_prompt.strip()
    # 使用使用者輸入的 prompt
elif custom_prompt:
    prompt_to_use = custom_prompt
    # 使用 OpenAI 預分析的 prompt
else:
    prompt_to_use = self.ocr_prompt
    # 使用 config.ini 中的預設 prompt

# 將 prompt 附加到 API 請求
data = {}
if prompt_to_use:
    data['prompt'] = prompt_to_use

# 發送請求到 DeepSeek-OCR API
response = requests.post(
    self.api_url,
    files=files,  # 圖片檔案
    data=data,    # prompt 參數
    timeout=self.request_timeout
)
```

**使用範例**：
- 預設情況：使用 `這是一本繁體中文書的內頁screen, 請OCR 並用繁體中文輸出結果。`
- 自訂 prompt：在文字框中輸入 `請識別圖片中的英文文字`，系統會使用此 prompt
- 清空文字框：系統會自動使用 `config.ini` 中的預設 prompt

### OCR 結果存儲

```python
def add_ocr_result(self, frame, result):
    # 保存圖片
    # 添加到結果列表
    # 保存到 JSON 文件
```

- 結果存儲在內存中（`self.ocr_results`）
- 同時保存到 JSON 文件（`ocr_results.json`）
- 自動限制結果數量（最多 100 條）

---

## 🐛 故障排除

### 問題 1：無法讀取相機畫面

**錯誤訊息**：
```
無法讀取相機畫面
```

**解決方法**：
1. 檢查相機是否正確連接
2. 確認 `config.ini` 中的 `camera_device` 設定正確
3. 檢查相機權限：`ls -l /dev/video*`
4. 點擊「🔧 重置相機」按鈕

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

### 問題 3：相機串流中斷

**現象**：相機預覽突然停止

**解決方法**：
1. 關閉並重新啟用「啟用相機預覽」開關
2. 點擊「🔧 重置相機」按鈕
3. 重新整理頁面

---

## 📌 注意事項

1. **相機資源**：確保只有一個應用程式在使用相機
2. **結果數量**：系統自動限制為最近 100 條記錄
3. **圖片存儲**：定期清理 `captured_images/` 目錄以節省空間
4. **效能**：相機預覽會持續串流，可能影響效能

---

## 🔄 與 Streamlit 版本的差異

| 功能 | Streamlit 版本 | Flask 版本 |
|------|---------------|-----------|
| 資源管理 | ⚠️ 多進程問題 | ✅ 單進程，資源管理簡單 |
| 即時預覽 | ⚠️ 需要刷新頁面 | ✅ 真正的即時串流（SSE） |
| F5 刷新 | ❌ 相機無法使用 | ✅ 正常運作 |
| 自訂 Prompt | ✅ 支援 | ✅ 支援（更靈活） |
| 界面設計 | Streamlit 預設 | ✅ 自訂設計（固定 sidebar） |

---

## 📚 相關文件

- [配置說明](CONFIGURATION.md)
- [安裝指南](INSTALLATION.md)
- [故障排除](TROUBLESHOOTING.md)
- [Streamlit 替代方案建議](../../README/STREAMLIT_ALTERNATIVE_SOLUTIONS.md)

---

## 版本資訊

- **版本**：v1.0.0
- **日期**：2025-11-12
- **作者**：AI Assistant

---

**結論**：Flask 版本提供了更穩定的 Web 界面，沒有 Streamlit 的多進程問題，適合需要可靠相機預覽的使用場景。

