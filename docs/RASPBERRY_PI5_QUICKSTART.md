# 🚀 Raspberry Pi 5 快速開始

## ⚡ 5 分鐘快速部署

### 在您的 Raspberry Pi 5 上執行以下指令：

```bash
# 1. 進入目錄
cd example_bookReader

# 2. 執行自動安裝腳本
./install_rpi5.sh

# 3. 登出後重新登入（套用群組權限）
# Ctrl+D 或 exit

# 4. 重新登入後，編輯設定檔
nano config.ini
# 修改這一行：
# api_url = http://您的API伺服器IP:5000

# 5. 連接硬體
# 按鈕一端 → GPIO17 (Pin 11)
# 按鈕另一端 → 3.3V (Pin 1)
# USB 攝影機 → USB 接口

# 6. 啟動程式
python3 book_reader.py
```

---

## ✅ 確認程式正常運行

啟動時您應該會看到：

```
使用 gpiod 庫（Raspberry Pi 5 相容）
pygame 2.x.x (SDL 2.x.x, Python 3.x.x)
...
============================================================
閱讀機器人已啟動
等待 GPIO17 觸發信號...
按 Ctrl+C 停止程式
============================================================
```

**關鍵訊息**: `使用 gpiod 庫（Raspberry Pi 5 相容）`

---

## 🔧 如果遇到問題

### 問題 1: 顯示「使用模擬模式」

**原因**: GPIO 庫未正確安裝

**解決**:
```bash
sudo apt install python3-libgpiod python3-gpiod
```

### 問題 2: 權限錯誤

**解決**:
```bash
sudo usermod -a -G gpio $USER
# 登出後重新登入
```

### 問題 3: 找不到攝影機

**檢查**:
```bash
ls /dev/video*
# 應該看到 /dev/video0
```

---

## 📚 詳細文檔

- [完整安裝指南](README/RASPBERRY_PI5_SETUP.md)
- [主要說明](README.md)
- [疑難排解](README/TROUBLESHOOTING.md)

---

**Raspberry Pi 5 完全支援版本**: 1.3.0  
**更新日期**: 2025-11-11

