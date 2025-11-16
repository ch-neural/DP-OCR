#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPIO 按鈕測試程式
功能：監聽 GPIO17 的按鈕點擊，當偵測到點擊時顯示 "Click detected"
"""

import time
import sys
import os

# 偵測 Raspberry Pi 版本
def detect_raspberry_pi_version():
    """偵測 Raspberry Pi 版本"""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
            
            # 檢查是否為 Raspberry Pi（透過 Hardware 欄位）
            is_raspberry_pi = 'Hardware' in cpuinfo and ('BCM' in cpuinfo or 'Raspberry' in cpuinfo)
            
            if not is_raspberry_pi:
                # 如果不是標準 Raspberry Pi 格式，檢查 Model 欄位（某些情況下可能沒有 Hardware）
                # 這可能是透過 SSH 連線或其他環境
                if 'Model' in cpuinfo:
                    for line in cpuinfo.split('\n'):
                        if 'Model' in line and ':' in line and 'model name' not in line.lower():
                            model = line.split(':')[1].strip()
                            # Pi 5: model = 63
                            if '63' in model:
                                return 5
                            # Pi 4: model = 19
                            elif '19' in model:
                                return 4
                # 如果沒有找到，返回 None（讓程式嘗試兩種庫）
                return None
            
            # 檢查 Model 欄位（Raspberry Pi 5 的 model 是 63）
            if 'Model' in cpuinfo:
                for line in cpuinfo.split('\n'):
                    if 'Model' in line and ':' in line and 'model name' not in line.lower():
                        model = line.split(':')[1].strip()
                        # Pi 5: model = 63
                        if '63' in model or 'Pi 5' in model or 'Raspberry Pi 5' in model:
                            return 5
                        # Pi 4: model = 19
                        elif '19' in model or 'Pi 4' in model or 'Raspberry Pi 4' in model:
                            return 4
            
            # 檢查 Revision 欄位（備用方法）
            if 'Revision' in cpuinfo:
                for line in cpuinfo.split('\n'):
                    if 'Revision' in line and ':' in line:
                        revision = line.split(':')[1].strip()
                        # Raspberry Pi 5 的 Revision 通常以 c0 或 d0 開頭
                        if revision.startswith(('c0', 'd0')):
                            return 5
                        # Raspberry Pi 4 的 Revision 通常以 c0 開頭（但不同於 Pi 5）
                        elif revision.startswith('c0') and 'Pi 4' in cpuinfo:
                            return 4
            
            return None
    except Exception:
        return None

# GPIO 庫狀態（將在下方設定）

# 偵測 Raspberry Pi 版本
PI_VERSION = detect_raspberry_pi_version()

# 優先嘗試 rpi-lgpio（RPi.GPIO 的 drop-in replacement，最相容）
# 然後嘗試 gpiod，最後回退到 RPi.GPIO
GPIO_AVAILABLE = False
GPIO_BACKEND = None

# 修復 systemd 服務運行時的 lgpio 通知文件創建問題
# 當作為 systemd 服務運行時，當前工作目錄可能沒有寫入權限
# 解決方案：確保工作目錄是可寫入的，或設置環境變數
def _setup_lgpio_environment():
    """設置 lgpio 庫的環境變數，解決 systemd 服務運行時的通知文件創建問題"""
    try:
        # 獲取當前腳本所在目錄
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 嘗試在腳本目錄創建臨時文件以測試寫入權限
        test_file = os.path.join(script_dir, '.lgpio_test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            # 如果成功，設置工作目錄為腳本目錄
            os.chdir(script_dir)
        except (OSError, PermissionError):
            # 如果腳本目錄不可寫，嘗試使用 /tmp 或用戶主目錄
            import tempfile
            temp_dir = tempfile.gettempdir()
            try:
                # 測試 /tmp 是否可寫
                test_file = os.path.join(temp_dir, '.lgpio_test')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                # 設置工作目錄為 /tmp
                os.chdir(temp_dir)
            except (OSError, PermissionError):
                # 最後嘗試用戶主目錄
                home_dir = os.path.expanduser('~')
                if os.access(home_dir, os.W_OK):
                    os.chdir(home_dir)
    except Exception:
        # 如果所有嘗試都失敗，繼續使用當前目錄
        pass

# 優先嘗試 rpi-lgpio（如果已安裝）
try:
    # 在導入 lgpio 之前設置環境
    _setup_lgpio_environment()
    
    import RPi.GPIO as GPIO
    import lgpio  # rpi-lgpio 依賴 lgpio
    # 測試是否能正常運作
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO_AVAILABLE = True
    GPIO_BACKEND = 'rpi-lgpio'
    if PI_VERSION == 5:
        print("✅ 使用 rpi-lgpio 庫（Raspberry Pi 5 相容的 RPi.GPIO 替代方案）")
    else:
        print("✅ 使用 rpi-lgpio 庫（RPi.GPIO 替代方案）")
except (ImportError, RuntimeError, FileNotFoundError, OSError) as e:
    # rpi-lgpio 初始化失敗（可能是權限問題或環境問題）
    # 記錄錯誤但不中斷，繼續嘗試其他選項
    GPIO_AVAILABLE = False  # 確保標記為不可用
    
    if "lgd-nfy" in str(e) or "No such file or directory" in str(e):
        # lgpio 通知文件創建失敗，這通常是環境問題
        print(f"⚠️  rpi-lgpio 初始化警告: {e}")
        print("   這可能是因為當前目錄權限問題或環境設定")
        print("   將嘗試使用 gpiod 庫...")
    
    # rpi-lgpio 未安裝或不可用，嘗試 gpiod
    try:
        import gpiod
        from gpiod.line import Direction, Value
        GPIO_AVAILABLE = True
        GPIO_BACKEND = 'gpiod'
        if PI_VERSION == 5:
            print("✅ 使用 gpiod 庫（Raspberry Pi 5 推薦）")
        else:
            print("✅ 使用 gpiod 庫")
    except ImportError:
        # gpiod 未安裝，嘗試傳統 RPi.GPIO
        try:
            import RPi.GPIO as GPIO
            # 測試 RPi.GPIO 是否能在當前系統上運作
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO_AVAILABLE = True
            GPIO_BACKEND = 'RPi.GPIO'
            
            if PI_VERSION == 5:
                print("✅ 使用 RPi.GPIO 庫（Raspberry Pi 5）")
                print("   注意: Raspberry Pi 5 建議使用 rpi-lgpio 或 gpiod")
                print("   安裝 rpi-lgpio: pip install rpi-lgpio")
                print("   或安裝 gpiod: sudo apt-get install python3-libgpiod python3-gpiod")
            else:
                print("✅ 使用 RPi.GPIO 庫（Raspberry Pi 4 及更早版本）")
        except (ImportError, RuntimeError) as e2:
            GPIO_AVAILABLE = False
            GPIO_BACKEND = None
            
            # 根據錯誤訊息判斷
            if "Cannot determine SOC peripheral base address" in str(e2):
                # Raspberry Pi 5 不支援舊版 RPi.GPIO
                print("❌ 錯誤: RPi.GPIO 不支援此 Raspberry Pi 版本")
                print("\n請選擇以下方案之一：")
                print("\n方案 1（推薦）: 安裝 rpi-lgpio（RPi.GPIO 的 drop-in replacement）")
                print("  pip install rpi-lgpio")
                print("  或: sudo apt-get install python3-rpi-lgpio")
                print("  sudo adduser $LOGNAME gpio")
                print("  sudo reboot")
                print("\n方案 2: 安裝 gpiod 庫")
                print("  sudo apt-get update")
                print("  sudo apt-get install -y python3-libgpiod python3-gpiod")
            else:
                print(f"❌ 警告: 無法匯入 GPIO 庫")
                print(f"   rpi-lgpio 錯誤: {e}")
                print(f"   RPi.GPIO 錯誤: {e2}")
                print("\n安裝說明：")
                if PI_VERSION == 5:
                    print("  Raspberry Pi 5（推薦）: pip install rpi-lgpio")
                    print("  Raspberry Pi 5（備選）: sudo apt-get install python3-libgpiod python3-gpiod")
                else:
                    print("  Raspberry Pi 4: sudo apt-get install python3-rpi.gpio")
                    print("  或使用 pip: pip3 install RPi.GPIO")
            sys.exit(1)
except Exception as e:
    # 其他未預期的錯誤（例如 lgpio 初始化失敗）
    # 嘗試 gpiod 作為備選
    if not GPIO_AVAILABLE:
        if "lgd-nfy" in str(e) or "No such file or directory" in str(e):
            # lgpio 通知文件創建失敗
            print(f"⚠️  rpi-lgpio 初始化失敗: {e}")
            print("   這可能是因為當前目錄權限問題或環境設定")
            print("   將嘗試使用 gpiod 庫...")
        else:
            print(f"⚠️  rpi-lgpio 初始化警告: {e}")
            print("   將嘗試其他 GPIO 庫...")
        
        try:
            import gpiod
            from gpiod.line import Direction, Value
            GPIO_AVAILABLE = True
            GPIO_BACKEND = 'gpiod'
            print("✅ 使用 gpiod 庫（備選方案）")
        except ImportError:
            GPIO_AVAILABLE = False
            GPIO_BACKEND = None
            print(f"❌ 錯誤: 無法初始化任何 GPIO 庫")
            print(f"   rpi-lgpio 錯誤: {e}")
            print("\n建議解決方案：")
            print("  1. 檢查 rpi-lgpio 權限: sudo adduser $LOGNAME gpio && sudo reboot")
            print("  2. 或使用 gpiod: sudo apt-get install python3-libgpiod python3-gpiod")
            sys.exit(1)


class GPIOButtonTester:
    """GPIO 按鈕測試類別"""
    
    def __init__(self, gpio_pin=17, debounce_delay=0.2):
        """
        初始化 GPIO 按鈕測試器
        
        Args:
            gpio_pin: GPIO 腳位編號（預設為 17）
            debounce_delay: 去彈跳延遲時間（秒），預設 0.2 秒
        """
        self.gpio_pin = gpio_pin
        self.debounce_delay = debounce_delay
        self.running = False
        
        if not GPIO_AVAILABLE:
            raise RuntimeError("GPIO 庫不可用，無法初始化")
        
        self._setup_gpio()
    
    def _setup_gpio(self):
        """設定 GPIO"""
        if GPIO_BACKEND == 'gpiod':
            # 使用 gpiod (Raspberry Pi 5)
            # Raspberry Pi 5 使用 gpiochip4
            chip_paths = ['/dev/gpiochip4', '/dev/gpiochip0', 'gpiochip4', 'gpiochip0']
            chip = None
            chip_path_used = None
            
            # 嘗試不同的 chip 路徑
            for chip_path in chip_paths:
                try:
                    chip = gpiod.Chip(chip_path)
                    chip_path_used = chip_path
                    print(f"✅ 找到 GPIO chip: {chip_path}")
                    break
                except Exception as e:
                    continue
            
            if chip is None:
                error_msg = "無法找到可用的 GPIO chip。請確認是否在 Raspberry Pi 上運行。"
                print(f"❌ {error_msg}")
                raise RuntimeError(error_msg)
            
            try:
                self.chip = chip
                
                # 根據診斷資訊，此版本的 gpiod 使用 request_lines API
                # 首先需要將 GPIO ID 轉換為 line offset
                try:
                    # 方法 1: 使用 line_offset_from_id 轉換 GPIO ID 到 offset
                    line_offset = self.chip.line_offset_from_id(self.gpio_pin)
                except AttributeError:
                    # 如果沒有 line_offset_from_id，直接使用 GPIO ID 作為 offset
                    line_offset = self.gpio_pin
                
                # 使用 request_lines 請求 GPIO line
                # 根據 gpiod API，request_lines 需要 LineRequest 配置
                try:
                    # 建立 LineRequest 配置
                    request = gpiod.LineRequest()
                    request.consumer = 'GPIOButtonTester'
                    request.request_type = gpiod.LINE_REQ_DIR_IN
                    request.flags = gpiod.LINE_REQ_FLAG_BIAS_PULL_UP
                    
                    # 使用 request_lines 請求 line（返回 Line 物件）
                    lines = self.chip.request_lines([line_offset], request)
                    if lines and len(lines) > 0:
                        self.gpio_line = lines[0]
                    else:
                        raise RuntimeError("request_lines 返回空列表")
                except (AttributeError, TypeError) as e:
                    # 如果 LineRequest 不存在，嘗試其他方式
                    try:
                        # 嘗試直接使用 request_lines 並傳入字典配置
                        lines = self.chip.request_lines(
                            [line_offset],
                            consumer='GPIOButtonTester',
                            type=gpiod.LINE_REQ_DIR_IN,
                            flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP
                        )
                        if lines and len(lines) > 0:
                            self.gpio_line = lines[0]
                        else:
                            raise RuntimeError("request_lines 返回空列表")
                    except (AttributeError, TypeError) as e2:
                        # 如果所有方法都失敗，提供清楚的錯誤訊息
                        available_methods = [m for m in dir(self.chip) if not m.startswith('_') and callable(getattr(self.chip, m, None))]
                        methods_str = ', '.join(sorted(available_methods)[:10])
                        
                        raise RuntimeError(
                            f"gpiod API 不相容。無法請求 GPIO line {self.gpio_pin}。\n\n"
                            f"可用的 Chip 方法: {methods_str}...\n\n"
                            f"錯誤詳情: {e2}\n\n"
                            "建議使用 rpi-lgpio（RPi.GPIO 的替代方案）：\n"
                            "  sudo apt-get install python3-rpi-lgpio\n"
                            "  或: pip install rpi-lgpio\n\n"
                            "rpi-lgpio 已安裝，程式應該會自動使用它。"
                        )
                
                print(f"✅ GPIO{self.gpio_pin} 設定完成（gpiod，使用 {chip_path_used}）")
            except Exception as e:
                print(f"❌ GPIO{self.gpio_pin} 設定失敗: {e}")
                print(f"   嘗試的 chip 路徑: {chip_path_used}")
                print(f"\n   提示: 請確認 gpiod 版本正確")
                print(f"   檢查指令: python3 -c 'import gpiod; print(gpiod.__version__ if hasattr(gpiod, \"__version__\") else \"未知版本\")'")
                raise
        
        elif GPIO_BACKEND in ('RPi.GPIO', 'rpi-lgpio'):
            # 使用 RPi.GPIO 或 rpi-lgpio
            # rpi-lgpio 是 Raspberry Pi 5 的 drop-in replacement
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                backend_name = 'rpi-lgpio' if GPIO_BACKEND == 'rpi-lgpio' else 'RPi.GPIO'
                print(f"✅ GPIO{self.gpio_pin} 設定完成（{backend_name}）")
            except RuntimeError as e:
                if "Cannot determine SOC peripheral base address" in str(e):
                    error_msg = (
                        "RPi.GPIO 不支援 Raspberry Pi 5。\n"
                        "請安裝 gpiod 庫：sudo apt-get install python3-libgpiod"
                    )
                    print(f"❌ {error_msg}")
                    raise RuntimeError(error_msg) from e
                else:
                    print(f"❌ GPIO{self.gpio_pin} 設定失敗: {e}")
                    raise
            except Exception as e:
                print(f"❌ GPIO{self.gpio_pin} 設定失敗: {e}")
                raise
    
    def _read_gpio(self):
        """
        讀取 GPIO 狀態
        
        Returns:
            bool: True 表示按鈕按下（LOW），False 表示按鈕未按下（HIGH）
        """
        if GPIO_BACKEND == 'gpiod':
            # gpiod: 0 = LOW (按下), 1 = HIGH (未按下)
            # 因為我們使用 PULL_UP，按下時會是 LOW (0)
            try:
                # 嘗試 get_value() 方法
                return self.gpio_line.get_value() == 0
            except AttributeError:
                try:
                    # 嘗試 value 屬性
                    return self.gpio_line.value == 0
                except AttributeError:
                    # 嘗試讀取方法
                    return self.gpio_line.read() == 0
        elif GPIO_BACKEND in ('RPi.GPIO', 'rpi-lgpio'):
            # RPi.GPIO / rpi-lgpio: GPIO.LOW = 按下, GPIO.HIGH = 未按下
            return GPIO.input(self.gpio_pin) == GPIO.LOW
    
    def _detect_click(self):
        """
        偵測按鈕點擊（包含去彈跳處理）
        
        Returns:
            bool: True 表示偵測到一次點擊
        """
        # 等待按鈕按下
        if not self._read_gpio():
            return False
        
        # 記錄按下時間
        press_time = time.time()
        
        # 等待去彈跳時間
        time.sleep(self.debounce_delay)
        
        # 確認按鈕仍然按下
        if not self._read_gpio():
            return False
        
        # 等待按鈕釋放
        while self._read_gpio():
            if not self.running:
                return False
            time.sleep(0.01)  # 10ms 檢查間隔
        
        # 再次等待去彈跳時間
        time.sleep(self.debounce_delay)
        
        # 確認按鈕已釋放
        if self._read_gpio():
            return False
        
        # 計算按壓時間
        release_time = time.time()
        press_duration = release_time - press_time
        
        # 只接受合理的按壓時間（0.1 秒到 5 秒）
        if 0.1 <= press_duration <= 5.0:
            return True
        
        return False
    
    def run(self):
        """執行按鈕監聽循環"""
        self.running = True
        
        print("\n" + "=" * 60)
        print(f"GPIO{self.gpio_pin} 按鈕測試程式已啟動")
        print("=" * 60)
        print("請按下按鈕進行測試...")
        print("按 Ctrl+C 停止程式")
        print("=" * 60 + "\n")
        
        click_count = 0
        
        try:
            while self.running:
                if self._detect_click():
                    click_count += 1
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                    print(f"[{timestamp}] Click detected (總計: {click_count} 次)")
                
                # 短暫延遲，避免 CPU 佔用過高
                time.sleep(0.01)
        
        except KeyboardInterrupt:
            print("\n\n" + "=" * 60)
            print("收到中斷信號，正在停止...")
            print(f"總共偵測到 {click_count} 次點擊")
            print("=" * 60)
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """清理 GPIO 資源"""
        self.running = False
        
        if GPIO_BACKEND == 'gpiod':
            if hasattr(self, 'gpio_line'):
                self.gpio_line.release()
            if hasattr(self, 'chip'):
                self.chip.close()
            print("✅ GPIO 資源已釋放（gpiod）")
        
        elif GPIO_BACKEND in ('RPi.GPIO', 'rpi-lgpio'):
            GPIO.cleanup()
            backend_name = 'rpi-lgpio' if GPIO_BACKEND == 'rpi-lgpio' else 'RPi.GPIO'
            print(f"✅ GPIO 資源已釋放（{backend_name}）")


def main():
    """主函數"""
    try:
        tester = GPIOButtonTester(gpio_pin=17, debounce_delay=0.2)
        tester.run()
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

