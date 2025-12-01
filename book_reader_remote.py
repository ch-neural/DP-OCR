#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
閱讀機器人 Flask Web 界面 - 遠端客戶端版本
功能：用戶使用自己的電腦/手機 Webcam 拍照 -> 上傳到伺服器 -> OCR 辨識 -> 顯示結果

使用方式：
    python book_reader_remote.py
    
    然後在任何設備的瀏覽器開啟：http://<伺服器IP>:8502
    用戶可以使用自己設備的 Webcam 拍攝照片並進行 OCR
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
from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from typing import Optional
import base64

# 取得腳本所在目錄
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 載入 .env 環境變數
load_dotenv(os.path.join(SCRIPT_DIR, '.env'))

# 嘗試匯入 OpenAI Vision 服務
try:
    from openai_vision_service import OpenAIVisionService
    OPENAI_VISION_AVAILABLE = True
except ImportError as e:
    OPENAI_VISION_AVAILABLE = False
    print(f"警告: 無法匯入 OpenAI Vision 服務 ({e})")
    print("將跳過圖像預分析功能")

# Flask 應用
app = Flask(__name__, 
            template_folder=os.path.join(SCRIPT_DIR, 'templates'),
            static_folder=os.path.join(SCRIPT_DIR, 'static'))
app.secret_key = os.urandom(24)
CORS(app)

# 版本號（用於前端快取控制）
VERSION = datetime.now().strftime("%Y%m%d-%H%M%S")


