# 模擬模式使用指南

## 🎮 什麼是模擬模式？

模擬模式允許您在**非 Raspberry Pi 環境**下測試和開發閱讀機器人程式，無需實際的 GPIO 硬體。這對於以下情況特別有用：

- 🖥️ 在開發機器（工作站、筆電）上開發和除錯
- 🧪 測試攝影機和 API 連線
- 📚 學習和了解程式運作流程
- 🔧 在沒有實體按鈕的環境下測試

## 🚀 快速開始

### 在非 Raspberry Pi 環境下執行

如果您在一般 Linux/Mac/Windows 電腦上執行程式，會自動啟用模擬模式：

```bash
cd example_bookReader
python3 book_reader.py
```

您會看到：
```
警告: 無法匯入 RPi.GPIO，將使用模擬模式
============================================================
使用模擬模式運行（無 GPIO 硬體）
將每 10 秒自動觸發一次
按 Ctrl+C 停止程式
============================================================

閱讀機器人已啟動（模擬模式）
將每 10 秒自動觸發一次
在此模式下，您可以測試攝影機和 API 連線
按 Ctrl+C 停止程式
============================================================
```

### 手動啟用模擬模式

即使在 Raspberry Pi 上，您也可以手動啟用模擬模式進行測試：

編輯 `config.ini`：
```ini
[GPIO]
simulation_mode = true        # 啟用模擬模式
simulation_trigger_interval = 10  # 每 10 秒自動觸發
```

---

## ⚙️ 設定說明

### 模擬模式相關參數

在 `config.ini` 的 `[GPIO]` 區段：

| 參數 | 類型 | 預設值 | 說明 |
|------|------|--------|------|
| `simulation_mode` | boolean | `false` | 是否啟用模擬模式 |
| `simulation_trigger_interval` | float | `10` | 自動觸發間隔（秒）|

### 範例設定

```ini
[GPIO]
# 觸發 GPIO 腳位編號（BCM 編號）
trigger_pin = 17

# GPIO 檢查間隔時間（秒）
check_interval = 0.5

# 去彈跳延遲時間（秒）
debounce_delay = 0.2

# 模擬模式（在非 Raspberry Pi 環境測試時設為 true）
simulation_mode = false

# 模擬觸發間隔（秒，僅模擬模式有效）
simulation_trigger_interval = 10
```

---

## 🎯 模擬模式 vs 真實模式

### 模擬模式運作方式

在模擬模式下：

1. ✅ **自動觸發**: 每隔設定的時間自動觸發一次（無需按鈕）
2. ✅ **攝影機功能**: 完全正常運作（如果有攝影機）
3. ✅ **OCR API**: 完全正常運作（需要 API 伺服器）
4. ✅ **音檔播放**: 完全正常運作
5. ✅ **日誌記錄**: 完全正常運作
6. ❌ **GPIO 偵測**: 不使用實體 GPIO

### 對照表

| 功能 | 真實模式 | 模擬模式 |
|------|---------|---------|
| GPIO 硬體 | ✅ 需要 | ❌ 不需要 |
| 按鈕觸發 | ✅ 實體按鈕 | ⏱️ 定時自動觸發 |
| 攝影機 | ✅ 需要 | ✅ 需要 |
| OCR API | ✅ 需要 | ✅ 需要 |
| 音檔播放 | ✅ 正常 | ✅ 正常 |
| LCD 預覽 | ✅ 可用 | ✅ 可用 |
| Raspberry Pi | ✅ 需要 | ❌ 不需要 |

---

## 📋 使用場景

### 場景 1: 開發機器上開發

**環境**: Ubuntu 工作站（無 Raspberry Pi 硬體）

**目的**: 開發和測試程式邏輯

**設定**:
```ini
[GPIO]
simulation_mode = true
simulation_trigger_interval = 5  # 5 秒觸發一次，方便快速測試

[CAMERA]
camera_device = 0  # 使用筆電內建攝影機
show_preview = true
preview_duration = 2.0

[API]
api_url = http://192.168.1.100:5000  # 遠端 API 伺服器
```

**執行**:
```bash
python3 book_reader.py
```

**效果**: 每 5 秒自動拍照、辨識、播放音檔

---

### 場景 2: 測試攝影機設定

**環境**: Raspberry Pi（有硬體但想測試攝影機）

**目的**: 調整攝影機參數、預覽效果

**設定**:
```ini
[GPIO]
simulation_mode = true
simulation_trigger_interval = 3

[CAMERA]
camera_device = 0
frame_width = 1920
frame_height = 1080
show_preview = true
preview_duration = 2.0
```

**執行**:
```bash
python3 book_reader.py
```

**優點**: 不需要一直按按鈕，自動重複拍照，方便測試

---

### 場景 3: 測試 API 連線

**環境**: 任何電腦

**目的**: 測試 DeepSeek-OCR API 是否正常

**設定**:
```ini
[GPIO]
simulation_mode = true
simulation_trigger_interval = 15

[CAMERA]
save_captured_image = true  # 儲存測試照片
image_save_path = test_images
```

**執行**:
```bash
# 準備測試圖片
mkdir -p test_images
# 將測試圖片放在攝影機前，或修改程式載入測試圖片

python3 book_reader.py
```

---

## 🔧 進階用法

### 快速測試模式（1 秒觸發）

適合快速驗證功能：

```ini
[GPIO]
simulation_mode = true
simulation_trigger_interval = 1  # 1 秒
```

### 定時任務模式（長時間觸發）

適合壓力測試或長時間運行：

