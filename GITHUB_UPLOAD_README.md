# 上傳到 GitHub 說明

## 已完成的準備工作

### 1. ✅ 更新 .gitignore

已排除以下敏感和不需要的文件：
- `.env` 和所有環境變數檔案（包含 API Keys）
- `config.ini`（本地配置，每個環境不同）
- `ocr_results.json`（測試數據）
- 日誌檔案 (`*.log`)
- 拍攝的圖片 (`captured_images/*.jpg`, `*.png`)
- Python 快取檔案 (`__pycache__/`, `*.pyc`)
- IDE 設定檔 (`.vscode/`, `.idea/`)
- 部分內部文檔（CHANGELOG、細節修復記錄等）

### 2. ✅ 創建範例配置文件

- `config.ini.example` - 配置檔案範例（不包含實際 API 位址）
- `.env.example` - 環境變數範例（不包含實際 API Key）

### 3. ✅ 移除敏感信息

已從 `README/OPENAI_PREANALYSIS.md` 中移除實際的 OpenAI API Key。

### 4. ✅ 創建 .gitattributes

設定 Git LFS 追蹤大型檔案（音頻檔案）和行尾處理。

### 5. ✅ 保留目錄結構

創建 `.gitkeep` 文件以保留空目錄：
- `logs/.gitkeep`
- `captured_images/.gitkeep`
- `voices/.gitkeep`

---

## 上傳步驟

### 方法 1: 創建新倉庫並上傳

```bash
# 1. 初始化 Git 倉庫
cd /GPUData/working/Deepseek-OCR/example_bookReader
git init

# 2. 添加所有文件（.gitignore 會自動排除不需要的文件）
git add .

# 3. 查看將要提交的文件（確認沒有敏感信息）
git status

# 4. 提交
git commit -m "Initial commit: DeepSeek-OCR Book Reader

- Flask Web 介面和 Streamlit 介面
- Raspberry Pi GPIO 按鈕支援
- OpenAI 預分析功能
- USB 相機整合
- OCR 結果朗讀
- 完整的安裝和使用文檔"

# 5. 在 GitHub 上創建新倉庫
# 到 https://github.com/new 創建一個新倉庫
# 倉庫名稱建議：deepseek-ocr-book-reader

# 6. 連接到 GitHub 倉庫（替換成您的用戶名和倉庫名）
git remote add origin https://github.com/YOUR_USERNAME/deepseek-ocr-book-reader.git

# 7. 推送到 GitHub
git branch -M main
git push -u origin main
```

### 方法 2: 使用 SSH（如果已設定 SSH Key）

```bash
# 初始化和提交（同上）
git init
git add .
git commit -m "Initial commit: DeepSeek-OCR Book Reader"

# 使用 SSH URL
git remote add origin git@github.com:YOUR_USERNAME/deepseek-ocr-book-reader.git
git branch -M main
git push -u origin main
```

---

## 後續設置

### 1. 在 GitHub 上添加 README.md 封面

建議在 GitHub 倉庫設置中添加：
- **Description**: DeepSeek-OCR 閱讀機器人 - 支援 Raspberry Pi GPIO、Web 介面、語音朗讀
- **Topics**: `deepseek-ocr`, `raspberry-pi`, `ocr`, `book-reader`, `flask`, `computer-vision`
- **Website**: (如果有部署的話)

### 2. 添加 LICENSE

建議添加開源授權協議，例如 MIT License：

```bash
# 在 GitHub 上添加 LICENSE 文件
# Repository → Add file → Create new file
# 文件名: LICENSE
# 選擇模板: MIT License
```

### 3. 設置 GitHub Actions（可選）

可以設置 CI/CD 來自動測試代碼：
- Python linting (pylint, flake8)
- 依賴安全檢查 (dependabot)

---

## 檔案清單（將上傳的文件）

### 核心程式
- ✅ `book_reader.py` - 主程式（GPIO + OCR）
- ✅ `book_reader_flask.py` - Flask Web 介面
- ✅ `book_reader_streamlit.py` - Streamlit 介面
- ✅ `openai_vision_service.py` - OpenAI 預分析服務
- ✅ `test_gpio_button.py` - GPIO 按鈕測試工具
- ✅ `test_components.py` - 元件測試工具

### 配置文件
- ✅ `config.ini.example` - 配置範例
- ✅ `.env.example` - 環境變數範例
- ✅ `requirements.txt` - Python 依賴
- ✅ `.gitignore` - Git 忽略規則
- ✅ `.gitattributes` - Git 屬性設定

### 啟動腳本
- ✅ `start_reader.sh` - 啟動腳本
- ✅ `run_with_display.sh` - LCD 顯示啟動腳本
- ✅ `install_rpi5.sh` - Raspberry Pi 5 安裝腳本

