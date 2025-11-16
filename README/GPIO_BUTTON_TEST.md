# GPIO 按鈕測試程式使用說明

## 功能說明

`test_gpio_button.py` 是一個簡單的 GPIO 按鈕測試程式，用於測試 GPIO17 的按鈕點擊功能。

當偵測到按鈕點擊時，程式會顯示 "Click detected" 訊息，並記錄點擊次數。

## 硬體連接

### 按鈕連接方式

```
GPIO17 (Pin 11) ──┬── 按鈕 ── GND
                  │
                  └── 10kΩ 上拉電阻 ── 3.3V
```

**注意**：
- 按鈕一端連接到 GPIO17
- 按鈕另一端連接到 GND
- GPIO17 需要上拉電阻（內部已啟用 PULL_UP）
- 當按鈕按下時，GPIO17 會從 HIGH (3.3V) 變為 LOW (0V)

### Raspberry Pi GPIO 接腳圖

```
    3.3V  [1]  [2]  5V
   GPIO2  [3]  [4]  5V
   GPIO3  [5]  [6]  GND
   GPIO4  [7]  [8]  GPIO14
     GND  [9]  [10] GPIO15
  GPIO17 [11]  [12] GPIO18  ← GPIO17 在這裡
  GPIO27 [13]  [14] GND
  GPIO22 [15]  [16] GPIO23
    3.3V [17]  [18] GPIO24
  GPIO10 [19]  [20] GND
   GPIO9  [21] [22] GPIO25
  GPIO11 [23]  [24] GPIO8
     GND [25]  [26] GPIO7
```

## 使用方法

### 1. 基本使用

```bash
cd /GPUData/working/Deepseek-OCR/example_bookReader
python test_gpio_button.py
```

### 2. 使用執行權限（推薦）

```bash
./test_gpio_button.py
```

### 3. 停止程式

按 `Ctrl+C` 停止程式

## 程式輸出範例

```
✅ 使用 RPi.GPIO 庫
✅ GPIO17 設定完成（RPi.GPIO）

============================================================
GPIO17 按鈕測試程式已啟動
============================================================
請按下按鈕進行測試...
按 Ctrl+C 停止程式
============================================================

[2025-11-11 12:30:45] Click detected (總計: 1 次)
[2025-11-11 12:30:47] Click detected (總計: 2 次)
[2025-11-11 12:30:49] Click detected (總計: 3 次)

^C

============================================================
收到中斷信號，正在停止...
總共偵測到 3 次點擊
============================================================
✅ GPIO 資源已釋放（RPi.GPIO）
```

## 功能特點

### 1. 自動檢測 GPIO 庫

程式會自動檢測可用的 GPIO 庫：
- **gpiod**：Raspberry Pi 5 相容
- **RPi.GPIO**：Raspberry Pi 4 及更早版本

### 2. 去彈跳處理（Debouncing）

- **預設去彈跳延遲**：0.2 秒
- **按壓時間檢查**：只接受 0.1 秒到 5 秒的按壓時間
- **防止誤觸發**：避免按鈕機械彈跳造成的多次觸發

### 3. 點擊計數

- 自動記錄點擊次數
- 每次點擊顯示時間戳記
- 程式結束時顯示總點擊次數

### 4. 優雅退出

- 支援 `Ctrl+C` 中斷
- 自動清理 GPIO 資源
- 顯示統計資訊

## 程式碼說明

### 主要類別：`GPIOButtonTester`

```python
class GPIOButtonTester:
    def __init__(self, gpio_pin=17, debounce_delay=0.2):
        """初始化 GPIO 按鈕測試器"""
    
    def _setup_gpio(self):
        """設定 GPIO"""
    
    def _read_gpio(self):
        """讀取 GPIO 狀態"""
    
    def _detect_click(self):
        """偵測按鈕點擊（包含去彈跳處理）"""
    
    def run(self):
        """執行按鈕監聽循環"""
    
    def cleanup(self):
        """清理 GPIO 資源"""
```

### 參數說明

- **gpio_pin**：GPIO 腳位編號（預設：17）
- **debounce_delay**：去彈跳延遲時間（秒），預設 0.2 秒

### 修改 GPIO 腳位

如果要測試其他 GPIO 腳位，可以修改程式碼：

```python
# 方法 1: 修改 main() 函數
def main():
    tester = GPIOButtonTester(gpio_pin=18, debounce_delay=0.2)  # 改為 GPIO18
    tester.run()

# 方法 2: 直接修改類別初始化
tester = GPIOButtonTester(gpio_pin=18, debounce_delay=0.2)
```

## 故障排除