```ini
[GPIO]
simulation_mode = true
simulation_trigger_interval = 60  # 1 分鐘
```

### 配合預覽除錯

適合調整攝影機角度和位置：

```ini
[GPIO]
simulation_mode = true
simulation_trigger_interval = 5

[CAMERA]
show_preview = true
preview_duration = 3.0  # 有足夠時間查看畫面
save_captured_image = true

[LOGGING]
log_level = DEBUG  # 詳細日誌
```

---

## 🐛 除錯技巧

### 技巧 1: 檢查模擬模式狀態

查看日誌檔案：
```bash
tail -f logs/book_reader.log | grep "模擬"
```

應該會看到：
```
2025-11-11 15:30:00 - WARNING - 使用模擬模式運行（無 GPIO 硬體）
2025-11-11 15:30:00 - INFO - 模擬觸發（等待 10 秒）...
```

### 技巧 2: 快速測試循環

```bash
# 設定短觸發間隔
sed -i 's/simulation_trigger_interval = 10/simulation_trigger_interval = 2/' config.ini

# 執行程式
python3 book_reader.py

# 觀察 2 秒循環測試
```

### 技巧 3: 使用假攝影機（無實體攝影機）

如果沒有攝影機，可以使用虛擬攝影機：

```bash
# 安裝 v4l2loopback（虛擬攝影機）
sudo apt install v4l2loopback-dkms

# 載入模組
sudo modprobe v4l2loopback

# 使用測試圖案
ffmpeg -re -f lavfi -i testsrc=size=1280x720:rate=30 -f v4l2 /dev/video0
```

---

## ⚠️ 注意事項

### 1. 自動觸發無法停止

模擬模式下，程式會自動觸發，無法透過釋放按鈕來停止處理。只能：
- 按 `Ctrl+C` 停止整個程式
- 設定較長的 `simulation_trigger_interval`

### 2. 資源佔用

如果觸發間隔太短，可能會：
- 快速佔用磁碟空間（儲存照片）
- API 伺服器負載過高
- CPU 使用率持續偏高

**建議**: 測試時使用 5-10 秒間隔

### 3. 錯誤累積

如果攝影機或 API 有問題，模擬模式會持續觸發錯誤。建議：
- 先用較長間隔測試
- 檢查日誌檔案
- 修正問題後再縮短間隔

### 4. 不適合生產環境

模擬模式僅用於開發和測試，生產環境應該：
```ini
[GPIO]
simulation_mode = false  # 關閉模擬模式
```

---

## 🔄 從模擬模式切換到真實模式

### 開發階段（模擬模式）

```ini
[GPIO]
simulation_mode = true
simulation_trigger_interval = 5
```

### 測試階段（真實硬體）

```ini
[GPIO]
simulation_mode = false  # 關閉模擬模式
trigger_pin = 17
```

### 生產部署（真實硬體）

```ini
[GPIO]
simulation_mode = false
trigger_pin = 17
check_interval = 0.5
debounce_delay = 0.2
```

---

## ❓ 常見問題

### Q1: 為什麼自動啟用模擬模式？

**A**: 如果程式偵測到無法匯入 `RPi.GPIO` 模組（通常是非 Raspberry Pi 環境），會自動啟用模擬模式。

您會看到訊息：
```
警告: 無法匯入 RPi.GPIO，將使用模擬模式
```

### Q2: 如何在 Raspberry Pi 上關閉模擬模式？

**A**: 確認 `config.ini` 中：
```ini
[GPIO]
simulation_mode = false
```

### Q3: 模擬模式會影響 OCR 準確度嗎？

**A**: 不會。模擬模式只是改變觸發方式（定時 vs 按鈕），OCR 辨識過程完全相同。

### Q4: 可以在模擬模式下測試按鈕嗎？

**A**: 不行。模擬模式不使用 GPIO，無法測試實體按鈕。要測試按鈕必須：
1. 在真實 Raspberry Pi 上
2. 關閉模擬模式（`simulation_mode = false`）

### Q5: 觸發間隔可以很短嗎？

**A**: 技術上可以設為 `0.1` 秒，但不建議：
- API 伺服器可能過載
- 磁碟快速佔滿（如果儲存照片）
- 日誌檔案快速增長

**建議最小值**: 2 秒

---

## 🎓 最佳實踐

1. **開發階段**: 
   - 使用模擬模式
   - 觸發間隔 5-10 秒
   - 啟用詳細日誌

2. **測試階段**:
   - 先用模擬模式驗證功能
   - 再用真實硬體測試
   - 逐步減少觸發間隔

3. **部署階段**:
   - 關閉模擬模式
   - 使用真實 GPIO
   - 調整去彈跳參數

4. **除錯階段**:
   - 啟用模擬模式快速重現問題
   - 使用短觸發間隔
   - 檢查日誌和儲存的照片

---

## 📊 效能比較

| 項目 | 真實模式 | 模擬模式 |
|------|---------|---------|
| CPU 使用 | 低（等待 GPIO）| 低（等待計時）|
| 測試速度 | 手動按鈕 | 自動定時 |
| 開發便利性 | 需要硬體 | 任何電腦 |
| 準確性 | 真實環境 | 相同（除 GPIO）|

---

## 🔗 相關文檔

- [主要說明](../README.md)
- [設定檔說明](CONFIGURATION.md)
- [疑難排解](TROUBLESHOOTING.md)
- [錯誤訊息](ERROR_MESSAGES.md)

---

**文檔版本**: 1.2.0  
**更新日期**: 2025-11-11  
**新增功能**: 模擬模式支援

