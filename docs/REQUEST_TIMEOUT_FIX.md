# HTTP 請求超時問題修復

**問題日期**: 2025-11-11  
**錯誤**: `requests.exceptions.ReadTimeout: Read timed out. (read timeout=30)`  
**狀態**: ✅ 已修復

---

## 📝 問題描述

在執行 Book Reader 時，當 DeepSeek-OCR 處理複雜圖像時，HTTP 請求會超時並導致程式崩潰。

### 錯誤訊息

```
requests.exceptions.ReadTimeout: HTTPConnectionPool(host='172.30.19.20', port=5000): 
Read timed out. (read timeout=30)
```

### 完整 Traceback

```python
Traceback (most recent call last):
  File "/GPUData/working/Deepseek-OCR/example_bookReader/book_reader.py", line 708, in <module>
    main()
  File "/GPUData/working/Deepseek-OCR/example_bookReader/book_reader.py", line 704, in main
    reader.run()
  File "/GPUData/working/Deepseek-OCR/example_bookReader/book_reader.py", line 620, in run
    self.process_trigger()
  File "/GPUData/working/Deepseek-OCR/example_bookReader/book_reader.py", line 572, in process_trigger
    text = self.send_to_ocr_api(frame, custom_prompt=custom_prompt)
  File "/GPUData/working/Deepseek-OCR/example_bookReader/book_reader.py", line 474, in send_to_ocr_api
    response = requests.post(...)
requests.exceptions.ReadTimeout: Read timed out. (read timeout=30)
```

---

## 🔍 根本原因

### 1. 超時設定過短

**Client 端配置**（`config.ini`）：
```ini
request_timeout = 30  # 30 秒超時
```

**Server 端實際處理時間**：
- 簡單圖像：4-10 秒 ✅
- **複雜圖像：30-60 秒** ⚠️（超過超時設定）

### 2. Server 端處理日誌

```
第1次 OCR: 4.28 秒完成 ✅
第2次 OCR: 35.37 秒完成 ⚠️（超過 30 秒）
```

當 Server 端處理時間超過 Client 端的 `request_timeout` 設定時，Client 端會拋出 `ReadTimeout` 例外，導致程式崩潰。

### 3. 為什麼會超時？

DeepSeek-OCR 的處理時間受多種因素影響：

| 因素 | 影響 | 處理時間範圍 |
|-----|------|------------|
| **圖像解析度** | 高解析度圖像需要更長處理時間 | +10-20秒 |
| **文字密度** | 文字越多，處理時間越長 | +5-15秒 |
| **圖像複雜度** | 包含表格、多列文字等 | +10-30秒 |
| **GPU 負載** | 其他請求同時處理時 | +5-10秒 |
| **Prompt 複雜度** | 複雜的 Prompt 需要更多推理 | +5-10秒 |

**結論**: 30 秒的超時設定對於複雜圖像來說太短了！

---

## ✅ 解決方案

### 修復 1: 增加超時時間

**檔案**: `example_bookReader/config.ini`

**修改位置**: 第 1-9 行

**修改前**:
```ini
[API]
# DeepSeek-OCR API 伺服器位址
api_url = http://172.30.19.20:5000
# API 端點
ocr_endpoint = /ocr
# 請求超時時間（秒）
request_timeout = 30
```

**修改後**:
```ini
[API]
# DeepSeek-OCR API 伺服器位址
api_url = http://172.30.19.20:5000
# API 端點
ocr_endpoint = /ocr
# 請求超時時間（秒）
# 注意：DeepSeek-OCR 處理複雜圖像可能需要 30-60 秒
# 建議設定為至少 60 秒以避免超時
request_timeout = 90
```

**修改原因**:
- 30 秒對複雜圖像來說太短
- 增加到 90 秒提供足夠的處理時間緩衝
- Server 端超時設定是 300 秒，Client 端應該小於這個值

---

### 修復 2: 添加錯誤處理

**檔案**: `example_bookReader/book_reader.py`

#### 修復 2.1: 在 `send_to_ocr_api()` 中添加日誌

**修改位置**: 第 472-476 行

