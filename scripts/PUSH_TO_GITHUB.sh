#!/bin/bash

# DeepSeek-OCR Book Reader - GitHub 推送腳本
# 此腳本會將專案推送到 GitHub

set -e  # 發生錯誤時停止

echo "============================================"
echo "DeepSeek-OCR Book Reader - GitHub 推送"
echo "============================================"
echo ""

# 檢查是否已經提交
if [ -z "$(git log --oneline 2>/dev/null)" ]; then
    echo "❌ 錯誤：尚未進行任何提交"
    echo "請先執行："
    echo "  git add ."
    echo "  git commit -m 'Initial commit'"
    exit 1
fi

# 顯示當前狀態
echo "📊 當前倉庫狀態："
echo "  總提交數: $(git rev-list --count HEAD)"
echo "  總文件數: $(git ls-files | wc -l)"
echo "  倉庫大小: $(du -sh . | cut -f1)"
echo ""

# 檢查是否有未提交的變更
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  警告：有未提交的變更"
    echo ""
    git status --short
    echo ""
    read -p "是否要先提交這些變更？(y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add .
        read -p "請輸入提交訊息: " commit_msg
        git commit -m "$commit_msg"
        echo "✅ 變更已提交"
    else
        echo "⚠️  將推送現有提交，未提交的變更不會被推送"
    fi
fi

echo ""
echo "============================================"
echo "設定 GitHub 遠端倉庫"
echo "============================================"
echo ""

# 檢查是否已設定遠端倉庫
if git remote | grep -q "origin"; then
    echo "ℹ️  已設定遠端倉庫："
    git remote -v
    echo ""
    read -p "是否要更新遠端倉庫 URL？(y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "請輸入新的 GitHub 倉庫 URL: " repo_url
        git remote set-url origin "$repo_url"
        echo "✅ 遠端倉庫 URL 已更新"
    fi
else
    echo "請在 GitHub 上創建新倉庫："
    echo "  1. 訪問 https://github.com/new"
    echo "  2. 倉庫名稱建議：deepseek-ocr-book-reader"
    echo "  3. 設為 Public 或 Private（視需求）"
    echo "  4. 不要勾選「Initialize with README」（我們已有 README）"
    echo ""
    read -p "請輸入 GitHub 倉庫 URL (HTTPS 或 SSH): " repo_url
    
    # 驗證 URL 格式
    if [[ ! $repo_url =~ ^(https://github.com/|git@github.com:) ]]; then
        echo "❌ 錯誤：無效的 GitHub URL"
        echo "URL 應該類似："
        echo "  HTTPS: https://github.com/username/repo.git"
        echo "  SSH:   git@github.com:username/repo.git"
        exit 1
    fi
    
    git remote add origin "$repo_url"
    echo "✅ 遠端倉庫已設定"
fi

echo ""
echo "============================================"
echo "最終檢查"
echo "============================================"
echo ""

# 檢查敏感信息
echo "🔍 檢查敏感信息..."
if git ls-files | grep -qE "^\.env$|^config\.ini$"; then
    echo "❌ 錯誤：發現敏感文件將被推送"
    git ls-files | grep -E "^\.env$|^config\.ini$"
    echo ""
    echo "請檢查 .gitignore 設定"
    exit 1
fi

# 檢查是否有完整的 API Key
if git grep -qE "sk-proj-[a-zA-Z0-9]{50,}" HEAD; then
    echo "❌ 錯誤：發現可能的 API Key"
    git grep -E "sk-proj-[a-zA-Z0-9]{50,}" HEAD
    echo ""
    echo "請移除 API Key 後重新提交"
    exit 1
fi

echo "✅ 安全檢查通過"
echo ""

# 顯示將要推送的內容
echo "📦 將要推送的提交："
git log --oneline --graph --decorate --all | head -10
echo ""

# 最終確認
echo "⚠️  注意事項："
echo "  - 確保您已經在 GitHub 上創建了倉庫"
echo "  - 確保您的 GitHub 認證已設定（SSH Key 或 Personal Access Token）"
echo "  - 音頻檔案較大，推送可能需要一些時間"
echo ""
read -p "確定要推送到 GitHub 嗎？(y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 已取消推送"
    exit 0
fi

echo ""
echo "============================================"
echo "推送到 GitHub"
echo "============================================"
echo ""

# 將 master 重命名為 main（如果需要）
current_branch=$(git branch --show-current)
if [ "$current_branch" = "master" ]; then
    echo "📝 將分支重命名為 main..."
    git branch -M main
fi

# 推送到 GitHub
echo "🚀 正在推送..."
if git push -u origin main; then
    echo ""
    echo "============================================"
    echo "✅ 推送成功！"
    echo "============================================"
    echo ""
    
    # 顯示倉庫 URL
    repo_url=$(git remote get-url origin)
    if [[ $repo_url =~ github.com[:/]([^/]+)/([^/.]+) ]]; then
        username=${BASH_REMATCH[1]}
        reponame=${BASH_REMATCH[2]%.git}
        echo "📁 您的倉庫："
        echo "   https://github.com/$username/$reponame"
        echo ""
        echo "🎉 專案已成功上傳到 GitHub！"
        echo ""
        echo "📝 後續步驟："
        echo "  1. 在 GitHub 上添加倉庫描述和主題標籤"
        echo "  2. 考慮添加 LICENSE 文件（建議 MIT License）"
        echo "  3. 設定 GitHub Pages（如果需要）"
        echo "  4. 邀請協作者（如果需要）"
    fi
else
    echo ""
    echo "============================================"
    echo "❌ 推送失敗"
    echo "============================================"
    echo ""
    echo "可能的原因："
    echo "  1. GitHub 認證失敗"
    echo "     解決：設定 SSH Key 或使用 Personal Access Token"
    echo "     參考：https://docs.github.com/en/authentication"
    echo ""
    echo "  2. 遠端倉庫不存在"
    echo "     解決：在 GitHub 上創建倉庫"
    echo ""
    echo "  3. 網路連接問題"
    echo "     解決：檢查網路連接"
    echo ""
    echo "  4. 倉庫已存在內容"
    echo "     解決：使用 git pull --rebase origin main"
    exit 1
fi

