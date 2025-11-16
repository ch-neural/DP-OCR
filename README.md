# DeepSeek-OCR 閱讀機器人

---

## ⚠️ 重要前置需求

> **🚨 本閱讀機器人需要搭配 DeepSeek-OCR API 服務才能使用！**

在使用本閱讀機器人之前，您**必須**先安裝並啟動 **DeepSeek-OCR API 服務**：

### 📦 DeepSeek-OCR API 服務（必需）

**GitHub 倉庫**：**[https://github.com/ch-neural/deepseek-ocr-api](https://github.com/ch-neural/deepseek-ocr-api)**

**快速安裝**：

```bash
# 1. Clone API 服務倉庫
git clone https://github.com/ch-neural/deepseek-ocr-api.git
cd deepseek-ocr-api

# 2. 安裝依賴
pip install -r requirements.txt

# 3. 登入 Hugging Face
huggingface-cli login

# 4. 啟動 API 服務
python app.py
```

**驗證安裝**：

```bash
curl http://localhost:5000/health
# 應該看到: {"status": "healthy", "model": "DeepSeek-OCR", ...}
```

> 💡 **詳細安裝指南**：請參閱 [README/DEEPSEEK_API_SETUP.md](README/DEEPSEEK_API_SETUP.md)

---

### 🔗 架構說明

```
┌────────────────────────────────────────────────────────────┐
│           DeepSeek-OCR 閱讀機器人 (本專案)                    │
│   Raspberry Pi + GPIO + 相機 + Web 介面                     │
└────────────────────────────────────────────────────────────┘
                      ↓ HTTP API 調用
┌────────────────────────────────────────────────────────────┐
│        DeepSeek-OCR API 服務 (必需安裝)                      │
│   https://github.com/ch-neural/deepseek-ocr-api           │
│   提供 OCR 辨識功能 (需要 GPU 支援)                          │
└────────────────────────────────────────────────────────────┘
```

**本閱讀機器人負責**：
- 📷 相機拍攝和預覽
- 🔘 GPIO 按鈕控制
- 🌐 Web 介面操作
- 🔊 語音朗讀
- 📝 結果顯示和管理

**DeepSeek-OCR API 服務負責**：
- 🤖 OCR 文字識別
- 🧠 DeepSeek-OCR 模型推理
- 🖼️ 圖像預處理
- ⚡ GPU 加速運算

---

## 📖 簡介

閱讀機器人是一個基於 Raspberry Pi 的自動化 OCR 辨識系統。當偵測到 GPIO 觸發信號時，會自動拍攝照片並使用 DeepSeek-OCR API 進行文字辨識，然後播放對應的語音回饋。

## ✨ 功能特色

- ⚡ **GPIO 觸發**: 偵測 GPIO17 信號自動啟動辨識流程
- 📷 **USB 攝影機**: 自動拍攝高解析度照片
- 🖥️ **LCD 預覽**: 可選顯示即時攝影機畫面，支援自動/手動拍照模式
- 🔍 **OCR 辨識**: 透過 DeepSeek-OCR API 進行高準確度文字辨識
- 🔊 **語音回饋**: 根據辨識結果播放成功或失敗音檔
- ⚙️ **彈性設定**: 所有參數皆可透過設定檔調整
- 📝 **完整日誌**: 記錄所有操作過程，方便除錯

## 📋 系統需求

### 硬體需求

- Raspberry Pi 3/4/5 或相容裝置
- USB 攝影機
- 觸發按鈕或開關（連接到 GPIO17）
- 喇叭或耳機（播放音檔用）

### 軟體需求

- Raspberry Pi OS (Raspbian) 或相容的 Linux 系統
- Python 3.7 或以上版本
- 網路連線（用於連接 DeepSeek-OCR API 伺服器）

## 🚀 安裝步驟

> ⚠️ **開始之前**：請確保已安裝並啟動 [DeepSeek-OCR API 服務](https://github.com/ch-neural/deepseek-ocr-api)

### 步驟 0：確認 DeepSeek-OCR API 服務

**必須先完成**：

```bash
# 測試 API 服務是否運行中
curl http://localhost:5000/health

# 預期回應：
# {
#   "status": "healthy",
#   "model": "DeepSeek-OCR",
#   "timestamp": "..."
# }
```

如果看到錯誤，請先安裝 API 服務：[https://github.com/ch-neural/deepseek-ocr-api](https://github.com/ch-neural/deepseek-ocr-api)

---

### 步驟 1：安裝閱讀機器人

#### 快速安裝（推薦）

```bash
cd example_bookReader

# 使用自動安裝腳本（Raspberry Pi 5 相容）
./install_rpi5.sh
```

### 手動安裝

#### 1. 安裝系統依賴

**所有 Raspberry Pi 版本**（統一使用 rpi-lgpio）:
```bash
sudo apt update
sudo apt install -y python3-pip python3-opencv libsdl2-mixer-2.0-0

# 安裝 rpi-lgpio（Raspberry Pi 5 相容的 RPi.GPIO 替代方案）
pip3 install rpi-lgpio
# 或使用系統套件
sudo apt install -y python3-rpi-lgpio
```

#### 2. 安裝 Python 套件

```bash
cd example_bookReader
pip3 install -r requirements.txt
```

程式現在**只使用 rpi-lgpio**（RPi.GPIO 的 drop-in replacement），相容所有 Raspberry Pi 版本：
- Raspberry Pi 5 → 使用 `rpi-lgpio`（推薦）
- Raspberry Pi 4 及更早 → 使用 `rpi-lgpio`（相容）

### 3. 設定權限

```bash
# 賦予執行權限
chmod +x book_reader.py

# 將使用者加入 gpio 群組（rpi-lgpio 需要，可能需要重新登入）
sudo usermod -a -G gpio $USER
sudo reboot  # 重新啟動後生效

# 將使用者加入 video 群組（用於攝影機）
sudo usermod -a -G video $USER
```

### 4. 硬體連接

#### GPIO 接線

將觸發按鈕連接到 Raspberry Pi（使用 PULL_UP 模式）：

```
按鈕一端 -> GPIO17 (Pin 11)
按鈕另一端 -> GND (Pin 6, 9, 14, 20, 25, 30, 34, 39 任一)
```

**注意**：
- 系統使用內部上拉電阻（PULL_UP），不需要外部上拉電阻
- 按鈕按下時，GPIO17 會從 HIGH (3.3V) 變為 LOW (0V)
- 系統會偵測完整的按鈕點擊（按下→釋放），而不是簡單的狀態檢查

#### USB 攝影機

將 USB 攝影機插入 Raspberry Pi 的 USB 接口。

確認攝影機已被系統識別：

```bash
ls /dev/video*
# 應該會看到 /dev/video0 或類似的裝置
```

## ⚙️ 設定說明

編輯 `config.ini` 檔案以調整系統參數：

### API 設定（重要！）

```ini
[API]
# DeepSeek-OCR API 伺服器位址
# 📌 請修改為您的 DeepSeek-OCR API 服務位址
api_url = http://localhost:5000         # 如果 API 在本機
# api_url = http://192.168.1.100:5000   # 如果 API 在區網其他機器
# api_url = http://your-server.com:5000 # 如果 API 在遠端伺服器

ocr_endpoint = /ocr
request_timeout = 90
```

**網路配置說明**：

| 場景 | API 位址設定 | 說明 |
|------|-------------|------|
| 同一台機器 | `http://localhost:5000` | API 和閱讀機器人在同一台機器 |
| 同一區網 | `http://192.168.1.100:5000` | API 在另一台區網機器 |
| 遠端伺服器 | `http://your-server.com:5000` | API 在遠端伺服器 |

> 💡 **完整配置指南**：請參閱 [README/DEEPSEEK_API_SETUP.md](README/DEEPSEEK_API_SETUP.md)

### GPIO 設定

```ini
[GPIO]
# 觸發 GPIO 腳位編號（BCM 編號）
trigger_pin = 17
# 去彈跳延遲時間（秒）
# 注意：系統現在使用按鈕點擊偵測（按下→釋放），不再使用間隔檢查方式
debounce_delay = 0.2
```

**按鈕點擊偵測機制**：
- 系統會偵測完整的按鈕點擊動作（按下→釋放）
- 包含去彈跳處理，避免誤觸發
- 只接受合理的按壓時間（0.1 秒到 5 秒）
- 使用 PULL_UP 模式，按鈕按下時 GPIO 變為 LOW

### 攝影機設定

```ini
[CAMERA]
# USB Camera 裝置編號（通常是 0）
camera_device = 0
# 拍攝解析度
frame_width = 1280
frame_height = 720
# LCD 預覽功能（可選）
show_preview = false          # 是否顯示攝影機預覽
preview_duration = 2.0        # 預覽時間（秒），0 = 等待按鍵
```

**LCD 預覽模式**:
- `show_preview = false` - 無預覽模式（SSH 無頭運行）
- `show_preview = true` + `preview_duration > 0` - 自動拍照模式（顯示倒數計時）
- `show_preview = true` + `preview_duration = 0` - 手動拍照模式（等待按鍵）

### 音訊設定

```ini
[AUDIO]
# 成功辨識後播放的音檔
success_sound = voices/看完了1.mp3
# 辨識失敗後播放的音檔
error_sound = voices/看不懂1.mp3
# 音量（0.0 到 1.0）
volume = 1.0
```

更多設定選項請參考 `config.ini` 檔案內的註解。

## 🎯 使用方式

### 基本使用

#### 1. 確認 DeepSeek-OCR API 服務運行中

```bash
# 測試 API 連接
curl http://localhost:5000/health

# 如果無法連接，請先啟動 API 服務
cd /path/to/deepseek-ocr-api
python app.py
```

#### 2. 啟動閱讀機器人

```bash
cd example_bookReader
python3 book_reader.py
```

3. 按下並釋放觸發按鈕（連接到 GPIO17），系統會：
   - （可選）顯示攝影機預覽畫面
   - 拍攝照片
   - 送到 API 辨識
   - 在終端機顯示辨識結果
   - 播放對應的音檔

**注意**：系統會偵測完整的按鈕點擊（按下→釋放），請確保按鈕按下時間在 0.1-5 秒之間

4. 按 `Ctrl+C` 停止程式

### 背景執行

如果要在背景執行閱讀機器人：

```bash
# 使用 nohup 背景執行
nohup python3 book_reader.py > output.log 2>&1 &

# 查看程序
ps aux | grep book_reader

# 停止程式（找到 PID 後執行）
kill <PID>
```

### 開機自動啟動

建立 systemd 服務：

```bash
sudo nano /etc/systemd/system/book-reader.service
```

內容如下：

```ini
[Unit]
Description=Book Reader Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/example_bookReader
ExecStart=/usr/bin/python3 /home/pi/example_bookReader/book_reader.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

啟用服務：

```bash
sudo systemctl daemon-reload
sudo systemctl enable book-reader.service
sudo systemctl start book-reader.service

# 查看狀態
sudo systemctl status book-reader.service

# 查看日誌
sudo journalctl -u book-reader.service -f
```

## 📂 目錄結構

```
example_bookReader/
├── book_reader.py          # 主程式
├── config.ini              # 設定檔
├── requirements.txt        # Python 依賴套件
├── README.md               # 本說明文件
├── README/                 # 詳細文檔目錄
│   ├── INSTALLATION.md     # 詳細安裝指南
│   ├── CONFIGURATION.md    # 設定檔說明
│   ├── TROUBLESHOOTING.md  # 疑難排解
│   └── ERROR_MESSAGES.md   # 錯誤訊息說明
├── voices/                 # 音檔目錄
│   ├── 看完了1.mp3
│   ├── 看完了2.mp3
│   ├── 看不懂1.mp3
│   └── 看不懂2.mp3
├── logs/                   # 日誌目錄（自動建立）
│   └── book_reader.log
└── captured_images/        # 拍攝的照片（自動建立）
    └── capture_YYYYMMDD_HHMMSS.jpg
```

## 🔧 進階功能

### 自訂提示詞

編輯 `config.ini` 中的 OCR 提示詞：

```ini
[OCR]
# 自訂提示詞（預設為標準 OCR）
prompt = <image>\n請辨識圖片中的所有文字，包含中文和英文。
```

### 除錯模式

將日誌等級設為 DEBUG 以取得更詳細的資訊：

```ini
[LOGGING]
log_level = DEBUG
```

### 測試攝影機

使用以下指令測試攝影機是否正常：

```bash
python3 -c "import cv2; cap = cv2.VideoCapture(0); ret, frame = cap.read(); print('攝影機測試:', '成功' if ret else '失敗'); cap.release()"
```

### 測試 GPIO

測試 GPIO 腳位是否正常：

```bash
# 安裝 GPIO 測試工具
sudo apt install -y python3-gpiozero

# 測試腳位
python3 -c "from gpiozero import Button; btn = Button(17); print('請按下按鈕...'); btn.wait_for_press(); print('按鈕觸發成功！')"
```

## ❓ 疑難排解

### 常見問題

詳細的疑難排解指南請參考 [README/TROUBLESHOOTING.md](README/TROUBLESHOOTING.md)

#### 1. 找不到攝影機

**錯誤訊息**: `無法開啟攝影機裝置 0`

**解決方法**:
- 確認攝影機已正確連接
- 檢查攝影機裝置編號: `ls /dev/video*`
- 修改 `config.ini` 中的 `camera_device` 設定

#### 2. GPIO 權限不足或 rpi-lgpio 初始化失敗

**錯誤訊息**: `rpi-lgpio 初始化失敗` 或 `No access to /dev/mem`

**解決方法**:
```bash
# 將使用者加入 gpio 群組
sudo usermod -a -G gpio $USER

# 重新啟動系統（讓權限生效）
sudo reboot

# 如果仍然失敗，重新安裝 rpi-lgpio
pip3 install --upgrade rpi-lgpio
# 或使用系統套件
sudo apt install --reinstall python3-rpi-lgpio
```

#### 3. API 連線失敗

**錯誤訊息**: `OCR API 錯誤`

**解決方法**:
- 確認 API 伺服器正在運行
- 檢查網路連線
- 確認 `config.ini` 中的 API 位址正確
- 測試 API: `curl http://172.30.19.20:5000/health`

#### 4. 找不到音檔

**錯誤訊息**: `找不到音檔: voices/看完了1.mp3`

**解決方法**:
- 確認 `voices/` 目錄存在
- 確認音檔已放置在正確位置
- 檢查檔案權限: `ls -l voices/`

### 取得協助

如果遇到其他問題，請查看：

1. 日誌檔案: `logs/book_reader.log`
2. 詳細文檔: `README/` 目錄
3. 錯誤訊息說明: `README/ERROR_MESSAGES.md`

## 📝 程式架構

### 主要類別

#### `BookReader` 類別

閱讀機器人的主要類別，包含以下方法：

- `__init__(config_file)`: 初始化機器人
- `capture_frame()`: 拍攝照片
- `send_to_ocr_api(frame)`: 送到 API 辨識
- `play_sound(sound_path)`: 播放音檔
- `process_trigger()`: 處理觸發事件
- `run()`: 主迴圈
- `cleanup()`: 清理資源

### 執行流程

```
1. 初始化系統（GPIO、攝影機、音訊）
   ↓
2. 進入主迴圈
   ↓
3. 偵測按鈕點擊（按下→釋放，包含去彈跳處理）
   ↓
4. 拍攝照片
   ↓
5. 送到 DeepSeek-OCR API
   ↓
6. 接收辨識結果
   ↓
7. 顯示結果並播放音檔
   ↓
8. 回到步驟 3（持續循環）
```

## 🔐 安全性考量

- **網路安全**: API 伺服器建議設定防火牆規則，限制只有特定 IP 可存取
- **檔案權限**: 確保設定檔和音檔的權限設定正確
- **隱私保護**: 拍攝的照片會儲存在本地，請定期清理或關閉儲存功能

## 📄 授權條款

本專案採用與 DeepSeek-OCR 相同的授權條款。

## 🤝 貢獻

歡迎提交問題回報和改進建議。

## 📞 聯絡資訊

如有任何問題或建議，請透過以下方式聯絡：

- 專案網址: [DeepSeek-OCR](https://github.com/unsloth/DeepSeek-OCR)
- 技術支援: 請參考 README/ 目錄下的文檔

---

**版本**: 1.0.0  
**更新日期**: 2025-11-11  
**作者**: DeepSeek-OCR Team

