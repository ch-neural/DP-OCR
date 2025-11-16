#!/bin/bash
# 閱讀機器人啟動腳本（含 DISPLAY 設定）
# 適用於透過 SSH 連線，但想讓預覽視窗顯示在 Raspberry Pi 本機螢幕

echo "========================================"
echo "  閱讀機器人（本機顯示模式）"
echo "========================================"
echo ""

# 設定 DISPLAY 到本機 LCD
export DISPLAY=:0
echo "✓ DISPLAY 已設定為: $DISPLAY"

# 檢查 DISPLAY 是否可用
if xset q &>/dev/null; then
    echo "✓ X11 顯示環境正常"
else
    echo "⚠️  警告: 無法連接到 X11 顯示環境"
    echo "   請確認："
    echo "   1. Raspberry Pi 已啟動圖形介面"
    echo "   2. 執行: xhost + (在本機終端機)"
fi

echo ""

# 確認當前目錄
if [ ! -f "book_reader.py" ]; then
    echo "✗ 錯誤: 找不到 book_reader.py"
    echo "  請在 example_bookReader/ 目錄中執行此腳本"
    exit 1
fi

# 啟動程式
echo "啟動閱讀機器人..."
echo "預覽視窗將顯示在 Raspberry Pi 的螢幕上"
echo "按 Ctrl+C 停止程式"
echo ""

python3 book_reader.py