class BookReaderRemote:
    """閱讀機器人遠端版本（客戶端 Webcam）"""
    
    def __init__(self, config_file='config.ini'):
        """初始化"""
        # 如果 config_file 不是絕對路徑，則相對於腳本目錄
        if not os.path.isabs(config_file):
            config_file = os.path.join(SCRIPT_DIR, config_file)
        
        self.config = self._load_config(config_file)
        self._setup_logging()
        self._setup_api()
        self._setup_openai_vision()
        self._create_directories()
        
        # OCR 結果存儲
        self.ocr_results_file = os.path.join(SCRIPT_DIR, 'ocr_results.json')
        self._load_ocr_results()
        
        self.logger.info("=" * 60)
        self.logger.info("閱讀機器人遠端版本初始化完成")
        self.logger.info(f"API 伺服器: {self.api_url}")
        self.logger.info("用戶可以使用自己設備的 Webcam 進行 OCR")
        self.logger.info("=" * 60)
    
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
        self.logger = logging.getLogger('BookReaderRemote')
        self.logger.setLevel(getattr(logging, log_level))
        
        for handler in handlers:
            self.logger.addHandler(handler)
    
    def _setup_api(self):
        """設定 API 相關參數"""
        api_url = self.config.get('API', 'api_url', fallback='http://172.30.19.20:5000')
        ocr_endpoint = self.config.get('API', 'ocr_endpoint', fallback='/ocr')
        self.api_url = api_url.rstrip('/') + ocr_endpoint
        self.request_timeout = self.config.getint('API', 'request_timeout', fallback=30)
        self.ocr_prompt = self.config.get('OCR', 'prompt', fallback='<image>\\nFree OCR.')
        
        # 圖片儲存設定
        self.save_captured_image = self.config.getboolean('CAMERA', 'save_captured_image', fallback=True)
        self.image_save_path = self.config.get('CAMERA', 'image_save_path', fallback='captured_images')
        
        if not os.path.isabs(self.image_save_path):
            self.image_save_path = os.path.join(SCRIPT_DIR, self.image_save_path)
    
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
    
    def _save_ocr_results(self):
        """保存 OCR 結果"""
        try:
            with open(self.ocr_results_file, 'w', encoding='utf-8') as f:
                json.dump(self.ocr_results, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存 OCR 結果失敗: {e}")
    
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
        
        files = {
            'file': ('image.jpg', img_encoded.tobytes(), 'image/jpeg')
        }
        
        # 準備提示詞（優先順序：user_prompt > custom_prompt > 預設）
        prompt_to_use = None
        if user_prompt and user_prompt.strip():
            prompt_to_use = user_prompt.strip()
            self.logger.info(f"使用使用者輸入的 Prompt: {prompt_to_use[:50]}...")
        elif custom_prompt:
            prompt_to_use = custom_prompt
            self.logger.info(f"使用 OpenAI 預分析的 Prompt")
        else:
            prompt_to_use = self.ocr_prompt
            self.logger.info(f"使用預設 Prompt")
        
        data = {}
        if prompt_to_use:
            data['prompt'] = prompt_to_use
        
        self.logger.info(f"發送請求至: {self.api_url}")
        
        try:
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
        
        # 執行 OCR
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
        """添加 OCR 結果到列表"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存圖片
        if self.save_captured_image:
            image_path = os.path.join(self.image_save_path, f"capture_{timestamp}.jpg")
            cv2.imwrite(image_path, frame)
            result['image_path'] = image_path
        
        result['id'] = timestamp
        result['datetime'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self.ocr_results.insert(0, result)
        
        # 限制結果數量
        if len(self.ocr_results) > 100:
            self.ocr_results = self.ocr_results[:100]
        
        self._save_ocr_results()
        self.logger.info(f"OCR 結果已添加: {result['id']}")


# 初始化
reader = BookReaderRemote()


# ============ Flask 路由 ============

@app.route('/')
def index():
    """主頁面 - 客戶端 Webcam 版本"""
    default_prompt = "這是一本繁體中文書的內頁, 請OCR 並用繁體中文輸出結果。"
    
    return render_template('book_reader_remote.html', 
                         default_prompt=default_prompt,
                         version=VERSION)


@app.route('/captured_images/<path:filename>')
def captured_images(filename):
    """提供 captured_images 目錄中的圖片"""
    image_path = os.path.join(reader.image_save_path, filename)
    if os.path.exists(image_path):
        directory = os.path.dirname(image_path)
        return send_from_directory(directory, filename)
    return 'File not found', 404


@app.route('/api/ocr/process', methods=['POST'])
def ocr_process():
    """處理 OCR 辨識（接收客戶端上傳的圖片）"""
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
        
        if frame is None:
            return jsonify({'error': '圖片解碼失敗'}), 400
            
    except Exception as e:
        reader.logger.error(f"圖片解碼失敗: {e}")
        return jsonify({'error': f'圖片解碼失敗: {e}'}), 400
    
    # 獲取使用者輸入的 prompt
    user_prompt = data.get('prompt', '').strip()
    if not user_prompt:
        user_prompt = None
    
    # 處理 OCR
    result = reader.process_ocr(frame, user_prompt=user_prompt)
    
    # 添加結果
    reader.add_ocr_result(frame, result)
    
    return jsonify(result)


@app.route('/api/ocr/results', methods=['GET'])
def get_ocr_results():
    """獲取 OCR 結果列表"""
    results = []
    for result in reader.ocr_results:
        result_copy = result.copy()
        if 'image_path' in result_copy and result_copy['image_path']:
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


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康檢查"""
    return jsonify({
        'status': 'ok',
        'version': VERSION,
        'mode': 'remote_webcam'
    })


# ============ 主程式 ============

if __name__ == '__main__':
    # 切換到腳本所在目錄
    os.chdir(SCRIPT_DIR)
    
    # 檢查是否有 SSL 證書
    cert_file = os.path.join(SCRIPT_DIR, 'cert.pem')
    key_file = os.path.join(SCRIPT_DIR, 'key.pem')
    use_ssl = os.path.exists(cert_file) and os.path.exists(key_file)
    
    print("\n" + "=" * 60)
    print("📖 Book Reader OCR - 遠端客戶端版本")
    print("=" * 60)
    
    if use_ssl:
        print(f"🔒 HTTPS 模式（Webcam 可用）")
        print(f"🌐 伺服器網址: https://0.0.0.0:8502")
        print(f"⚠️  首次連接請接受自簽證書警告")
    else:
        print(f"🌐 HTTP 模式")
        print(f"🌐 伺服器網址: http://0.0.0.0:8502")
        print(f"⚠️  Webcam 功能需要 HTTPS，請使用「上傳圖片」功能")
    
    print(f"📡 用戶可以使用自己設備的 Webcam 進行 OCR")
    print(f"📁 圖片儲存路徑: {reader.image_save_path}")
    print("=" * 60 + "\n")
    
    # 啟動 Flask 應用
    if use_ssl:
        app.run(host='0.0.0.0', port=8502, debug=True, threaded=True, 
                use_reloader=False, ssl_context=(cert_file, key_file))
    else:
        app.run(host='0.0.0.0', port=8502, debug=True, threaded=True, use_reloader=False)
