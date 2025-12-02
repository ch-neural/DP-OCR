# 閱讀機器人錯誤訊息說明

## 📋 概述

本文檔詳細說明閱讀機器人可能遇到的各種錯誤訊息、發生原因及解決方法。

---

## 🔴 設定檔相關錯誤

### 錯誤 1: 找不到設定檔

**錯誤訊息**:
```
錯誤: 找不到設定檔 config.ini
```

**發生原因**:
- 設定檔 `config.ini` 不存在或路徑錯誤
- 執行程式的目錄不正確

**解決方法**:
1. 確認當前目錄是否為 `example_bookReader/`
2. 檢查設定檔是否存在：
   ```bash
   ls -l config.ini
   ```
3. 如果設定檔不存在，請從範本建立：
   ```bash
   cp config.ini.example config.ini
   ```

---

## 🔴 GPIO 相關錯誤

### 錯誤 2: Raspberry Pi 5 GPIO 庫錯誤

**錯誤訊息**:
```
RuntimeError: Cannot determine SOC peripheral base address
```
或
```
❌ 錯誤: Raspberry Pi 5 必須使用 gpiod 庫
```

**發生原因**:
- Raspberry Pi 5 不支援 `RPi.GPIO` 庫
- `gpiod` 庫未安裝
- 程式錯誤地回退到 `RPi.GPIO` 庫

**解決方法**:

**步驟 1**: 選擇並安裝 GPIO 庫

**方案 1（推薦）**: 安裝 gpiod 庫
```bash
sudo apt-get update
sudo apt-get install -y python3-libgpiod python3-gpiod
```

**方案 2（備選）**: 安裝 rpi-lgpio（RPi.GPIO 的 drop-in replacement）
```bash
sudo apt-get update
sudo apt-get install -y python3-rpi-lgpio
sudo adduser $LOGNAME gpio
sudo reboot
```

**步驟 2**: 驗證安裝
```bash
python3 -c "import gpiod; print('✓ gpiod 安裝成功')"
```

**步驟 3**: 檢查 GPIO 晶片
```bash
ls -l /dev/gpiochip*
# Raspberry Pi 5 應該看到 /dev/gpiochip4
```

**步驟 4**: 設定權限（如果需要）
```bash
# 將使用者加入 gpio 群組
sudo usermod -a -G gpio $USER
# 登出後重新登入使設定生效
```

**步驟 5**: 重新執行程式
```bash
python3 test_gpio_button.py
# 或
python3 book_reader.py
```

**注意事項**:
- Raspberry Pi 5 不支援傳統的 `RPi.GPIO` 庫
- 推薦使用 `gpiod` 或 `rpi-lgpio`（RPi.GPIO 的 drop-in replacement）
- 程式會自動嘗試三種庫：`gpiod` → `rpi-lgpio` → `RPi.GPIO`
- 如果偵測到 Pi 5 但推薦的庫未安裝，程式會顯示明確的錯誤訊息和安裝指引

### 錯誤 2-1: gpiod API 不相容錯誤

**錯誤訊息**:
```
AttributeError: 'Chip' object has no attribute 'get_line'
```
或
```
❌ GPIO17 設定失敗: 'Chip' object has no attribute 'get_line'
```

**發生原因**:
- `gpiod` 庫的 API 版本不同
- 使用了錯誤的 API 方法（`get_line` 不存在）
- `python3-libgpiod` 版本與程式碼不相容

**解決方法**:

**步驟 1**: 確認安裝正確的 gpiod 套件
```bash
# 確認已安裝 python3-libgpiod
dpkg -l | grep libgpiod

# 如果未安裝，重新安裝
sudo apt-get update
sudo apt-get install --reinstall python3-libgpiod python3-gpiod
```

**步驟 2**: 檢查 gpiod 版本
```bash
python3 -c "import gpiod; print(dir(gpiod.Chip('/dev/gpiochip4')))"
```

