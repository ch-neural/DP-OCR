# 閱讀機器人快速開始指南

## ⚡ 5 分鐘快速部署

### 1. 安裝系統依賴

```bash
sudo apt update
sudo apt install -y python3-pip python3-rpi.gpio python3-opencv libsdl2-mixer-2.0-0
```

### 2. 安裝 Python 套件

```bash
cd example_bookReader
pip3 install -r requirements.txt
```

### 3. 連接硬體（Raspberry Pi 版本）

```
按鈕一端 → GPIO17 (Pin 11)
按鈕另一端 → GND (Pin 6)
USB 攝影機 → USB 接口
```

### 4. 設定 API 位址

```bash
nano config.ini
# 修改以下行：
# api_url = http://172.30.19.20:5000  # 改為您的 API 伺服器位址
```

### 5. 設定權限

```bash
sudo usermod -a -G gpio,video $USER
# 登出後重新登入
```

### 6. 測試系統

```bash
python3 test_components.py
```

### 7. 選擇啟動模式

```bash
# 🌐 Flask Web 版（伺服器相機 + GPIO）
python3 book_reader_flask.py

# 📱 Remote 遠端版（客戶端 Webcam，自動 HTTPS）
python3 book_reader_remote.py

# 💻 CLI 終端機版
python3 book_reader.py
```

---

## 🎯 三種執行模式快速選擇

| 模式 | 啟動命令 | 網址 | 適用場景 |
|------|---------|------|---------|
| **Flask Web 版** | `python3 book_reader_flask.py` | `http://IP:8502` | RPi 相機 + GPIO 按鈕 |
| **Remote 遠端版** | `python3 book_reader_remote.py` | `https://IP:8502` | 用戶自帶 Webcam |
| **CLI 終端機版** | `python3 book_reader.py` | N/A | 無頭運行 + 音效 |

### 📱 Remote 遠端版（推薦給一般電腦使用）

```bash
python3 book_reader_remote.py
```

- 🔐 **自動 HTTPS**：程式會自動生成 SSL 憑證
- 🎥 用戶可使用自己電腦/手機的 Webcam
- ⚠️ 首次連接時，瀏覽器會顯示安全警告，點擊「進階」→「繼續前往」即可

---

## 🔧 常用命令

```bash
# Flask Web 版（伺服器相機）
python3 book_reader_flask.py

# Remote 遠端版（客戶端 Webcam）
python3 book_reader_remote.py

# CLI 終端機版
python3 book_reader.py

# 背景執行
nohup python3 book_reader_remote.py > output.log 2>&1 &

# 查看日誌
tail -f logs/book_reader.log

# 查看拍攝的照片
ls -lh captured_images/

# 停止程式
pkill -f book_reader
```

---

## 📝 設定檔快速參考

| 設定項目 | 位置 | 常用值 |
|---------|------|--------|
| API 伺服器 | `[API] api_url` | `http://IP:5000` |
| GPIO 腳位 | `[GPIO] trigger_pin` | `17` |
| 攝影機編號 | `[CAMERA] camera_device` | `0` |
| 圖片解析度 | `[CAMERA] frame_width/height` | `1280x720`, `1920x1080` |
| LCD 預覽 | `[CAMERA] show_preview` | `true`, `false` |
| 預覽時間 | `[CAMERA] preview_duration` | `2.0`（秒），`0`（等按鍵）|
| 成功音檔 | `[AUDIO] success_sound` | `voices/看完了1.mp3` |
| 錯誤音檔 | `[AUDIO] error_sound` | `voices/看不懂1.mp3` |
| 日誌等級 | `[LOGGING] log_level` | `INFO`, `DEBUG` |

---

## ❓ 快速疑難排解

| 問題 | 解決方法 |
|------|----------|
| 找不到攝影機 | `ls /dev/video*` 檢查裝置 |
| GPIO 權限不足 | `sudo usermod -a -G gpio $USER` |
| API 連線失敗 | 檢查 `config.ini` 中的 `api_url` |
| 找不到音檔 | 確認 `voices/` 目錄存在 |
| 按鈕沒反應 | 用三用電表測試接線 |
| Webcam 無法使用 | 使用 HTTPS 版本 (`book_reader_remote.py`) |
| SSL 憑證警告 | 點擊「進階」→「繼續前往」 |

---

## 📚 詳細文檔

- 完整說明：[README.md](README.md)
- 詳細安裝：[README/INSTALLATION.md](README/INSTALLATION.md)
- 設定說明：[README/CONFIGURATION.md](README/CONFIGURATION.md)
- SSL 憑證：[README/SSL_AUTO_CERTIFICATE.md](README/SSL_AUTO_CERTIFICATE.md)
- 疑難排解：[README/TROUBLESHOOTING.md](README/TROUBLESHOOTING.md)
- 錯誤訊息：[README/ERROR_MESSAGES.md](README/ERROR_MESSAGES.md)

---

## 🎓 GPIO 腳位對照

```
實體腳位 11 = GPIO17 (BCM) ← 預設使用
實體腳位 1  = 3.3V
實體腳位 6  = GND
```

完整腳位圖請參考：[README/INSTALLATION.md](README/INSTALLATION.md)

---

**版本**: 1.4.0  
**更新日期**: 2025-12-02