### 問題 1: "無法匯入 GPIO 庫" 或 "Raspberry Pi 5 必須使用 gpiod 庫"

**錯誤訊息**:
```
❌ 錯誤: Raspberry Pi 5 必須使用 gpiod 庫
```
或
```
RuntimeError: Cannot determine SOC peripheral base address
```

**原因**：
- Raspberry Pi 5 不支援 `RPi.GPIO` 庫
- `gpiod` 庫未安裝
- 程式錯誤地回退到 `RPi.GPIO` 庫

**解決方法**：

**步驟 1**: 安裝 gpiod 庫（Raspberry Pi 5 專用）
```bash
sudo apt-get update
sudo apt-get install -y python3-libgpiod python3-gpiod
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
```

**注意事項**:
- Raspberry Pi 5 必須使用 `gpiod` 庫，不能使用 `RPi.GPIO`
- 程式會自動偵測 Raspberry Pi 版本並使用正確的庫
- 如果偵測到 Pi 5 但 `gpiod` 未安裝，程式會顯示明確的錯誤訊息和安裝指引

### 問題 2: "GPIO17 設定失敗"

**錯誤訊息**:
```
❌ GPIO17 設定失敗: Permission denied
```
或
```
❌ GPIO17 設定失敗: 無法找到可用的 GPIO chip
```

**原因**：
- GPIO 腳位已被其他程式佔用
- 權限不足
- GPIO 晶片路徑錯誤（Raspberry Pi 5）

**解決方法**：

**方法 1**: 檢查並設定權限
```bash
# 將使用者加入 gpio 群組
sudo usermod -a -G gpio $USER
# 登出後重新登入使設定生效
```

**方法 2**: 檢查是否有其他程式使用 GPIO17
```bash
# 檢查 gpiod 使用情況
sudo lsof | grep gpiochip

# 檢查是否有其他程式使用 GPIO
ps aux | grep -E "(book_reader|test_gpio)"
```

**方法 3**: 檢查 GPIO 晶片（Raspberry Pi 5）
```bash
# 列出所有 GPIO 晶片
ls -l /dev/gpiochip*

# Raspberry Pi 5 應該看到 /dev/gpiochip4
# 如果沒有，可能需要更新系統
sudo apt update && sudo apt full-upgrade -y
sudo reboot
```

**方法 4**: 使用 sudo 運行（僅測試用，不推薦）
```bash
sudo python3 test_gpio_button.py
```

### 問題 3: 按鈕無反應

**可能原因**：
1. 按鈕連接錯誤
2. 上拉電阻未啟用
3. GPIO 腳位設定錯誤

**檢查步驟**：
1. 確認按鈕連接正確（GPIO17 和 GND）
2. 確認程式顯示 "GPIO17 設定完成"
3. 使用萬用電錶檢查按鈕按下時 GPIO17 是否變為 LOW

### 問題 4: 多次觸發（無去彈跳）

**原因**：去彈跳延遲時間太短

**解決方法**：
```python
# 增加去彈跳延遲時間
tester = GPIOButtonTester(gpio_pin=17, debounce_delay=0.3)  # 改為 0.3 秒
```

## 技術細節

### GPIO 狀態邏輯

- **未按下**：GPIO17 = HIGH (3.3V)，`_read_gpio()` 返回 `False`
- **按下**：GPIO17 = LOW (0V)，`_read_gpio()` 返回 `True`

### 去彈跳流程

1. 偵測到按鈕按下（GPIO 變為 LOW）
2. 等待去彈跳延遲時間（預設 0.2 秒）
3. 確認按鈕仍然按下
4. 等待按鈕釋放（GPIO 變為 HIGH）
5. 再次等待去彈跳延遲時間
6. 確認按鈕已釋放
7. 檢查按壓時間是否在合理範圍內（0.1-5 秒）
8. 如果通過所有檢查，記錄為一次點擊

### 線程安全

- 使用 `self.running` 標誌控制循環
- 支援 `KeyboardInterrupt` 優雅退出
- 自動清理 GPIO 資源

## 相關文件

- [book_reader.py 主程式](../book_reader.py) - 完整的閱讀機器人程式
- [config.ini 設定檔](../config.ini) - GPIO 設定範例

## 版本資訊

- **版本**：v1.0.0
- **建立日期**：2025-11-11
- **相容性**：Raspberry Pi 4/5，Python 3.7+

---

**提示**：此測試程式是 `book_reader.py` 的簡化版本，專注於 GPIO 按鈕測試。如果需要更複雜的功能（如攝影機、OCR、音訊播放），請參考 `book_reader.py`。