**步驟 3**: 更新系統（如果需要）
```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

**步驟 4**: 驗證修復
```bash
python3 test_gpio_button.py
```

**技術說明**:
- 程式已更新為自動嘗試多種 `gpiod` API 方式：
  1. `chip.get_lines([pin])` - 返回 Line 物件列表
  2. `chip.line(pin)` - 直接取得單個 Line
  3. 舊版 API（如果存在）
- 如果所有方式都失敗，程式會顯示明確的錯誤訊息

### 錯誤 2-2: lgpio 通知文件創建失敗（systemd 服務運行時）

**錯誤訊息**:
```
FileNotFoundError: [Errno 2] No such file or directory: '.lgd-nfy-3'
```
或
```
⚠️  rpi-lgpio 初始化警告: [Errno 2] No such file or directory: '.lgd-nfy-3'
```

**發生原因**:
- 當作為 systemd 服務運行時，`lgpio` 庫嘗試在當前工作目錄創建通知文件 `.lgd-nfy-*`
- systemd 服務的默認工作目錄可能沒有寫入權限
- 這通常發生在 Raspberry Pi 5 上使用 `rpi-lgpio` 庫時

**解決方法**:

**方法 1（推薦）**: 在 systemd service 文件中設置 `WorkingDirectory`

1. **編輯 systemd service 文件**:
```bash
sudo nano /etc/systemd/system/gpio-button-test.service
```

2. **確保設置正確的 WorkingDirectory**:
```ini
[Unit]
Description=GPIO Button Test Service
After=multi-user.target

[Service]
Type=simple
User=pi
Group=pi
# 關鍵：設置工作目錄為腳本所在目錄，確保有寫入權限
WorkingDirectory=/GPUData/working/Deepseek-OCR/example_bookReader
ExecStart=/usr/bin/python3 /GPUData/working/Deepseek-OCR/example_bookReader/test_gpio_button.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

3. **重新載入並重啟服務**:
```bash
sudo systemctl daemon-reload
sudo systemctl restart gpio-button-test.service
sudo systemctl status gpio-button-test.service
```

**方法 2**: 使用虛擬環境（venv）

如果使用 Python 虛擬環境，確保在 service 文件中使用完整路徑：

```ini
[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/my_project
ExecStart=/home/pi/my_project/venv/bin/python /home/pi/my_project/test_gpio_button.py
```

**方法 3**: 程式自動修復（已實現）

程式已自動處理此問題：
- 在導入 `lgpio` 之前，程式會自動檢測並設置可寫入的工作目錄
- 優先使用腳本所在目錄，如果不可寫則嘗試 `/tmp` 或用戶主目錄
- 如果所有嘗試都失敗，程式會自動回退到 `gpiod` 庫

**驗證修復**:
```bash
# 查看服務日誌
sudo journalctl -u gpio-button-test.service -f

# 應該看到類似訊息：
# ✅ 使用 rpi-lgpio 庫（Raspberry Pi 5 相容的 RPi.GPIO 替代方案）
# ✅ GPIO17 設定完成（rpi-lgpio）
```

**技術說明**:
- `lgpio` 庫在初始化時會創建通知文件 `.lgd-nfy-*` 用於回調通知
- 這些文件必須創建在當前工作目錄中
- systemd 服務的默認工作目錄通常是 `/`，普通用戶沒有寫入權限
- 解決方案是設置 `WorkingDirectory` 到一個用戶有寫入權限的目錄

