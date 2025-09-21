# Jimmy's Space - 個人部落格

這是一個使用純 HTML, Tailwind CSS, 和 JavaScript 建立的靜態個人部落格網站。

## 技術棧

*   **前端**: HTML, JavaScript
*   **樣式**: Tailwind CSS
*   **部署**: Vercel

## 專案結構

所有公開的網站檔案都位於 `public` 資料夾中，這也是 Vercel 部署的網站根目錄。

*   `public/index.html`: 網站首頁。
*   `public/post.html`: 文章頁面模板。
*   `public/style.css`: 主要的 CSS 樣式檔案。
*   `public/main.js`: 首頁的 JavaScript 邏輯。
*   `public/post.js`: 文章頁面的 JavaScript 邏輯。
*   `public/posts/`: 存放部落格文章的 Markdown 檔案和 `posts.json` 索引。
*   `public/assets/`: 存放圖片等靜態資源。

## 運作方式

1.  `main.js` 會讀取 `public/posts/posts.json` 來在首頁上動態生成文章卡片列表。
2.  點擊文章卡片會跳轉到 `public/post.html`，並透過 URL 參數 (`?slug=...`) 傳遞文章的識別符。
3.  `post.js` 會根據 `slug` 參數讀取對應的 Markdown 檔案 (`/posts/slug.md`)，並使用 [Marked.js](https://marked.js.org/) 將其轉換為 HTML 顯示在頁面上。

## AI Startup School 字幕自動化流程

這個專案提供 `scripts/fetch_ai_startup_school.py`，協助從 YouTube 抓取 AI Startup School 影片的自動字幕，並轉換成部落格需要的 Markdown 格式（`###` 講者標題 + `<small>` 時間軸）。

### 前置需求

- macOS 或 Linux 上的 Python 3.9+。
- 已安裝 [`yt-dlp`](https://github.com/yt-dlp/yt-dlp)。Homebrew 使用者可以執行 `brew install yt-dlp`。

### 基本用法

```bash
# 抓取 posts.json 中每一筆影片，並覆寫對應的 Markdown 檔案
python scripts/fetch_ai_startup_school.py

# 只處理特定 slug（可重複指定）
python scripts/fetch_ai_startup_school.py --slug andrej-karpathy-software-is-changing-again

# 先下載字幕並快取，下次可用 --skip-download 直接重整 Markdown
python scripts/fetch_ai_startup_school.py --skip-download

# 查看結果但不寫回檔案
python scripts/fetch_ai_startup_school.py --slug ... --dry-run
```

### 輸出說明

- 產生的 Markdown 會保留原來 `<!-- summary -->` 區塊的內容（若檔案已存在）。
- 下載的 `.vtt` 字幕會放在 `.cache/ai_startup_school/<slug>/`，避免重複下載；可以手動清除這個資料夾以重新抓取字幕。
- 預設會在覆寫既有檔案前建立 `*.md.bak` 備份；使用 `--force` 可跳過備份並直接覆寫。
