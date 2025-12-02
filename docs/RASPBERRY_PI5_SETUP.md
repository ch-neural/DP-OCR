# Raspberry Pi 5 安裝指南

## 🎯 Raspberry Pi 5 特別說明

Raspberry Pi 5 使用了新的 **RP1 I/O 控制器**來處理 GPIO。本程式支援三種 GPIO 庫：

1. **gpiod**（推薦）：現代化的 GPIO 庫，專為 Raspberry Pi 5 設計
2. **rpi-lgpio**（備選）：RPi.GPIO 的 drop-in replacement，與所有 Raspberry Pi 版本相容
3. **RPi.GPIO**（傳統）：傳統 GPIO 庫，主要用於 Raspberry Pi 4 及更早版本

程式會**自動嘗試這些庫**，優先使用 `gpiod`，如果不可用則嘗試 `rpi-lgpio`，最後回退到 `RPi.GPIO`。

---

## 🚀 快速安裝（Raspberry Pi 5）

### 步驟 1: 安裝系統依賴

```bash
# 更新系統
sudo apt update
sudo apt upgrade -y

# 安裝 Python GPIO 庫（推薦：gpiod）
sudo apt install -y python3-libgpiod python3-gpiod

# 或安裝備選庫（rpi-lgpio，RPi.GPIO 的 drop-in replacement）
sudo apt install -y python3-rpi-lgpio
sudo adduser $LOGNAME gpio
sudo reboot

# 或安裝傳統庫（RPi.GPIO，主要用於 Pi 4 及更早版本）
pip3 install RPi.GPIO

# 安裝其他依賴
sudo apt install -y python3-pip python3-opencv libsdl2-mixer-2.0-0
```

**注意**：程式會自動嘗試三種庫，優先順序為：
1. `gpiod`（推薦）
2. `rpi-lgpio`（備選，RPi.GPIO 的 drop-in replacement）
3. `RPi.GPIO`（傳統，主要用於 Pi 4 及更早版本）

### 步驟 2: 安裝 Python 套件

```bash
cd example_bookReader
pip3 install -r requirements.txt
```

### 步驟 3: 設定權限

```bash
# 將使用者加入 gpio 群組
sudo usermod -a -G gpio,video,audio $USER

# 登出後重新登入使設定生效
```

### 步驟 4: 測試 GPIO

```bash
# 測試 gpiod 是否正常
python3 << 'EOF'
import gpiod

chip = gpiod.Chip('/dev/gpiochip4')
print(f"✓ GPIO 晶片: {chip.name()}")
print(f"✓ 可用腳位數: {chip.num_lines()}")
chip.close()
print("✓ gpiod 測試成功！")
EOF
```

### 步驟 5: 執行程式

```bash
python3 book_reader.py
```

您應該會看到：
```
使用 gpiod 庫（Raspberry Pi 5 相容）
閱讀機器人已啟動
等待 GPIO17 觸發信號...
```

---

## 📊 GPIO 庫對照表

| Raspberry Pi 版本 | 推薦 GPIO 庫 | 備選 GPIO 庫 | 安裝指令 | 自動偵測 |
|------------------|------------|------------|---------|---------|
| **Raspberry Pi 5** | `gpiod` ⭐ | `rpi-lgpio` | `sudo apt install python3-libgpiod` | ✅ |
| Raspberry Pi 5 | `rpi-lgpio` ⭐⭐ | `gpiod` | `sudo apt install python3-rpi-lgpio` | ✅ |
| Raspberry Pi 4 | `RPi.GPIO` | `gpiod` | `pip install RPi.GPIO` | ✅ |
| Raspberry Pi 3 | `RPi.GPIO` | `gpiod` | `pip install RPi.GPIO` | ✅ |
| Raspberry Pi Zero | `RPi.GPIO` | `gpiod` | `pip install RPi.GPIO` | ✅ |

**說明**：
- ⭐ `gpiod`：現代化 GPIO 庫，專為 Raspberry Pi 5 設計
- ⭐⭐ `rpi-lgpio`：RPi.GPIO 的 drop-in replacement，與所有 Raspberry Pi 版本相容
- 程式會**自動嘗試三種庫**，優先順序：`gpiod` → `rpi-lgpio` → `RPi.GPIO`
- 如果推薦的庫不可用，會自動回退到下一個選項
- Raspberry Pi 5 建議使用 `gpiod` 或 `rpi-lgpio` 以獲得最佳相容性

---

