#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
閱讀機器人 Flask Web 界面 - 遠端客戶端版本
功能：用戶使用自己的電腦/手機 Webcam 拍照 -> 上傳到伺服器 -> OCR 辨識 -> 顯示結果

使用方式：
    python book_reader_remote.py
    
    然後在任何設備的瀏覽器開啟：https://<伺服器IP>:8502
    用戶可以使用自己設備的 Webcam 拍攝照片並進行 OCR
    
    程式會自動檢查並建立 SSL 自簽憑證，以支援 HTTPS 和 Webcam 功能
"""

import os
import sys
import time
import json
import logging
import configparser
from datetime import datetime, timedelta
from pathlib import Path
import cv2
import requests
import numpy as np
from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from typing import Optional, Tuple
import base64

# 取得腳本所在目錄
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 載入 .env 環境變數
load_dotenv(os.path.join(SCRIPT_DIR, '.env'))


class SSLCertificateManager:
    """SSL 自簽憑證管理器
    
    自動檢查並建立 SSL 自簽憑證，用於 HTTPS 連線。
    這是讓瀏覽器能夠使用 Webcam 功能的必要條件。
    """
    
    def __init__(self, cert_dir: str = None, cert_name: str = "cert", 
                 key_name: str = "key", validity_days: int = 365):
        """
        初始化 SSL 憑證管理器
        
        Args:
            cert_dir: 憑證存放目錄（預設為腳本目錄）
            cert_name: 憑證檔案名稱（不含副檔名）
            key_name: 私鑰檔案名稱（不含副檔名）
            validity_days: 憑證有效天數
        """
        self.cert_dir = cert_dir or SCRIPT_DIR
        self.cert_file = os.path.join(self.cert_dir, f"{cert_name}.pem")
        self.key_file = os.path.join(self.cert_dir, f"{key_name}.pem")
        self.validity_days = validity_days
    
    def check_certificates_exist(self) -> bool:
        """檢查憑證檔案是否存在"""
        return os.path.exists(self.cert_file) and os.path.exists(self.key_file)
    
    def check_certificate_valid(self) -> Tuple[bool, str]:
        """
        檢查憑證是否有效（未過期）
        
        Returns:
            Tuple[bool, str]: (是否有效, 說明訊息)
        """
        if not self.check_certificates_exist():
            return False, "憑證檔案不存在"
        
        try:
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            
            with open(self.cert_file, "rb") as f:
                cert_data = f.read()
            
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            
            # 檢查過期時間
            now = datetime.utcnow()
            if cert.not_valid_after_utc.replace(tzinfo=None) < now:
                return False, f"憑證已於 {cert.not_valid_after_utc} 過期"
            
            # 檢查是否即將過期（7天內）
            days_until_expiry = (cert.not_valid_after_utc.replace(tzinfo=None) - now).days
            if days_until_expiry < 7:
                return False, f"憑證將於 {days_until_expiry} 天後過期，建議更新"
            
            return True, f"憑證有效，將於 {days_until_expiry} 天後過期"
            
        except ImportError:
            # 如果沒有 cryptography 庫，只檢查檔案是否存在
            return True, "憑證檔案存在（無法驗證有效期）"
        except Exception as e:
            return False, f"檢查憑證時發生錯誤: {e}"
    
    def generate_self_signed_certificate(self, 
                                          common_name: str = "localhost",
                                          organization: str = "Book Reader OCR",
                                          country: str = "TW") -> Tuple[bool, str]:
        """
        生成自簽 SSL 憑證
        
        Args:
            common_name: 憑證通用名稱（通常是網域名或 localhost）
            organization: 組織名稱
            country: 國家代碼
            
        Returns:
            Tuple[bool, str]: (是否成功, 說明訊息)
        """
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            import ipaddress
            import socket
            
            print("🔐 正在生成 SSL 自簽憑證...")
            
            # 生成私鑰
            key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            # 獲取本機 IP 地址
            local_ips = self._get_local_ips()
            
            # 設定憑證主體
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, country),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            ])
            
            # 設定 Subject Alternative Names（讓憑證對多個網址有效）
            san_list = [
                x509.DNSName("localhost"),
                x509.DNSName("*.localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                x509.IPAddress(ipaddress.IPv6Address("::1")),
            ]
            
            # 添加本機 IP 地址
            for ip in local_ips:
                try:
                    san_list.append(x509.IPAddress(ipaddress.IPv4Address(ip)))
                except Exception:
                    pass
            
            # 生成憑證
            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.utcnow())
                .not_valid_after(datetime.utcnow() + timedelta(days=self.validity_days))
                .add_extension(
                    x509.SubjectAlternativeName(san_list),
                    critical=False,
                )
                .add_extension(
                    x509.BasicConstraints(ca=True, path_length=0),
                    critical=True,
                )
                .sign(key, hashes.SHA256(), default_backend())
            )
            
            # 寫入私鑰檔案
            with open(self.key_file, "wb") as f:
                f.write(key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # 寫入憑證檔案
            with open(self.cert_file, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            
            # 設定檔案權限（僅限擁有者讀寫）
            os.chmod(self.key_file, 0o600)
            os.chmod(self.cert_file, 0o644)
            
            ip_info = ", ".join(local_ips) if local_ips else "無"
            return True, f"SSL 憑證已成功建立！\n   - 憑證檔案: {self.cert_file}\n   - 私鑰檔案: {self.key_file}\n   - 有效期限: {self.validity_days} 天\n   - 本機 IP: {ip_info}"
            
        except ImportError as e:
            return False, f"缺少 cryptography 套件，請執行: pip install cryptography\n錯誤詳情: {e}"
        except Exception as e:
            return False, f"生成憑證時發生錯誤: {e}"
    
    def _get_local_ips(self) -> list:
        """獲取本機所有 IP 地址"""
        import socket
        ips = []
        try:
            # 方法 1: 透過連接外部地址獲取主要 IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ips.append(s.getsockname()[0])
            s.close()
        except Exception:
            pass
        
        try:
            # 方法 2: 獲取所有網路介面的 IP
            hostname = socket.gethostname()
            for ip in socket.gethostbyname_ex(hostname)[2]:
                if ip not in ips and not ip.startswith("127."):
                    ips.append(ip)
        except Exception:
            pass
        
        return ips
    
    def ensure_certificates(self, force_regenerate: bool = False) -> Tuple[bool, str]:
        """
        確保 SSL 憑證存在且有效，如果不存在或無效則自動建立
        
        Args:
            force_regenerate: 是否強制重新生成憑證
            
        Returns:
            Tuple[bool, str]: (是否成功, 說明訊息)
        """
        if force_regenerate:
            print("🔄 強制重新生成 SSL 憑證...")
            return self.generate_self_signed_certificate()
        
        if not self.check_certificates_exist():
            print("📝 未找到 SSL 憑證，正在自動建立...")
            return self.generate_self_signed_certificate()
        
        is_valid, message = self.check_certificate_valid()
        if not is_valid:
            print(f"⚠️  {message}，正在重新建立...")
            return self.generate_self_signed_certificate()
        
        return True, f"✅ 使用現有 SSL 憑證: {message}"
    
    def get_ssl_context(self) -> Tuple[str, str]:
        """獲取 SSL context 所需的憑證和私鑰路徑"""
        return (self.cert_file, self.key_file)

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

def main():
    """主程式入口"""
    # 切換到腳本所在目錄
    os.chdir(SCRIPT_DIR)
    
    print("\n" + "=" * 60)
    print("📖 Book Reader OCR - 遠端客戶端版本")
    print("=" * 60)
    
    # 初始化 SSL 憑證管理器並確保憑證存在
    ssl_manager = SSLCertificateManager(cert_dir=SCRIPT_DIR)
    success, message = ssl_manager.ensure_certificates()
    
    if success:
        print(f"\n{message}\n")
        cert_file, key_file = ssl_manager.get_ssl_context()
        use_ssl = True
    else:
        print(f"\n❌ SSL 憑證建立失敗: {message}")
        print("⚠️  將使用 HTTP 模式，Webcam 功能可能無法使用")
        print("💡 建議安裝 cryptography 套件: pip install cryptography\n")
        use_ssl = False
    
    # 獲取本機 IP 地址
    local_ips = ssl_manager._get_local_ips()
    
    print("-" * 60)
    if use_ssl:
        print("🔒 HTTPS 模式（Webcam 可用）")
        print(f"🌐 本機網址: https://localhost:8502")
        for ip in local_ips:
            print(f"🌐 區網網址: https://{ip}:8502")
        print("⚠️  首次連接請接受自簽憑證警告")
    else:
        print("🌐 HTTP 模式")
        print(f"🌐 本機網址: http://localhost:8502")
        for ip in local_ips:
            print(f"🌐 區網網址: http://{ip}:8502")
        print("⚠️  Webcam 功能需要 HTTPS，請使用「上傳圖片」功能")
    
    print("-" * 60)
    print(f"📡 用戶可以使用自己設備的 Webcam 進行 OCR")
    print(f"📁 圖片儲存路徑: {reader.image_save_path}")
    print("=" * 60 + "\n")
    
    # 啟動 Flask 應用
    if use_ssl:
        app.run(host='0.0.0.0', port=8502, debug=True, threaded=True, 
                use_reloader=False, ssl_context=(cert_file, key_file))
    else:
        app.run(host='0.0.0.0', port=8502, debug=True, threaded=True, use_reloader=False)


if __name__ == '__main__':
    main()