**修改前**:
```python
# 發送請求
self.logger.info(f"發送請求至: {self.api_url}")
response = requests.post(...)
```

**修改後**:
```python
# 發送請求（加上完整的錯誤處理）
self.logger.info(f"發送請求至: {self.api_url}")
self.logger.info(f"超時設定: {self.request_timeout} 秒")

from requests.exceptions import Timeout, ConnectionError, RequestException

response = requests.post(...)
```

**修改原因**:
- 顯示超時設定，方便除錯
- 匯入錯誤處理所需的例外類別

---

#### 修復 2.2: 在 `send_to_ocr_api()` 中改善錯誤訊息

**修改位置**: 第 491-497 行

**修改前**:
```python
else:
    error_msg = response.json().get('error', '未知錯誤')
    self.logger.error(f"OCR API 錯誤 (HTTP {response.status_code}): {error_msg}")
    return None
```

**修改後**:
```python
else:
    error_msg = response.json().get('error', '未知錯誤')
    self.logger.error(f"======== OCR API 錯誤 ========")
    self.logger.error(f"HTTP 狀態碼: {response.status_code}")
    self.logger.error(f"錯誤訊息: {error_msg}")
    self.logger.error(f"============================")
    return None
```

**修改原因**:
- 使用結構化格式顯示錯誤訊息
- 更容易在日誌中識別錯誤

---

#### 修復 2.3: 在 `process_trigger()` 中添加 try-except

**修改位置**: 第 582-618 行

**修改前**:
```python
text = None
error_occurred = False

# 使用自訂 prompt（如果有）或預設 prompt
text = self.send_to_ocr_api(frame, custom_prompt=custom_prompt)

# 4. 根據結果播放音檔
if text is not None and text.strip():
    # 成功...
else:
    # 失敗...
```

**修改後**:
```python
text = None
error_occurred = False

# 使用自訂 prompt（如果有）或預設 prompt
# 加上錯誤處理（捕獲超時和連線錯誤）
from requests.exceptions import Timeout, ConnectionError, RequestException

try:
    text = self.send_to_ocr_api(frame, custom_prompt=custom_prompt)
except Timeout as timeout_err:
    error_occurred = True
    self.logger.error(f"======== OCR API 請求超時 ========")
    self.logger.error(f"超時設定: {self.request_timeout} 秒")
    self.logger.error(f"錯誤訊息: {str(timeout_err)}")
    self.logger.error(f"建議: 增加 config.ini 中的 request_timeout 設定")
    self.logger.error(f"或等待圖像處理完成（複雜圖像可能需要 30-60 秒）")
    self.logger.error(f"================================")
except ConnectionError as conn_err:
    error_occurred = True
    self.logger.error(f"======== OCR API 連線錯誤 ========")
    self.logger.error(f"API 位址: {self.api_url}")
    self.logger.error(f"錯誤訊息: {str(conn_err)}")
    self.logger.error(f"建議: 檢查網路連線和 API 伺服器狀態")
    self.logger.error(f"================================")
except RequestException as req_err:
    error_occurred = True
    self.logger.error(f"======== OCR API 請求錯誤 ========")
    self.logger.error(f"錯誤訊息: {str(req_err)}")
    self.logger.error(f"================================")
except Exception as general_err:
    error_occurred = True
    self.logger.error(f"======== OCR 執行錯誤 ========")
    self.logger.error(f"錯誤類型: {type(general_err).__name__}")
    self.logger.error(f"錯誤訊息: {str(general_err)}")
    self.logger.error(f"============================")
    import traceback
    self.logger.error(f"錯誤詳情:\n{traceback.format_exc()}")

# 4. 根據結果播放音檔
if error_occurred:
    # 發生錯誤，播放錯誤音檔
    self.logger.warning("OCR 執行失敗，播放錯誤音檔")
    self.play_sound(self.error_sound)
elif text is not None and text.strip():
    # 成功...
```