## 🔧 Raspberry Pi 5 GPIO 差異

### GPIO 晶片裝置

- **Raspberry Pi 5**: `/dev/gpiochip4`
- **Raspberry Pi 4 及更早**: `/dev/gpiochip0`

程式已經自動處理這個差異。

### 腳位編號

GPIO 腳位編號（BCM 模式）**完全相同**：

| 實體腳位 | BCM 編號 | 說明 |
|---------|---------|------|
| Pin 11 | GPIO 17 | 預設觸發腳位 |
| Pin 1 | 3.3V | 電源 |
| Pin 6 | GND | 接地 |

接線方式與舊版 Raspberry Pi **完全相同**。

---

## 🐛 疑難排解

### 問題 1: 找不到 gpiod 模組

**錯誤訊息**:
```
ModuleNotFoundError: No module named 'gpiod'
```

**解決方法**:
```bash
# 使用 apt 安裝（不是 pip）
sudo apt install python3-libgpiod python3-gpiod

# 驗證安裝
python3 -c "import gpiod; print('✓ gpiod 安裝成功')"
```

### 問題 2: 權限不足

**錯誤訊息**:
```
PermissionError: [Errno 13] Permission denied: '/dev/gpiochip4'
```

**解決方法**:
```bash
# 方案 1: 加入 gpio 群組
sudo usermod -a -G gpio $USER
# 登出後重新登入

# 方案 2: 使用 sudo（不推薦）
sudo python3 book_reader.py
```

### 問題 3: 找不到 gpiochip4

**錯誤訊息**:
```
FileNotFoundError: [Errno 2] No such file or directory: '/dev/gpiochip4'
```

**原因**: 可能不是 Raspberry Pi 5，或者核心版本過舊

**檢查方法**:
```bash
# 檢查可用的 GPIO 晶片
ls -l /dev/gpiochip*

# 檢查 Raspberry Pi 版本
cat /proc/cpuinfo | grep Model
```

**解決方法**:
- 如果是 Raspberry Pi 4 或更早版本，程式會自動使用 RPi.GPIO
- 如果確實是 Raspberry Pi 5，更新系統：
  ```bash
  sudo apt update
  sudo apt full-upgrade -y
  sudo reboot
  ```

### 問題 4: 程式使用模擬模式

**訊息**:
```
警告: 無法匯入 GPIO 庫，將使用模擬模式
```

**原因**: 兩個 GPIO 庫都沒安裝

**解決方法**:
```bash
# Raspberry Pi 5
sudo apt install python3-libgpiod python3-gpiod

# 或 Raspberry Pi 4 及更早
pip3 install RPi.GPIO
```

---

## 📝 完整安裝腳本

建立一個自動安裝腳本 `install_rpi5.sh`：

```bash
#!/bin/bash
echo "=== Raspberry Pi 5 閱讀機器人安裝腳本 ==="
echo ""

# 檢查是否為 Raspberry Pi 5
MODEL=$(cat /proc/cpuinfo | grep Model | cut -d: -f2 | xargs)
echo "偵測到: $MODEL"
echo ""

# 更新系統
echo "1. 更新系統..."
sudo apt update

# 安裝 GPIO 庫
echo "2. 安裝 GPIO 庫..."
if [[ $MODEL == *"Raspberry Pi 5"* ]]; then
    echo "   安裝 gpiod（Raspberry Pi 5）"
    sudo apt install -y python3-libgpiod python3-gpiod
else
    echo "   安裝 RPi.GPIO（Raspberry Pi 4 及更早）"
    pip3 install RPi.GPIO
fi

# 安裝其他依賴
echo "3. 安裝系統依賴..."
sudo apt install -y python3-pip python3-opencv libsdl2-mixer-2.0-0

# 安裝 Python 套件
echo "4. 安裝 Python 套件..."
pip3 install -r requirements.txt

# 設定權限
echo "5. 設定使用者權限..."
sudo usermod -a -G gpio,video,audio $USER

# 測試 GPIO
echo "6. 測試 GPIO..."
python3 << 'EOF'
try:
    import gpiod
    chip = gpiod.Chip('/dev/gpiochip4')
    print(f"✓ 使用 gpiod (Raspberry Pi 5)")
    print(f"✓ GPIO 晶片: {chip.name()}")
    chip.close()
except:
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        print(f"✓ 使用 RPi.GPIO")
        GPIO.cleanup()
    except Exception as e:
        print(f"✗ GPIO 測試失敗: {e}")
EOF

echo ""
echo "=== 安裝完成 ==="
echo "請登出後重新登入以套用群組權限"
echo "然後執行: python3 book_reader.py"
```

