# 閱讀機器人疑難排解指南

## 📋 目錄

- [系統診斷](#系統診斷)
- [常見問題](#常見問題)
- [效能最佳化](#效能最佳化)
- [進階除錯](#進階除錯)
- [硬體問題](#硬體問題)

---

## 🔍 系統診斷

在開始排除問題之前，請先執行系統診斷以確認各元件狀態。

### 診斷檢查清單

建立診斷腳本 `diagnostic.sh`：

```bash
#!/bin/bash
echo "=== 閱讀機器人系統診斷 ==="
echo ""

echo "1. Python 版本:"
python3 --version
echo ""

echo "2. 系統資訊:"
uname -a
cat /etc/os-release | grep PRETTY_NAME
echo ""

echo "3. 記憶體使用:"
free -h
echo ""

echo "4. 磁碟空間:"
df -h | grep -E '(Filesystem|/$)'
echo ""

echo "5. GPIO 權限:"
if groups | grep -q gpio; then
    echo "✓ 使用者在 gpio 群組中"
else
    echo "✗ 使用者不在 gpio 群組中"
fi
echo ""

echo "6. Video 權限:"
if groups | grep -q video; then
    echo "✓ 使用者在 video 群組中"
else
    echo "✗ 使用者不在 video 群組中"
fi
echo ""

echo "7. 攝影機裝置:"
ls -l /dev/video* 2>/dev/null || echo "找不到攝影機裝置"
echo ""

echo "8. Python 套件:"
echo "- RPi.GPIO:"
python3 -c "import RPi.GPIO; print('✓ 已安裝')" 2>/dev/null || echo "✗ 未安裝"
echo "- OpenCV:"
python3 -c "import cv2; print('✓ 已安裝 -', cv2.__version__)" 2>/dev/null || echo "✗ 未安裝"
echo "- Requests:"
python3 -c "import requests; print('✓ 已安裝 -', requests.__version__)" 2>/dev/null || echo "✗ 未安裝"
echo "- Pygame:"
python3 -c "import pygame; print('✓ 已安裝 -', pygame.__version__)" 2>/dev/null || echo "✗ 未安裝"
echo ""

echo "9. API 伺服器連線:"
API_URL=$(grep api_url config.ini | cut -d= -f2 | tr -d ' ')
if curl -s "${API_URL%/*}/health" > /dev/null 2>&1; then
    echo "✓ API 伺服器可連線"
else
    echo "✗ 無法連線到 API 伺服器: $API_URL"
fi
echo ""

echo "10. 檔案結構:"
echo "- config.ini: $(test -f config.ini && echo '✓' || echo '✗')"
echo "- book_reader.py: $(test -f book_reader.py && echo '✓' || echo '✗')"
echo "- voices/ 目錄: $(test -d voices && echo '✓' || echo '✗')"
echo "- 成功音檔: $(test -f voices/看完了1.mp3 && echo '✓' || echo '✗')"
echo "- 錯誤音檔: $(test -f voices/看不懂1.mp3 && echo '✓' || echo '✗')"
echo ""

echo "=== 診斷完成 ==="
```

執行診斷：

```bash
chmod +x diagnostic.sh
./diagnostic.sh
```

---

## ❓ 常見問題

### 問題 1: 程式啟動後沒有反應

**症狀**:
- 程式執行但沒有任何輸出
- 按下按鈕沒有回應

**可能原因**:
1. GPIO 腳位設定錯誤
2. 按鈕接線錯誤
3. 日誌輸出被關閉

**診斷步驟**:

1. **確認程式正在執行**:
   ```bash
   ps aux | grep book_reader
   ```

2. **檢查即時日誌**:
   ```bash
   tail -f logs/book_reader.log
   ```

3. **啟用終端機輸出**:
   修改 `config.ini`：
   ```ini
   [LOGGING]
   console_output = true
   log_level = DEBUG
   ```

4. **測試 GPIO 狀態**:
   ```bash
   # 建立測試腳本
   cat > test_gpio.py << 'EOF'
   import RPi.GPIO as GPIO
   import time
   
   GPIO.setmode(GPIO.BCM)
   GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
   
   print("監聽 GPIO17，請按下按鈕...")
   try:
       while True:
           state = GPIO.input(17)
           print(f"GPIO17 狀態: {'HIGH' if state else 'LOW'}", end='\r')
           time.sleep(0.1)
   except KeyboardInterrupt:
       GPIO.cleanup()
   EOF
   
   python3 test_gpio.py
   ```

**解決方法**:

- 如果 GPIO 測試沒有反應，檢查接線
- 確認使用正確的 GPIO 編號（BCM 模式）
- 嘗試更換按鈕或開關

### 問題 2: 拍攝的照片模糊或太暗

**症狀**:
- OCR 辨識失敗率高
- 儲存的照片品質不佳

**可能原因**:
1. 光線不足
2. 攝影機對焦不正確
3. 拍攝時機太早（攝影機未穩定）
4. 攝影機鏡頭髒污

**解決方法**:

1. **增加拍攝延遲**:
   修改 `config.ini`：
   ```ini
   [CAMERA]
   capture_delay = 1.0  # 增加到 1 秒
   ```

2. **調整攝影機設定**:
   ```python
   # 建立測試腳本
   cat > test_camera.py << 'EOF'
   import cv2
   import time
   
   cap = cv2.VideoCapture(0)
   cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
   cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
   
   # 自動對焦
   cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
   
   # 自動曝光
   cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
   
   time.sleep(2)  # 等待穩定
   
   ret, frame = cap.read()
   if ret:
       cv2.imwrite('test_capture.jpg', frame)
       print("測試照片已儲存: test_capture.jpg")
   
   cap.release()
   EOF
   
   python3 test_camera.py
   ```

3. **改善環境光線**:
   - 增加照明
   - 避免逆光
   - 使用白色背景

4. **清潔鏡頭**:
   - 使用軟布清潔攝影機鏡頭

### 問題 3: OCR 辨識結果不正確

**症狀**:
- 辨識的文字與實際內容不符
- 經常辨識失敗

**可能原因**:
1. 圖片品質問題
2. 文字太小或太模糊
3. 字體特殊或手寫
4. 提示詞不適當

**解決方法**:

1. **使用自訂提示詞**:
   修改 `config.ini`：
   ```ini
   [OCR]
   # 針對印刷體
   prompt = <image>\n請辨識圖片中的所有印刷文字，包含中文和英文。
   
   # 或針對手寫
   prompt = <image>\n請仔細辨識這張圖片中的手寫文字。
   
   # 或針對表格
   prompt = <image>\n請辨識這個表格的所有內容，保持表格結構。
   ```

2. **提高圖片解析度**:
   修改 `config.ini`：
   ```ini
   [CAMERA]
   frame_width = 1920
   frame_height = 1080
   ```

3. **調整拍攝角度**:
   - 確保文字方向正確
   - 避免傾斜或扭曲
   - 保持適當距離

4. **測試 API**:
   ```bash
   # 使用已知的測試圖片
   curl -X POST -F "file=@test_image.png" \
     http://172.30.19.20:5000/ocr
   ```

### 問題 4: 音檔播放異常

**症狀**:
- 音檔不播放
- 播放有雜音或斷續
- 音量太小

**可能原因**:
1. 音訊裝置設定錯誤
2. 音檔格式不相容
3. CPU 負載過高
4. 音量設定太低

**解決方法**:

1. **測試音訊系統**:
   ```bash
   # 測試系統音訊
   aplay /usr/share/sounds/alsa/Front_Center.wav
   
   # 測試音檔
   aplay voices/看完了1.mp3
   
   # 或使用 pygame
   python3 -c "import pygame; pygame.mixer.init(); pygame.mixer.music.load('voices/看完了1.mp3'); pygame.mixer.music.play(); import time; time.sleep(3)"
   ```

2. **調整音量**:
   ```bash
   # 使用 alsamixer 調整
   alsamixer
   
   # 或使用命令
   amixer set Master 100%
   ```

3. **修改設定**:
   修改 `config.ini`：
   ```ini
   [AUDIO]
   volume = 1.0  # 最大音量
   ```

4. **轉換音檔格式**:
   ```bash
   # 安裝 ffmpeg
   sudo apt install ffmpeg
   
   # 轉換音檔
   ffmpeg -i voices/看完了1.mp3 -ar 44100 -ac 2 voices/看完了1_converted.mp3
   ```

### 問題 5: 程式記憶體使用過高

**症狀**:
- 系統變慢
- 程式當機
- 出現記憶體錯誤

**可能原因**:
1. 圖片解析度過高
2. 記憶體洩漏
3. 攝影機資源未正確釋放

**解決方法**:

1. **降低圖片解析度**:
   修改 `config.ini`：
   ```ini
   [CAMERA]
   frame_width = 800
   frame_height = 600
   ```

2. **監控記憶體使用**:
   ```bash
   # 即時監控
   watch -n 1 "ps aux | grep book_reader | grep -v grep"
   
   # 或使用 htop
   htop
   ```

3. **增加 swap 空間**:
   ```bash
   sudo nano /etc/dphys-swapfile
   # 修改 CONF_SWAPSIZE=1024
   sudo /etc/init.d/dphys-swapfile restart
   ```

4. **定期重啟程式**:
   使用 cron 每天重啟：
   ```bash
   crontab -e
   # 加入：
   # 0 3 * * * pkill -f book_reader.py && sleep 10 && cd /path/to/example_bookReader && python3 book_reader.py &
   ```

---

## 🚀 效能最佳化

### 1. 減少處理時間

**優化拍攝速度**:

```ini
[CAMERA]
# 使用較低解析度但足夠辨識的尺寸
frame_width = 1024
frame_height = 768
# 減少延遲時間
capture_delay = 0.3
```

**優化 API 請求**:

```ini
[API]
# 適當的超時時間
request_timeout = 20
```

### 2. 降低 CPU 使用率

**調整檢查間隔**:

```ini
[GPIO]
# 增加檢查間隔（降低 CPU 佔用）
check_interval = 0.5
```

### 3. 減少磁碟使用

**關閉不必要的儲存**:

```ini
[CAMERA]
# 不儲存拍攝的照片
save_captured_image = false

[LOGGING]
# 只記錄重要訊息
log_level = WARNING
```

**設定日誌輪替**:

```bash
# 安裝 logrotate
sudo apt install logrotate

# 建立設定檔
sudo nano /etc/logrotate.d/book-reader

# 加入內容：
/path/to/example_bookReader/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

### 4. 網路最佳化

**使用有線網路**:
- 有線網路比 WiFi 更穩定快速

**設定靜態 IP**:
```bash
sudo nano /etc/dhcpcd.conf

# 加入：
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8
```

---

## 🔧 進階除錯

### 1. 使用偵錯模式

建立偵錯版本的執行腳本 `run_debug.sh`：

```bash
#!/bin/bash
echo "=== 閱讀機器人偵錯模式 ==="

# 啟用詳細日誌
export PYTHONUNBUFFERED=1

# 執行程式並記錄所有輸出
python3 -u book_reader.py 2>&1 | tee debug_$(date +%Y%m%d_%H%M%S).log
```

### 2. 逐步測試

建立測試腳本 `test_components.py`：

```python
#!/usr/bin/env python3
"""元件測試腳本"""

import sys
import time

def test_gpio():
    """測試 GPIO"""
    print("測試 GPIO...", end=" ")
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        state = GPIO.input(17)
        GPIO.cleanup()
        print(f"✓ (當前狀態: {'HIGH' if state else 'LOW'})")
        return True
    except Exception as e:
        print(f"✗ ({e})")
        return False

def test_camera():
    """測試攝影機"""
    print("測試攝影機...", end=" ")
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("✗ (無法開啟)")
            return False
        ret, frame = cap.read()
        cap.release()
        if ret:
            print(f"✓ (解析度: {frame.shape[1]}x{frame.shape[0]})")
            return True
        else:
            print("✗ (無法讀取)")
            return False
    except Exception as e:
        print(f"✗ ({e})")
        return False

def test_api():
    """測試 API 連線"""
    print("測試 API...", end=" ")
    try:
        import requests
        import configparser
        
        config = configparser.ConfigParser()
        config.read('config.ini')
        api_url = config.get('API', 'api_url').rstrip('/')
        
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"✓ ({api_url})")
            return True
        else:
            print(f"✗ (HTTP {response.status_code})")
            return False
    except Exception as e:
        print(f"✗ ({e})")
        return False

def test_audio():
    """測試音訊"""
    print("測試音訊...", end=" ")
    try:
        import pygame
        import os
        
        pygame.mixer.init()
        
        sound_file = 'voices/看完了1.mp3'
        if not os.path.exists(sound_file):
            print(f"✗ (找不到音檔: {sound_file})")
            return False
        
        pygame.mixer.music.load(sound_file)
        print("✓")
        pygame.mixer.quit()
        return True
    except Exception as e:
        print(f"✗ ({e})")
        return False

def main():
    print("\n=== 元件測試 ===\n")
    
    tests = [
        ("GPIO", test_gpio),
        ("攝影機", test_camera),
        ("API 連線", test_api),
        ("音訊系統", test_audio)
    ]
    
    results = []
    for name, test_func in tests:
        result = test_func()
        results.append(result)
        time.sleep(0.5)
    
    print(f"\n=== 測試結果: {sum(results)}/{len(results)} 通過 ===\n")
    
    if all(results):
        print("✓ 所有測試通過，系統正常")
        return 0
    else:
        print("✗ 有測試失敗，請檢查錯誤訊息")
        return 1

if __name__ == '__main__':
    sys.exit(main())
```

執行測試：

```bash
chmod +x test_components.py
python3 test_components.py
```

### 3. 網路封包分析

如果懷疑 API 通訊有問題：

```bash
# 安裝 tcpdump
sudo apt install tcpdump

# 監聽 HTTP 流量
sudo tcpdump -i any -A 'tcp port 5000'

# 在另一個終端執行程式
python3 book_reader.py
```

### 4. 效能分析

使用 Python profiler：

```bash
python3 -m cProfile -o profile.stats book_reader.py

# 分析結果
python3 -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"
```

---

## 🔨 硬體問題

### GPIO 硬體檢查

1. **使用三用電表測試**:
   - 測試 GPIO17 和 GND 之間的電壓
   - 按下按鈕時應該有 3.3V

2. **使用 LED 測試**:
   ```
   LED 正極 -> GPIO17
   LED 負極 -> 電阻(330Ω) -> GND
   ```
   按下按鈕時 LED 應該亮起

### 攝影機硬體檢查

1. **更換 USB 端口**
2. **使用有供電的 USB Hub**
3. **測試其他攝影機**
4. **檢查 USB 線材**

### 供電問題

Raspberry Pi 供電不足會導致各種問題：

1. **使用官方電源供應器** (5V 3A)
2. **檢查電壓**:
   ```bash
   vcgencmd get_throttled
   # 0x0 表示正常
   # 非 0x0 表示有供電問題
   ```
3. **監控電壓**:
   ```bash
   watch -n 1 vcgencmd measure_volts
   ```

---

## 📊 疑難排解流程圖

```
開始
  ↓
程式能啟動嗎？
  ├─ 否 → 檢查 Python 環境和套件
  └─ 是 ↓
        ↓
GPIO 能偵測嗎？
  ├─ 否 → 檢查權限和接線
  └─ 是 ↓
        ↓
攝影機能拍照嗎？
  ├─ 否 → 檢查攝影機連接和驅動
  └─ 是 ↓
        ↓
API 能連線嗎？
  ├─ 否 → 檢查網路和 API 伺服器
  └─ 是 ↓
        ↓
OCR 辨識正確嗎？
  ├─ 否 → 檢查圖片品質和提示詞
  └─ 是 ↓
        ↓
音檔能播放嗎？
  ├─ 否 → 檢查音訊裝置和檔案
  └─ 是 ↓
        ↓
問題解決 ✓
```

---

## 📞 進一步協助

如果以上方法都無法解決問題：

1. **收集診斷資訊**:
   ```bash
   ./diagnostic.sh > diagnostic_report.txt
   ./test_components.py >> diagnostic_report.txt
   tail -100 logs/book_reader.log >> diagnostic_report.txt
   ```

2. **查看相關文檔**:
   - [錯誤訊息說明](ERROR_MESSAGES.md)
   - [設定檔說明](CONFIGURATION.md)
   - [安裝指南](INSTALLATION.md)

3. **社群資源**:
   - Raspberry Pi 論壇
   - DeepSeek-OCR GitHub Issues

---

**文檔版本**: 1.0.0  
**更新日期**: 2025-11-11

