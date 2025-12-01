#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPIO 按鈕服務類別
功能：監聽 GPIO17 的按鈕點擊，當偵測到完整的按鈕點擊（按下→釋放）時觸發回調函數
用於整合到 Flask Web 應用中，透過 SSE 推送按鈕事件到前端
"""

import time
import sys
import os
import threading
import logging
from typing import Callable, Optional

# 設定 logger
logger = logging.getLogger('GPIOButtonService')

# 偵測 Raspberry Pi 版本
def detect_raspberry_pi_version():
    """偵測 Raspberry Pi 版本"""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
            
            # 檢查是否為 Raspberry Pi（透過 Hardware 欄位）
            is_raspberry_pi = 'Hardware' in cpuinfo and ('BCM' in cpuinfo or 'Raspberry' in cpuinfo)
            
            if not is_raspberry_pi:
                # 如果不是標準 Raspberry Pi 格式，檢查 Model 欄位
                if 'Model' in cpuinfo:
                    for line in cpuinfo.split('\n'):
                        if 'Model' in line and ':' in line and 'model name' not in line.lower():
                            model = line.split(':')[1].strip()
                            if '63' in model:
                                return 5
                            elif '19' in model:
                                return 4
                return None
            
            # 檢查 Model 欄位
            if 'Model' in cpuinfo:
                for line in cpuinfo.split('\n'):
                    if 'Model' in line and ':' in line and 'model name' not in line.lower():
                        model = line.split(':')[1].strip()
                        if '63' in model or 'Pi 5' in model or 'Raspberry Pi 5' in model:
                            return 5
                        elif '19' in model or 'Pi 4' in model or 'Raspberry Pi 4' in model:
                            return 4
            
            return None
    except Exception:
        return None


# GPIO 庫狀態
PI_VERSION = detect_raspberry_pi_version()
GPIO_AVAILABLE = False
GPIO_BACKEND = None
GPIO = None


def _setup_lgpio_environment():
    """設置 lgpio 庫的環境變數，解決 systemd 服務運行時的通知文件創建問題"""
    try:
        # 優先使用用戶家目錄（最可靠）
        home_dir = os.path.expanduser('~')
        if os.access(home_dir, os.W_OK):
            os.chdir(home_dir)
            return
        
        # 嘗試 /tmp 目錄
        import tempfile
        temp_dir = tempfile.gettempdir()
        if os.access(temp_dir, os.W_OK):
            os.chdir(temp_dir)
            return
        
        # 最後嘗試腳本目錄
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if os.access(script_dir, os.W_OK):
            os.chdir(script_dir)
    except Exception:
        pass


def _init_gpio():
    """初始化 GPIO 庫"""
    global GPIO_AVAILABLE, GPIO_BACKEND, GPIO
    
    # 優先嘗試 rpi-lgpio
    try:
        _setup_lgpio_environment()
        import RPi.GPIO as _GPIO
        import lgpio
        _GPIO.setmode(_GPIO.BCM)
        _GPIO.setwarnings(False)
        GPIO_AVAILABLE = True
        GPIO_BACKEND = 'rpi-lgpio'
        GPIO = _GPIO
        logger.info("✅ 使用 rpi-lgpio 庫")
        return
    except (ImportError, RuntimeError, FileNotFoundError, OSError) as e:
        logger.debug(f"rpi-lgpio 初始化失敗: {e}")
    
    # 嘗試 gpiod
    try:
        import gpiod
        from gpiod.line import Direction, Value
        GPIO_AVAILABLE = True
        GPIO_BACKEND = 'gpiod'
        GPIO = gpiod
        logger.info("✅ 使用 gpiod 庫")
        return
    except ImportError:
        pass
    
    # 嘗試傳統 RPi.GPIO
    try:
        import RPi.GPIO as _GPIO
        _GPIO.setmode(_GPIO.BCM)
        _GPIO.setwarnings(False)
        GPIO_AVAILABLE = True
        GPIO_BACKEND = 'RPi.GPIO'
        GPIO = _GPIO
        logger.info("✅ 使用 RPi.GPIO 庫")
        return
    except (ImportError, RuntimeError):
        pass
    
    # 所有庫都不可用
    GPIO_AVAILABLE = False
    GPIO_BACKEND = None
    GPIO = None
    logger.warning("❌ 無法載入任何 GPIO 庫，按鈕功能將無法使用")


# 初始化 GPIO
_init_gpio()


class GPIOButtonService:
    """
    GPIO 按鈕服務類別
    
    功能：
    - 在背景線程中監聽 GPIO17 按鈕點擊
    - 偵測完整的按鈕動作（按下→釋放）
    - 包含去彈跳處理
    - 當偵測到點擊時，通知所有已註冊的回調函數
    
    使用方式：
        service = GPIOButtonService(gpio_pin=17)
        service.on_click(my_callback_function)
        service.start()
        # ... 程式運行 ...
        service.stop()
    """
    
    def __init__(self, gpio_pin: int = 17, debounce_delay: float = 0.2, 
                 simulation_mode: bool = False, simulation_interval: float = 10.0):
        """
        初始化 GPIO 按鈕服務
        
        Args:
            gpio_pin: GPIO 腳位編號（BCM 編號），預設為 17
            debounce_delay: 去彈跳延遲時間（秒），預設 0.2 秒
            simulation_mode: 是否啟用模擬模式（非 Raspberry Pi 環境測試用）
            simulation_interval: 模擬觸發間隔（秒）
        """
        self.gpio_pin = gpio_pin
        self.debounce_delay = debounce_delay
        self.simulation_mode = simulation_mode
        self.simulation_interval = simulation_interval
        
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.callbacks: list[Callable[[], None]] = []
        
        # GPIO 相關
        self.gpio_line = None
        self.chip = None
        
        # 如果 GPIO 不可用且不是模擬模式，發出警告
        if not GPIO_AVAILABLE and not self.simulation_mode:
            logger.warning("GPIO 庫不可用，將自動切換到模擬模式")
            self.simulation_mode = True
        
        # 設定 GPIO（非模擬模式時）
        if not self.simulation_mode and GPIO_AVAILABLE:
            self._setup_gpio()
        
        logger.info(f"GPIOButtonService 初始化完成 (GPIO{gpio_pin}, "
                   f"{'模擬模式' if self.simulation_mode else GPIO_BACKEND})")
    
    def _setup_gpio(self):
        """設定 GPIO"""
        if GPIO_BACKEND == 'gpiod':
            self._setup_gpiod()
        elif GPIO_BACKEND in ('RPi.GPIO', 'rpi-lgpio'):
            self._setup_rpi_gpio()
    
    def _setup_gpiod(self):
        """使用 gpiod 設定 GPIO（支援 gpiod 2.x API）"""
        chip_paths = ['/dev/gpiochip4', '/dev/gpiochip0', 'gpiochip4', 'gpiochip0']
        chip = None
        chip_path_used = None
        
        for chip_path in chip_paths:
            try:
                chip = GPIO.Chip(chip_path)
                chip_path_used = chip_path
                logger.info(f"找到 GPIO chip: {chip_path}")
                break
            except Exception:
                continue
        
        if chip is None:
            raise RuntimeError("無法找到可用的 GPIO chip")
        
        self.chip = chip
        
        try:
            # gpiod 2.x API
            from gpiod.line import Direction, Bias
            
            # 創建 LineSettings
            line_settings = GPIO.LineSettings(
                direction=Direction.INPUT,
                bias=Bias.PULL_UP
            )
            
            # 創建配置字典 {offset: settings}
            config = {self.gpio_pin: line_settings}
            
            # 請求 GPIO lines
            self.gpio_line = self.chip.request_lines(
                consumer="GPIOButtonService",
                config=config
            )
            
            logger.info(f"GPIO{self.gpio_pin} 設定完成 (gpiod 2.x，使用 {chip_path_used})")
        except ImportError as e:
            logger.error(f"gpiod 模組導入失敗: {e}")
            raise RuntimeError("gpiod 2.x API 不可用，請安裝 rpi-lgpio")
        except Exception as e:
            logger.error(f"GPIO{self.gpio_pin} 設定失敗: {e}")
            raise
    
    def _setup_rpi_gpio(self):
        """使用 RPi.GPIO 或 rpi-lgpio 設定 GPIO"""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            logger.info(f"GPIO{self.gpio_pin} 設定完成 ({GPIO_BACKEND})")
        except RuntimeError as e:
            if "Cannot determine SOC peripheral base address" in str(e):
                raise RuntimeError("RPi.GPIO 不支援此 Raspberry Pi 版本，請安裝 rpi-lgpio")
            raise
    
    def _read_gpio(self) -> bool:
        """
        讀取 GPIO 狀態
        
        Returns:
            bool: True 表示按鈕按下（LOW），False 表示按鈕未按下（HIGH）
        """
        if self.simulation_mode:
            return False
        
        if GPIO_BACKEND == 'gpiod':
            try:
                # gpiod 2.x API: 使用 get_value(offset) 方法
                from gpiod.line import Value
                value = self.gpio_line.get_value(self.gpio_pin)
                # Value.INACTIVE = LOW (按下), Value.ACTIVE = HIGH (未按下)
                return value == Value.INACTIVE
            except ImportError:
                # 舊版 API 兼容
                try:
                    value = self.gpio_line.get_value(self.gpio_pin)
                    return value == 0
                except Exception:
                    return False
            except Exception as e:
                logger.debug(f"gpiod 讀取失敗: {e}")
                return False
        elif GPIO_BACKEND in ('RPi.GPIO', 'rpi-lgpio'):
            return GPIO.input(self.gpio_pin) == GPIO.LOW
        
        return False
    
    def _detect_click(self) -> bool:
        """
        偵測按鈕點擊（包含去彈跳處理）
        
        偵測流程：
        1. 等待按鈕按下（GPIO 變為 LOW）
        2. 等待去彈跳時間
        3. 確認按鈕仍然按下
        4. 等待按鈕釋放（GPIO 變為 HIGH）
        5. 再次等待去彈跳時間
        6. 確認按鈕已釋放
        7. 檢查按壓時間是否在合理範圍（0.1-5 秒）
        
        Returns:
            bool: True 表示偵測到一次有效點擊
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
            logger.info(f"偵測到按鈕點擊，按壓時間: {press_duration:.2f} 秒")
            return True
        
        return False
    
    def _run_loop(self):
        """背景線程執行的主循環"""
        logger.info("GPIO 按鈕監聽服務已啟動")
        
        if self.simulation_mode:
            # 模擬模式：定時觸發
            logger.info(f"模擬模式：每 {self.simulation_interval} 秒觸發一次")
            while self.running:
                time.sleep(self.simulation_interval)
                if self.running:
                    logger.info("模擬按鈕觸發")
                    self._notify_callbacks()
        else:
            # 真實 GPIO 模式：監聽按鈕點擊
            while self.running:
                if self._detect_click():
                    self._notify_callbacks()
                time.sleep(0.01)  # 10ms 檢查間隔
        
        logger.info("GPIO 按鈕監聽服務已停止")
    
    def _notify_callbacks(self):
        """通知所有已註冊的回調函數"""
        for callback in self.callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"回調函數執行錯誤: {e}")
    
    def on_click(self, callback: Callable[[], None]):
        """
        註冊按鈕點擊回調函數
        
        Args:
            callback: 當按鈕被點擊時要執行的函數（無參數）
        """
        if callback not in self.callbacks:
            self.callbacks.append(callback)
            logger.debug(f"已註冊回調函數: {callback.__name__}")
    
    def off_click(self, callback: Callable[[], None]):
        """
        移除按鈕點擊回調函數
        
        Args:
            callback: 要移除的回調函數
        """
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            logger.debug(f"已移除回調函數: {callback.__name__}")
    
    def start(self):
        """啟動 GPIO 按鈕監聽服務"""
        if self.running:
            logger.warning("服務已在運行中")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("GPIO 按鈕服務已啟動")
    
    def stop(self):
        """停止 GPIO 按鈕監聽服務"""
        if not self.running:
            return
        
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        
        self._cleanup()
        logger.info("GPIO 按鈕服務已停止")
    
    def _cleanup(self):
        """清理 GPIO 資源"""
        if GPIO_BACKEND == 'gpiod':
            if self.gpio_line:
                try:
                    # gpiod 2.x: LineRequest 物件會自動釋放，但可以顯式關閉
                    if hasattr(self.gpio_line, 'release'):
                        self.gpio_line.release()
                    elif hasattr(self.gpio_line, 'close'):
                        self.gpio_line.close()
                except Exception:
                    pass
                self.gpio_line = None
            if self.chip:
                try:
                    self.chip.close()
                except Exception:
                    pass
                self.chip = None
            logger.debug("GPIO 資源已釋放 (gpiod)")
        elif GPIO_BACKEND in ('RPi.GPIO', 'rpi-lgpio') and not self.simulation_mode:
            try:
                GPIO.cleanup(self.gpio_pin)
            except Exception:
                pass
            logger.debug(f"GPIO 資源已釋放 ({GPIO_BACKEND})")
    
    def is_running(self) -> bool:
        """檢查服務是否正在運行"""
        return self.running
    
    def get_status(self) -> dict:
        """
        獲取服務狀態
        
        Returns:
            dict: 包含服務狀態資訊
        """
        return {
            'running': self.running,
            'gpio_pin': self.gpio_pin,
            'simulation_mode': self.simulation_mode,
            'gpio_backend': GPIO_BACKEND if not self.simulation_mode else 'simulation',
            'gpio_available': GPIO_AVAILABLE,
            'callbacks_count': len(self.callbacks)
        }


