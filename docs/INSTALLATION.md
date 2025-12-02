# 閱讀機器人詳細安裝指南

## 📋 目錄

- [安裝前準備](#安裝前準備)
- [作業系統設定](#作業系統設定)
- [套件安裝](#套件安裝)
- [硬體配置](#硬體配置)
- [設定與測試](#設定與測試)
- [進階安裝](#進階安裝)

---

## 🛠️ 安裝前準備

### 硬體清單

| 項目 | 規格 | 必要性 | 備註 |
|------|------|--------|------|
| Raspberry Pi | 3/4/5 或相容裝置 | 必要 | 建議 Pi 4 2GB 以上 |
| SD 卡 | 16GB 以上，Class 10 | 必要 | 建議 32GB |
| USB 攝影機 | 支援 UVC 協定 | 必要 | 解析度 720p 以上 |
| 按鈕/開關 | 一般按鈕或撥動開關 | 必要 | 用於 GPIO 觸發 |
| 杜邦線 | 母對母或公對母 | 必要 | 連接按鈕到 GPIO |
| 音訊輸出 | 喇叭、耳機或 HDMI | 必要 | 播放音檔用 |
| 電源供應器 | 5V 3A（Pi 4）| 必要 | 官方電源供應器佳 |
| 網路連線 | 乙太網路或 WiFi | 必要 | 連接 API 伺服器 |

### 軟體需求

- Raspberry Pi OS (Raspbian) Buster 或更新版本
- Python 3.7 或以上
- 網路連線
- SSH 存取（遠端安裝時）

### 預備知識

- 基本 Linux 指令操作
- Raspberry Pi GPIO 基礎知識
- 網路設定基礎

---

## 💻 作業系統設定

### 1. 安裝 Raspberry Pi OS

#### 使用 Raspberry Pi Imager（推薦）

1. 下載 Raspberry Pi Imager：
   - 網址: https://www.raspberrypi.org/software/

2. 選擇作業系統：
   - Raspberry Pi OS (32-bit) 或
   - Raspberry Pi OS Lite（無桌面環境，較省資源）

3. 進階設定（齒輪圖示）：
   - 啟用 SSH
   - 設定使用者名稱和密碼
   - 設定 WiFi（如需要）
   - 設定時區

4. 寫入 SD 卡

#### 首次開機設定

```bash
# 更新系統
sudo apt update
sudo apt upgrade -y

# 設定區域和時區
sudo raspi-config
# 選擇：
# 1. System Options -> Wireless LAN (設定 WiFi)
# 2. Localisation Options -> Timezone
# 3. Localisation Options -> Locale (選擇 zh_TW.UTF-8)
# 4. Interface Options -> Camera (如使用 Pi Camera，需啟用)

# 重新開機
sudo reboot
```

### 2. 系統優化

#### 增加 Swap 空間（建議）

```bash
# 編輯 swap 設定
sudo nano /etc/dphys-swapfile

# 修改以下行：
# CONF_SWAPSIZE=1024  # 從 100 改為 1024

# 重啟 swap 服務
sudo /etc/init.d/dphys-swapfile stop
sudo /etc/init.d/dphys-swapfile start
```

#### 設定靜態 IP（建議）

```bash
# 編輯網路設定
sudo nano /etc/dhcpcd.conf

# 在檔案末尾加入（根據您的網路環境修改）：
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 8.8.4.4

# 或針對 WiFi：
interface wlan0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 8.8.4.4

# 重啟網路服務
sudo systemctl restart dhcpcd
```

---

## 📦 套件安裝

### 1. 安裝系統依賴

```bash
# 更新套件列表
sudo apt update

# 安裝 Python 開發工具
sudo apt install -y python3-pip python3-dev python3-setuptools

# 安裝 GPIO 相關套件
sudo apt install -y python3-rpi.gpio

# 安裝 OpenCV 依賴（重要！）
sudo apt install -y \
    libopencv-dev \
    python3-opencv \
    libatlas-base-dev \
    libjasper-dev \
    libqtgui4 \
    libqt4-test \
    libhdf5-dev \
    libhdf5-serial-dev

# 安裝音訊相關套件
sudo apt install -y \
    libsdl2-mixer-2.0-0 \
    libsdl2-2.0-0 \
    alsa-utils \
    pulseaudio

# 安裝其他工具
sudo apt install -y \
    git \
    curl \
    wget \
    vim \
    htop
```

### 2. 安裝 Python 套件

#### 方法 1: 使用 requirements.txt（推薦）

```bash
# 進入專案目錄
cd /path/to/example_bookReader

# 安裝所有依賴
pip3 install -r requirements.txt

# 或使用 sudo（如果遇到權限問題）
sudo pip3 install -r requirements.txt
```

#### 方法 2: 逐一安裝

```bash
# RPi.GPIO
sudo pip3 install RPi.GPIO

# OpenCV
sudo pip3 install opencv-python

# Requests
sudo pip3 install requests

# Pygame
sudo pip3 install pygame
```

### 3. 驗證安裝

```bash
# 建立驗證腳本
cat > verify_install.py << 'EOF'
#!/usr/bin/env python3
import sys

packages = {
    'RPi.GPIO': 'RPi.GPIO',
    'OpenCV': 'cv2',
    'Requests': 'requests',
    'Pygame': 'pygame'
}

print("驗證 Python 套件安裝...\n")

all_ok = True
for name, module in packages.items():
    try:
        mod = __import__(module)
        version = getattr(mod, '__version__', '未知版本')
        print(f"✓ {name}: {version}")
    except ImportError as e:
        print(f"✗ {name}: 未安裝 ({e})")
        all_ok = False

if all_ok:
    print("\n所有套件安裝成功！")
    sys.exit(0)
else:
    print("\n有套件未正確安裝，請檢查錯誤訊息")
    sys.exit(1)
EOF

# 執行驗證
python3 verify_install.py
```

---

## 🔌 硬體配置

### 1. GPIO 接線

#### 材料準備

- 按鈕或開關 x 1
- 杜邦線 x 2

#### 接線方式

**基本接線**（使用內部下拉電阻）：

```
按鈕/開關端 1 ──→ GPIO17 (實體腳位 11)
按鈕/開關端 2 ──→ 3.3V (實體腳位 1 或 17)
```

**使用外部下拉電阻**（可選）：

```
3.3V ──→ 按鈕/開關端 1 ──→ GPIO17
                            ↓
                        10kΩ 電阻
                            ↓
                          GND
```

#### Raspberry Pi GPIO 腳位圖

```
3.3V  (1)  (2)  5V
GPIO2 (3)  (4)  5V
GPIO3 (5)  (6)  GND
GPIO4 (7)  (8)  GPIO14
GND   (9)  (10) GPIO15
GPIO17(11) (12) GPIO18  ← 我們使用 GPIO17 (腳位 11)
GPIO27(13) (14) GND
GPIO22(15) (16) GPIO23
3.3V  (17) (18) GPIO24
GPIO10(19) (20) GND
...
```

#### 測試 GPIO 連接

```bash
# 建立測試腳本
cat > test_gpio_hardware.py << 'EOF'
#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

print("GPIO17 硬體測試")
print("請按下按鈕...")
print("按 Ctrl+C 結束")
print()

try:
    last_state = GPIO.input(17)
    print(f"初始狀態: {'HIGH' if last_state else 'LOW'}")
    
    while True:
        current_state = GPIO.input(17)
        
        if current_state != last_state:
            if current_state == GPIO.HIGH:
                print("✓ 按鈕按下 (HIGH)")
            else:
                print("✓ 按鈕放開 (LOW)")
            last_state = current_state
        
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print("\n測試結束")
finally:
    GPIO.cleanup()
EOF

python3 test_gpio_hardware.py
```

### 2. USB 攝影機設定

#### 連接攝影機

1. 將 USB 攝影機插入 Raspberry Pi 的 USB 接口
2. 等待幾秒讓系統識別

#### 驗證攝影機

```bash
# 檢查攝影機裝置
ls -l /dev/video*

# 應該看到類似輸出：
# crw-rw----+ 1 root video 81, 0 Nov 11 12:00 /dev/video0

# 查看攝影機資訊
v4l2-ctl --list-devices

# 查看支援的格式
v4l2-ctl --list-formats-ext
```

#### 測試攝影機拍攝

```bash
# 方法 1: 使用 fswebcam
sudo apt install fswebcam
fswebcam -r 1280x720 test_image.jpg

# 方法 2: 使用 OpenCV
cat > test_camera_capture.py << 'EOF'
#!/usr/bin/env python3
import cv2

print("開啟攝影機...")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("✗ 無法開啟攝影機")
    exit(1)

print("設定解析度...")
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

print("拍攝照片...")
ret, frame = cap.read()

if ret:
    cv2.imwrite('test_camera.jpg', frame)
    print(f"✓ 拍攝成功！")
    print(f"  解析度: {frame.shape[1]}x{frame.shape[0]}")
    print(f"  檔案: test_camera.jpg")
else:
    print("✗ 無法拍攝照片")

cap.release()
EOF

python3 test_camera_capture.py
```

#### 常見問題

**問題**: 攝影機裝置不存在

```bash
# 確認 USB 裝置
lsusb

# 重新載入 USB 驅動
sudo modprobe uvcvideo
```

**問題**: 權限不足

```bash
# 將使用者加入 video 群組
sudo usermod -a -G video $USER

# 登出後重新登入
```

### 3. 音訊設定

#### 測試音訊輸出

```bash
# 列出音訊裝置
aplay -l

# 測試音訊（3.5mm 或 HDMI）
aplay /usr/share/sounds/alsa/Front_Center.wav
```

#### 選擇音訊輸出

```bash
# 使用 raspi-config
sudo raspi-config
# 選擇：System Options -> Audio -> 選擇輸出裝置

# 或使用命令列
# 輸出到 3.5mm 插孔
amixer cset numid=3 1

# 輸出到 HDMI
amixer cset numid=3 2
```

#### 調整音量

```bash
# 使用 alsamixer（互動式）
alsamixer

# 使用命令設定音量（0-100）
amixer set Master 80%
```

---

## ⚙️ 設定與測試

### 1. 下載閱讀機器人程式

```bash
# 如果是從 Git 取得
cd ~
git clone <repository-url> example_bookReader
cd example_bookReader

# 或者手動複製檔案到 Raspberry Pi
# 使用 scp：
# scp -r example_bookReader/ pi@192.168.1.100:~/
```

### 2. 設定權限

```bash
cd ~/example_bookReader

# 賦予執行權限
chmod +x book_reader.py

# 將使用者加入必要的群組
sudo usermod -a -G gpio,video,audio $USER

# 登出後重新登入使設定生效
```

### 3. 編輯設定檔

```bash
# 複製範本（如果有）
cp config.ini.example config.ini

# 編輯設定
nano config.ini
```

**必須修改的項目**：

```ini
[API]
# 修改為您的 DeepSeek-OCR API 伺服器位址
api_url = http://172.30.19.20:5000
```

**可選修改項目**：

```ini
[GPIO]
trigger_pin = 17  # 如使用其他腳位，請修改

[CAMERA]
camera_device = 0  # 如有多個攝影機，可能需要修改

[AUDIO]
success_sound = voices/看完了1.mp3
error_sound = voices/看不懂1.mp3
volume = 0.8  # 調整音量
```

### 4. 測試 API 連線

```bash
# 測試 API 伺服器
curl http://172.30.19.20:5000/health

# 應該回傳類似：
# {"status":"healthy","service":"DeepSeek-OCR API","timestamp":"..."}

# 測試 OCR 功能（使用測試圖片）
curl -X POST -F "file=@test_image.jpg" http://172.30.19.20:5000/ocr
```

### 5. 執行完整測試

```bash
# 執行元件測試腳本
python3 test_components.py

# 預期輸出：
# === 元件測試 ===
# 測試 GPIO... ✓
# 測試攝影機... ✓
# 測試 API... ✓
# 測試音訊系統... ✓
# === 測試結果: 4/4 通過 ===
```

### 6. 首次執行

```bash
# 前景執行（測試用）
python3 book_reader.py

# 按下按鈕測試功能
# 按 Ctrl+C 停止
```

---

## 🚀 進階安裝

### 1. 設定為系統服務（開機自動啟動）

#### 建立 systemd 服務

```bash
# 建立服務檔案
sudo nano /etc/systemd/system/book-reader.service
```

輸入以下內容：

```ini
[Unit]
Description=Book Reader Service
After=network.target sound.target

[Service]
Type=simple
User=pi
Group=pi
# 重要：必須設置 WorkingDirectory，確保用戶有寫入權限
# 這對於 rpi-lgpio 庫（Raspberry Pi 5）特別重要，因為它需要在工作目錄創建通知文件
WorkingDirectory=/home/pi/example_bookReader
ExecStart=/usr/bin/python3 /home/pi/example_bookReader/book_reader.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

# 環境變數（如需要）
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

**重要注意事項**:
- **WorkingDirectory 必須設置**：這對於 Raspberry Pi 5 使用 `rpi-lgpio` 庫時特別重要
- `rpi-lgpio` 庫需要在當前工作目錄創建通知文件 `.lgd-nfy-*`
- 如果 `WorkingDirectory` 未設置或指向沒有寫入權限的目錄，會出現 `FileNotFoundError: [Errno 2] No such file or directory: '.lgd-nfy-3'` 錯誤
- 程式已自動處理此問題，但建議在 systemd service 文件中明確設置 `WorkingDirectory`
- 如果使用虛擬環境（venv），請使用 venv 中 Python 的完整路徑：
  ```ini
  WorkingDirectory=/home/pi/my_project
  ExecStart=/home/pi/my_project/venv/bin/python /home/pi/my_project/book_reader.py
  ```

**疑難排解**:
如果遇到 `lgpio` 通知文件創建失敗的錯誤，請參考 [ERROR_MESSAGES.md](ERROR_MESSAGES.md#錯誤-2-2-lgpio-通知文件創建失敗systemd-服務運行時) 的詳細說明。

#### 啟用並啟動服務

```bash
# 重新載入 systemd
sudo systemctl daemon-reload

# 啟用服務（開機自動啟動）
sudo systemctl enable book-reader.service

# 啟動服務
sudo systemctl start book-reader.service

# 查看狀態
sudo systemctl status book-reader.service

# 查看日誌
sudo journalctl -u book-reader.service -f

# 停止服務
sudo systemctl stop book-reader.service

# 重啟服務
sudo systemctl restart book-reader.service
```

### 2. 設定日誌輪替

```bash
# 建立 logrotate 設定
sudo nano /etc/logrotate.d/book-reader
```

輸入以下內容：

```
/home/pi/example_bookReader/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 pi pi
}
```

### 3. 設定定期清理

```bash
# 編輯 crontab
crontab -e

# 加入以下行：

# 每天凌晨 2 點清理 7 天前的照片
0 2 * * * find /home/pi/example_bookReader/captured_images/ -name "*.jpg" -mtime +7 -delete

# 每週日凌晨 3 點重啟服務
0 3 * * 0 sudo systemctl restart book-reader.service
```

### 4. 設定遠端存取

#### SSH 金鑰認證

```bash
# 在本機產生金鑰（如果還沒有）
ssh-keygen -t rsa -b 4096

# 複製公鑰到 Raspberry Pi
ssh-copy-id pi@192.168.1.100

# 之後就可以免密碼登入
ssh pi@192.168.1.100
```

#### VNC 遠端桌面（可選）

```bash
# 啟用 VNC
sudo raspi-config
# 選擇：Interface Options -> VNC -> Enable

# 設定 VNC 解析度
sudo raspi-config
# 選擇：Display Options -> Resolution

# 重新開機
sudo reboot
```

### 5. 效能監控

#### 安裝監控工具

```bash
sudo apt install -y htop iotop nethogs
```

#### 建立監控腳本

```bash
cat > monitor.sh << 'EOF'
#!/bin/bash
echo "=== 系統監控 ==="
echo ""

echo "CPU 溫度:"
vcgencmd measure_temp

echo ""
echo "記憶體使用:"
free -h | grep Mem

echo ""
echo "磁碟使用:"
df -h | grep -E '(/$|/home)'

echo ""
echo "閱讀機器人程序:"
ps aux | grep book_reader | grep -v grep || echo "未執行"

echo ""
echo "最近 5 筆日誌:"
tail -5 /home/pi/example_bookReader/logs/book_reader.log
EOF

chmod +x monitor.sh
```

---

## ✅ 安裝檢查清單

完成以下項目確保安裝成功：

- [ ] Raspberry Pi OS 已安裝並更新
- [ ] Python 3.7+ 已安裝
- [ ] 所有系統依賴套件已安裝
- [ ] 所有 Python 套件已安裝並驗證
- [ ] GPIO 腳位已正確接線並測試
- [ ] USB 攝影機已連接並測試
- [ ] 音訊輸出已設定並測試
- [ ] API 伺服器可正常連線
- [ ] 設定檔已正確設定
- [ ] 所有元件測試通過
- [ ] 程式可正常執行
- [ ] 音檔檔案已放置
- [ ] 權限設定正確
- [ ] （可選）systemd 服務已設定
- [ ] （可選）日誌輪替已設定

---

## 📞 安裝支援

如果在安裝過程中遇到問題：

1. 查看 [疑難排解指南](TROUBLESHOOTING.md)
2. 查看 [錯誤訊息說明](ERROR_MESSAGES.md)
3. 檢查系統日誌：`journalctl -xe`
4. 檢查程式日誌：`tail -50 logs/book_reader.log`

---

**文檔版本**: 1.0.0  
**更新日期**: 2025-11-11

