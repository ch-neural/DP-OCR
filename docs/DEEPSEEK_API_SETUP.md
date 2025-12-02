# DeepSeek-OCR API 服務安裝指南

## 概述

本閱讀機器人專案需要搭配 **DeepSeek-OCR API 服務**才能運作。本文檔詳細說明如何安裝和配置 API 服務。

---

## 🔗 官方倉庫

**DeepSeek-OCR API 服務**：[https://github.com/ch-neural/deepseek-ocr-api](https://github.com/ch-neural/deepseek-ocr-api)

這是一個高效能的 OCR API 服務，採用 DeepSeek-OCR 模型和 Unsloth 框架。

---

## 📦 安裝步驟

### 步驟 1：Clone 倉庫

```bash
# Clone DeepSeek-OCR API 服務
git clone https://github.com/ch-neural/deepseek-ocr-api.git
cd deepseek-ocr-api
```

### 步驟 2：安裝依賴

```bash
# 安裝 Python 依賴
pip install -r requirements.txt
```

**主要依賴**：
- `flask` - Web 框架
- `unsloth` - 加速推理框架
- `transformers` - Hugging Face 模型庫
- `torch` - PyTorch（需要 CUDA 版本）
- `pillow` - 圖像處理

### 步驟 3：Hugging Face 認證

DeepSeek-OCR 模型託管在 Hugging Face Hub，需要先登入：

```bash
# 登入 Hugging Face
huggingface-cli login
```

系統會提示輸入 Token：
1. 訪問 [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. 創建新 Token（需要 `read` 權限）
3. 複製 Token 並貼到終端

### 步驟 4：啟動 API 服務

```bash
# 啟動開發伺服器
python app.py
```

或使用生產模式（Gunicorn）：

```bash
chmod +x start_production.sh
./start_production.sh
```

**預設配置**：
- 監聽位址：`0.0.0.0:5000`
- 首次啟動會自動下載模型（約 6GB）
- 需要 GPU 支援（建議 8GB+ 顯存）

---

## ✅ 驗證安裝

### 測試 1：健康檢查

```bash
curl http://localhost:5000/health
```

**預期回應**：
```json
{
  "status": "healthy",
  "model": "DeepSeek-OCR",
  "timestamp": "2025-11-16T15:30:00"
}
```

### 測試 2：OCR 識別

準備一張測試圖片，然後：

```bash
curl -X POST http://localhost:5000/ocr \
  -F "file=@test_image.png"
```

**預期回應**：
```json
{
  "success": true,
  "text": "圖片中的文字內容",
  "filename": "test_image.png",
  "timestamp": "2025-11-16T15:31:00"
}
```

### 測試 3：Web UI

訪問 [http://localhost:5000](http://localhost:5000)，應該看到 DeepSeek-OCR API 的 Web 介面。

---

## ⚙️ 配置選項

### 修改監聽位址和埠號

編輯 `app.py` 或設定環境變數：

```bash
export FLASK_HOST="0.0.0.0"  # 監聽所有網路介面
export FLASK_PORT="5000"     # 埠號
```

### 修改上傳檔案大小限制

編輯 `config.py`：

```python
class Config:
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
```

### 調整 OCR 參數

編輯 `config.py`：

```python
class Config:
    OCR_BASE_SIZE = 1024      # 圖片預處理基準大小
    OCR_IMAGE_SIZE = 640      # 實際推理大小
    OCR_CROP_MODE = True      # 是否啟用裁切模式
    DEFAULT_PROMPT = "OCR: "  # 預設提示詞
```

---

## 🖥️ 系統需求

### 硬體需求

| 元件 | 最低需求 | 建議配置 |
|------|---------|---------|
| **CPU** | 4 核心 | 8 核心+ |
| **RAM** | 8 GB | 16 GB+ |
| **GPU** | NVIDIA GPU（4GB 顯存）| NVIDIA GPU（8GB+ 顯存）|
| **儲存空間** | 10 GB | 20 GB+ |

### 軟體需求

- **作業系統**：Linux（Ubuntu 20.04+ 推薦）
- **Python**：3.8+
- **CUDA**：11.8+ （GPU 版本）
- **NVIDIA Driver**：最新版本

### GPU 驅動安裝

Ubuntu/Debian：

```bash
# 安裝 NVIDIA 驅動
sudo apt update
sudo apt install nvidia-driver-535

# 安裝 CUDA Toolkit
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin
sudo mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600
sudo apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/3bf863cc.pub
sudo add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/ /"
sudo apt update
sudo apt install cuda

# 重新啟動
sudo reboot

# 驗證 GPU
nvidia-smi
```

---

## 🌐 網路配置

### 場景 1：同一台機器（本機）

閱讀機器人和 API 服務在同一台機器：

```ini
# config.ini
[API]
api_url = http://localhost:5000
```

### 場景 2：同一區網（不同機器）

API 服務在另一台區網機器：

```bash
# 1. 在 API 服務器上啟動（監聽所有介面）
python app.py --host 0.0.0.0

# 2. 查詢 API 服務器的 IP
ip addr show

# 3. 在閱讀機器人配置中設定
# config.ini
[API]
api_url = http://192.168.1.100:5000  # 替換為實際 IP
```

### 場景 3：跨網路（遠端伺服器）

API 服務在遠端伺服器：

```ini
# config.ini
[API]
api_url = http://your-server.com:5000
```

**注意事項**：
- 確保防火牆允許連接埠 5000
- 考慮使用 HTTPS（反向代理 + SSL）
- 建議設定認證機制（API Key）

---

## 🔧 故障排除

### 問題 1：模型下載失敗

**錯誤訊息**：`401 Client Error: Unauthorized`

**解決方法**：
1. 確認已執行 `huggingface-cli login`
2. 檢查 Token 權限（需要 `read` 權限）
3. 嘗試手動下載模型：
   ```bash
   huggingface-cli download unsloth/DeepSeek-OCR --local-dir ./deepseek_ocr
   ```

### 問題 2：GPU 無法偵測

**錯誤訊息**：`NotImplementedError: Unsloth cannot find any torch accelerator`

**解決方法**：
1. 確認 NVIDIA 驅動已安裝：`nvidia-smi`
2. 確認 CUDA 已安裝：`nvcc --version`
3. 重新安裝 PyTorch（CUDA 版本）：
   ```bash
   pip uninstall torch torchvision torchaudio
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

### 問題 3：記憶體不足

**錯誤訊息**：`CUDA out of memory`

**解決方法**：
1. 降低批次大小
2. 調整 OCR 參數（`OCR_BASE_SIZE`, `OCR_IMAGE_SIZE`）
3. 使用 4-bit 量化（已預設啟用）
4. 關閉其他 GPU 應用程式

### 問題 4：連接逾時

**錯誤訊息**：從閱讀機器人無法連接到 API

**解決方法**：
1. 確認 API 服務正在運行：`curl http://localhost:5000/health`
2. 檢查防火牆：`sudo ufw status`
3. 檢查埠號是否被佔用：`sudo netstat -tulpn | grep 5000`
4. 測試網路連接：`ping API_SERVER_IP`

---

## 📊 效能優化

### 1. 使用生產模式

```bash
# 使用 Gunicorn（多 worker）
./start_production.sh

# 或手動設定
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 2. 調整 OCR 參數

根據您的使用場景調整參數：

```python
# 快速模式（降低準確度）
OCR_BASE_SIZE = 512
OCR_IMAGE_SIZE = 320

# 平衡模式（推薦）
OCR_BASE_SIZE = 1024
OCR_IMAGE_SIZE = 640

# 高品質模式（更高準確度）
OCR_BASE_SIZE = 2048
OCR_IMAGE_SIZE = 1024
```

### 3. 啟用快取

對於重複的圖片，可以實作快取機制（需要自行開發）。

---

## 📚 進階配置

### 自訂提示詞

```bash
curl -X POST http://localhost:5000/ocr \
  -F "file=@invoice.png" \
  -F "prompt=請只提取發票上的金額"
```

### 批次處理

```bash
curl -X POST http://localhost:5000/ocr/batch \
  -F "files=@image1.png" \
  -F "files=@image2.png" \
  -F "files=@image3.png"
```

### Python 客戶端

```python
import requests

def ocr_image(image_path, api_url="http://localhost:5000"):
    with open(image_path, 'rb') as f:
        response = requests.post(
            f"{api_url}/ocr",
            files={'file': f}
        )
    return response.json()

# 使用
result = ocr_image("test.png")
print(result['text'])
```

---

## 🔐 安全性建議

### 1. 啟用 HTTPS

使用 Nginx 反向代理：

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. 添加認證

實作 API Key 認證（需要自行開發）。

### 3. 限制存取

使用防火牆限制只允許特定 IP 存取：

```bash
sudo ufw allow from 192.168.1.0/24 to any port 5000
```

---

## 📝 相關文檔

- [DeepSeek-OCR API 官方文檔](https://github.com/ch-neural/deepseek-ocr-api)
- [API 端點說明](https://github.com/ch-neural/deepseek-ocr-api#api-usage)
- [錯誤訊息參考](https://github.com/ch-neural/deepseek-ocr-api/blob/main/README/ERROR_MESSAGES.md)

---

## 🆘 獲取幫助

如果遇到問題：

1. 檢查 [常見問題](#故障排除)
2. 查看 API 服務日誌：`tail -f logs/app.log`
3. 到 [GitHub Issues](https://github.com/ch-neural/deepseek-ocr-api/issues) 搜尋類似問題
4. 提交新的 Issue（提供詳細的錯誤訊息和環境資訊）

---

**完成安裝後，記得測試 API 連接，然後就可以開始使用閱讀機器人了！** 🎉