# 全域服務實例（用於 Flask 應用）
_gpio_service: Optional[GPIOButtonService] = None


def get_gpio_service() -> Optional[GPIOButtonService]:
    """獲取全域 GPIO 服務實例"""
    return _gpio_service


def init_gpio_service(gpio_pin: int = 17, debounce_delay: float = 0.2,
                      simulation_mode: bool = False, simulation_interval: float = 10.0) -> GPIOButtonService:
    """
    初始化並返回全域 GPIO 服務實例
    
    Args:
        gpio_pin: GPIO 腳位編號
        debounce_delay: 去彈跳延遲時間
        simulation_mode: 是否啟用模擬模式
        simulation_interval: 模擬觸發間隔
        
    Returns:
        GPIOButtonService: GPIO 服務實例
    """
    global _gpio_service
    
    if _gpio_service is not None:
        _gpio_service.stop()
    
    _gpio_service = GPIOButtonService(
        gpio_pin=gpio_pin,
        debounce_delay=debounce_delay,
        simulation_mode=simulation_mode,
        simulation_interval=simulation_interval
    )
    
    return _gpio_service


def cleanup_gpio_service():
    """清理全域 GPIO 服務"""
    global _gpio_service
    
    if _gpio_service is not None:
        _gpio_service.stop()
        _gpio_service = None


if __name__ == "__main__":
    # 測試程式碼
    logging.basicConfig(level=logging.DEBUG)
    
    def test_callback():
        print(f"[{time.strftime('%H:%M:%S')}] 按鈕被點擊了！")
    
    # 創建服務（如果不在 Raspberry Pi 上，會自動使用模擬模式）
    service = GPIOButtonService(
        gpio_pin=17,
        debounce_delay=0.2,
        simulation_mode=False,  # 自動偵測
        simulation_interval=5.0
    )
    
    # 註冊回調
    service.on_click(test_callback)
    
    # 啟動服務
    service.start()
    
    print("GPIO 按鈕服務測試")
    print(f"狀態: {service.get_status()}")
    print("按 Ctrl+C 停止...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止...")
        service.stop()
        print("已停止")