執行安裝腳本：
```bash
chmod +x install_rpi5.sh
./install_rpi5.sh
```

---

## 🧪 測試 GPIO（Raspberry Pi 5）

### 測試腳本 1: 讀取 GPIO 狀態

建立 `test_gpio_rpi5.py`：

```python
#!/usr/bin/env python3
"""Raspberry Pi 5 GPIO 測試腳本"""

import gpiod
import time

# 設定
GPIO_PIN = 17
CHIP_DEVICE = '/dev/gpiochip4'

print("=== Raspberry Pi 5 GPIO 測試 ===")
print(f"測試腳位: GPIO{GPIO_PIN}")
print(f"GPIO 晶片: {CHIP_DEVICE}")
print("請按下連接到 GPIO17 的按鈕...")
print("按 Ctrl+C 結束\n")

# 開啟 GPIO 晶片
chip = gpiod.Chip(CHIP_DEVICE)
line = chip.get_line(GPIO_PIN)

# 設定為輸入模式
line.request(consumer="test", type=gpiod.LINE_REQ_DIR_IN)

try:
    last_state = line.get_value()
    print(f"初始狀態: {'HIGH' if last_state else 'LOW'}")
    
    while True:
        state = line.get_value()
        
        if state != last_state:
            if state == 1:
                print("✓ 按鈕按下 (HIGH)")
            else:
                print("✓ 按鈕放開 (LOW)")
            last_state = state
        
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print("\n測試結束")
finally:
    line.release()
    chip.close()
```

執行測試：
```bash
python3 test_gpio_rpi5.py
```

### 測試腳本 2: 自動偵測 GPIO 庫

建立 `detect_gpio.py`：

```python
#!/usr/bin/env python3
"""自動偵測可用的 GPIO 庫"""

import sys

print("=== GPIO 庫偵測 ===\n")

# 測試 gpiod (Raspberry Pi 5)
print("1. 測試 gpiod...")
try:
    import gpiod
    chip = gpiod.Chip('/dev/gpiochip4')
    print(f"   ✓ gpiod 可用")
    print(f"   ✓ 晶片: {chip.name()}")
    print(f"   ✓ 腳位數: {chip.num_lines()}")
    chip.close()
    print("   → 建議使用: gpiod (Raspberry Pi 5 相容)\n")
    sys.exit(0)
except Exception as e:
    print(f"   ✗ gpiod 不可用: {e}\n")

# 測試 RPi.GPIO (Raspberry Pi 4 及更早)
print("2. 測試 RPi.GPIO...")
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(17, GPIO.IN)
    GPIO.cleanup()
    print(f"   ✓ RPi.GPIO 可用")
    print("   → 建議使用: RPi.GPIO\n")
    sys.exit(0)
except Exception as e:
    print(f"   ✗ RPi.GPIO 不可用: {e}\n")

# 兩者都不可用
print("✗ 找不到可用的 GPIO 庫")
print("\n建議安裝:")
print("  Raspberry Pi 5: sudo apt install python3-libgpiod")
print("  其他版本:       pip3 install RPi.GPIO")
sys.exit(1)
```

執行偵測：
```bash
python3 detect_gpio.py
```

---

## 📚 相關資源

### 官方文檔

- [Raspberry Pi 5 GPIO 文檔](https://www.raspberrypi.com/documentation/computers/raspberry-pi-5.html)
- [libgpiod 文檔](https://git.kernel.org/pub/scm/libs/libgpiod/libgpiod.git/about/)

### 腳位圖

執行以下指令查看腳位圖：
```bash
pinout
```

或參考線上版本：
- https://pinout.xyz/

---

## ✅ 確認清單

在 Raspberry Pi 5 上部署前，請確認：

- [ ] 已安裝 `python3-libgpiod` 和 `python3-gpiod`
- [ ] 已執行 `detect_gpio.py` 確認 gpiod 可用
- [ ] 使用者已加入 `gpio` 群組
- [ ] GPIO 接線正確（GPIO17 + 3.3V）
- [ ] 執行 `test_gpio_rpi5.py` 測試按鈕
- [ ] 程式啟動時顯示「使用 gpiod 庫」

---

**文檔版本**: 1.3.0  
**更新日期**: 2025-11-11  
**新增功能**: Raspberry Pi 5 完整支援

