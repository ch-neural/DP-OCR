# 閱讀機器人設定檔說明

## 📋 目錄

- [設定檔概述](#設定檔概述)
- [API 設定](#api-設定)
- [GPIO 設定](#gpio-設定)
- [攝影機設定](#攝影機設定)
- [音訊設定](#音訊設定)
- [OCR 設定](#ocr-設定)
- [日誌設定](#日誌設定)
- [進階設定範例](#進階設定範例)

---

## 📄 設定檔概述

閱讀機器人使用 INI 格式的設定檔 `config.ini` 來管理所有可調整的參數。

### 設定檔結構

```ini
[API]          # API 伺服器相關設定
[GPIO]         # GPIO 腳位和觸發設定
[CAMERA]       # 攝影機相關設定
[AUDIO]        # 音訊播放設定
[OCR]          # OCR 辨識設定
[LOGGING]      # 日誌記錄設定
```

### 設定檔位置

預設位置：`example_bookReader/config.ini`

可透過程式參數指定其他位置：

```bash
python3 book_reader.py --config /path/to/custom_config.ini
```

### 設定檔語法

```ini
# 註解行以 # 開頭
[Section]  # 區段名稱
key = value  # 設定項目

# 字串值
string_value = some text

# 數字值
integer_value = 42
float_value = 3.14

# 布林值
boolean_value = true  # 或 false
```

---

## 🌐 API 設定

### [API] 區段

控制與 DeepSeek-OCR API 伺服器的連線設定。

```ini
[API]
# DeepSeek-OCR API 伺服器位址
api_url = http://172.30.19.20:5000

# API 端點
ocr_endpoint = /ocr

# 請求超時時間（秒）
request_timeout = 30
```

### 設定項目說明

#### `api_url`

- **類型**: 字串
- **必填**: 是
- **預設值**: `http://172.30.19.20:5000`
- **說明**: DeepSeek-OCR API 伺服器的完整 URL
- **範例**:
  ```ini
  # HTTP 連線
  api_url = http://192.168.1.100:5000
  
  # HTTPS 連線
  api_url = https://api.example.com:5000
  
  # 使用域名
  api_url = http://ocr-server.local:5000
  ```

#### `ocr_endpoint`

- **類型**: 字串
- **必填**: 否
- **預設值**: `/ocr`
- **說明**: OCR API 的端點路徑
- **範例**:
  ```ini
  ocr_endpoint = /ocr
  ocr_endpoint = /api/v1/ocr
  ```

#### `request_timeout`

- **類型**: 整數
- **必填**: 否
- **預設值**: `30`
- **單位**: 秒
- **說明**: HTTP 請求的超時時間
- **建議值**:
  - 快速網路：`15-20` 秒
  - 一般網路：`30` 秒
  - 慢速網路：`60` 秒
- **範例**:
  ```ini
  request_timeout = 60  # 增加到 60 秒
  ```

---

## 🔌 GPIO 設定

### [GPIO] 區段

控制 GPIO 腳位和觸發行為。

```ini
[GPIO]
# 觸發 GPIO 腳位編號（BCM 編號）
trigger_pin = 17

# GPIO 檢查間隔時間（秒）
check_interval = 0.5

# 去彈跳延遲時間（秒）
debounce_delay = 0.2
```

### 設定項目說明

#### `trigger_pin`

- **類型**: 整數
- **必填**: 是
- **預設值**: `17`
- **說明**: 觸發辨識的 GPIO 腳位編號（使用 BCM 編號）
- **可用腳位**: 2, 3, 4, 17, 27, 22, 10, 9, 11, 等（避免使用特殊功能腳位）
- **範例**:
  ```ini
  # 使用 GPIO17（實體腳位 11）
  trigger_pin = 17
  
  # 使用 GPIO27（實體腳位 13）
  trigger_pin = 27
  ```

#### BCM vs 實體腳位對照表

| BCM 編號 | 實體腳位 | 說明 |
|----------|----------|------|
| GPIO2    | Pin 3    | I2C SDA |
| GPIO3    | Pin 5    | I2C SCL |
| GPIO4    | Pin 7    | 一般用途 |
| GPIO17   | Pin 11   | 一般用途（預設使用）|
| GPIO27   | Pin 13   | 一般用途 |
| GPIO22   | Pin 15   | 一般用途 |
| GPIO10   | Pin 19   | SPI MOSI |
| GPIO9    | Pin 21   | SPI MISO |
| GPIO11   | Pin 23   | SPI SCLK |

#### `check_interval`

- **類型**: 浮點數
- **必填**: 否
- **預設值**: `0.5`
- **單位**: 秒
- **說明**: 檢查 GPIO 狀態的間隔時間
- **影響**:
  - 數值越小：反應越快，但 CPU 佔用越高
  - 數值越大：反應較慢，但 CPU 佔用越低
- **建議值**:
  - 快速反應：`0.1-0.3` 秒
  - 平衡模式：`0.5` 秒（預設）
  - 省電模式：`1.0` 秒
- **範例**:
  ```ini
  check_interval = 0.1  # 更快的反應時間
  ```

#### `debounce_delay`

- **類型**: 浮點數
- **必填**: 否
- **預設值**: `0.2`
- **單位**: 秒
- **說明**: 去彈跳延遲時間，避免重複觸發
- **作用**: 在此時間內的重複觸發會被忽略
- **建議值**:
  - 機械按鈕：`0.2-0.5` 秒
  - 觸控開關：`0.1-0.2` 秒
  - 繼電器：`0.5-1.0` 秒
- **範例**:
  ```ini
  debounce_delay = 0.5  # 增加去彈跳時間
  ```

---

## 📷 攝影機設定

### [CAMERA] 區段

控制 USB 攝影機的拍攝參數。

```ini
[CAMERA]
# USB Camera 裝置編號（0 = 第一個攝影機）
camera_device = 0

# 拍攝解析度寬度
frame_width = 1280

# 拍攝解析度高度
frame_height = 720

# 拍攝前延遲時間（秒）
capture_delay = 0.5

# 儲存拍攝的圖片（用於除錯）
save_captured_image = true

# 圖片儲存路徑
image_save_path = captured_images

# 是否顯示攝影機畫面到 LCD 螢幕
show_preview = false

# 預覽視窗名稱
preview_window_name = Book Reader - Camera Preview

# 預覽顯示時間（秒，0 表示持續顯示直到按鍵）
preview_duration = 2.0
```

### 設定項目說明

#### `camera_device`

- **類型**: 整數
- **必填**: 是
- **預設值**: `0`
- **說明**: USB 攝影機的裝置編號
- **對應關係**:
  - `0` → `/dev/video0`
  - `1` → `/dev/video1`
- **如何確認**:
  ```bash
  ls -l /dev/video*
  v4l2-ctl --list-devices
  ```
- **範例**:
  ```ini
  camera_device = 0  # 使用第一個攝影機
  camera_device = 1  # 使用第二個攝影機
  ```

#### `frame_width` 和 `frame_height`

- **類型**: 整數
- **必填**: 是
- **預設值**: `1280` x `720`
- **單位**: 像素
- **說明**: 拍攝的圖片解析度
- **常用解析度**:
  
  | 名稱 | 寬度 | 高度 | 適用場景 |
  |------|------|------|----------|
  | VGA | 640 | 480 | 低解析度，快速處理 |
  | HD | 1280 | 720 | 平衡品質與速度（預設）|
  | Full HD | 1920 | 1080 | 高品質，文字清晰 |
  | 2K | 2560 | 1440 | 超高品質，處理較慢 |

- **考量因素**:
  - 解析度越高：文字辨識越準確，但傳輸和處理時間越長
  - 解析度越低：處理速度快，但辨識準確度可能降低
- **建議**:
  - 印刷體文字：`1280x720` 或 `1920x1080`
  - 手寫文字：`1920x1080` 以上
  - 小字體：`1920x1080` 以上
- **範例**:
  ```ini
  # 高品質設定
  frame_width = 1920
  frame_height = 1080
  
  # 快速處理設定
  frame_width = 640
  frame_height = 480
  ```

#### `capture_delay`

- **類型**: 浮點數
- **必填**: 否
- **預設值**: `0.5`
- **單位**: 秒
- **說明**: 開啟攝影機後等待穩定的時間
- **作用**: 讓攝影機完成自動對焦和曝光調整
- **建議值**:
  - 快速攝影機：`0.3-0.5` 秒
  - 一般攝影機：`0.5-1.0` 秒（預設）
  - 慢速攝影機：`1.0-2.0` 秒
- **範例**:
  ```ini
  capture_delay = 1.0  # 增加穩定時間
  ```

#### `save_captured_image`

- **類型**: 布林值
- **必填**: 否
- **預設值**: `true`
- **說明**: 是否儲存拍攝的圖片
- **用途**:
  - `true`: 儲存圖片，方便除錯和檢查辨識結果
  - `false`: 不儲存圖片，節省磁碟空間
- **範例**:
  ```ini
  # 除錯模式：儲存圖片
  save_captured_image = true
  
  # 生產模式：不儲存圖片
  save_captured_image = false
  ```

#### `image_save_path`

- **類型**: 字串
- **必填**: 否（當 `save_captured_image = true` 時必填）
- **預設值**: `captured_images`
- **說明**: 圖片儲存目錄的路徑
- **可使用**:
  - 相對路徑：相對於程式執行目錄
  - 絕對路徑：完整路徑
- **範例**:
  ```ini
  # 相對路徑
  image_save_path = captured_images
  
  # 絕對路徑
  image_save_path = /home/pi/photos
  
  # 依日期分類
  image_save_path = images/2025-11-11
  ```

#### `show_preview`

- **類型**: 布林值
- **必填**: 否
- **預設值**: `false`
- **說明**: 是否在拍照時顯示攝影機預覽畫面到 LCD 螢幕
- **用途**:
  - `true`: 顯示即時預覽，方便調整角度和位置
  - `false`: 不顯示預覽，直接拍照（無頭模式）
- **優點**:
  - 可以看到拍攝畫面
  - 方便調整攝影機角度
  - 確認文件位置正確
- **注意事項**:
  - 需要連接 LCD 螢幕或透過 VNC
  - 會增加拍照時間
  - 無頭運行（SSH）時建議設為 `false`
- **範例**:
  ```ini
  # 顯示預覽（有螢幕時）
  show_preview = true
  
  # 無預覽模式（SSH 無頭運行）
  show_preview = false
  ```

#### `preview_window_name`

- **類型**: 字串
- **必填**: 否（當 `show_preview = true` 時建議設定）
- **預設值**: `Book Reader - Camera Preview`
- **說明**: 預覽視窗的標題名稱
- **用途**: 在多視窗環境中識別預覽視窗
- **範例**:
  ```ini
  preview_window_name = Book Reader - Camera Preview
  preview_window_name = 閱讀機器人 - 攝影機預覽
  preview_window_name = OCR Preview
  ```

#### `preview_duration`

- **類型**: 浮點數
- **必填**: 否
- **預設值**: `2.0`
- **單位**: 秒
- **說明**: 預覽畫面顯示的時間
- **特殊值**:
  - `> 0`: 顯示指定秒數後自動拍照（含倒數計時）
  - `0`: 持續顯示直到按下任意鍵才拍照
- **模式說明**:

  **自動拍照模式**（`preview_duration > 0`）:
  ```ini
  preview_duration = 2.0  # 顯示 2 秒後自動拍照
  ```
  - 顯示即時畫面
  - 螢幕上顯示倒數計時
  - 時間到自動拍照
  - 適合固定位置的自動化拍攝

  **手動拍照模式**（`preview_duration = 0`）:
  ```ini
  preview_duration = 0  # 等待按鍵才拍照
  ```
  - 持續顯示即時畫面
  - 螢幕上顯示「按任意鍵拍照」
  - 使用者調整好位置後按鍵拍照
  - 適合需要精確對位的場景

- **建議值**:
  - 快速拍攝：`1.0-2.0` 秒
  - 預覽確認：`3.0-5.0` 秒
  - 手動控制：`0` 秒
- **範例**:
  ```ini
  # 顯示 3 秒後自動拍照
  preview_duration = 3.0
  
  # 等待使用者按鍵
  preview_duration = 0
  ```

### LCD 預覽功能使用範例

#### 場景 1: 自動拍照模式（推薦給一般使用）

```ini
[CAMERA]
camera_device = 0
frame_width = 1280
frame_height = 720
capture_delay = 0.5
save_captured_image = true
image_save_path = captured_images

# 啟用 LCD 預覽，2 秒後自動拍照
show_preview = true
preview_window_name = 閱讀機器人預覽
preview_duration = 2.0
```

**流程**:
1. 按下按鈕觸發
2. 顯示即時畫面和倒數計時
3. 2 秒後自動拍照
4. 顯示「已拍攝！」1 秒
5. 送到 OCR API 辨識

#### 場景 2: 手動拍照模式（精確對位）

```ini
[CAMERA]
show_preview = true
preview_window_name = 書籍掃描器
preview_duration = 0
```

**流程**:
1. 按下按鈕觸發
2. 顯示即時畫面和「按任意鍵拍照」
3. 使用者調整文件位置
4. 使用者按下鍵盤任意鍵
5. 立即拍照並處理

#### 場景 3: 無預覽模式（SSH 無頭運行）

```ini
[CAMERA]
show_preview = false
capture_delay = 0.5
```

**流程**:
1. 按下按鈕觸發
2. 等待 0.5 秒穩定
3. 直接拍照
4. 送到 OCR API 辨識

---

## 🔊 音訊設定

### [AUDIO] 區段

控制音檔播放相關設定。

```ini
[AUDIO]
# 成功辨識後播放的音檔
success_sound = voices/看完了1.mp3

# 辨識失敗後播放的音檔
error_sound = voices/看不懂1.mp3

# 音量（0.0 到 1.0）
volume = 1.0
```

### 設定項目說明

#### `success_sound`

- **類型**: 字串
- **必填**: 是
- **預設值**: `voices/看完了1.mp3`
- **說明**: OCR 辨識成功時播放的音檔路徑
- **支援格式**: MP3, WAV, OGG
- **範例**:
  ```ini
  success_sound = voices/看完了1.mp3
  success_sound = sounds/success.wav
  success_sound = /home/pi/audio/done.mp3
  ```

#### `error_sound`

- **類型**: 字串
- **必填**: 是
- **預設值**: `voices/看不懂1.mp3`
- **說明**: OCR 辨識失敗時播放的音檔路徑
- **支援格式**: MP3, WAV, OGG
- **範例**:
  ```ini
  error_sound = voices/看不懂1.mp3
  error_sound = sounds/error.wav
  error_sound = /home/pi/audio/fail.mp3
  ```

#### `volume`

- **類型**: 浮點數
- **必填**: 否
- **預設值**: `1.0`
- **範圍**: `0.0`（靜音）到 `1.0`（最大音量）
- **說明**: 音檔播放的音量
- **範例**:
  ```ini
  volume = 1.0   # 最大音量
  volume = 0.8   # 80% 音量
  volume = 0.5   # 50% 音量
  volume = 0.0   # 靜音
  ```

### 音檔準備建議

1. **格式選擇**:
   - MP3: 檔案小，相容性好（推薦）
   - WAV: 音質好，但檔案大
   - OGG: 開源格式，壓縮率高

2. **音質設定**:
   ```bash
   # 使用 ffmpeg 轉換音檔
   ffmpeg -i input.mp3 -ar 44100 -ac 2 -b:a 192k output.mp3
   ```

3. **長度建議**:
   - 成功音：2-5 秒
   - 錯誤音：2-5 秒

---

## 🔍 OCR 設定

### [OCR] 區段

控制 OCR 辨識的提示詞設定。

```ini
[OCR]
# 自訂提示詞（預設為標準 OCR）
prompt = <image>\nFree OCR.
```

### 設定項目說明

#### `prompt`

- **類型**: 字串
- **必填**: 否
- **預設值**: `<image>\nFree OCR.`
- **說明**: 送到 DeepSeek-OCR API 的提示詞
- **格式**: 必須以 `<image>` 開頭，後接指示文字
- **用途**: 指導模型如何辨識圖片

### 提示詞範例

```ini
# 標準 OCR（預設）
prompt = <image>\nFree OCR.

# 中文文件辨識
prompt = <image>\n請辨識圖片中的所有中文文字，保持原有的格式和結構。

# 英文文件辨識
prompt = <image>\nPlease recognize all English text in the image.

# 中英混合辨識
prompt = <image>\n請辨識圖片中的所有文字，包含中文、英文和數字。

# 表格辨識
prompt = <image>\n請辨識這個表格的所有內容，包含表頭和所有資料列，保持表格結構。

# 手寫文字辨識
prompt = <image>\n請仔細辨識這張圖片中的手寫文字。

# 名片辨識
prompt = <image>\n請辨識這張名片的所有資訊，包含姓名、職稱、公司、電話和電子郵件。

# 發票辨識
prompt = <image>\n請辨識這張發票的所有資訊，包含發票號碼、日期、金額和品項。

# 書籍內容辨識
prompt = <image>\n請辨識書頁中的所有文字內容，保持段落和格式。
```

---

## 📝 日誌設定

### [LOGGING] 區段

控制日誌記錄的行為。

```ini
[LOGGING]
# 日誌等級（DEBUG, INFO, WARNING, ERROR）
log_level = INFO

# 日誌檔案路徑
log_file = logs/book_reader.log

# 是否在終端機顯示日誌
console_output = true
```

### 設定項目說明

#### `log_level`

- **類型**: 字串
- **必填**: 否
- **預設值**: `INFO`
- **可選值**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **說明**: 日誌記錄的詳細程度

**日誌等級說明**:

| 等級 | 用途 | 記錄內容 |
|------|------|----------|
| DEBUG | 除錯開發 | 所有詳細訊息，包括變數值、函數調用等 |
| INFO | 一般使用 | 重要事件，如啟動、觸發、辨識結果（預設）|
| WARNING | 警告訊息 | 可能的問題，但不影響運行 |
| ERROR | 錯誤訊息 | 錯誤事件，可能影響功能 |
| CRITICAL | 嚴重錯誤 | 嚴重錯誤，可能導致程式終止 |

**範例**:

```ini
# 除錯模式：記錄所有訊息
log_level = DEBUG

# 一般模式：記錄重要事件
log_level = INFO

# 簡潔模式：只記錄警告和錯誤
log_level = WARNING
```

#### `log_file`

- **類型**: 字串
- **必填**: 否
- **預設值**: `logs/book_reader.log`
- **說明**: 日誌檔案的儲存路徑
- **範例**:
  ```ini
  log_file = logs/book_reader.log
  log_file = /var/log/book_reader.log
  log_file = logs/book_reader_$(date +%Y%m%d).log  # 依日期
  ```

#### `console_output`

- **類型**: 布林值
- **必填**: 否
- **預設值**: `true`
- **說明**: 是否在終端機顯示日誌
- **範例**:
  ```ini
  # 顯示在終端機（除錯時使用）
  console_output = true
  
  # 只寫入檔案（背景執行時使用）
  console_output = false
  ```

---

## 🎯 進階設定範例

### 場景 1: 高速辨識模式

適用於快速連續辨識，犧牲部分品質換取速度。

```ini
[API]
api_url = http://192.168.1.100:5000
request_timeout = 15

[GPIO]
trigger_pin = 17
check_interval = 0.2
debounce_delay = 0.3

[CAMERA]
camera_device = 0
frame_width = 640
frame_height = 480
capture_delay = 0.2
save_captured_image = false

[AUDIO]
success_sound = voices/看完了1.mp3
error_sound = voices/看不懂1.mp3
volume = 1.0

[OCR]
prompt = <image>\nFree OCR.

[LOGGING]
log_level = WARNING
log_file = logs/book_reader.log
console_output = false
```

### 場景 2: 高品質辨識模式

適用於需要高準確度的場景，處理時間較長。

```ini
[API]
api_url = http://192.168.1.100:5000
request_timeout = 60

[GPIO]
trigger_pin = 17
check_interval = 0.5
debounce_delay = 0.5

[CAMERA]
camera_device = 0
frame_width = 1920
frame_height = 1080
capture_delay = 1.0
save_captured_image = true
image_save_path = captured_images

[AUDIO]
success_sound = voices/看完了1.mp3
error_sound = voices/看不懂1.mp3
volume = 0.8

[OCR]
prompt = <image>\n請仔細辨識圖片中的所有文字，包含中文、英文和數字，保持原有格式。

[LOGGING]
log_level = DEBUG
log_file = logs/book_reader.log
console_output = true
```

### 場景 3: 書籍掃描模式

適用於掃描書籍內容。

```ini
[API]
api_url = http://192.168.1.100:5000
request_timeout = 45

[GPIO]
trigger_pin = 17
check_interval = 0.5
debounce_delay = 1.0

[CAMERA]
camera_device = 0
frame_width = 1920
frame_height = 1080
capture_delay = 0.8
save_captured_image = true
image_save_path = scanned_books

[AUDIO]
success_sound = voices/看完了1.mp3
error_sound = voices/看不懂1.mp3
volume = 0.5

[OCR]
prompt = <image>\n請辨識書頁中的所有文字內容，保持段落、標題和格式結構。

[LOGGING]
log_level = INFO
log_file = logs/book_scanner.log
console_output = true
```

---

## 🔧 設定檔管理

### 備份設定檔

```bash
# 建立備份
cp config.ini config.ini.backup

# 依日期備份
cp config.ini config.ini.$(date +%Y%m%d)
```

### 多個設定檔

可以準備多個設定檔用於不同場景：

```bash
# 場景設定檔
config.high_quality.ini
config.high_speed.ini
config.book_scanner.ini

# 切換使用
cp config.high_quality.ini config.ini
```

### 驗證設定檔

建立驗證腳本：

```python
#!/usr/bin/env python3
import configparser
import os

config = configparser.ConfigParser()
config.read('config.ini')

# 檢查必要設定
required = {
    'API': ['api_url'],
    'GPIO': ['trigger_pin'],
    'CAMERA': ['camera_device', 'frame_width', 'frame_height'],
    'AUDIO': ['success_sound', 'error_sound']
}

all_ok = True
for section, keys in required.items():
    if not config.has_section(section):
        print(f"✗ 缺少區段: [{section}]")
        all_ok = False
        continue
    
    for key in keys:
        if not config.has_option(section, key):
            print(f"✗ 缺少設定: [{section}] {key}")
            all_ok = False

# 檢查檔案是否存在
if config.has_option('AUDIO', 'success_sound'):
    path = config.get('AUDIO', 'success_sound')
    if not os.path.exists(path):
        print(f"✗ 找不到檔案: {path}")
        all_ok = False

if all_ok:
    print("✓ 設定檔驗證通過")
else:
    print("✗ 設定檔有問題，請檢查")
```

---

**文檔版本**: 1.0.0  
**更新日期**: 2025-11-11

