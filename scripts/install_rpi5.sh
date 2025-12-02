#!/bin/bash
# Raspberry Pi 5 閱讀機器人自動安裝腳本

echo "============================================================"
echo "  Raspberry Pi 5 閱讀機器人安裝腳本"
echo "============================================================"
echo ""

# 檢查是否為 root
if [ "$EUID" -eq 0 ]; then
    echo "請勿使用 root 或 sudo 執行此腳本"
    echo "腳本會在需要時自動要求 sudo 權限"
    exit 1
fi

# 偵測 Raspberry Pi 型號
MODEL=$(cat /proc/cpuinfo | grep Model | cut -d: -f2 | xargs 2>/dev/null || echo "未知")
echo "偵測到系統: $MODEL"
echo ""

# 步驟 1: 更新系統
echo "[1/7] 更新系統..."
sudo apt update

# 步驟 2: 安裝 GPIO 庫
echo ""
echo "[2/7] 安裝 GPIO 庫..."
if [[ $MODEL == *"Raspberry Pi 5"* ]]; then
    echo "      安裝 gpiod（Raspberry Pi 5 專用）"
    sudo apt install -y python3-libgpiod python3-gpiod
    echo "      ✓ gpiod 安裝完成"
else
    echo "      安裝 RPi.GPIO（Raspberry Pi 4 及更早版本）"
    pip3 install --user RPi.GPIO
    echo "      ✓ RPi.GPIO 安裝完成"
fi

# 步驟 3: 安裝系統依賴
echo ""
echo "[3/7] 安裝系統依賴..."
sudo apt install -y \
    python3-pip \
    python3-opencv \
    libsdl2-mixer-2.0-0 \
    libsdl2-2.0-0 \
    alsa-utils
echo "      ✓ 系統依賴安裝完成"

# 步驟 4: 安裝 Python 套件
echo ""
echo "[4/7] 安裝 Python 套件..."
pip3 install --user -r requirements.txt
echo "      ✓ Python 套件安裝完成"

# 步驟 5: 設定使用者權限
echo ""
echo "[5/7] 設定使用者權限..."
sudo usermod -a -G gpio,video,audio $USER
echo "      ✓ 使用者已加入 gpio, video, audio 群組"

# 步驟 6: 建立必要目錄
echo ""
echo "[6/7] 建立必要目錄..."
mkdir -p logs
mkdir -p captured_images
echo "      ✓ 目錄建立完成"

# 步驟 7: 測試 GPIO
echo ""
echo "[7/7] 測試 GPIO..."
python3 << 'EOTEST'
import sys

# 測試 gpiod
try:
    import gpiod
    chip = gpiod.Chip('/dev/gpiochip4')
    print(f"      ✓ 使用 gpiod (Raspberry Pi 5)")
    print(f"      ✓ GPIO 晶片: {chip.name()}")
    print(f"      ✓ 可用腳位: {chip.num_lines()}")
    chip.close()
    sys.exit(0)
except Exception as e:
    pass

# 測試 RPi.GPIO
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    print(f"      ✓ 使用 RPi.GPIO")
    GPIO.cleanup()
    sys.exit(0)
except Exception as e:
    pass

# 兩者都失敗
print(f"      ✗ GPIO 測試失敗")
print(f"      請檢查安裝步驟")
sys.exit(1)
EOTEST

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "  ✓ 安裝完成！"
    echo "============================================================"
    echo ""
    echo "下一步："
    echo "  1. 登出後重新登入以套用群組權限"
    echo "  2. 編輯 config.ini 設定 API 位址"
    echo "  3. 連接硬體（按鈕、攝影機）"
    echo "  4. 執行: python3 book_reader.py"
    echo ""
    echo "詳細說明請參考："
    echo "  - README.md"
    echo "  - README/RASPBERRY_PI5_SETUP.md"
    echo ""
else
    echo ""
    echo "============================================================"
    echo "  ✗ 安裝失敗"
    echo "============================================================"
    echo ""
    echo "請檢查上方錯誤訊息，或參考："
    echo "  - README/RASPBERRY_PI5_SETUP.md"
    echo "  - README/TROUBLESHOOTING.md"
    echo ""
    exit 1
fi

