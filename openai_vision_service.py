#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI Vision 服務
用於圖像預分析，判斷場景類型和是否包含文字
"""

import os
import base64
import logging
from openai import OpenAI


class OpenAIVisionService:
    """
    OpenAI Vision 服務類別
    
    功能：
    1. 分析圖像場景（書本、PDF、街道、風景等）
    2. 判斷是否包含文字
    3. 生成適合的 OCR prompt
    """
    
    def __init__(self, api_key=None, model="gpt-4o-mini"):
        """
        初始化 OpenAI Vision 服務
        
        Args:
            api_key: OpenAI API Key，若為 None 則從環境變數讀取
            model: 使用的模型，預設為 gpt-4o-mini
        """
        self.logger = logging.getLogger('OpenAIVisionService')
        
        # 取得 API Key
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            error_msg = "未設定 OPENAI_API_KEY。請在 .env 檔案或環境變數中設定。"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        
        self.logger.info(f"OpenAI Vision 服務初始化完成，使用模型: {self.model}")
    
    def encode_image_to_base64(self, image_data):
        """
        將圖像數據編碼為 base64
        
        Args:
            image_data: 圖像的 bytes 數據
            
        Returns:
            str: base64 編碼的圖像字串
        """
        return base64.b64encode(image_data).decode('utf-8')
    
    def analyze_image(self, image_data):
        """
        分析圖像內容
        
        Args:
            image_data: 圖像的 bytes 數據（JPEG 格式）
            
        Returns:
            dict: 分析結果
                {
                    'has_text': bool,           # 是否包含文字
                    'scene_type': str,          # 場景類型
                    'scene_description': str,   # 場景描述
                    'text_regions': str,        # 文字區域描述
                    'confidence': str,          # 置信度
                    'suggested_prompt': str,    # 建議的 OCR prompt
                    'raw_response': str         # 原始回應
                }
                
                若發生錯誤則返回
                {
                    'error': str,               # 錯誤訊息
                    'has_text': False
                }
        """
        self.logger.info("開始分析圖像...")
        
        # 將圖像編碼為 base64
        base64_image = self.encode_image_to_base64(image_data)
        
        # 構建分析提示詞
        analysis_prompt = """請仔細分析這張圖片，並以 JSON 格式回答以下問題：

1. 這張圖片是否包含任何文字內容（包括中文、英文、數字等）？
2. 圖片的場景類型是什麼？（例如：書本、翻開的書、PDF頁、名片、海報、街道、風景、室內、物品等）
3. 如果包含文字，請描述文字出現在圖片的哪些區域（例如：整頁、上半部、中央、表格中等）
4. 如果包含文字，文字的類型是什麼？（例如：印刷體、手寫、標題、正文、表格、標籤等）
5. 您對這個判斷的置信度如何？（高、中、低）

