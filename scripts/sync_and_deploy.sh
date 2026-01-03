#!/bin/bash

# 確保腳本在遇到錯誤時停止執行
set -e

# 檢查是否帶有 -y 或 --yes 參數以自動確認
AUTO_CONFIRM=false
if [[ "$1" == "-y" || "$1" == "--yes" ]]; then
    AUTO_CONFIRM=true
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  警告：未檢測到 OPENAI_API_KEY 環境變數。"
    echo "    若無 API Key，將無法執行自動翻譯與摘要生成。"
fi

# 確保安裝 openai 套件，避免 ModuleNotFoundError
python3 -m pip install openai
# 確保 yt-dlp 是最新的，避免 nsig extraction failed 錯誤
python3 -m pip install --upgrade yt-dlp

echo "🎬 [1/3] 開始執行：同步 YC AI Startup School 影片..."

# 執行 Python 爬蟲
# 1. 爬取播放清單更新 posts.json
# 2. 自動下載新影片字幕並生成 Markdown
python3 scripts/fetch_ai_startup_school.py --crawl-playlist "https://www.youtube.com/playlist?list=PLQ-uHSnFig5NPx4adxl97CZb8vU4numwi"

echo "--------------------------------------------------"
echo "✅ [2/3] 資料抓取完成！以下是變更的檔案："
git status public/posts

echo "⚠️  提醒：新抓取的文章標題預設為英文，日期為今天。"
echo "    若需修改中文標題或調整日期，請現在編輯 public/posts/posts.json，然後再手動提交。"
echo "--------------------------------------------------"

# 詢問是否要部署
if [ "$AUTO_CONFIRM" = true ]; then
    echo "🚀 [3/3] 自動確認部署 (-y)..."
    REPLY="y"
else
    read -p "🚀 [3/3] 是否要立即提交並推送到 Vercel？ (y/n) " -n 1 -r
    echo ""
fi
if [[ $REPLY =~ ^[Yy]$ ]]
then
    git add .
    git commit -m "Content Update: 自動同步 YC AI Startup School 最新影片"
    git push origin main
    echo "🎉 部署指令已發送！請至 Vercel Dashboard 查看進度。"
else
    echo "👌 已暫停。您可以手動檢查檔案 (public/posts/) 後再提交。"
fi