**參考資料**:
- Raspberry Pi 論壇討論: [raspberry pi 5 python script as service failed](https://forums.raspberrypi.com/viewtopic.php?t=370000)

### 錯誤 3: GPIO 權限不足

**錯誤訊息**:
```
RuntimeError: No access to /dev/mem. Try running as root!
```
或
```
PermissionError: [Errno 13] Permission denied: '/dev/gpiochip4'
```

**發生原因**:
- 當前使用者沒有 GPIO 存取權限
- 需要 root 權限或加入 gpio 群組

**解決方法**:

**方法 1**: 將使用者加入 gpio 群組（推薦）
```bash
sudo usermod -a -G gpio $USER
# 登出後重新登入
```

**方法 2**: 使用 sudo 執行（不推薦，僅測試用）
```bash
sudo python3 book_reader.py
```

**方法 3**: 設定 GPIO 權限規則
```bash
sudo nano /etc/udev/rules.d/99-gpio.rules
# 加入以下內容：
# SUBSYSTEM=="gpio", GROUP="gpio", MODE="0660"
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### 錯誤 4: GPIO 腳位衝突

**錯誤訊息**:
```
RuntimeError: The GPIO channel is already in use
```

**發生原因**:
- GPIO 腳位已被其他程式或服務佔用
- 程式異常結束未正確清理 GPIO

**解決方法**:
1. 手動清理 GPIO：
   ```bash
   python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.cleanup()"
   ```
2. 檢查是否有其他程式使用 GPIO：
   ```bash
   ps aux | grep book_reader
   # 如果有，停止該程序
   kill <PID>
   ```
3. 重新啟動程式

---

## 🔴 攝影機相關錯誤

### 錯誤 4: 無法開啟攝影機

**錯誤訊息**:
```
錯誤: 無法開啟攝影機裝置 0
```

**發生原因**:
- USB 攝影機未正確連接
- 攝影機被其他程式佔用
- 攝影機裝置編號錯誤
- 缺少攝影機驅動程式

**解決方法**:

1. **檢查攝影機連接**:
   ```bash
   ls /dev/video*
   # 應該看到 /dev/video0 或類似裝置
   ```

2. **測試攝影機**:
   ```bash
   # 使用 v4l2 工具測試
   sudo apt install v4l-utils
   v4l2-ctl --list-devices
   
   # 使用 OpenCV 測試
   python3 -c "import cv2; cap = cv2.VideoCapture(0); print('成功' if cap.isOpened() else '失敗'); cap.release()"
   ```

3. **檢查權限**:
   ```bash
   # 將使用者加入 video 群組
   sudo usermod -a -G video $USER
   # 登出後重新登入
   ```

4. **修改設定檔**:
   如果攝影機不是 `/dev/video0`，修改 `config.ini`：
   ```ini
   [CAMERA]
   camera_device = 1  # 改為正確的裝置編號
   ```

5. **檢查其他程式**:
   ```bash
   # 查看是否有其他程式使用攝影機
   lsof /dev/video0
   ```

### 錯誤 5: 無法讀取影像

**錯誤訊息**:
```
錯誤: 無法從攝影機讀取影像
```

**發生原因**:
- 攝影機硬體故障
- 攝影機尚未初始化完成
- USB 供電不足

**解決方法**:
1. **增加初始化延遲時間**:
   修改 `config.ini`：
   ```ini
   [CAMERA]
   capture_delay = 1.0  # 增加延遲時間
   ```

2. **檢查 USB 供電**:
   - 使用有供電的 USB Hub
   - 確認 Raspberry Pi 電源供應充足

3. **測試不同解析度**:
   修改 `config.ini`：
   ```ini
   [CAMERA]
   frame_width = 640
   frame_height = 480
   ```

---

## 🔴 API 連線相關錯誤

### 錯誤 6: 無法連線到 API 伺服器

**錯誤訊息**:
```
requests.exceptions.ConnectionError: Failed to establish a new connection
```

**發生原因**:
- API 伺服器未啟動
- 網路連線問題
- 防火牆阻擋連線
- API 位址設定錯誤

**解決方法**:

1. **檢查 API 伺服器狀態**:
   ```bash
   curl http://172.30.19.20:5000/health
   # 應該返回: {"status": "healthy", ...}
   ```

2. **檢查網路連線**:
   ```bash
   ping 172.30.19.20
   ```

3. **確認 API 位址設定**:
   檢查 `config.ini`：
   ```ini
   [API]
   api_url = http://172.30.19.20:5000  # 確認位址正確
   ```

4. **檢查防火牆設定**:
   ```bash
   # 在 API 伺服器上
   sudo ufw status
   sudo ufw allow 5000/tcp
   ```

### 錯誤 7: API 請求超時

**錯誤訊息**:
```
requests.exceptions.Timeout: Request timed out
```

**發生原因**:
- API 伺服器處理時間過長
- 網路延遲過高
- 超時時間設定過短

**解決方法**:

1. **增加超時時間**:
   修改 `config.ini`：
   ```ini
   [API]
   request_timeout = 60  # 增加到 60 秒
   ```

2. **檢查 API 伺服器負載**:
   ```bash
   # 在 API 伺服器上
   top
   nvidia-smi  # 檢查 GPU 使用率
   ```

3. **優化圖片大小**:
   降低拍攝解析度以減少傳輸和處理時間：
   ```ini
   [CAMERA]
   frame_width = 1024
   frame_height = 768
   ```

### 錯誤 8: API 回傳錯誤

**錯誤訊息**:
```
OCR API 錯誤 (HTTP 400): 不支援的檔案類型
```

**發生原因**:
- 圖片格式不正確
- 圖片檔案損壞
- API 伺服器設定問題

**解決方法**:

1. **檢查儲存的圖片**:
   ```bash
   ls -lh captured_images/
   file captured_images/capture_*.jpg
   ```

2. **測試 API**:
   ```bash
   # 手動測試 API
   curl -X POST -F "file=@captured_images/capture_20251111_120000.jpg" \
     http://172.30.19.20:5000/ocr
   ```

3. **查看 API 伺服器日誌**:
   檢查伺服器端的錯誤訊息

### 錯誤 9: 模型未返回結果

**錯誤訊息**:
```
OCR API 錯誤 (HTTP 500): 模型未返回任何結果
```

**發生原因**:
- 圖片內容無法辨識
- 圖片品質過低
- 模型處理異常

**解決方法**:

1. **檢查圖片品質**:
   - 確保光線充足
   - 調整攝影機對焦
   - 增加拍攝延遲時間

2. **使用自訂提示詞**:
   修改 `config.ini`：
   ```ini
   [OCR]
   prompt = <image>\n請仔細辨識圖片中的所有文字。
   ```

3. **查看儲存的圖片**:
   檢查 `captured_images/` 目錄中的圖片是否清晰

---

## 🔴 音訊相關錯誤

### 錯誤 10: 找不到音檔

**錯誤訊息**:
```
錯誤: 找不到音檔: voices/看完了1.mp3
```

**發生原因**:
- 音檔不存在
- 音檔路徑設定錯誤
- 檔案權限問題

**解決方法**:

1. **檢查音檔是否存在**:
   ```bash
   ls -l voices/
   ```

2. **確認檔案權限**:
   ```bash
   chmod 644 voices/*.mp3
   ```

3. **修改設定檔路徑**:
   如果音檔在其他位置，修改 `config.ini`：
   ```ini
   [AUDIO]
   success_sound = /path/to/your/success.mp3
   error_sound = /path/to/your/error.mp3
   ```

### 錯誤 11: 音訊播放失敗

**錯誤訊息**:
```
pygame.error: Unable to open audio device
```

**發生原因**:
- 音訊裝置未正確設定
- 缺少音訊驅動程式
- 音訊裝置被佔用

**解決方法**:

1. **檢查音訊裝置**:
   ```bash
   aplay -l  # 列出音訊裝置
   ```

2. **測試音訊播放**:
   ```bash
   aplay /usr/share/sounds/alsa/Front_Center.wav
   ```

3. **安裝音訊套件**:
   ```bash
   sudo apt install -y alsa-utils pulseaudio
   ```

4. **設定音訊輸出**:
   ```bash
   # 使用 raspi-config 設定音訊輸出
   sudo raspi-config
   # 選擇: System Options -> Audio -> 選擇輸出裝置
   ```

5. **重新初始化音訊系統**:
   ```bash
   pulseaudio --kill
   pulseaudio --start
   ```

---

## 🔴 檔案系統相關錯誤

### 錯誤 12: 權限不足

**錯誤訊息**:
```
PermissionError: [Errno 13] Permission denied: 'logs/book_reader.log'
```

**發生原因**:
- 目錄權限不足
- 檔案被其他程式鎖定

**解決方法**:

1. **修改目錄權限**:
   ```bash
   chmod 755 logs/
   chmod 755 captured_images/
   ```

2. **修改檔案擁有者**:
   ```bash
   sudo chown -R $USER:$USER example_bookReader/
   ```

### 錯誤 13: 磁碟空間不足

**錯誤訊息**:
```
OSError: [Errno 28] No space left on device
```

**發生原因**:
- SD 卡或硬碟空間不足
- 拍攝的照片或日誌佔用過多空間

**解決方法**:

1. **檢查磁碟使用量**:
   ```bash
   df -h
   du -sh captured_images/ logs/
   ```

2. **清理舊檔案**:
   ```bash
   # 刪除 7 天前的照片
   find captured_images/ -name "*.jpg" -mtime +7 -delete
   
   # 清理日誌檔案
   > logs/book_reader.log
   ```

3. **關閉圖片儲存**:
   修改 `config.ini`：
   ```ini
   [CAMERA]
   save_captured_image = false
   ```

4. **設定自動清理**:
   建立 cron 任務定期清理：
   ```bash
   crontab -e
   # 加入以下行（每天凌晨 2 點清理）
   # 0 2 * * * find /path/to/example_bookReader/captured_images/ -name "*.jpg" -mtime +7 -delete
   ```

---

## 🔴 執行時期錯誤

### 錯誤 14: 模組匯入失敗

**錯誤訊息**:
```
ModuleNotFoundError: No module named 'RPi'
```
或
```
ModuleNotFoundError: No module named 'gpiod'
```

**發生原因**:
- 缺少必要的 Python 套件
- Python 環境設定錯誤
- Raspberry Pi 5 缺少 gpiod 庫

**解決方法**:

1. **檢查 Raspberry Pi 版本**:
   ```bash
   cat /proc/cpuinfo | grep Model
   ```

2. **根據版本安裝對應的 GPIO 庫**:
   
   **Raspberry Pi 5**:
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-libgpiod python3-gpiod
   ```
   
   **Raspberry Pi 4 及更早版本**:
   ```bash
   pip3 install RPi.GPIO
   # 或
   sudo apt-get install python3-rpi.gpio
   ```

3. **安裝其他必要套件**:
   ```bash
   pip3 install -r requirements.txt
   ```
   
   或個別安裝：
   ```bash
   pip3 install opencv-python requests pygame
   ```

4. **檢查 Python 版本**:
   ```bash
   python3 --version  # 應該是 3.7 或以上
   ```

5. **驗證安裝**:
   ```bash
   # Raspberry Pi 5
   python3 -c "import gpiod; print('✓ gpiod 已安裝')"
   
   # Raspberry Pi 4 及更早
   python3 -c "import RPi.GPIO; print('✓ RPi.GPIO 已安裝')"
   ```

### 錯誤 15: 記憶體不足

**錯誤訊息**:
```
MemoryError: Unable to allocate array
```

**發生原因**:
- Raspberry Pi 記憶體不足
- 圖片解析度過高

**解決方法**:

1. **降低圖片解析度**:
   修改 `config.ini`：
   ```ini
   [CAMERA]
   frame_width = 640
   frame_height = 480
   ```

2. **增加 swap 空間**:
   ```bash
   # 編輯 swap 設定
   sudo nano /etc/dphys-swapfile
   # 修改 CONF_SWAPSIZE=1024
   sudo /etc/init.d/dphys-swapfile restart
   ```

3. **關閉其他程式**:
   釋放記憶體空間

---

## 🔴 網路相關錯誤

### 錯誤 16: DNS 解析失敗

**錯誤訊息**:
```
requests.exceptions.ConnectionError: Failed to resolve hostname
```

**發生原因**:
- 使用域名但 DNS 無法解析
- 網路設定錯誤

**解決方法**:

1. **改用 IP 位址**:
   修改 `config.ini`：
   ```ini
   [API]
   api_url = http://172.30.19.20:5000  # 使用 IP 而非域名
   ```

2. **檢查 DNS 設定**:
   ```bash
   cat /etc/resolv.conf
   ping 8.8.8.8  # 測試網路連線
   ```

### 錯誤 17: SSL 憑證錯誤

**錯誤訊息**:
```
requests.exceptions.SSLError: [SSL: CERTIFICATE_VERIFY_FAILED]
```

**發生原因**:
- HTTPS 連線但憑證無效
- 系統時間不正確

**解決方法**:

1. **改用 HTTP**:
   修改 `config.ini`：
   ```ini
   [API]
   api_url = http://172.30.19.20:5000  # 使用 HTTP
   ```

2. **更新系統時間**:
   ```bash
   sudo date -s "2025-11-11 12:00:00"
   # 或啟用 NTP
   sudo timedatectl set-ntp true
   ```

---

## 📊 錯誤優先級

| 優先級 | 錯誤類型 | 影響程度 | 處理建議 |
|--------|----------|----------|----------|
| 🔴 高 | GPIO 權限不足 | 程式無法執行 | 立即處理 |
| 🔴 高 | 攝影機無法開啟 | 核心功能失效 | 立即處理 |
| 🔴 高 | API 連線失敗 | 核心功能失效 | 立即處理 |
| 🟡 中 | 音檔找不到 | 功能部分失效 | 儘快處理 |
| 🟡 中 | API 請求超時 | 處理變慢 | 儘快處理 |
| 🟢 低 | 日誌寫入失敗 | 不影響功能 | 可稍後處理 |
| 🟢 低 | 圖片儲存失敗 | 不影響功能 | 可稍後處理 |

---

## 🔍 除錯技巧

### 1. 啟用詳細日誌

修改 `config.ini`：
```ini
[LOGGING]
log_level = DEBUG
console_output = true
```

### 2. 查看即時日誌

```bash
tail -f logs/book_reader.log
```

### 3. 測試各個元件

```bash
# 測試 GPIO
python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.setup(17, GPIO.IN); print(GPIO.input(17))"

# 測試攝影機
python3 -c "import cv2; cap = cv2.VideoCapture(0); ret, frame = cap.read(); print(ret); cap.release()"

# 測試 API
curl http://172.30.19.20:5000/health

# 測試音訊
python3 -c "import pygame; pygame.mixer.init(); print('OK')"
```

### 4. 使用除錯模式執行

```bash
python3 -u book_reader.py 2>&1 | tee debug.log
```

---

## 📞 取得協助

如果以上解決方法都無法解決您的問題，請：

1. 查看完整日誌檔案: `logs/book_reader.log`
2. 記錄詳細的錯誤訊息
3. 記錄系統環境資訊:
   ```bash
   python3 --version
   uname -a
   cat /etc/os-release
   ```
4. 參考其他文檔:
   - [安裝指南](INSTALLATION.md)
   - [設定說明](CONFIGURATION.md)
   - [疑難排解](TROUBLESHOOTING.md)

---

**文檔版本**: 1.0.0  
**更新日期**: 2025-11-11

