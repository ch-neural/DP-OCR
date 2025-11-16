#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
閱讀機器人 Streamlit 界面
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
import streamlit as st
from PIL import Image
from dotenv import load_dotenv
import threading
from typing import Dict, List, Optional
import subprocess
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


class BookReaderStreamlit:
    """閱讀機器人 Streamlit 界面類別"""
    
    def __init__(self, config_file='config.ini'):
        """
        初始化閱讀機器人 Streamlit 界面
        
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
        
        # 相機連接（用於持續預覽）
        self.camera_cap = None
        
        # 確保相機資源已釋放（防止重複初始化問題）
        self._release_camera()
        
        self.logger.info("閱讀機器人 Streamlit 界面初始化完成")
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
        self.logger = logging.getLogger('BookReaderStreamlit')
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
    
    def _save_ocr_results(self):
        """保存 OCR 結果"""
        try:
            with open(self.ocr_results_file, 'w', encoding='utf-8') as f:
                json.dump(self.ocr_results, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存 OCR 結果失敗: {e}")
    
    def _check_camera_available(self, device_index):
        """
        檢查相機設備是否可用
        
        Args:
            device_index: 相機設備編號
            
        Returns:
            bool: 相機是否可用
        """
        # 抑制 OpenCV 警告訊息
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            test_cap = None
            try:
                test_cap = cv2.VideoCapture(device_index)
                if test_cap.isOpened():
                    # 嘗試讀取一幀
                    ret, _ = test_cap.read()
                    return ret
            except Exception:
                return False
            finally:
                if test_cap is not None:
                    test_cap.release()
        
        return False
    
    def _find_available_camera(self):
        """
        檢查預設相機設備（設備 0）是否可用
        
        Returns:
            int: 相機設備編號（0），若不可用則返回 None
        """
        # 只檢查設備 0
        if self._check_camera_available(0):
            return 0
        
        return None
    
    def _init_camera(self):
        """初始化相機連接（用於持續預覽，只使用設備 0）"""
        # 如果相機已打開且正常，直接返回
        if self.camera_cap is not None and self.camera_cap.isOpened():
            # 測試讀取一幀，確認相機真的可用
            try:
                ret, _ = self.camera_cap.read()
                if ret:
                    return True
                else:
                    # 讀取失敗，釋放舊連接
                    self.logger.warning("相機連接異常，嘗試重新初始化...")
                    self._force_release_camera()
            except Exception as e:
                self.logger.warning(f"測試相機讀取時發生錯誤: {e}")
                self._force_release_camera()
        
        # 確保舊連接已釋放
        if self.camera_cap is not None:
            self._force_release_camera()
        
        # 只使用設備 0
        device_to_use = 0
        
        # 檢查相機是否被其他進程佔用
        in_use, pids = self._check_camera_in_use(device_to_use)
        if in_use:
            # 檢查是否是 Streamlit 進程佔用（可能是舊實例）
            current_pid = os.getpid()
            streamlit_pids = [pid for pid in pids if pid != current_pid]
            
            if streamlit_pids:
                self.logger.warning(f"相機設備 {device_to_use} 被 Streamlit 進程佔用（PIDs: {streamlit_pids}），等待釋放...")
                # 等待舊進程釋放資源（最多等待 5 秒）
                max_wait = 5
                wait_interval = 0.5
                waited = 0
                while waited < max_wait:
                    time.sleep(wait_interval)
                    waited += wait_interval
                    in_use, pids = self._check_camera_in_use(device_to_use)
                    if not in_use:
                        self.logger.info(f"相機資源已釋放（等待 {waited:.1f} 秒）")
                        break
                    # 檢查是否還是同一個進程
                    remaining_pids = [pid for pid in pids if pid != current_pid]
                    if not remaining_pids:
                        self.logger.info(f"相機資源已釋放（等待 {waited:.1f} 秒）")
                        break
                
                # 如果仍然被佔用，記錄錯誤但繼續嘗試
                if self._check_camera_in_use(device_to_use)[0]:
                    self.logger.error(f"相機設備 {device_to_use} 仍被佔用，將嘗試強制初始化")
            else:
                self.logger.error(f"相機設備 {device_to_use} 被其他進程佔用（PIDs: {pids}），無法初始化")
                return False
        
        # 嘗試初始化相機（最多重試 5 次，因為可能需要等待舊進程釋放）
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # 在每次嘗試前再次檢查是否被佔用（但如果是 Streamlit 進程，允許繼續）
                if attempt > 0:
                    in_use, pids = self._check_camera_in_use(device_to_use)
                    if in_use:
                        current_pid = os.getpid()
                        non_streamlit_pids = [pid for pid in pids if pid != current_pid]
                        if non_streamlit_pids:
                            # 檢查是否還是 Streamlit 進程
                            try:
                                for pid in non_streamlit_pids:
                                    result = subprocess.run(
                                        ['ps', '-p', str(pid), '-o', 'comm='],
                                        capture_output=True,
                                        text=True,
                                        timeout=1
                                    )
                                    if 'streamlit' not in result.stdout.lower():
                                        self.logger.warning(f"相機設備 {device_to_use} 被非 Streamlit 進程佔用（PID: {pid}），等待...")
                                        time.sleep(2.0)
                                        continue
                            except Exception:
                                pass
                        
                        self.logger.warning(f"相機設備 {device_to_use} 仍被佔用（嘗試 {attempt + 1}/{max_retries}），等待釋放...")
                        time.sleep(2.0)  # 等待更長時間
                        continue
                
                self.camera_cap = cv2.VideoCapture(device_to_use)
                
                if self.camera_cap.isOpened():
                    # 設定解析度
                    self.camera_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
                    self.camera_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
                    
                    # 等待攝影機穩定
                    time.sleep(self.capture_delay)
                    
                    # 測試讀取一幀
                    ret, _ = self.camera_cap.read()
                    if ret:
                        self.logger.info(f"相機初始化成功（嘗試 {attempt + 1}/{max_retries}）")
                        return True
                    else:
                        self.logger.warning(f"相機打開但無法讀取畫面（嘗試 {attempt + 1}/{max_retries}）")
                        self._force_release_camera()
                else:
                    self.logger.warning(f"無法打開相機（嘗試 {attempt + 1}/{max_retries}）")
                    self._force_release_camera()
                
                # 如果不是最後一次嘗試，等待後重試
                if attempt < max_retries - 1:
                    time.sleep(2.0)  # 增加等待時間
                    
            except Exception as e:
                self.logger.error(f"初始化相機時發生錯誤: {e}")
                self._force_release_camera()
                if attempt < max_retries - 1:
                    time.sleep(2.0)  # 增加等待時間
        
        return False
    
    def _check_camera_in_use(self, device_index=0):
        """
        檢查相機是否被其他進程佔用
        
        Args:
            device_index: 相機設備編號
            
        Returns:
            tuple: (是否被佔用, 佔用進程列表)
        """
        try:
            device_path = f"/dev/video{device_index}"
            result = subprocess.run(
                ['lsof', device_path],
                capture_output=True,
                text=True,
                timeout=2
            )
            # 如果有輸出，表示有進程在使用
            if result.stdout.strip():
                processes = result.stdout.strip().split('\n')[1:]  # 跳過標題行
                pids = set()
                for proc in processes:
                    parts = proc.split()
                    if len(parts) > 1:
                        try:
                            pid = int(parts[1])
                            pids.add(pid)
                        except (ValueError, IndexError):
                            pass
                
                if pids:
                    self.logger.warning(f"相機設備 {device_path} 被以下進程佔用:")
                    for proc in processes:
                        self.logger.warning(f"  {proc}")
                    return True, list(pids)
            return False, []
        except subprocess.TimeoutExpired:
            self.logger.warning("檢查相機佔用狀態超時")
            return False, []
        except FileNotFoundError:
            # lsof 命令不存在，跳過檢查
            return False, []
        except Exception as e:
            self.logger.debug(f"檢查相機佔用狀態時發生錯誤: {e}")
            return False, []
    
    def _force_release_camera(self, device_index=0):
        """
        強制釋放相機資源（使用多種方法）
        
        Args:
            device_index: 相機設備編號
        """
        # 方法 1: 標準釋放
        if self.camera_cap is not None:
            try:
                if self.camera_cap.isOpened():
                    self.camera_cap.release()
                self.camera_cap = None
            except Exception as e:
                self.logger.warning(f"標準釋放相機時發生錯誤: {e}")
                self.camera_cap = None
        
        # 方法 2: 關閉所有 OpenCV 視窗（釋放相關資源）
        try:
            cv2.destroyAllWindows()
        except Exception as e:
            self.logger.debug(f"關閉 OpenCV 視窗時發生錯誤: {e}")
        
        # 方法 3: 強制垃圾回收
        gc.collect()
        
        # 方法 4: 等待資源釋放
        time.sleep(1.0)  # 增加等待時間
        
        self.logger.info("相機資源已強制釋放")
    
    def _release_camera(self):
        """釋放相機連接"""
        self._force_release_camera()
    
    def get_camera_frame(self):
        """
        從 USB Camera 讀取一幀影像（使用持續連接）
        
        Returns:
            拍攝的影像（numpy array），若失敗則回傳 None
        """
        # 確保相機已初始化
        if not self._init_camera():
            return None
        
        # 讀取影像
        ret, frame = self.camera_cap.read()
        
        if not ret:
            # 嘗試重新初始化（最多重試一次）
            self._release_camera()
            if not self._init_camera():
                return None
            ret, frame = self.camera_cap.read()
            if not ret:
                return None
        
        return frame
    
    def capture_frame(self):
        """
        從 USB Camera 拍攝一張照片
        
        Returns:
            拍攝的影像（numpy array），若失敗則回傳 None
        """
        frame = self.get_camera_frame()
        
        if frame is None:
            return None
        
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
        
        # 準備提示詞
        data = {}
        prompt_to_use = custom_prompt if custom_prompt else self.ocr_prompt
        if prompt_to_use:
            data['prompt'] = prompt_to_use
            self.logger.info(f"使用 Prompt: {prompt_to_use}")
        
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
                self.logger.info(f"OCR 辨識成功，文字長度: {len(text)} 字元")
                return text
            else:
                error_msg = response.json().get('error', '未知錯誤')
                self.logger.error(f"OCR API 錯誤: HTTP {response.status_code}, {error_msg}")
                return None
        except Exception as e:
            self.logger.error(f"OCR API 請求失敗: {e}")
            return None
    
    def process_ocr(self, frame):
        """
        處理 OCR 辨識
        
        Args:
            frame: 要處理的影像
            
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
        text = self.send_to_ocr_api(frame, custom_prompt=custom_prompt)
        
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