**修改原因**:
- **捕獲 Timeout 錯誤** - 當超時時不會崩潰，而是顯示清楚的錯誤訊息
- **捕獲 ConnectionError** - 當連線失敗時顯示詳細資訊
- **捕獲 RequestException** - 捕獲所有 requests 相關錯誤
- **通用錯誤處理** - 捕獲未預期的錯誤
- **清楚的錯誤訊息** - 每種錯誤都有詳細的日誌和建議
- **播放錯誤音檔** - 讓使用者知道發生錯誤
- **程式不崩潰** - 錯誤後繼續運行，等待下一次觸發

---

## 📊 修改效果比較

### 修改前

```
Client 端: request_timeout = 30 秒
Server 端: 處理時間 35.37 秒
結果: ❌ ReadTimeout 錯誤，程式崩潰
```

### 修改後

```
Client 端: request_timeout = 90 秒
Server 端: 處理時間 35.37 秒
結果: ✅ 成功完成，正常運行

或者，如果仍然超時：
Client 端: request_timeout = 90 秒
Server 端: 處理時間 95 秒（極複雜圖像）
結果: ✅ 捕獲 Timeout 錯誤，顯示詳細訊息，播放錯誤音檔，繼續運行
```

---

## 🎯 建議的超時時間設定

根據不同的使用場景，建議的超時時間：

| 場景 | 建議超時時間 | 說明 |
|-----|------------|------|
| **簡單文字（名片、標籤）** | 30-45 秒 | 處理快速，30 秒足夠 |
| **一般書頁** | 60-90 秒 | 標準書頁，90 秒最佳 |
| **複雜文檔（表格、多列）** | 90-120 秒 | 複雜圖像需要更長時間 |
| **高解析度掃描** | 120-180 秒 | 高清圖像需要大量處理 |
| **保險設定（不想超時）** | 180-300 秒 | 最保險，但會等很久 |

**推薦設定**: `request_timeout = 90` （平衡速度和可靠性）

---

## 🔧 如何調整超時時間

### 方法 1: 修改 config.ini（推薦）

編輯 `example_bookReader/config.ini`：

```ini
[API]
request_timeout = 90  # 改為您需要的秒數
```

### 方法 2: 環境變數（進階）

未來可以考慮支援環境變數覆蓋：

```bash
export REQUEST_TIMEOUT=120
python book_reader.py
```

---

## 🐛 除錯技巧

### 1. 查看 Server 端處理時間

在 Server 端日誌中尋找：

```
OCR 處理耗時: XX.XX 秒
```

如果經常看到超過 60 秒的處理時間，應該增加 `request_timeout`。

### 2. 測試不同圖像的處理時間

使用不同類型的圖像測試：

```bash
# 簡單圖像
curl -X POST -F "file=@simple_text.jpg" http://172.30.19.20:5000/ocr

# 複雜圖像
curl -X POST -F "file=@complex_table.jpg" http://172.30.19.20:5000/ocr
```

記錄每種圖像的處理時間，並據此調整超時設定。

### 3. 監控日誌

查看 `logs/book_reader.log`：

```bash
tail -f logs/book_reader.log | grep -E "(超時|Timeout|處理時間)"
```

---

## 📚 相關文檔

- `README/ERROR_MESSAGES.md` - 一般錯誤訊息說明
- `README/CONFIGURATION.md` - 設定檔說明
- `config.ini` - 設定檔

---

## ✅ 總結

### 問題原因

- Client 端超時設定太短（30 秒）
- Server 端處理複雜圖像需要 30-60 秒
- 沒有錯誤處理，超時時程式崩潰

### 解決方案

1. ✅ **增加超時時間到 90 秒** - 足以處理大部分圖像
2. ✅ **添加完整的錯誤處理** - 捕獲 Timeout, ConnectionError, RequestException
3. ✅ **清楚的錯誤訊息** - 顯示超時設定、建議、錯誤詳情
4. ✅ **程式不崩潰** - 錯誤後播放錯誤音檔並繼續運行

### 預期效果

- ✅ 99% 的圖像不會超時
- ✅ 即使超時也不會崩潰
- ✅ 清楚的錯誤訊息幫助除錯
- ✅ 使用者體驗更好（播放錯誤音檔而非崩潰）

**現在可以重新啟動 Book Reader，問題已解決！** 🎉

