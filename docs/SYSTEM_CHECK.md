# 閱讀機器人系統檢查指南

## 📋 系統檢查清單

在部署閱讀機器人之前，請按照此清單逐項檢查系統狀態。

---

## 1️⃣ 硬體檢查

### Raspberry Pi

```bash
# 檢查 Raspberry Pi 型號
cat /proc/cpuinfo | grep Model

# 檢查記憶體
free -h

# 檢查磁碟空間
df -h

# 檢查 CPU 溫度
vcgencmd measure_temp

# 檢查電壓（供電是否充足）
vcgencmd get_throttled
# 0x0 表示正常
```

**預期結果**:
- Raspberry Pi 3/4/5
- 至少 500MB 可用記憶體
- 至少 2GB 可用磁碟空間
- CPU 溫度 < 80°C
- 電壓正常（0x0）

### GPIO 腳位

```bash
# 檢查 GPIO 是否可用
gpio readall  # 如果沒有此命令，執行: sudo apt install wiringpi

# 檢查 GPIO17 狀態
python3 << EOF
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
print(f"GPIO17 狀態: {GPIO.input(17)}")
GPIO.cleanup()
EOF
```

**預期結果**:
- 能正常讀取 GPIO 狀態
- GPIO17 在未按下按鈕時為 LOW (0)
- 按下按鈕時為 HIGH (1)

### USB 攝影機

```bash
# 列出 USB 裝置
lsusb

# 列出 Video 裝置
ls -l /dev/video*

# 檢查攝影機資訊
v4l2-ctl --list-devices

# 檢查支援的解析度
v4l2-ctl --list-formats-ext -d /dev/video0
```

**預期結果**:
- 顯示 USB 攝影機裝置
- 至少有一個 `/dev/video0` 裝置
- 支援 640x480 或更高解析度

### 音訊輸出

```bash
# 列出音訊裝置
aplay -l

# 測試音訊播放
aplay /usr/share/sounds/alsa/Front_Center.wav

# 檢查音量
amixer get Master
```

**預期結果**:
- 顯示至少一個音訊輸出裝置
- 能聽到測試音效
- 音量不為 0

---

## 2️⃣ 軟體環境檢查

### Python 環境

```bash
# Python 版本
python3 --version
# 應該 >= 3.7

# pip 版本
pip3 --version

# 已安裝的 Python 套件
pip3 list | grep -E "(RPi.GPIO|opencv|requests|pygame)"
```

**預期結果**:
```
Python 3.7.0 或更高
pip 已安裝
顯示所需套件及版本
```

### 系統套件

```bash
# 檢查必要的系統套件
dpkg -l | grep -E "(python3-rpi.gpio|python3-opencv|libsdl2)"
```

**預期結果**:
所有套件都顯示為已安裝 (ii 狀態)

---

## 3️⃣ 網路連線檢查

### 基本連線

```bash
# 檢查 IP 位址
ip addr show

# 檢查網路連線
ping -c 3 8.8.8.8

# 檢查 DNS 解析
ping -c 3 google.com
```

**預期結果**:
- 顯示有效的 IP 位址
- 能 ping 通外部 IP
- DNS 解析正常

### API 伺服器連線

```bash
# 從 config.ini 讀取 API 位址（手動替換）
API_URL="http://172.30.19.20:5000"

# 檢查伺服器連線
ping -c 3 172.30.19.20

# 檢查 API 健康狀態
curl -s $API_URL/health

# 測試 OCR 功能（需要測試圖片）
# curl -X POST -F "file=@test.jpg" $API_URL/ocr
```

**預期結果**:
```json
{
  "status": "healthy",
  "service": "DeepSeek-OCR API",
  "timestamp": "..."
}
```

---

## 4️⃣ 檔案系統檢查

### 目錄結構

```bash
cd example_bookReader

# 檢查必要檔案和目錄
ls -l

# 應該包含：
# - book_reader.py
# - config.ini
# - requirements.txt
# - README.md
# - voices/
# - README/
```

**預期結果**:
所有必要檔案都存在

### 檔案權限

```bash
# 檢查執行權限
ls -l book_reader.py test_components.py start_reader.sh

# 檢查目錄權限
ls -ld logs captured_images voices
```

**預期結果**:
- Python 檔案有讀取權限
- Shell 腳本有執行權限 (x)
- 目錄有寫入權限

### 音檔檢查

```bash
# 檢查音檔
ls -lh voices/

# 測試音檔格式
file voices/*.mp3
```

**預期結果**:
- 至少有兩個音檔（成功和失敗）
- 音檔格式正確（Audio file with ID3）

---

## 5️⃣ 設定檔檢查

### 設定檔存在性

```bash
# 檢查設定檔
test -f config.ini && echo "✓ 設定檔存在" || echo "✗ 設定檔不存在"

# 檢查設定檔格式
python3 -c "import configparser; c=configparser.ConfigParser(); c.read('config.ini'); print('✓ 設定檔格式正確')"
```

### 關鍵設定檢查

```bash
# 檢查 API 設定
grep -E "^api_url" config.ini

# 檢查 GPIO 設定
grep -E "^trigger_pin" config.ini

# 檢查攝影機設定
grep -E "^camera_device" config.ini

# 檢查音檔設定
grep -E "^(success_sound|error_sound)" config.ini
```

**預期結果**:
所有關鍵設定都有值