def main():
    """Streamlit 主應用程式"""
    st.set_page_config(
        page_title="Book Reader OCR",
        page_icon="📖",
        layout="wide"
    )
    
    st.title("📖 Book Reader OCR System")
    st.markdown("---")
    
    # 初始化 BookReader
    # 檢查是否需要重新創建 reader（解決 Streamlit 多進程問題）
    need_recreate = False
    
    if 'reader' in st.session_state:
        reader = st.session_state.reader
        
        # 檢查相機是否被其他 Streamlit 進程佔用
        in_use, pids = reader._check_camera_in_use(0)
        if in_use:
            current_pid = os.getpid()
            other_pids = [pid for pid in pids if pid != current_pid]
            if other_pids:
                # 檢查是否是 Streamlit 進程
                try:
                    for pid in other_pids:
                        result = subprocess.run(
                            ['ps', '-p', str(pid), '-o', 'comm='],
                            capture_output=True,
                            text=True,
                            timeout=1
                        )
                        if 'streamlit' in result.stdout.lower():
                            reader.logger.warning(f"檢測到其他 Streamlit 進程（PID: {pid}）佔用相機，將重新創建 reader...")
                            need_recreate = True
                            break
                except Exception:
                    pass
        
        # 檢查是否需要重置相機（從 session_state 中讀取）
        if st.session_state.get('reset_camera_flag', False):
            reader.logger.info("檢測到相機重置標記，強制釋放相機資源...")
            reader._force_release_camera()
            st.session_state.reset_camera_flag = False
            need_recreate = True  # 重置後重新創建
        
        if not need_recreate and reader.camera_cap is not None:
            try:
                if not reader.camera_cap.isOpened():
                    reader.logger.info("檢測到相機連接異常，釋放舊連接...")
                    reader._force_release_camera()
                    need_recreate = True
                else:
                    # 即使 isOpened() 返回 True，也測試讀取一幀確認真的可用
                    try:
                        ret, _ = reader.camera_cap.read()
                        if not ret:
                            reader.logger.warning("相機連接異常（無法讀取），釋放舊連接...")
                            reader._force_release_camera()
                            need_recreate = True
                    except Exception as e:
                        reader.logger.warning(f"測試相機讀取時發生錯誤: {e}")
                        reader._force_release_camera()
                        need_recreate = True
            except Exception as e:
                reader.logger.warning(f"檢查相機狀態時發生錯誤: {e}")
                reader._force_release_camera()
                need_recreate = True
    
    # 如果需要重新創建，先釋放舊資源
    if need_recreate and 'reader' in st.session_state:
        reader = st.session_state.reader
        reader.logger.info("釋放舊的 reader 資源...")
        reader._force_release_camera()
        del st.session_state.reader
    
    # 創建新的 reader
    if 'reader' not in st.session_state:
        with st.spinner("正在初始化系統..."):
            st.session_state.reader = BookReaderStreamlit()
    
    reader = st.session_state.reader
    
    # 側邊欄
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # 相機設定
        st.subheader("📷 Camera Settings")
        st.info(f"使用相機設備: {reader.camera_device}")
        
        # 相機預覽開關
        enable_preview = st.checkbox("Enable Camera Preview", value=True)
        
        # 自動刷新開關（僅在啟用預覽時顯示）
        auto_refresh = True
        if enable_preview:
            auto_refresh = st.checkbox(
                "Auto Refresh Preview", 
                value=True,
                help="自動刷新預覽畫面。關閉後需手動點擊「刷新預覽」按鈕更新畫面。"
            )
        
        # OCR 設定
        st.subheader("OCR Settings")
        custom_prompt = st.text_area(
            "Custom Prompt (Optional)",
            value=reader.ocr_prompt,
            help="Leave empty to use default prompt"
        )
        
        # 初始化處理狀態
        if 'processing' not in st.session_state:
            st.session_state.processing = False
        
        # 手動觸發 OCR
        if st.button("📸 Capture & OCR", type="primary", width='stretch', disabled=st.session_state.processing):
            st.session_state.capture_triggered = True
            st.session_state.processing = True
            st.rerun()  # 立即刷新以開始處理
        
        # 手動刷新預覽按鈕（僅在啟用預覽且關閉自動刷新時顯示）
        if enable_preview and not auto_refresh:
            if st.button("🔄 Refresh Preview", width='stretch', disabled=st.session_state.processing):
                st.rerun()
        
        # 重置相機連接按鈕（用於修復相機連接問題）
        if enable_preview:
            if st.button("🔧 Reset Camera", width='stretch', disabled=st.session_state.processing, 
                        help="重置相機連接，用於修復 F5 刷新後相機無法使用的問題"):
                reader.logger.info("使用者手動重置相機連接...")
                # 設置重置標記
                st.session_state.reset_camera_flag = True
                # 強制釋放相機資源
                reader._force_release_camera()
                # 重置失敗計數
                if 'camera_fail_count' in st.session_state:
                    st.session_state.camera_fail_count = 0
                st.success("相機連接已重置，請稍候...")
                time.sleep(2.0)  # 增加等待時間，確保資源釋放
                st.rerun()
    
    # 主內容區域
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📷 Camera Preview")
        
        # 初始化預覽 placeholder（固定在 session_state 中）
        if 'preview_placeholder' not in st.session_state:
            st.session_state.preview_placeholder = st.empty()
        
        preview_placeholder = st.session_state.preview_placeholder
        
        if enable_preview:
            # 讀取相機畫面
            frame = reader.get_camera_frame()
            
            if frame is not None:
                # 轉換 BGR 到 RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # 使用 width='stretch' 替代 use_container_width=True
                preview_placeholder.image(frame_rgb, width='stretch', channels="RGB")
            else:
                # 顯示詳細的錯誤訊息和解決方法
                with preview_placeholder.container():
                    st.error("❌ 無法讀取相機畫面")
                    st.markdown("""
                    **可能的原因：**
                    1. 相機未連接或未正確連接
                    2. 相機被其他程序佔用
                    3. 相機權限問題
                    4. 相機設備編號不正確
                    
                    **解決方法：**
                    1. 檢查相機連接：`ls -l /dev/video*`
                    2. 檢查是否有其他程序使用相機：`lsof /dev/video0`
                    3. 檢查用戶權限：確保用戶在 `video` 群組中
                    4. 嘗試修改 `config.ini` 中的 `camera_device` 設定
                    """)
                    
                    # 顯示相機狀態（只在用戶點擊時檢測）
                    if 'check_camera_status' not in st.session_state:
                        st.session_state.check_camera_status = False
                    
                    if st.button("🔍 檢查相機狀態", width='stretch'):
                        st.session_state.check_camera_status = True
                    
                    if st.session_state.check_camera_status:
                        with st.expander("🔍 相機狀態", expanded=True):
                            camera_available = reader._check_camera_available(0)
                            if camera_available:
                                st.success("✅ 相機設備 0 可用")
                            else:
                                st.error("❌ 相機設備 0 不可用")
                                st.markdown("""
                                **檢查命令：**
                                - `ls -l /dev/video0` - 查看相機設備
                                - `lsof /dev/video0` - 檢查相機是否被佔用
                                """)
        
        # OCR 結果顯示區域（使用固定的 placeholder）
        if 'ocr_result_placeholder' not in st.session_state:
            st.session_state.ocr_result_placeholder = st.empty()
        
        ocr_result_placeholder = st.session_state.ocr_result_placeholder
        
        # 手動觸發 OCR（放在預覽下方）
        if st.session_state.get('capture_triggered', False) and st.session_state.get('processing', False):
            st.session_state.capture_triggered = False
            
            with ocr_result_placeholder.container():
                with st.spinner("正在拍攝照片並執行 OCR..."):
                    # 拍攝照片
                    frame = reader.capture_frame()
                    
                    if frame is not None:
                        # 顯示拍攝的照片
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        st.image(frame_rgb, caption="Captured Image", width='stretch')
                        
                        # 獲取自訂 prompt（從側邊欄）
                        prompt_to_use = custom_prompt if custom_prompt and custom_prompt.strip() else None
                        
                        # 執行 OCR（使用自訂 prompt）
                        if prompt_to_use:
                            # 直接調用 send_to_ocr_api 並手動處理結果
                            text = reader.send_to_ocr_api(frame, custom_prompt=prompt_to_use)
                            if text is not None and text.strip():
                                result = {
                                    'status': 'completed',
                                    'text': text,
                                    'timestamp': datetime.now().isoformat()
                                }
                            else:
                                result = {
                                    'status': 'error',
                                    'error': 'OCR API 返回空結果',
                                    'timestamp': datetime.now().isoformat()
                                }
                        else:
                            # 使用預設處理流程（包含 OpenAI 預分析）
                            result = reader.process_ocr(frame)
                        
                        # 添加結果
                        reader.add_ocr_result(frame, result)
                        
                        # 顯示結果
                        if result['status'] == 'completed':
                            st.success("✅ OCR 辨識成功！")
                            st.text_area("OCR Result", value=result['text'], height=200, key=f"ocr_result_{time.time()}")
                        elif result['status'] == 'skipped':
                            st.warning(f"⚠️ 跳過 OCR: {result.get('skip_reason', 'Unknown')}")
                        else:
                            st.error(f"❌ OCR 辨識失敗: {result.get('error', 'Unknown error')}")
                    else:
                        st.error("拍攝照片失敗")
            
            # 處理完成，重置狀態
            st.session_state.processing = False
    
    with col2:
        st.header("📋 OCR Results History")
        
        if len(reader.ocr_results) == 0:
            st.info("尚無 OCR 結果")
        else:
            # 顯示結果列表
            for idx, result in enumerate(reader.ocr_results):
                with st.expander(f"📄 {result.get('datetime', 'Unknown')} - {result.get('status', 'unknown').upper()}", expanded=(idx == 0)):
                    # 顯示圖片
                    if 'image_path' in result and os.path.exists(result['image_path']):
                        img = cv2.imread(result['image_path'])
                        if img is not None:
                            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                            st.image(img_rgb, width='stretch')
                    
                    # 顯示 OCR 結果
                    if result.get('status') == 'completed':
                        st.text_area(
                            "OCR Text",
                            value=result.get('text', ''),
                            height=150,
                            key=f"ocr_text_{idx}",
                            disabled=True
                        )
                        
                        # 複製按鈕
                        st.code(result.get('text', ''), language=None)
                    elif result.get('status') == 'skipped':
                        st.warning(f"跳過原因: {result.get('skip_reason', 'Unknown')}")
                    else:
                        st.error(f"錯誤: {result.get('error', 'Unknown error')}")
                    
                    # 顯示時間戳
                    st.caption(f"ID: {result.get('id', 'Unknown')} | Time: {result.get('datetime', 'Unknown')}")
        
        # 清除結果按鈕
        if st.button("🗑️ Clear All Results", width='stretch'):
            reader.ocr_results = []
            reader._save_ocr_results()
            st.rerun()
    
    # 自動刷新預覽（僅在啟用預覽、啟用自動刷新且不在處理 OCR 時）
    if enable_preview and auto_refresh and not st.session_state.get('processing', False):
        # 追蹤相機失敗次數（用於延長刷新間隔）
        if 'camera_fail_count' not in st.session_state:
            st.session_state.camera_fail_count = 0
        
        # 直接嘗試初始化相機（不進行額外檢測）
        camera_available = False
        try:
            camera_available = reader._init_camera()
        except Exception as e:
            reader.logger.error(f"初始化相機時發生異常: {e}")
            camera_available = False
        
        # 只有在相機可用時才自動刷新
        if camera_available:
            # 重置失敗計數
            st.session_state.camera_fail_count = 0
            # 使用 Streamlit 的自動刷新功能
            # 調整刷新頻率，避免過快刷新導致畫面不穩定
            time.sleep(0.2)  # 約 5 FPS，減少刷新頻率以提升穩定性
            st.rerun()
        else:
            # 相機不可用時，增加失敗計數
            st.session_state.camera_fail_count += 1
            
            # 根據失敗次數調整刷新間隔
            # 失敗次數越多，刷新間隔越長（避免持續嘗試）
            if st.session_state.camera_fail_count <= 3:
                refresh_interval = 2.0  # 前 3 次失敗：2 秒
            elif st.session_state.camera_fail_count <= 10:
                refresh_interval = 5.0  # 4-10 次失敗：5 秒
            else:
                refresh_interval = 10.0  # 10 次以上失敗：10 秒
            
            reader.logger.warning(f"相機不可用（失敗 {st.session_state.camera_fail_count} 次），{refresh_interval} 秒後再檢查")
            time.sleep(refresh_interval)
            st.rerun()


if __name__ == '__main__':
    main()

