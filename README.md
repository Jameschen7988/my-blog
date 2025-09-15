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