---

## 6️⃣ 使用者權限檢查

### 群組檢查

```bash
# 檢查使用者所屬群組
groups

# 應該包含：
# - gpio
# - video
# - audio
```

**預期結果**:
使用者在 gpio、video、audio 群組中

### 如果不在群組中

```bash
# 加入群組
sudo usermod -a -G gpio,video,audio $USER

# 登出後重新登入
# 或使用 newgrp 立即生效（暫時）
newgrp gpio
newgrp video
```

---

## 7️⃣ 元件整合測試

### 執行測試腳本

```bash
cd example_bookReader
python3 test_components.py
```

**預期結果**:
```
=== 元件測試 ===

測試 GPIO... ✓ (當前狀態: LOW)
測試攝影機... ✓ (解析度: 1280x720)
測試 API... ✓ (http://172.30.19.20:5000)
測試音訊系統... ✓

=== 測試結果: 4/4 通過 ===

✓ 所有測試通過，系統正常
```

---

## 8️⃣ 系統日誌檢查

### 檢查系統日誌

```bash
# 檢查核心日誌（GPIO、USB）
dmesg | tail -50

# 檢查系統日誌
journalctl -xe | tail -50

# 檢查 USB 裝置日誌
journalctl | grep -i usb | tail -20
```

**注意事項**:
- 檢查是否有錯誤訊息
- 檢查是否有權限拒絕訊息
- 檢查 USB 裝置是否正確識別

---

## 🔧 完整診斷腳本

建立 `system_check.sh` 腳本：

```bash
#!/bin/bash
echo "=== 閱讀機器人系統檢查 ==="
echo ""

# 1. 硬體檢查
echo "【硬體檢查】"
echo "Raspberry Pi: $(cat /proc/cpuinfo | grep Model | cut -d: -f2)"
echo "記憶體: $(free -h | awk '/^Mem:/ {print $7}') 可用"
echo "磁碟空間: $(df -h / | awk 'NR==2 {print $4}') 可用"
echo "CPU 溫度: $(vcgencmd measure_temp)"
echo ""

# 2. GPIO
echo "【GPIO】"
python3 -c "import RPi.GPIO; print('✓ RPi.GPIO 可用')" 2>/dev/null || echo "✗ RPi.GPIO 不可用"
echo ""

# 3. 攝影機
echo "【攝影機】"
ls /dev/video0 >/dev/null 2>&1 && echo "✓ 攝影機裝置存在" || echo "✗ 找不到攝影機"
echo ""

# 4. 音訊
echo "【音訊】"
aplay -l >/dev/null 2>&1 && echo "✓ 音訊裝置可用" || echo "✗ 音訊裝置不可用"
echo ""

# 5. Python 套件
echo "【Python 套件】"
for pkg in RPi.GPIO cv2 requests pygame; do
    python3 -c "import $pkg" 2>/dev/null && echo "✓ $pkg" || echo "✗ $pkg"
done
echo ""

# 6. 網路
echo "【網路連線】"
ping -c 1 8.8.8.8 >/dev/null 2>&1 && echo "✓ 網路連線正常" || echo "✗ 網路連線失敗"
echo ""

# 7. API 伺服器
echo "【API 伺服器】"
API_URL=$(grep api_url config.ini 2>/dev/null | cut -d= -f2 | tr -d ' ')
if [ -n "$API_URL" ]; then
    curl -s "${API_URL%/*}/health" >/dev/null 2>&1 && echo "✓ API 可連線: $API_URL" || echo "✗ API 無法連線: $API_URL"
else
    echo "✗ 找不到 API 設定"
fi
echo ""

# 8. 檔案
echo "【檔案結構】"
test -f book_reader.py && echo "✓ book_reader.py" || echo "✗ book_reader.py"
test -f config.ini && echo "✓ config.ini" || echo "✗ config.ini"
test -d voices && echo "✓ voices/" || echo "✗ voices/"
echo ""

# 9. 權限
echo "【使用者權限】"
groups | grep -q gpio && echo "✓ gpio 群組" || echo "✗ gpio 群組"
groups | grep -q video && echo "✓ video 群組" || echo "✗ video 群組"
echo ""

echo "=== 檢查完成 ==="
```

執行診斷：

```bash
chmod +x system_check.sh
./system_check.sh
```

---

## ✅ 檢查結果判斷

### 全部通過

如果所有檢查都通過（✓），您的系統已準備就緒，可以執行：

```bash
./start_reader.sh
```

### 部分失敗

根據失敗的項目，參考對應的文檔：

| 失敗項目 | 參考文檔 |
|---------|---------|
| Python 套件 | [INSTALLATION.md](INSTALLATION.md) |
| GPIO/攝影機/音訊 | [INSTALLATION.md](INSTALLATION.md) |
| API 連線 | [CONFIGURATION.md](CONFIGURATION.md) |
| 權限問題 | [ERROR_MESSAGES.md](ERROR_MESSAGES.md) |
| 其他問題 | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |

---

## 📞 取得協助

如果檢查結果顯示多個失敗項目，建議：

1. 儲存檢查結果：
   ```bash
   ./system_check.sh > check_result.txt
   ```

2. 查看詳細文檔
3. 逐項修復問題
4. 重新執行檢查

---

**文檔版本**: 1.0.0  
**更新日期**: 2025-11-11

