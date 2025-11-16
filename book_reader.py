#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
閱讀機器人主程式
功能：偵測 GPIO 觸發 -> 拍攝照片 -> OCR 辨識 -> 播放音檔
"""

import os
import sys
import time
import logging
import configparser
from datetime import datetime
from pathlib import Path

# 只使用 rpi-lgpio（RPi.GPIO 的 drop-in replacement）
GPIO_AVAILABLE = False
GPIO_BACKEND = None

# 修復 systemd 服務運行時的 lgpio 通知文件創建問題
# 當作為 systemd 服務運行時，當前工作目錄可能沒有寫入權限
# 解決方案：確保工作目錄是可寫入的
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

# 只嘗試 rpi-lgpio（RPi.GPIO 的 drop-in replacement）
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
    print("✅ 使用 rpi-lgpio 庫（Raspberry Pi 5 相容的 RPi.GPIO 替代方案）")
except (ImportError, RuntimeError, FileNotFoundError, OSError) as e:
    GPIO_AVAILABLE = False
    GPIO_BACKEND = None
    
    if "lgd-nfy" in str(e) or "No such file or directory" in str(e):
        print(f"⚠️  rpi-lgpio 初始化失敗: {e}")
        print("   這可能是因為當前目錄權限問題或環境設定")
    else:
        print(f"⚠️  rpi-lgpio 初始化失敗: {e}")
    
    print("\n請安裝 rpi-lgpio：")
    print("  pip install rpi-lgpio")
    print("  或: sudo apt-get install python3-rpi-lgpio")
    print("  sudo adduser $LOGNAME gpio")
    print("  sudo reboot")
    print("\n將使用模擬模式運行")
except Exception as e:
    GPIO_AVAILABLE = False
    GPIO_BACKEND = None
    print(f"❌ 錯誤: 無法初始化 rpi-lgpio 庫")
    print(f"   錯誤訊息: {e}")
    print("\n建議解決方案：")
    print("  1. 檢查 rpi-lgpio 權限: sudo adduser $LOGNAME gpio && sudo reboot")
    print("  2. 重新安裝 rpi-lgpio: pip install rpi-lgpio")
    print("\n將使用模擬模式運行")

import cv2
import requests
import pygame
from dotenv import load_dotenv
import threading
import numpy as np

# 嘗試匯入 PIL/Pillow 以支援中文文字顯示
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("警告: 無法匯入 PIL/Pillow，中文文字可能顯示為亂碼")
    print("請安裝: pip install Pillow")

# 載入 .env 環境變數
load_dotenv()

# 嘗試匯入 OpenAI Vision 服務
try:
    from openai_vision_service import OpenAIVisionService
    OPENAI_VISION_AVAILABLE = True
except ImportError as e:
    OPENAI_VISION_AVAILABLE = False
    print(f"警告: 無法匯入 OpenAI Vision 服務 ({e})")
    print("將跳過圖像預分析功能")


class BookReader:
    """閱讀機器人類別"""
    
    def __init__(self, config_file='config.ini'):
        """
        初始化閱讀機器人
        
        Args:
            config_file: 設定檔路徑
        """
        self.config = self._load_config(config_file)
        self._setup_logging()
        self._setup_gpio()
        self._setup_camera()
        self._setup_audio()
        self._setup_api()
        self._setup_openai_vision()
        self._create_directories()
        
        self.logger.info("閱讀機器人初始化完成")
        self.logger.info(f"API 伺服器: {self.api_url}")
        if not self.simulation_mode:
            self.logger.info(f"觸發 GPIO 腳位: {self.trigger_pin}")
    
    def _load_config(self, config_file):
        """
        載入設定檔
        
        Args:
            config_file: 設定檔路徑
            
        Returns:
            ConfigParser 物件
        """
        config = configparser.ConfigParser()
        
        if not os.path.exists(config_file):
            print(f"錯誤: 找不到設定檔 {config_file}")
            sys.exit(1)
        
        config.read(config_file, encoding='utf-8')
        return config
    
    def _setup_logging(self):
        """設定日誌系統"""
        log_level = self.config.get('LOGGING', 'log_level', fallback='INFO')
        log_file = self.config.get('LOGGING', 'log_file', fallback='logs/book_reader.log')
        console_output = self.config.getboolean('LOGGING', 'console_output', fallback=True)
        
        # 建立日誌目錄
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 設定日誌格式
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # 設定日誌處理器
        handlers = []
        
        # 檔案處理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)
        
        # 終端機處理器
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(log_format))
            handlers.append(console_handler)
        
        # 設定 logger
        self.logger = logging.getLogger('BookReader')
        self.logger.setLevel(getattr(logging, log_level))
        
        for handler in handlers:
            self.logger.addHandler(handler)
    
    def _setup_gpio(self):
        """設定 GPIO"""
        self.trigger_pin = self.config.getint('GPIO', 'trigger_pin', fallback=17)
        self.debounce_delay = self.config.getfloat('GPIO', 'debounce_delay', fallback=0.2)
        self.simulation_mode = self.config.getboolean('GPIO', 'simulation_mode', fallback=False)
        self.simulation_trigger_interval = self.config.getfloat('GPIO', 'simulation_trigger_interval', fallback=10)
        self.running = True  # 用於控制主循環
        
        # 檢查是否為模擬模式或 GPIO 不可用
        if not GPIO_AVAILABLE or self.simulation_mode:
            self.simulation_mode = True
            self.logger.warning("=" * 60)
            self.logger.warning("使用模擬模式運行（無 GPIO 硬體）")
            self.logger.warning(f"將每 {self.simulation_trigger_interval} 秒自動觸發一次")
            self.logger.warning("按 Ctrl+C 停止程式")
            self.logger.warning("=" * 60)
            return
        
        # 只使用 rpi-lgpio（RPi.GPIO 的 drop-in replacement）
        if GPIO_BACKEND == 'rpi-lgpio':
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            # 使用 PULL_UP：按鈕按下時 GPIO 變為 LOW
            GPIO.setup(self.trigger_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self.logger.info(f"GPIO 設定完成 (rpi-lgpio): 腳位 {self.trigger_pin}，使用 PULL_UP")
        else:
            raise RuntimeError(f"不支援的 GPIO 後端: {GPIO_BACKEND}，請確保使用 rpi-lgpio")
    
    def _setup_camera(self):
        """設定攝影機"""
        self.camera_device = self.config.getint('CAMERA', 'camera_device', fallback=0)
        self.frame_width = self.config.getint('CAMERA', 'frame_width', fallback=1280)
        self.frame_height = self.config.getint('CAMERA', 'frame_height', fallback=720)
        self.capture_delay = self.config.getfloat('CAMERA', 'capture_delay', fallback=0.5)
        self.save_captured_image = self.config.getboolean('CAMERA', 'save_captured_image', fallback=True)
        self.image_save_path = self.config.get('CAMERA', 'image_save_path', fallback='captured_images')
        self.show_preview = self.config.getboolean('CAMERA', 'show_preview', fallback=False)
        self.preview_window_name = self.config.get('CAMERA', 'preview_window_name', fallback='閱讀機器人 - 即時預覽')
        self.result_window_name = self.config.get('CAMERA', 'result_window_name', fallback='閱讀機器人 - 拍攝結果')
        self.preview_duration = self.config.getfloat('CAMERA', 'preview_duration', fallback=2.0)
        self.continuous_preview = self.config.getboolean('CAMERA', 'continuous_preview', fallback=True)
        self.result_display_duration = self.config.getfloat('CAMERA', 'result_display_duration', fallback=3.0)
        
        # 預覽相關變數
        self.preview_cap = None
        self.preview_active = False
        
        self.logger.info(f"攝影機設定完成: 裝置 {self.camera_device}, 解析度 {self.frame_width}x{self.frame_height}")
        if self.show_preview:
            if self.continuous_preview:
                self.logger.info(f"LCD 持續預覽已啟用")
            else:
                self.logger.info(f"LCD 預覽已啟用: 顯示時間 {self.preview_duration} 秒")
    
    def _setup_audio(self):
        """設定音訊系統"""
        pygame.mixer.init()
        
        self.success_sound = self.config.get('AUDIO', 'success_sound', fallback='voices/看完了1.mp3')
        self.error_sound = self.config.get('AUDIO', 'error_sound', fallback='voices/看不懂1.mp3')
        self.volume = self.config.getfloat('AUDIO', 'volume', fallback=1.0)
        
        # 檢查音檔是否存在
        if not os.path.exists(self.success_sound):
            self.logger.warning(f"找不到成功音檔: {self.success_sound}")
        
        if not os.path.exists(self.error_sound):
            self.logger.warning(f"找不到錯誤音檔: {self.error_sound}")
        
        self.logger.info(f"音訊系統初始化完成")
    
    def _create_directories(self):
        """建立必要的目錄"""
        if self.save_captured_image:
            os.makedirs(self.image_save_path, exist_ok=True)
    
    def _start_continuous_preview(self):
        """啟動持續預覽"""
        if not self.show_preview or not self.continuous_preview:
            return
        
        self.logger.info("啟動持續預覽視窗...")
        self.preview_cap = cv2.VideoCapture(self.camera_device)
        
        if not self.preview_cap.isOpened():
            self.logger.error("無法開啟預覽攝影機")
            self.preview_cap = None
            return
        
        self.preview_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.preview_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        
        cv2.namedWindow(self.preview_window_name, cv2.WINDOW_NORMAL)
        self.preview_active = True
        self.logger.info("持續預覽視窗已開啟")
    
    def _resize_frame_for_display(self, frame, scale=2.0):
        """
        將圖像放大用於顯示（不改變實際拍攝解析度）
        
        Args:
            frame: 原始圖像
            scale: 放大倍數（預設 2.0 倍）
            
        Returns:
            放大後的圖像
        """
        height, width = frame.shape[:2]
        new_width = int(width * scale)
        new_height = int(height * scale)
        return cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
    
    def _put_chinese_text(self, frame, text, position, font_scale=1.0, color=(0, 255, 0), thickness=2):
        """
        在 OpenCV 圖像上繪製中文文字（使用 PIL 支援中文）
        
        Args:
            frame: OpenCV 圖像（BGR 格式）
            text: 要顯示的文字（支援中文）
            position: 文字位置 (x, y)
            font_scale: 字體大小倍數
            color: 文字顏色 (B, G, R)
            thickness: 文字粗細
            
        Returns:
            繪製文字後的圖像
        """
        if not PIL_AVAILABLE:
            # 如果 PIL 不可用，使用 OpenCV 的 putText（可能顯示亂碼）
            cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
            return frame
        
        # 將 OpenCV 圖像轉換為 PIL 圖像
        # OpenCV 使用 BGR，PIL 使用 RGB
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        
        # 嘗試載入中文字體
        font_size = int(20 * font_scale)
        font = None
        
        # 嘗試多個常見的中文字體路徑
        font_paths = [
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',  # 文泉驛微米黑
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',     # 文泉驛正黑
            '/usr/share/fonts/truetype/arphic/uming.ttc',       # AR PL UMing
            '/usr/share/fonts/truetype/arphic/ukai.ttc',        # AR PL UKai
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',  # Noto Sans CJK
            '/System/Library/Fonts/PingFang.ttc',               # macOS
            'C:/Windows/Fonts/msyh.ttc',                        # Windows 微軟雅黑
            'C:/Windows/Fonts/simsun.ttc',                       # Windows 宋體
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except Exception:
                    continue
        
        # 如果找不到字體，使用預設字體（可能無法顯示中文）
        if font is None:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()
        
        # 繪製文字
        # PIL 使用 RGB，OpenCV 使用 BGR，所以需要轉換顏色
        rgb_color = (color[2], color[1], color[0])
        draw.text(position, text, font=font, fill=rgb_color)
        
        # 將 PIL 圖像轉換回 OpenCV 格式
        frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        
        return frame
    
    def _update_preview(self, status_text=None):
        """
        更新預覽視窗
        
        Args:
            status_text: 可選的狀態文字，若為 None 則顯示預設文字
        """
        if not self.preview_active or self.preview_cap is None:
            return
        
        ret, frame = self.preview_cap.read()
        if ret:
            # 在預覽畫面上顯示狀態文字
            display_frame = frame.copy()
            text = status_text if status_text else "Live Preview - Waiting"
            # 放大文字大小以配合放大後的視窗
            font_scale = 2.0
            thickness = 4
            # 使用 OpenCV 的 putText（英文顯示）
            cv2.putText(display_frame, text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness)
            # 將圖像放大二倍用於顯示
            display_frame = self._resize_frame_for_display(display_frame, scale=2.0)
            cv2.imshow(self.preview_window_name, display_frame)
            cv2.waitKey(1)
    
    def _stop_continuous_preview(self):
        """停止持續預覽"""
        if self.preview_cap is not None:
            self.preview_cap.release()
            self.preview_cap = None
        
        if self.preview_active:
            cv2.destroyWindow(self.preview_window_name)
            self.preview_active = False
            self.logger.info("持續預覽視窗已關閉")
    
    def _read_gpio(self):
        """
        讀取 GPIO 狀態
        
        Returns:
            bool: True 表示按鈕按下（LOW），False 表示按鈕未按下（HIGH）
        """
        if GPIO_BACKEND == 'rpi-lgpio':
            # rpi-lgpio: GPIO.LOW = 按下, GPIO.HIGH = 未按下
            # 因為我們使用 PULL_UP，按下時會是 LOW
            return GPIO.input(self.trigger_pin) == GPIO.LOW
        return False
    
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
    
    def _processing_worker(self, frame, custom_prompt, result_dict):
        """
        在背景線程中執行 OpenAI 預分析和 OCR 處理
        
        Args:
            frame: 要處理的影像
            custom_prompt: 已經生成的自訂 prompt（若有 OpenAI 預分析）
            result_dict: 共享字典，用於傳遞結果回主線程
                - 'status': 當前狀態 ('openai_analysis', 'ocr_processing', 'completed', 'error')
                - 'ocr_text': OCR 辨識結果
                - 'error': 錯誤訊息
                - 'error_type': 錯誤類型
        """
        from requests.exceptions import Timeout, ConnectionError, RequestException
        
        try:
            # 步驟 1: OpenAI 預分析（如果啟用且尚未執行）
            if self.enable_preanalysis and self.openai_service and custom_prompt is None:
                result_dict['status'] = 'openai_analysis'
                self.logger.info("=" * 60)
                self.logger.info("步驟 2A: OpenAI 圖像預分析")
                self.logger.info("=" * 60)
                
                # 將 frame 編碼為 JPEG bytes
                _, img_encoded = cv2.imencode('.jpg', frame)
                image_data = img_encoded.tobytes()
                
                # 執行預分析
                should_perform_ocr, result = self.openai_service.should_perform_ocr(image_data)
                
                if should_perform_ocr:
                    # 有文字，使用建議的 prompt
                    custom_prompt = result
                    self.logger.info(f"✅ 圖像包含文字，將執行 OCR")
                    self.logger.info(f"   建議的 Prompt: {custom_prompt}")
                else:
                    # 沒有文字，跳過 OCR
                    skip_reason = result
                    self.logger.info(f"❌ 圖像不包含文字，跳過 OCR")
                    self.logger.info(f"   原因: {skip_reason}")
                    result_dict['status'] = 'skipped'
                    result_dict['skip_reason'] = skip_reason
                    return
            
            # 步驟 2: 執行 DeepSeek-OCR 辨識
            result_dict['status'] = 'ocr_processing'
            self.logger.info("=" * 60)
            self.logger.info("步驟 2B: 執行 DeepSeek-OCR 辨識")
            self.logger.info("=" * 60)
            
            text = self.send_to_ocr_api(frame, custom_prompt=custom_prompt)
            
            if text is not None:
                result_dict['ocr_text'] = text
                result_dict['status'] = 'completed'
            else:
                result_dict['status'] = 'error'
                result_dict['error'] = 'OCR API 返回 None'
                result_dict['error_type'] = 'OCRError'
        
        except Timeout as timeout_err:
            result_dict['status'] = 'error'
            result_dict['error'] = str(timeout_err)
            result_dict['error_type'] = 'Timeout'
            self.logger.error(f"======== OCR API 請求超時 ========")
            self.logger.error(f"超時設定: {self.request_timeout} 秒")
            self.logger.error(f"錯誤訊息: {str(timeout_err)}")
            self.logger.error(f"建議: 增加 config.ini 中的 request_timeout 設定")
            self.logger.error(f"================================")
        except ConnectionError as conn_err:
            result_dict['status'] = 'error'
            result_dict['error'] = str(conn_err)
            result_dict['error_type'] = 'ConnectionError'
            self.logger.error(f"======== OCR API 連線錯誤 ========")
            self.logger.error(f"API 位址: {self.api_url}")
            self.logger.error(f"錯誤訊息: {str(conn_err)}")
            self.logger.error(f"================================")
        except RequestException as req_err:
            result_dict['status'] = 'error'
            result_dict['error'] = str(req_err)
            result_dict['error_type'] = 'RequestException'
            self.logger.error(f"======== OCR API 請求錯誤 ========")
            self.logger.error(f"錯誤訊息: {str(req_err)}")
            self.logger.error(f"================================")
        except Exception as general_err:
            result_dict['status'] = 'error'
            result_dict['error'] = str(general_err)
            result_dict['error_type'] = type(general_err).__name__
            self.logger.error(f"======== 處理錯誤 ========")
            self.logger.error(f"錯誤類型: {type(general_err).__name__}")
            self.logger.error(f"錯誤訊息: {str(general_err)}")
            self.logger.error(f"========================")
            import traceback
            self.logger.error(f"錯誤詳情:\n{traceback.format_exc()}")
    
    def _setup_api(self):
        """設定 API 相關參數"""
        api_url = self.config.get('API', 'api_url', fallback='http://172.30.19.20:5000')
        ocr_endpoint = self.config.get('API', 'ocr_endpoint', fallback='/ocr')
        self.api_url = api_url.rstrip('/') + ocr_endpoint
        self.request_timeout = self.config.getint('API', 'request_timeout', fallback=30)
        self.ocr_prompt = self.config.get('OCR', 'prompt', fallback='<image>\\nFree OCR.')
    
    def _setup_openai_vision(self):
        """設定 OpenAI Vision 圖像預分析功能"""
        # 檢查是否啟用預分析功能
        self.enable_preanalysis = self.config.getboolean('OPENAI', 'enable_preanalysis', fallback=False)
        
        self.openai_service = None
        
        if not self.enable_preanalysis:
            self.logger.info("OpenAI 圖像預分析功能已停用")
            return
        
        if not OPENAI_VISION_AVAILABLE:
            self.logger.warning("OpenAI Vision 服務不可用，已停用預分析功能")
            self.enable_preanalysis = False
            return
        
        # 初始化 OpenAI Vision 服務
        openai_api_key = os.getenv('OPENAI_API_KEY')
        openai_model = self.config.get('OPENAI', 'model', fallback='gpt-4o-mini')
        
        if not openai_api_key:
            self.logger.warning("未設定 OPENAI_API_KEY，已停用預分析功能")
            self.logger.warning("請在 .env 檔案中設定 OPENAI_API_KEY")
            self.enable_preanalysis = False
            return
        
        self.openai_service = OpenAIVisionService(
            api_key=openai_api_key,
            model=openai_model
        )
        
        self.logger.info("=" * 60)
        self.logger.info("✅ OpenAI 圖像預分析功能已啟用")
        self.logger.info(f"   模型: {openai_model}")
        self.logger.info("   流程: 圖像 → OpenAI 分析 → 判斷是否有文字 → OCR")
        self.logger.info("=" * 60)
    
    def capture_frame(self):
        """
        從 USB Camera 拍攝一張照片
        
        Returns:
            拍攝的影像（numpy array），若失敗則回傳 None
        """
        self.logger.info("開始拍攝照片...")
        
        # 如果使用持續預覽，直接從預覽攝影機拍攝
        if self.continuous_preview and self.preview_cap is not None:
            # 在預覽視窗顯示拍照倒數
            for i in range(int(self.preview_duration * 10)):
                ret, frame = self.preview_cap.read()
                if ret:
                    display_frame = frame.copy()
                    remaining = self.preview_duration - (i * 0.1)
                    text = f"Capture in: {remaining:.1f}s"
                    # 放大文字大小以配合放大後的視窗
                    font_scale = 2.0
                    thickness = 4
                    # 使用 OpenCV 的 putText（英文顯示）
                    cv2.putText(display_frame, text, (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness)
                    # 將圖像放大二倍用於顯示
                    display_frame = self._resize_frame_for_display(display_frame, scale=2.0)
                    cv2.imshow(self.preview_window_name, display_frame)
                    cv2.waitKey(100)
            
            # 拍攝最終照片
            ret, frame = self.preview_cap.read()
            
            if not ret:
                self.logger.error("無法從預覽攝影機讀取影像")
                return None
            
            self.logger.info(f"成功拍攝照片，解析度: {frame.shape[1]}x{frame.shape[0]}")
            
            # 在結果視窗顯示拍攝的照片
            cv2.namedWindow(self.result_window_name, cv2.WINDOW_NORMAL)
            result_frame = frame.copy()
            text = "Captured! Processing..."
            # 放大文字大小以配合放大後的視窗
            font_scale = 2.0
            thickness = 4
            # 使用 OpenCV 的 putText（英文顯示）
            cv2.putText(result_frame, text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness)
            # 將圖像放大二倍用於顯示
            result_frame = self._resize_frame_for_display(result_frame, scale=2.0)
            cv2.imshow(self.result_window_name, result_frame)
            cv2.waitKey(int(self.result_display_duration * 1000))
            
            # 儲存拍攝的圖片（用於除錯）
            if self.save_captured_image:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                image_path = os.path.join(self.image_save_path, f"capture_{timestamp}.jpg")
                cv2.imwrite(image_path, frame)
                self.logger.info(f"照片已儲存至: {image_path}")
            
            return frame
        
        # 非持續預覽模式：原有邏輯
        cap = None
        frame = None
        
        # 開啟攝影機
        cap = cv2.VideoCapture(self.camera_device)
        
        if not cap.isOpened():
            self.logger.error(f"無法開啟攝影機裝置 {self.camera_device}")
            return None
        
        # 設定解析度
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        
        # 如果啟用預覽，顯示即時畫面
        if self.show_preview:
            self.logger.info("顯示攝影機預覽...")
            cv2.namedWindow(self.preview_window_name, cv2.WINDOW_NORMAL)
            
            # 預覽模式
            if self.preview_duration > 0:
                # 顯示指定時間後自動拍照
                start_time = time.time()
                while time.time() - start_time < self.preview_duration:
                    ret, preview_frame = cap.read()
                    if ret:
                        # 在畫面上顯示倒數計時
                        remaining = self.preview_duration - (time.time() - start_time)
                        text = f"Capture in: {remaining:.1f}s"
                        # 放大文字大小以配合放大後的視窗
                        font_scale = 2.0
                        thickness = 4
                        # 使用 OpenCV 的 putText（英文顯示）
                        cv2.putText(preview_frame, text, (10, 30), 
                                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness)
                        # 將圖像放大二倍用於顯示
                        preview_frame = self._resize_frame_for_display(preview_frame, scale=2.0)
                        cv2.imshow(self.preview_window_name, preview_frame)
                        cv2.waitKey(1)
                self.logger.info("預覽時間結束，開始拍照")
            else:
                # 持續顯示直到按下任意鍵
                self.logger.info("顯示預覽畫面，按任意鍵拍照...")
                while True:
                    ret, preview_frame = cap.read()
                    if ret:
                        # 顯示提示文字
                        text = "Press any key to capture"
                        # 放大文字大小以配合放大後的視窗
                        font_scale = 2.0
                        thickness = 4
                        # 使用 OpenCV 的 putText（英文顯示）
                        cv2.putText(preview_frame, text, (10, 30), 
                                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness)
                        # 將圖像放大二倍用於顯示
                        preview_frame = self._resize_frame_for_display(preview_frame, scale=2.0)
                        cv2.imshow(self.preview_window_name, preview_frame)
                        if cv2.waitKey(1) != -1:  # 如果有按鍵
                            break
                self.logger.info("偵測到按鍵，開始拍照")
        else:
            # 等待攝影機穩定（無預覽模式）
            time.sleep(self.capture_delay)
        
        # 讀取最終影像
        ret, frame = cap.read()
        
        if not ret:
            self.logger.error("無法從攝影機讀取影像")
            cap.release()
            if self.show_preview:
                cv2.destroyWindow(self.preview_window_name)
            return None
        
        self.logger.info(f"成功拍攝照片，解析度: {frame.shape[1]}x{frame.shape[0]}")
        
        # 如果有預覽，顯示拍攝結果 1 秒
        if self.show_preview:
            result_frame = frame.copy()
            text = "Captured!"
            # 放大文字大小以配合放大後的視窗
            font_scale = 2.0
            thickness = 4
            # 使用 OpenCV 的 putText（英文顯示）
            cv2.putText(result_frame, text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness)
            # 將圖像放大二倍用於顯示
            result_frame = self._resize_frame_for_display(result_frame, scale=2.0)
            cv2.imshow(self.preview_window_name, result_frame)
            cv2.waitKey(1000)
            cv2.destroyWindow(self.preview_window_name)
        
        # 儲存拍攝的圖片（用於除錯）
        if self.save_captured_image:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = os.path.join(self.image_save_path, f"capture_{timestamp}.jpg")
            cv2.imwrite(image_path, frame)
            self.logger.info(f"照片已儲存至: {image_path}")
        
        # 釋放攝影機
        cap.release()
        
        return frame
    
    def send_to_ocr_api(self, frame, custom_prompt=None):
        """
        將影像送到 DeepSeek-OCR API 進行辨識
        
        Args:
            frame: 要辨識的影像（numpy array）
            custom_prompt: 自訂的 OCR prompt，若為 None 則使用設定檔中的預設 prompt
            
        Returns:
            辨識結果文字，若失敗則回傳 None
        """
        self.logger.info("準備將照片送至 OCR API...")
        
        # 將影像編碼為 JPEG 格式
        _, img_encoded = cv2.imencode('.jpg', frame)
        
        # 準備檔案
        files = {
            'file': ('image.jpg', img_encoded.tobytes(), 'image/jpeg')
        }
        
        # 準備提示詞（優先使用 custom_prompt，否則使用設定檔中的 prompt）
        data = {}
        prompt_to_use = custom_prompt if custom_prompt else self.ocr_prompt
        if prompt_to_use:
            data['prompt'] = prompt_to_use
            self.logger.info(f"使用 Prompt: {prompt_to_use}")
        
        # 發送請求（加上完整的錯誤處理）
        self.logger.info(f"發送請求至: {self.api_url}")
        self.logger.info(f"超時設定: {self.request_timeout} 秒")
        
        from requests.exceptions import Timeout, ConnectionError, RequestException
        
        response = requests.post(
            self.api_url,
            files=files,
            data=data,
            timeout=self.request_timeout
        )
        
        # 檢查回應
        if response.status_code == 200:
            result = response.json()
            text = result.get('text', '')
            self.logger.info(f"OCR 辨識成功，文字長度: {len(text)} 字元")
            return text
        else:
            error_msg = response.json().get('error', '未知錯誤')
            self.logger.error(f"======== OCR API 錯誤 ========")
            self.logger.error(f"HTTP 狀態碼: {response.status_code}")
            self.logger.error(f"錯誤訊息: {error_msg}")
            self.logger.error(f"============================")
            return None
    
    def play_sound(self, sound_path):
        """
        播放音檔
        
        Args:
            sound_path: 音檔路徑
        """
        if not os.path.exists(sound_path):
            self.logger.error(f"找不到音檔: {sound_path}")
            return
        
        self.logger.info(f"播放音檔: {sound_path}")
        
        pygame.mixer.music.load(sound_path)
        pygame.mixer.music.set_volume(self.volume)
        pygame.mixer.music.play()
        
        # 等待播放完成
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        
        self.logger.info("音檔播放完成")
    
    def process_trigger(self):
        """處理一次觸發事件"""
        self.logger.info("=" * 60)
        self.logger.info("偵測到觸發信號，開始處理...")
        
        # 1. 拍攝照片
        frame = self.capture_frame()
        
        if frame is None:
            self.logger.error("拍攝照片失敗，播放錯誤音檔")
            self.play_sound(self.error_sound)
            return
        
        # 2. 啟動背景線程執行 OpenAI 預分析和 OCR 處理
        result_dict = {
            'status': 'starting',
            'ocr_text': None,
            'error': None,
            'error_type': None,
            'skip_reason': None
        }
        
        processing_thread = threading.Thread(
            target=self._processing_worker,
            args=(frame, None, result_dict)
        )
        processing_thread.daemon = True
        processing_thread.start()
        
        # 3. 在主線程中持續更新預覽視窗，直到背景處理完成
        status_text_map = {
            'starting': 'Live Preview - Preparing...',
            'openai_analysis': 'Live Preview - AI Analyzing...',
            'ocr_processing': 'Live Preview - OCR Processing...',
            'completed': 'Live Preview - Completed',
            'error': 'Live Preview - Error',
            'skipped': 'Live Preview - Skipped'
        }
        
        while processing_thread.is_alive():
            current_status = result_dict.get('status', 'starting')
            status_text = status_text_map.get(current_status, 'Live Preview - Processing...')
            self._update_preview(status_text)
            time.sleep(0.03)  # 約 30 FPS
        
        # 等待背景線程結束
        processing_thread.join(timeout=1.0)
        
        # 4. 根據處理結果播放音檔
        final_status = result_dict.get('status')
        
        if final_status == 'skipped':
            # 圖像不包含文字，跳過 OCR
            self.logger.info("圖像不包含文字，靜默跳過")
            return
        
        elif final_status == 'completed':
            # 成功取得辨識結果
            text = result_dict.get('ocr_text')
            if text and text.strip():
                self.logger.info("=" * 60)
                self.logger.info("辨識結果:")
                self.logger.info(text)
                self.logger.info("=" * 60)
                
                print("\n" + "=" * 60)
                print("辨識結果:")
                print(text)
                print("=" * 60 + "\n")
                
                self.play_sound(self.success_sound)
            else:
                # 辨識結果為空
                self.logger.warning("OCR 辨識結果為空，播放錯誤音檔")
                self.play_sound(self.error_sound)
        
        elif final_status == 'error':
            # 發生錯誤
            error_type = result_dict.get('error_type', 'Unknown')
            error_msg = result_dict.get('error', '未知錯誤')
            self.logger.error(f"處理失敗: {error_type} - {error_msg}")
            self.play_sound(self.error_sound)
        
        else:
            # 未知狀態
            self.logger.warning(f"未知的處理狀態: {final_status}")
            self.play_sound(self.error_sound)
    
    def run(self):
        """主迴圈：持續監聽 GPIO 並處理觸發事件"""
        self.logger.info("閱讀機器人開始運行...")
        
        if self.simulation_mode:
            # 模擬模式
            print("\n" + "=" * 60)
            print("閱讀機器人已啟動（模擬模式）")
            print(f"將每 {self.simulation_trigger_interval} 秒自動觸發一次")
            print("在此模式下，您可以測試攝影機和 API 連線")
            print("按 Ctrl+C 停止程式")
            print("=" * 60 + "\n")
            
            # 啟動持續預覽
            self._start_continuous_preview()
            
            # 模擬模式主迴圈
            while True:
                self.logger.info(f"模擬觸發（等待 {self.simulation_trigger_interval} 秒）...")
                
                # 在等待期間持續更新預覽
                start_time = time.time()
                while time.time() - start_time < self.simulation_trigger_interval:
                    self._update_preview()
                    time.sleep(0.03)  # 約 30 FPS
                
                # 處理觸發事件
                self.process_trigger()
        else:
            # 真實 GPIO 模式（使用按鈕點擊偵測）
            self.logger.info(f"等待 GPIO{self.trigger_pin} 按鈕點擊...")
            
            print("\n" + "=" * 60)
            print("閱讀機器人已啟動")
            print(f"等待 GPIO{self.trigger_pin} 按鈕點擊...")
            print("按 Ctrl+C 停止程式")
            print("=" * 60 + "\n")
            
            # 啟動持續預覽
            self._start_continuous_preview()
            
            click_count = 0
            
            try:
                while self.running:
                    # 更新預覽
                    self._update_preview()
                    
                    # 偵測按鈕點擊
                    if self._detect_click():
                        click_count += 1
                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                        self.logger.info(f"[{timestamp}] 偵測到按鈕點擊（總計: {click_count} 次）")
                        
                        # 處理觸發事件
                        self.process_trigger()
                    
                    # 短暫延遲，避免 CPU 佔用過高
                    time.sleep(0.01)
            
            except KeyboardInterrupt:
                print("\n\n" + "=" * 60)
                print("收到中斷信號，正在停止...")
                print(f"總共偵測到 {click_count} 次點擊")
                print("=" * 60)
                self.running = False
    
    def cleanup(self):
        """清理資源"""
        self.logger.info("正在清理資源...")
        self.running = False
        
        # 停止持續預覽
        self._stop_continuous_preview()
        
        if GPIO_AVAILABLE and not self.simulation_mode:
            if GPIO_BACKEND == 'rpi-lgpio':
                # 清理 rpi-lgpio
                GPIO.cleanup()
                self.logger.info("✅ GPIO 資源已釋放（rpi-lgpio）")
        
        pygame.mixer.quit()
        cv2.destroyAllWindows()
        
        self.logger.info("資源清理完成")


def main():
    """主函數"""
    reader = None
    
    try:
        # 建立閱讀機器人實例
        reader = BookReader()
        
        # 執行主迴圈
        reader.run()
    except KeyboardInterrupt:
        print("\n收到中斷信號，正在停止...")
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 確保清理資源
        if reader is not None:
            reader.cleanup()


if __name__ == '__main__':
    main()

