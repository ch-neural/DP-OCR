#!/bin/bash
# 閱讀機器人啟動腳本

# 設定 DISPLAY 到本機 LCD（適用於 SSH 連線時）
export DISPLAY=:0

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "  閱讀機器人啟動程序"
echo "========================================"
echo "DISPLAY 已設定為: $DISPLAY"
echo ""

# 檢查是否在正確的目錄
if [ ! -f "book_reader.py" ]; then
    echo -e "${RED}錯誤: 找不到 book_reader.py${NC}"
    echo "請確認您在 example_bookReader/ 目錄中執行此腳本"
    exit 1
fi

# 檢查設定檔
if [ ! -f "config.ini" ]; then
    echo -e "${RED}錯誤: 找不到 config.ini${NC}"
    echo "請先建立設定檔"
    exit 1
fi

# 檢查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}錯誤: 找不到 Python3${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} 找到 Python: $(python3 --version)"

# 檢查必要的目錄
mkdir -p logs
mkdir -p captured_images
echo -e "${GREEN}✓${NC} 目錄結構已準備"

# 檢查權限
if ! groups | grep -q gpio; then
    echo -e "${YELLOW}警告: 使用者不在 gpio 群組中${NC}"
    echo "  建議執行: sudo usermod -a -G gpio $USER"
    echo "  然後重新登入"
fi

if ! groups | grep -q video; then
    echo -e "${YELLOW}警告: 使用者不在 video 群組中${NC}"
    echo "  建議執行: sudo usermod -a -G video $USER"
    echo "  然後重新登入"
fi

# 詢問是否執行測試
echo ""
read -p "是否先執行元件測試？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "執行元件測試..."
    python3 test_components.py
    
    if [ $? -ne 0 ]; then
        echo ""
        echo -e "${RED}元件測試失敗${NC}"
        read -p "是否仍要繼續啟動？(y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# 啟動程式
echo ""
echo "========================================"
echo "  啟動閱讀機器人..."
echo "========================================"
echo ""
echo "按 Ctrl+C 停止程式"
echo ""

# 執行主程式
python3 book_reader.py

# 捕捉退出訊號
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}程式正常結束${NC}"
else
    echo ""
    echo -e "${RED}程式異常結束${NC}"
    echo "請查看日誌: logs/book_reader.log"
fi