### 文檔
- ✅ `README.md` - 主要說明文檔
- ✅ `QUICK_START.md` - 快速開始指南
- ✅ `PROJECT_SUMMARY.md` - 專案摘要
- ✅ `FILE_LIST.md` - 檔案清單
- ✅ `RASPBERRY_PI5_QUICKSTART.md` - RPi5 快速開始
- ✅ `gpio-button-test.service.example` - Systemd 服務範例

### README 目錄（保留的文檔）
- ✅ `README/CONFIGURATION.md`
- ✅ `README/ERROR_MESSAGES.md`
- ✅ `README/FLASK_INTERFACE.md`
- ✅ `README/GPIO_BUTTON_TEST.md`
- ✅ `README/INSTALLATION.md`
- ✅ `README/LCD_PREVIEW_GUIDE.md`
- ✅ `README/OPENAI_PREANALYSIS.md`
- ✅ `README/RASPBERRY_PI5_SETUP.md`
- ✅ `README/STREAMLIT_INTERFACE.md`
- ✅ `README/SYSTEM_CHECK.md`
- ✅ `README/TROUBLESHOOTING.md`
- ❌ `README/OPENAI_PREANALYSIS_CHANGELOG.md` (內部文檔，不上傳)
- ❌ `README/REQUEST_TIMEOUT_FIX.md` (內部文檔，不上傳)
- ❌ `README/CONTINUOUS_PREVIEW_FEATURE.md` (內部文檔，不上傳)
- ❌ `README/SIMULATION_MODE.md` (內部文檔，不上傳)

### 靜態資源
- ✅ `static/` - CSS/JS 文件
- ✅ `templates/` - HTML 模板
- ✅ `voices/.gitkeep` - 音頻目錄（空）

### 目錄結構佔位
- ✅ `logs/.gitkeep`
- ✅ `captured_images/.gitkeep`
- ✅ `voices/.gitkeep`

---

## 不會上傳的文件（已在 .gitignore 中）

### 敏感信息
- ❌ `.env` - 環境變數（包含 OpenAI API Key）
- ❌ `config.ini` - 本地配置（包含 API 位址）

### 運行時生成的文件
- ❌ `ocr_results.json` - OCR 結果（測試數據）
- ❌ `logs/*.log` - 日誌檔案
- ❌ `captured_images/*.jpg` - 拍攝的圖片
- ❌ `__pycache__/` - Python 快取

### IDE 和系統文件
- ❌ `.vscode/`, `.idea/` - IDE 設定
- ❌ `.DS_Store`, `Thumbs.db` - 系統檔案

---

## 檢查清單

在執行 `git push` 前，請確認：

- [ ] 已移除所有 API Keys
- [ ] 已移除實際的 API 位址（使用 localhost 或範例位址）
- [ ] `config.ini.example` 只包含範例配置
- [ ] `.env.example` 只包含佔位符
- [ ] `README/OPENAI_PREANALYSIS.md` 中的 API Key 已替換為範例
- [ ] 執行 `git status` 確認沒有敏感文件
- [ ] 檢查 `git diff` 確認修改正確

---

## 驗證命令

```bash
# 檢查哪些文件將被提交
git status

# 檢查 .gitignore 是否生效
git status --ignored

# 搜尋可能的敏感信息（在 git add 之前執行）
grep -r "sk-proj-" . 2>/dev/null | grep -v ".git" | grep -v "README"
grep -r "OPENAI_API_KEY=" . 2>/dev/null | grep -v ".git" | grep -v "example" | grep -v "README"

# 檢查 staged 的文件
git diff --cached --name-only
```

---

## 故障排除

### 問題 1: 推送失敗（身份驗證）

**錯誤**:
```
remote: Support for password authentication was removed on August 13, 2021.
```

**解決方案**:
使用 Personal Access Token (PAT) 代替密碼：
1. 到 https://github.com/settings/tokens
2. Generate new token (classic)
3. 選擇 `repo` 權限
4. 複製 token
5. 推送時使用 token 作為密碼

### 問題 2: 檔案太大

**錯誤**:
```
remote: error: File xxx.mp3 is 100.00 MB; this exceeds GitHub's file size limit of 100 MB
```

**解決方案**:
使用 Git LFS（已在 .gitattributes 中設定）：
```bash
git lfs install
git lfs track "*.mp3"
git add .gitattributes
git commit -m "Add Git LFS support"
```

### 問題 3: 不小心提交了敏感信息

**解決方案**:
```bash
# 從歷史記錄中移除敏感文件
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/sensitive/file" \
  --prune-empty --tag-name-filter cat -- --all

# 或使用 BFG Repo-Cleaner（推薦）
# https://rtyley.github.io/bfg-repo-cleaner/
```

---

## 完成後

上傳完成後，您的倉庫應該：
- ✅ 包含所有必要的程式碼和文檔
- ✅ 不包含任何敏感信息
- ✅ 其他人可以 clone 並使用（只需設定自己的 config.ini 和 .env）
- ✅ 有清晰的安裝和使用說明

祝上傳順利！🚀

