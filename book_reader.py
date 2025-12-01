#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
閱讀機器人主程式（CLI 版本）
功能：偵測 GPIO 觸發 -> 拍攝照片 -> OCR 辨識 -> 播放音檔

使用方式：
    python book_reader.py

按下 GPIO17 按鈕（按下→釋放）觸發拍照和 OCR 辨識
"""

import os
import sys
import time
import logging
import configparser
from datetime import datetime
from pathlib import Path

import cv2
import requests
import numpy as np
from dotenv import load_dotenv

# 取得腳本所在目錄
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 載入 .env 環境變數
load_dotenv(os.path.join(SCRIPT_DIR, '.env'))

# 嘗試匯入 GPIO 按鈕服務
try:
    from gpio_button_service import GPIOButtonService, GPIO_AVAILABLE, GPIO_BACKEND
    GPIO_SERVICE_AVAILABLE = True
except ImportError as e:
    GPIO_SERVICE_AVAILABLE = False
    GPIO_AVAILABLE = False
    GPIO_BACKEND = None
    print(f"警告: 無法匯入 GPIO 按鈕服務 ({e})")
    print("將使用模擬模式運行")

# 嘗試匯入 pygame（音檔播放）
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("警告: 無法匯入 pygame，音檔播放功能將不可用")

# 嘗試匯入 PIL/Pillow 以支援中文文字顯示
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("警告: 無法匯入 PIL/Pillow，中文文字可能顯示為亂碼")

# 嘗試匯入 OpenAI Vision 服務
try:
    from openai_vision_service import OpenAIVisionService
    OPENAI_VISION_AVAILABLE = True
except ImportError as e:
    OPENAI_VISION_AVAILABLE = False
    print(f"警告: 無法匯入 OpenAI Vision 服務 ({e})")
    print("將跳過圖像預分析功能")


class BookReader:
    """閱讀機器人類別（CLI 版本，使用 GPIO 按鈕觸發）"""
    
    def __init__(self, config_file='config.ini'):
        """
        初始化閱讀機器人
        
        Args:
            config_file: 設定檔路徑
        """
        # 如果 config_file 不是絕對路徑，則相對於腳本目錄
        if not os.path.isabs(config_file):
            config_file = os.path.join(SCRIPT_DIR, config_file)
        
        self.config = self._load_config(config_file)
        self._setup_logging()
        self._setup_camera()
        self._setup_audio()
        self._setup_api()
        self._setup_openai_vision()
        self._setup_gpio()
        self._create_directories()
        
        self.running = True
        self.trigger_pending = False  # 待處理的觸發事件標誌
        
        self.logger.info("閱讀機器人初始化完成")
        self.logger.info(f"API 伺服器: {self.api_url}")
        if self.gpio_service:
            self.logger.info(f"GPIO 模式: {self.gpio_service.get_status()}")
    
    def _load_config(self, config_file):
        """載入設定檔"""
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
        
        # 如果日誌檔案路徑是相對路徑，則相對於腳本目錄
        if not os.path.isabs(log_file):
            log_file = os.path.join(SCRIPT_DIR, log_file)
        
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
    
    def _setup_camera(self):
        """設定攝影機"""
        self.camera_device = self.config.getint('CAMERA', 'camera_device', fallback=0)
        self.frame_width = self.config.getint('CAMERA', 'frame_width', fallback=1280)
        self.frame_height = self.config.getint('CAMERA', 'frame_height', fallback=720)
        self.capture_delay = self.config.getfloat('CAMERA', 'capture_delay', fallback=0.5)
        self.save_captured_image = self.config.getboolean('CAMERA', 'save_captured_image', fallback=True)
        self.image_save_path = self.config.get('CAMERA', 'image_save_path', fallback='captured_images')
        self.show_preview = self.config.getboolean('CAMERA', 'show_preview', fallback=False)
        self.preview_window_name = self.config.get('CAMERA', 'preview_window_name', fallback='Book Reader - Preview')
        self.result_window_name = self.config.get('CAMERA', 'result_window_name', fallback='Book Reader - Result')
        self.preview_duration = self.config.getfloat('CAMERA', 'preview_duration', fallback=2.0)
        self.continuous_preview = self.config.getboolean('CAMERA', 'continuous_preview', fallback=True)
        self.result_display_duration = self.config.getfloat('CAMERA', 'result_display_duration', fallback=3.0)
        
        # 如果圖片儲存路徑是相對路徑，則相對於腳本目錄
        if not os.path.isabs(self.image_save_path):
            self.image_save_path = os.path.join(SCRIPT_DIR, self.image_save_path)
        
        # 預覽相關變數
        self.preview_cap = None
        self.preview_active = False
        
        self.logger.info(f"攝影機設定完成: 裝置 {self.camera_device}, 解析度 {self.frame_width}x{self.frame_height}")
    
    def _setup_audio(self):
        """設定音訊系統"""
        if not PYGAME_AVAILABLE:
            self.success_sound = None
            self.error_sound = None
            self.volume = 1.0
            self.logger.warning("pygame 不可用，音檔播放功能已停用")
            return
        
        pygame.mixer.init()
        
        success_sound = self.config.get('AUDIO', 'success_sound', fallback='voices/看完了1.mp3')
        error_sound = self.config.get('AUDIO', 'error_sound', fallback='voices/看不懂1.mp3')
        self.volume = self.config.getfloat('AUDIO', 'volume', fallback=1.0)
        
        # 轉為絕對路徑
        if not os.path.isabs(success_sound):
            success_sound = os.path.join(SCRIPT_DIR, success_sound)
        if not os.path.isabs(error_sound):
            error_sound = os.path.join(SCRIPT_DIR, error_sound)
        
        self.success_sound = success_sound if os.path.exists(success_sound) else None
        self.error_sound = error_sound if os.path.exists(error_sound) else None
        
        if not self.success_sound:
            self.logger.warning(f"找不到成功音檔: {success_sound}")
        if not self.error_sound:
            self.logger.warning(f"找不到錯誤音檔: {error_sound}")
        
        self.logger.info("音訊系統初始化完成")
    
    def _setup_api(self):
        """設定 API 相關參數"""
        api_url = self.config.get('API', 'api_url', fallback='http://172.30.19.20:5000')
        ocr_endpoint = self.config.get('API', 'ocr_endpoint', fallback='/ocr')
        self.api_url = api_url.rstrip('/') + ocr_endpoint
        self.request_timeout = self.config.getint('API', 'request_timeout', fallback=30)
        self.ocr_prompt = self.config.get('OCR', 'prompt', fallback='<image>\\nFree OCR.')
    
    def _setup_openai_vision(self):
        """設定 OpenAI Vision 圖像預分析功能"""
        self.enable_preanalysis = self.config.getboolean('OPENAI', 'enable_preanalysis', fallback=False)
        self.openai_service = None
        
        if not self.enable_preanalysis:
            self.logger.info("OpenAI 圖像預分析功能已停用")
            return
        
        if not OPENAI_VISION_AVAILABLE:
            self.logger.warning("OpenAI Vision 服務不可用，已停用預分析功能")
            self.enable_preanalysis = False
            return
        
        openai_api_key = os.getenv('OPENAI_API_KEY')
        openai_model = self.config.get('OPENAI', 'model', fallback='gpt-4o-mini')
        
        if not openai_api_key:
            self.logger.warning("未設定 OPENAI_API_KEY，已停用預分析功能")
            self.enable_preanalysis = False
            return
        
        self.openai_service = OpenAIVisionService(
            api_key=openai_api_key,
            model=openai_model
        )
        
        self.logger.info("✅ OpenAI 圖像預分析功能已啟用")
    
    def _setup_gpio(self):
        """設定 GPIO 按鈕服務"""
        self.gpio_service = None
        
        if not GPIO_SERVICE_AVAILABLE:
            self.logger.warning("GPIO 服務不可用，將使用模擬模式")
            self._setup_simulation_mode()
            return
        
        # 讀取 GPIO 設定
        gpio_pin = self.config.getint('GPIO', 'trigger_pin', fallback=17)
        debounce_delay = self.config.getfloat('GPIO', 'debounce_delay', fallback=0.2)
        simulation_mode = self.config.getboolean('GPIO', 'simulation_mode', fallback=False)
        simulation_interval = self.config.getfloat('GPIO', 'simulation_trigger_interval', fallback=10.0)
        
        # 創建 GPIO 服務
        self.gpio_service = GPIOButtonService(
            gpio_pin=gpio_pin,
            debounce_delay=debounce_delay,
            simulation_mode=simulation_mode,
            simulation_interval=simulation_interval
        )
        
        # 註冊按鈕點擊回調
        self.gpio_service.on_click(self._on_button_click)
        
        mode_str = "模擬模式" if simulation_mode else "GPIO 模式"
        self.logger.info(f"✅ GPIO 按鈕服務已啟用 (GPIO{gpio_pin}, {mode_str})")
    
    def _setup_simulation_mode(self):
        """設定模擬模式（無 GPIO 硬體時）"""
        simulation_interval = self.config.getfloat('GPIO', 'simulation_trigger_interval', fallback=10.0)
        
        if GPIO_SERVICE_AVAILABLE:
            self.gpio_service = GPIOButtonService(
                gpio_pin=17,
                simulation_mode=True,
                simulation_interval=simulation_interval
            )
            self.gpio_service.on_click(self._on_button_click)
            self.logger.info(f"使用模擬模式（每 {simulation_interval} 秒觸發一次）")
        else:
            self.gpio_service = None
            self.logger.warning("GPIO 服務不可用，無法啟動模擬模式")
    
    def _create_directories(self):
        """建立必要的目錄"""
        if self.save_captured_image:
            os.makedirs(self.image_save_path, exist_ok=True)
    
    def _on_button_click(self):
        """GPIO 按鈕點擊回調函數（在背景線程中執行）"""
        self.logger.info("🔘 偵測到 GPIO 按鈕點擊！")
        # 設置標誌，讓主線程處理（避免線程衝突）
        self.trigger_pending = True
    
    def _start_preview(self):
        """啟動相機預覽"""
        if not self.show_preview or not self.continuous_preview:
            return
        
        self.logger.info("啟動相機預覽...")
        self.preview_cap = cv2.VideoCapture(self.camera_device)
        
        if not self.preview_cap.isOpened():
            self.logger.error("無法開啟相機進行預覽")
            self.preview_cap = None
            return
        
        self.preview_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.preview_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        
        cv2.namedWindow(self.preview_window_name, cv2.WINDOW_NORMAL)
        self.preview_active = True
        self.logger.info("相機預覽已啟動")
    
    def _update_preview(self, status_text="Waiting for button..."):
        """更新預覽視窗"""
        if not self.preview_active or self.preview_cap is None:
            return
        
        ret, frame = self.preview_cap.read()
        if ret:
            display_frame = frame.copy()
            cv2.putText(display_frame, status_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            cv2.imshow(self.preview_window_name, display_frame)
            cv2.waitKey(1)
    
    def _stop_preview(self):
        """停止相機預覽"""
        if self.preview_cap is not None:
            self.preview_cap.release()
            self.preview_cap = None
        
        if self.preview_active:
            cv2.destroyWindow(self.preview_window_name)
            self.preview_active = False
            self.logger.info("相機預覽已停止")
    
    def capture_frame(self):
        """
        從 USB Camera 拍攝一張照片
        
        Returns:
            拍攝的影像（numpy array），若失敗則回傳 None
        """
        self.logger.info("開始拍攝照片...")
        
        # 如果使用持續預覽，直接從預覽攝影機拍攝
        if self.continuous_preview and self.preview_cap is not None:
            self.logger.info("從預覽攝影機拍攝...")
            ret, frame = self.preview_cap.read()
            if not ret:
                self.logger.error("無法從預覽攝影機讀取影像")
                return None
            self.logger.info("從預覽攝影機拍攝成功")
        else:
            # 開啟新的攝影機連接
            cap = cv2.VideoCapture(self.camera_device)
            if not cap.isOpened():
                self.logger.error(f"無法開啟攝影機裝置 {self.camera_device}")
                return None
            
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
            time.sleep(self.capture_delay)
            
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                self.logger.error("無法從攝影機讀取影像")
                return None
        
        self.logger.info(f"成功拍攝照片，解析度: {frame.shape[1]}x{frame.shape[0]}")
        
        # 儲存拍攝的圖片
        if self.save_captured_image:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = os.path.join(self.image_save_path, f"capture_{timestamp}.jpg")
            cv2.imwrite(image_path, frame)
            self.logger.info(f"照片已儲存至: {image_path}")
        
        return frame
    
    def send_to_ocr_api(self, frame, custom_prompt=None):
        """
        將影像送到 DeepSeek-OCR API 進行辨識
        
        Args:
            frame: 要辨識的影像（numpy array）
            custom_prompt: 自訂的 OCR prompt
            
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
        
        # 準備提示詞
        data = {}
        prompt_to_use = custom_prompt if custom_prompt else self.ocr_prompt
        if prompt_to_use:
            data['prompt'] = prompt_to_use
            self.logger.info(f"使用 Prompt: {prompt_to_use}")
        
        # 發送請求
        self.logger.info(f"發送請求至: {self.api_url}")
        
        response = requests.post(
            self.api_url,
            files=files,
            data=data,
            timeout=self.request_timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            text = result.get('text', '')
            self.logger.info(f"OCR 辨識成功，文字長度: {len(text)} 字元")
            return text
        else:
            error_msg = response.json().get('error', '未知錯誤')
            self.logger.error(f"OCR API 錯誤: HTTP {response.status_code}, {error_msg}")
            return None
    
    def play_sound(self, sound_path):
        """播放音檔"""
        if not PYGAME_AVAILABLE or sound_path is None:
            return
        
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
        """處理一次觸發事件（拍照 + OCR）"""
        self.logger.info("=" * 60)
        self.logger.info("開始處理觸發事件...")
        
        # 更新預覽狀態
        self._update_preview("Capturing...")
        
        # 1. 拍攝照片
        frame = self.capture_frame()
        
        if frame is None:
            self.logger.error("拍攝照片失敗")
            self.play_sound(self.error_sound)
            return
        
        # 更新預覽狀態
        self._update_preview("Processing OCR...")
        
        # 2. OpenAI 預分析（如果啟用）
        custom_prompt = None
        if self.enable_preanalysis and self.openai_service:
            self.logger.info("執行 OpenAI 圖像預分析...")
            _, img_encoded = cv2.imencode('.jpg', frame)
            image_data = img_encoded.tobytes()
            
            should_perform_ocr, result = self.openai_service.should_perform_ocr(image_data)
            
            if should_perform_ocr:
                custom_prompt = result
                self.logger.info(f"✅ 圖像包含文字，將執行 OCR")
            else:
                self.logger.info(f"❌ 圖像不包含文字，跳過 OCR")
                self._update_preview("No text detected")
                return
        
        # 3. 執行 OCR
        text = self.send_to_ocr_api(frame, custom_prompt=custom_prompt)
        
        if text and text.strip():
            self.logger.info("=" * 60)
            self.logger.info("辨識結果:")
            self.logger.info(text)
            self.logger.info("=" * 60)
            
            print("\n" + "=" * 60)
            print("辨識結果:")
            print(text)
            print("=" * 60 + "\n")
            
            self._update_preview("OCR Success!")
            self.play_sound(self.success_sound)
        else:
            self.logger.warning("OCR 辨識結果為空")
            self._update_preview("OCR Failed")
            self.play_sound(self.error_sound)
    
    def run(self):
        """主迴圈：啟動 GPIO 監聽並等待觸發"""
        self.logger.info("閱讀機器人開始運行...")
        
        print("\n" + "=" * 60)
        print("📖 閱讀機器人已啟動")
        if self.gpio_service:
            status = self.gpio_service.get_status()
            if status['simulation_mode']:
                print(f"🔄 模擬模式：每 {self.config.getfloat('GPIO', 'simulation_trigger_interval', fallback=10)} 秒觸發")
            else:
                print(f"🔘 等待 GPIO{status['gpio_pin']} 按鈕點擊...")
        print("按 Ctrl+C 停止程式")
        print("=" * 60 + "\n")
        
        # 啟動預覽
        self._start_preview()
        
        # 啟動 GPIO 服務
        if self.gpio_service:
            self.gpio_service.start()
        
        # 主迴圈
        try:
            while self.running:
                # 檢查是否有待處理的觸發事件
                if self.trigger_pending:
                    self.trigger_pending = False
                    self.process_trigger()
                
                # 更新預覽
                self._update_preview("Waiting for button...")
                time.sleep(0.03)  # 約 30 FPS
        except KeyboardInterrupt:
            print("\n收到中斷信號，正在停止...")
            self.running = False
    
    def cleanup(self):
        """清理資源"""
        self.logger.info("正在清理資源...")
        self.running = False
        
        # 停止 GPIO 服務
        if self.gpio_service:
            self.gpio_service.stop()
        
        # 停止預覽
        self._stop_preview()
        
        # 清理 pygame
        if PYGAME_AVAILABLE:
            pygame.mixer.quit()
        
        cv2.destroyAllWindows()
        
        self.logger.info("資源清理完成")


def main():
    """主函數"""
    reader = None
    
    try:
        # 切換到腳本目錄
        os.chdir(SCRIPT_DIR)
        
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
