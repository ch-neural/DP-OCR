#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
閱讀機器人 Flask Web 界面
功能：相機即時預覽 -> 拍攝照片 -> OCR 辨識 -> 顯示結果
"""

import os
import sys
import time
import json
import logging
import configparser
from datetime import datetime
from pathlib import Path
import cv2
import requests
import numpy as np
from flask import Flask, render_template, request, jsonify, Response, session
from flask_cors import CORS
from dotenv import load_dotenv
import threading
from typing import Dict, List, Optional
import base64
import gc

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

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
app.secret_key = os.urandom(24)  # 用於 session
CORS(app)

# 設定 static 目錄，允許訪問 captured_images

# 全域相機連接（單例模式）
camera_cap = None
current_camera_device = None  # 追蹤當前使用的相機設備 ID
camera_lock = threading.Lock()


class BookReaderFlask:
    """閱讀機器人 Flask 界面類別"""
    
    def __init__(self, config_file='config.ini'):
        """
        初始化閱讀機器人 Flask 界面
        
        Args:
            config_file: 設定檔路徑
        """
        self.config = self._load_config(config_file)
        self._setup_logging()
        self._setup_camera()
        self._setup_api()
        self._setup_openai_vision()
        self._create_directories()
        
        # OCR 結果存儲文件
        self.ocr_results_file = 'ocr_results.json'
        self._load_ocr_results()
        
        self.logger.info("閱讀機器人 Flask 界面初始化完成")
        self.logger.info(f"API 伺服器: {self.api_url}")
    
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
        self.logger = logging.getLogger('BookReaderFlask')
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
        
        self.logger.info(f"攝影機設定完成: 裝置 {self.camera_device}, 解析度 {self.frame_width}x{self.frame_height}")
    
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
        
        # 初始化 OpenAI Vision 服務
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
    
    def _create_directories(self):
        """建立必要的目錄"""
        if self.save_captured_image:
            os.makedirs(self.image_save_path, exist_ok=True)
    
    def _load_ocr_results(self):
        """載入 OCR 結果"""
        if os.path.exists(self.ocr_results_file):
            try:
                with open(self.ocr_results_file, 'r', encoding='utf-8') as f:
                    self.ocr_results = json.load(f)
            except Exception as e:
                self.logger.error(f"載入 OCR 結果失敗: {e}")
                self.ocr_results = []
        else:
            self.ocr_results = []
    
    def detect_available_cameras(self, max_check=10):
        """
        偵測可用的相機設備
        
        Args:
            max_check: 最多檢查的相機設備數量
            
        Returns:
            list: 可用相機設備 ID 列表
        """
        available_cameras = []
        
        for device_id in range(max_check):
            cap = None
            try:
                cap = cv2.VideoCapture(device_id)
                if cap.isOpened():
                    # 嘗試讀取一幀來確認相機真的可用
                    ret, _ = cap.read()
                    if ret:
                        available_cameras.append({
                            'id': device_id,
                            'name': f'Camera {device_id}',
                            'device_path': f'/dev/video{device_id}'
                        })
                        self.logger.info(f"偵測到可用相機: 設備 {device_id} (/dev/video{device_id})")
            except Exception as e:
                self.logger.debug(f"檢查相機設備 {device_id} 時發生錯誤: {e}")
            finally:
                if cap is not None:
                    cap.release()
        
        if not available_cameras:
            self.logger.warning("未偵測到任何可用相機")
        else:
            self.logger.info(f"共偵測到 {len(available_cameras)} 個可用相機")
        
        return available_cameras
    
    def set_camera_device(self, device_id):
        """
        設定要使用的相機設備
        
        Args:
            device_id: 相機設備編號
            
        Returns:
            bool: 是否設定成功
        """
        # 釋放舊的相機連接
        global camera_cap, current_camera_device
        with camera_lock:
            if camera_cap is not None:
                try:
                    camera_cap.release()
                    self.logger.info(f"已釋放舊相機設備: {current_camera_device}")
                except Exception as e:
                    self.logger.warning(f"釋放舊相機時發生錯誤: {e}")
                camera_cap = None
                current_camera_device = None
                # 等待資源完全釋放
                time.sleep(0.3)
        
        # 測試新設備是否可用
        test_cap = None
        try:
            test_cap = cv2.VideoCapture(device_id)
            if test_cap.isOpened():
                # 設定解析度
                test_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
                test_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
                # 讀取一幀測試
                ret, _ = test_cap.read()
                if ret:
                    self.camera_device = device_id
                    self.logger.info(f"相機設備已切換為: {device_id}")
                    return True
                else:
                    self.logger.warning(f"相機設備 {device_id} 無法讀取畫面")
            else:
                self.logger.warning(f"無法打開相機設備 {device_id}")
        except Exception as e:
            self.logger.error(f"設定相機設備 {device_id} 時發生錯誤: {e}")
        finally:
            if test_cap is not None:
                test_cap.release()
        
        return False
    
    def _save_ocr_results(self):
        """保存 OCR 結果"""
        try:
            with open(self.ocr_results_file, 'w', encoding='utf-8') as f:
                json.dump(self.ocr_results, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存 OCR 結果失敗: {e}")
    
    def get_camera(self, device_id=None):
        """
        獲取相機連接（單例模式）
        
        Args:
            device_id: 相機設備編號，如果為 None 則使用 self.camera_device
            
        Returns:
            VideoCapture 物件或 None
        """
        global camera_cap, current_camera_device
        
        # 如果指定了 device_id，使用指定的設備
        target_device = device_id if device_id is not None else self.camera_device
        
        with camera_lock:
            # 如果相機已打開且設備編號相同，直接返回
            if camera_cap is not None and camera_cap.isOpened() and current_camera_device == target_device:
                return camera_cap
            
            # 設備不同或已關閉，釋放舊連接
            if camera_cap is not None:
                camera_cap.release()
                camera_cap = None
                current_camera_device = None
            
            # 初始化新相機連接
            camera_cap = cv2.VideoCapture(target_device)
            if camera_cap.isOpened():
                camera_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
                camera_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
                time.sleep(self.capture_delay)
                current_camera_device = target_device
                self.logger.info(f"相機初始化成功: 設備 {target_device}")
            else:
                self.logger.error(f"無法打開相機設備 {target_device}")
                camera_cap = None
                current_camera_device = None
                return None
        
        return camera_cap
    
    def get_camera_frame(self):
        """從 USB Camera 讀取一幀影像"""
        cap = self.get_camera()
        if cap is None:
            return None
        
        ret, frame = cap.read()
        if not ret:
            return None
        
        return frame
    
    def capture_frame(self):
        """
        從 USB Camera 拍攝一張照片
        
        Returns:
            frame: 拍攝的影像（numpy array），失敗則返回 None
            
        Raises:
            Exception: 如果相機無法打開或讀取失敗，會記錄詳細錯誤訊息
        """
        try:
            cap = self.get_camera()
            if cap is None:
                self.logger.error(f"無法獲取相機連接（設備 {self.camera_device}）")
                return None
            
            ret, frame = cap.read()
            if not ret or frame is None:
                self.logger.error(f"無法從相機讀取畫面（設備 {self.camera_device}）")
                return None
            
            # 儲存拍攝的圖片
            if self.save_captured_image:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                image_path = os.path.join(self.image_save_path, f"capture_{timestamp}.jpg")
                cv2.imwrite(image_path, frame)
                self.logger.info(f"照片已儲存至: {image_path}")
            
            return frame
        except Exception as e:
            self.logger.error(f"拍攝照片時發生錯誤: {e}")
            return None
    
    def send_to_ocr_api(self, frame, custom_prompt=None, user_prompt=None):
        """
        將影像送到 DeepSeek-OCR API 進行辨識
        
        Args:
            frame: 要辨識的影像（numpy array）
            custom_prompt: 自訂的 OCR prompt（OpenAI 預分析結果）
            user_prompt: 使用者輸入的 prompt
            
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
        # 優先順序：user_prompt > custom_prompt > 預設 prompt
        prompt_to_use = None
        if user_prompt and user_prompt.strip():
            prompt_to_use = user_prompt.strip()
            self.logger.info(f"使用使用者輸入的 Prompt: {prompt_to_use}")
        elif custom_prompt:
            prompt_to_use = custom_prompt
            self.logger.info(f"使用 OpenAI 預分析的 Prompt: {prompt_to_use}")
        else:
            prompt_to_use = self.ocr_prompt
            self.logger.info(f"使用預設 Prompt: {prompt_to_use}")
        
        data = {}
        if prompt_to_use:
            data['prompt'] = prompt_to_use
        
        # 發送請求
        self.logger.info(f"發送請求至: {self.api_url}")
        
        try:
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
                
                # 詳細日誌：記錄返回結果的完整資訊
                self.logger.info(f"OCR API 返回結果:")
                self.logger.info(f"  - 狀態碼: {response.status_code}")
                self.logger.info(f"  - 文字長度: {len(text)} 字元")
                self.logger.info(f"  - 文字前 100 字元: {text[:100] if text else '(空)'}")
                self.logger.info(f"  - 文字後 100 字元: {text[-100:] if text and len(text) > 100 else text if text else '(空)'}")
                
                # 檢查文字是否異常短（可能是被截斷或處理失敗）
                if text and len(text) < 50:
                    self.logger.warning(f"⚠️ OCR 結果異常短（{len(text)} 字元），可能不完整")
                
                return text
            else:
                error_msg = response.json().get('error', '未知錯誤')
                self.logger.error(f"OCR API 錯誤: HTTP {response.status_code}, {error_msg}")
                return None
        except Exception as e:
            self.logger.error(f"OCR API 請求失敗: {e}")
            return None
    
    def process_ocr(self, frame, user_prompt=None):
        """
        處理 OCR 辨識
        
        Args:
            frame: 要處理的影像
            user_prompt: 使用者輸入的 prompt
            
        Returns:
            dict: 包含 OCR 結果的字典
        """
        # 執行 OpenAI 預分析（如果啟用）
        custom_prompt = None
        if self.enable_preanalysis and self.openai_service:
            try:
                _, img_encoded = cv2.imencode('.jpg', frame)
                image_data = img_encoded.tobytes()
                
                should_perform_ocr, result = self.openai_service.should_perform_ocr(image_data)
                
                if should_perform_ocr:
                    custom_prompt = result
                    self.logger.info(f"✅ 圖像包含文字，將執行 OCR")
                else:
                    self.logger.info(f"❌ 圖像不包含文字，跳過 OCR")
                    return {
                        'status': 'skipped',
                        'skip_reason': result,
                        'timestamp': datetime.now().isoformat()
                    }
            except Exception as e:
                self.logger.error(f"OpenAI 預分析失敗: {e}")
        
        # 執行 OCR（使用 user_prompt 或 custom_prompt）
        text = self.send_to_ocr_api(frame, custom_prompt=custom_prompt, user_prompt=user_prompt)
        
        if text is not None and text.strip():
            return {
                'status': 'completed',
                'text': text,
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'status': 'error',
                'error': 'OCR API 返回空結果',
                'timestamp': datetime.now().isoformat()
            }
    
    def add_ocr_result(self, frame, result):
        """
        添加 OCR 結果到列表
        
        Args:
            frame: 原始影像
            result: OCR 結果字典
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存圖片
        if self.save_captured_image:
            image_path = os.path.join(self.image_save_path, f"capture_{timestamp}.jpg")
            cv2.imwrite(image_path, frame)
            # 保存相對路徑（相對於 static 目錄）
            result['image_path'] = image_path
        
        # 添加到結果列表
        result['id'] = timestamp
        result['datetime'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self.ocr_results.insert(0, result)  # 插入到開頭，最新的在前面
        
        # 限制結果數量（保留最近 100 條）
        if len(self.ocr_results) > 100:
            self.ocr_results = self.ocr_results[:100]
        
        # 保存到文件
        self._save_ocr_results()
        
        self.logger.info(f"OCR 結果已添加: {result['id']}")


# 初始化 BookReader
reader = BookReaderFlask()


@app.route('/')
def index():
    """主頁面"""
    # 預設 prompt
    default_prompt = "這是一本繁體中文書的內頁screen, 請OCR 並用繁體中文輸出結果。"
    
    # 偵測可用相機
    available_cameras = reader.detect_available_cameras()
    current_camera_id = reader.camera_device
    
    return render_template('book_reader.html', 
                         default_prompt=default_prompt,
                         available_cameras=available_cameras,
                         current_camera_id=current_camera_id)


@app.route('/captured_images/<path:filename>')
def captured_images(filename):
    """提供 captured_images 目錄中的圖片"""
    from flask import send_from_directory
    image_path = os.path.join(reader.image_save_path, filename)
    if os.path.exists(image_path):
        directory = os.path.dirname(image_path)
        return send_from_directory(directory, filename)
    return 'File not found', 404


@app.route('/api/camera/stream')
def camera_stream():
    """相機串流（Server-Sent Events）"""
    # 從查詢參數獲取相機設備 ID 和解析度
    camera_id = request.args.get('camera_id', type=int)
    resolution = request.args.get('resolution', type=str)
    
    # 如果提供了解析度參數，更新設定
    if resolution:
        try:
            width, height = map(int, resolution.split('x'))
            reader.frame_width = width
            reader.frame_height = height
            reader.logger.info(f"串流解析度設定為: {width}x{height}")
        except Exception as e:
            reader.logger.warning(f"解析解析度參數失敗: {e}")
    
    def generate():
        consecutive_errors = 0
        max_consecutive_errors = 10  # 連續錯誤超過10次則停止
        cap = None
        last_camera_id = None
        
        try:
            while True:
                # 只在首次或相機ID變更時獲取相機
                if cap is None or camera_id != last_camera_id:
                    # 釋放舊相機（如果是獨立實例）
                    if cap is not None:
                        cap.release()
                        cap = None
                        time.sleep(0.2)  # 等待資源釋放
                    
                    # 創建獨立的相機實例（不使用全局單例，避免資源競爭）
                    target_device = camera_id if camera_id is not None else reader.camera_device
                    cap = cv2.VideoCapture(target_device)
                    
                    if cap.isOpened():
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, reader.frame_width)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, reader.frame_height)
                        time.sleep(reader.capture_delay)  # 等待相機初始化
                        reader.logger.info(f"串流相機初始化成功: 設備 {target_device}")
                    else:
                        reader.logger.warning(f"串流無法打開相機設備 {target_device}")
                    
                    last_camera_id = camera_id
                    
                    if cap is None or not cap.isOpened():
                        consecutive_errors += 1
                        if consecutive_errors <= max_consecutive_errors:
                            yield f"data: {json.dumps({'error': '無法打開相機'})}\n\n"
                        else:
                            yield f"data: {json.dumps({'error': '相機無法打開，請檢查設備'})}\n\n"
                            break
                        time.sleep(0.5)  # 等待後重試
                        continue
                
                # 讀取畫面
                if cap is not None and cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        # 轉換 BGR 到 RGB
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        # 編碼為 JPEG
                        _, buffer = cv2.imencode('.jpg', frame_rgb, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        frame_bytes = buffer.tobytes()
                        frame_base64 = base64.b64encode(frame_bytes).decode('utf-8')
                        
                        yield f"data: {json.dumps({'frame': frame_base64})}\n\n"
                        consecutive_errors = 0  # 重置錯誤計數
                    else:
                        consecutive_errors += 1
                        if consecutive_errors <= max_consecutive_errors:
                            yield f"data: {json.dumps({'error': '無法讀取相機畫面'})}\n\n"
                        else:
                            yield f"data: {json.dumps({'error': '相機讀取失敗，請檢查連接'})}\n\n"
                            # 標記相機需要重新獲取
                            if cap is not None:
                                cap.release()
                            cap = None
                            consecutive_errors = 0
                            time.sleep(0.5)  # 等待後重試
                            continue
                else:
                    # 相機已關閉，需要重新獲取
                    if cap is not None:
                        cap.release()
                    cap = None
                    consecutive_errors += 1
                    if consecutive_errors <= max_consecutive_errors:
                        yield f"data: {json.dumps({'error': '相機連接已斷開'})}\n\n"
                    else:
                        yield f"data: {json.dumps({'error': '相機連接失敗，請檢查設備'})}\n\n"
                        break
                
                time.sleep(0.033)  # 約 30 FPS
        except GeneratorExit:
            # 客戶端斷開連接
            reader.logger.info("客戶端斷開串流連接")
        except Exception as e:
            reader.logger.error(f"串流發生錯誤: {e}")
            yield f"data: {json.dumps({'error': f'串流錯誤: {str(e)}'})}\n\n"
        finally:
            # 清理資源
            if cap is not None:
                cap.release()
                reader.logger.info("串流結束，已釋放相機資源")
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/camera/list', methods=['GET'])
def get_camera_list():
    """獲取可用相機列表"""
    cameras = reader.detect_available_cameras()
    return jsonify({
        'cameras': cameras,
        'current_camera_id': reader.camera_device
    })


@app.route('/api/camera/set', methods=['POST'])
def set_camera():
    """設定要使用的相機設備"""
    data = request.json
    device_id = data.get('device_id')
    
    if device_id is None:
        return jsonify({'error': '未提供 device_id'}), 400
    
    success = reader.set_camera_device(device_id)
    
    if success:
        return jsonify({
            'success': True,
            'device_id': device_id,
            'message': f'相機設備已切換為 {device_id}'
        })
    else:
        return jsonify({
            'success': False,
            'error': f'無法設定相機設備 {device_id}'
        }), 400


@app.route('/api/camera/resolution', methods=['POST'])
def set_camera_resolution():
    """設定相機解析度"""
    global camera_cap, current_camera_device
    
    data = request.json
    width = data.get('width')
    height = data.get('height')
    
    if width is None or height is None:
        return jsonify({'error': '未提供 width 或 height'}), 400
    
    try:
        # 更新解析度設定
        reader.frame_width = int(width)
        reader.frame_height = int(height)
        reader.logger.info(f"相機解析度已更新為: {width}x{height}")
        
        # 強制釋放並重新初始化相機，以套用新的解析度
        with camera_lock:
            if camera_cap is not None:
                camera_cap.release()
                camera_cap = None
                current_camera_device = None
                reader.logger.info("已釋放相機資源，等待重新初始化")
        
        # 在鎖外等待更長時間，讓相機資源完全釋放
        time.sleep(1.0)  # 增加等待時間到 1 秒
        
        # 重新初始化相機（下次拍攝時會自動初始化）
        reader.logger.info("相機將在下次使用時以新解析度初始化")
        
        return jsonify({
            'success': True,
            'width': reader.frame_width,
            'height': reader.frame_height,
            'message': f'相機解析度已設定為 {width}x{height}，相機已重置'
        })
    except Exception as e:
        reader.logger.error(f"設定相機解析度失敗: {e}")
        return jsonify({
            'success': False,
            'error': f'無法設定相機解析度: {str(e)}'
        }), 400


@app.route('/api/camera/capture', methods=['POST'])
def camera_capture():
    """拍攝照片"""
    try:
        frame = reader.capture_frame()
        
        if frame is None:
            error_msg = (
                f'無法拍攝照片。可能的原因：\n'
                f'1. 相機設備 {reader.camera_device} 無法打開\n'
                f'2. 相機正在被其他程序使用（如串流預覽）\n'
                f'3. 相機連接異常\n'
                f'請檢查相機連接或嘗試重置相機'
            )
            reader.logger.error(error_msg)
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
        
        # 轉換為 base64
        _, buffer = cv2.imencode('.jpg', frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'success': True,
            'frame': frame_base64
        })
    except Exception as e:
        error_msg = f'拍攝照片時發生未預期的錯誤: {str(e)}'
        reader.logger.error(error_msg, exc_info=True)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@app.route('/api/ocr/process', methods=['POST'])
def ocr_process():
    """處理 OCR 辨識"""
    data = request.json
    
    # 獲取 base64 編碼的圖片
    frame_base64 = data.get('frame')
    if not frame_base64:
        return jsonify({'error': '沒有提供圖片'}), 400
    
    # 解碼圖片
    try:
        frame_bytes = base64.b64decode(frame_base64)
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception as e:
        return jsonify({'error': f'圖片解碼失敗: {e}'}), 400
    
    # 獲取使用者輸入的 prompt
    # 如果為空字串或 None，後端會使用預設 prompt（從 config.ini 讀取）
    user_prompt = data.get('prompt', '').strip()
    if not user_prompt:
        user_prompt = None  # 設為 None，讓 process_ocr 使用預設 prompt
    
    # 處理 OCR（prompt 會附加到 DeepSeek-OCR API 請求中）
    result = reader.process_ocr(frame, user_prompt=user_prompt)
    
    # 添加結果
    reader.add_ocr_result(frame, result)
    
    return jsonify(result)


@app.route('/api/ocr/results', methods=['GET'])
def get_ocr_results():
    """獲取 OCR 結果列表"""
    # 將圖片路徑轉換為可訪問的 URL
    results = []
    for result in reader.ocr_results:
        result_copy = result.copy()
        if 'image_path' in result_copy and result_copy['image_path']:
            # 轉換為可訪問的 URL
            filename = os.path.basename(result_copy['image_path'])
            result_copy['image_url'] = f'/captured_images/{filename}'
        results.append(result_copy)
    return jsonify(results)


@app.route('/api/ocr/results/clear', methods=['POST'])
def clear_ocr_results():
    """清除所有 OCR 結果"""
    reader.ocr_results = []
    reader._save_ocr_results()
    return jsonify({'success': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8502, debug=True, threaded=True)