請以以下 JSON 格式回答（不要包含其他文字）：
{
  "has_text": true/false,
  "scene_type": "場景類型",
  "scene_description": "場景的詳細描述",
  "text_regions": "文字區域描述（如果有文字）",
  "text_type": "文字類型（如果有文字）",
  "confidence": "高/中/低"
}
"""
        
        # 發送請求到 OpenAI API（加上錯誤處理）
        from openai import OpenAIError, APIError, RateLimitError, APIConnectionError
        import json
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": analysis_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.3  # 較低的溫度以獲得更一致的結果
            )
            
            # 提取回應
            raw_response = response.choices[0].message.content.strip()
            self.logger.info(f"OpenAI 原始回應: {raw_response}")
            
            # 解析 JSON 回應
            # 嘗試提取 JSON（可能被包在 ```json ``` 中）
            json_str = raw_response
            if '```json' in raw_response:
                json_str = raw_response.split('```json')[1].split('```')[0].strip()
            elif '```' in raw_response:
                json_str = raw_response.split('```')[1].split('```')[0].strip()
            
            analysis_result = json.loads(json_str)
            
            # 添加原始回應
            analysis_result['raw_response'] = raw_response
            
            # 如果包含文字，生成建議的 OCR prompt
            if analysis_result.get('has_text', False):
                suggested_prompt = self._generate_ocr_prompt(analysis_result)
                analysis_result['suggested_prompt'] = suggested_prompt
                
                self.logger.info(f"✅ 圖像包含文字")
                self.logger.info(f"   場景類型: {analysis_result.get('scene_type', 'N/A')}")
                self.logger.info(f"   文字區域: {analysis_result.get('text_regions', 'N/A')}")
                self.logger.info(f"   建議 Prompt: {suggested_prompt}")
            else:
                analysis_result['suggested_prompt'] = None
                self.logger.info(f"❌ 圖像不包含文字，跳過 OCR")
                self.logger.info(f"   場景類型: {analysis_result.get('scene_type', 'N/A')}")
            
            return analysis_result
            
        except RateLimitError as rate_err:
            error_msg = f"OpenAI API 速率限制錯誤: {str(rate_err)}"
            self.logger.error(error_msg)
            return {'error': error_msg, 'has_text': False}
            
        except APIConnectionError as conn_err:
            error_msg = f"OpenAI API 連線錯誤: {str(conn_err)}"
            self.logger.error(error_msg)
            return {'error': error_msg, 'has_text': False}
            
        except APIError as api_err:
            error_msg = f"OpenAI API 錯誤: {str(api_err)}"
            self.logger.error(error_msg)
            return {'error': error_msg, 'has_text': False}
            
        except json.JSONDecodeError as json_err:
            error_msg = f"解析 OpenAI 回應 JSON 失敗: {str(json_err)}"
            self.logger.error(error_msg)
            self.logger.error(f"原始回應: {raw_response if 'raw_response' in locals() else 'N/A'}")
            return {'error': error_msg, 'has_text': False}
            
        except OpenAIError as openai_err:
            error_msg = f"OpenAI 錯誤: {str(openai_err)}"
            self.logger.error(error_msg)
            return {'error': error_msg, 'has_text': False}
            
        except Exception as general_err:
            error_msg = f"圖像分析發生未預期的錯誤: {str(general_err)}"
            self.logger.error(error_msg)
            import traceback
            self.logger.error(f"錯誤詳情:\n{traceback.format_exc()}")
            return {'error': error_msg, 'has_text': False}
    
    def _generate_ocr_prompt(self, analysis_result):
        """
        根據分析結果生成適合的 OCR prompt
        
        Args:
            analysis_result: analyze_image 返回的分析結果
            
        Returns:
            str: 建議的 OCR prompt
        """
        scene_type = analysis_result.get('scene_type', '').lower()
        text_regions = analysis_result.get('text_regions', '')
        text_type = analysis_result.get('text_type', '')
        scene_description = analysis_result.get('scene_description', '')
        
        # 根據場景類型生成不同的 prompt
        prompt_template = "<image>\n"
        
        if '書' in scene_type or 'book' in scene_type:
            prompt_template += "這是一本書的內容。請辨識頁面中的所有文字，保留原始的段落和換行格式。"
        
        elif 'pdf' in scene_type or '文件' in scene_type or 'document' in scene_type:
            prompt_template += "這是一個 PDF 文件頁面。請辨識頁面中的所有文字內容。"
        
        elif '名片' in scene_type or 'card' in scene_type:
            prompt_template += "這是一張名片。請辨識名片上的所有資訊，包括姓名、職稱、公司、電話、郵箱等。"
        
        elif '表格' in scene_type or 'table' in scene_type or '表格' in text_type:
            prompt_template += "圖片中包含表格。請辨識表格中的所有內容，並盡可能保留表格結構。"
        
        elif '海報' in scene_type or 'poster' in scene_type or '標題' in text_type:
            prompt_template += "這是一張海報或標題內容。請辨識圖片中的所有文字，注意標題和正文的層次。"
        
        elif '手寫' in text_type or 'handwritten' in text_type:
            prompt_template += "圖片中包含手寫文字。請盡可能辨識手寫的內容。"
        
        elif '標籤' in scene_type or 'label' in scene_type:
            prompt_template += "這是一個標籤或標示。請辨識標籤上的所有文字和資訊。"
        
        else:
            # 通用 prompt
            prompt_template += f"這是一張包含文字的圖片（{scene_type}）。請辨識圖片中的所有文字內容。"
        
        # 如果有特定的文字區域描述，添加到 prompt 中
        if text_regions and text_regions != 'N/A':
            prompt_template += f" 文字主要位於：{text_regions}。"
        
        return prompt_template
    
    def should_perform_ocr(self, image_data):
        """
        判斷是否應該執行 OCR
        
        這是一個便利方法，整合了圖像分析和判斷邏輯
        
        Args:
            image_data: 圖像的 bytes 數據（JPEG 格式）
            
        Returns:
            tuple: (should_ocr, prompt_or_reason)
                - should_ocr: bool, 是否應該執行 OCR
                - prompt_or_reason: str, 如果應該執行則返回建議的 prompt，
                                         否則返回不執行的原因
        """
        # 加上錯誤處理
        from openai import OpenAIError, APIError, RateLimitError, APIConnectionError
        import json
        
        analysis_result = self.analyze_image(image_data)
        
        # 檢查是否發生錯誤
        if 'error' in analysis_result:
            error_msg = analysis_result['error']
            self.logger.error(f"======== OpenAI 圖像分析錯誤 ========")
            self.logger.error(f"錯誤訊息: {error_msg}")
            self.logger.error(f"======================================")
            # 發生錯誤時，預設執行 OCR（以免漏掉有文字的圖像）
            return True, '<image>\nFree OCR.'
        
        # 判斷是否包含文字
        has_text = analysis_result.get('has_text', False)
        
        if has_text:
            suggested_prompt = analysis_result.get('suggested_prompt', '<image>\nFree OCR.')
            return True, suggested_prompt
        else:
            scene_type = analysis_result.get('scene_type', '未知場景')
            reason = f"圖像不包含文字（場景類型: {scene_type}）"
            return False, reason


def test_openai_vision_service():
    """測試 OpenAI Vision 服務"""
    import cv2
    
    print("=" * 60)
    print("OpenAI Vision 服務測試")
    print("=" * 60)
    
    # 初始化服務
    service = OpenAIVisionService()
    print("✅ 服務初始化成功")
    
    # 讀取測試圖片
    test_image_path = "captured_images/capture_20251111_110512.jpg"
    
    if not os.path.exists(test_image_path):
        print(f"❌ 找不到測試圖片: {test_image_path}")
        return
    
    # 讀取圖片
    frame = cv2.imread(test_image_path)
    _, img_encoded = cv2.imencode('.jpg', frame)
    image_data = img_encoded.tobytes()
    
    print(f"\n測試圖片: {test_image_path}")
    print("正在分析圖像...")
    
    # 執行分析
    should_ocr, result = service.should_perform_ocr(image_data)
    
    print("\n" + "=" * 60)
    print("分析結果:")
    print("=" * 60)
    
    if should_ocr:
        print(f"✅ 應該執行 OCR")
        print(f"\n建議的 Prompt:")
        print(result)
    else:
        print(f"❌ 不應執行 OCR")
        print(f"\n原因: {result}")
    
    print("=" * 60)


if __name__ == '__main__':
    # 載入 .env 檔案
    from dotenv import load_dotenv
    load_dotenv()
    
    # 執行測試
    test_openai_vision_service()

