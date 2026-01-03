# Engineering Specifications & Tickets

**對應 PRD 版本**: 1.1
**目標**: 將產品需求轉化為具體的技術實作任務。

---

## Phase 1: Content Value & Hygiene (立即執行)

### Ticket 1.1: 實作「編輯點評」區塊 (Editor's Take)
**優先級:** High
**類型:** Backend / Python Script
**目標:** 在自動生成的文章中預留空間，讓站長可以手動添加個人觀點，且在重新生成時不會被覆蓋。

**實作細節:**
1.  **檔案:** `scripts/fetch_ai_startup_school.py`
2.  **函式:** `build_markdown`
3.  **邏輯:**
    *   在 `<!-- endsummary -->` 之後，插入新的 HTML 註解區塊：
        ```markdown
        <!-- my_take -->
        > **編輯點評**：在此處添加您的觀點...
        <!-- end_my_take -->
        ```
4.  **函式:** 新增 `read_existing_my_take(path)` (參考 `read_existing_summary`)
    *   **邏輯:** 在覆寫檔案前，先讀取舊檔中的 `my_take` 內容。如果存在且不為預設值，則保留該內容傳入 `build_markdown`，避免每次執行腳本都把辛苦寫的點評洗掉。

**驗收標準 (Acceptance Criteria):**
*   執行腳本後，Markdown 檔案包含 `<!-- my_take -->` 區塊。
*   手動修改點評內容後，再次執行腳本，內容**不會**被重置。

### Ticket 1.2: 標籤雲與相關文章 (Tag Cloud & Related Posts)
**優先級:** Medium
**類型:** Frontend / JS
**目標:** 增加使用者在網站的停留時間與內容發現率。

**實作細節:**
1.  **首頁 (`public/main.js`, `public/index.html`):**
    *   讀取 `posts.json`，提取所有不重複的 `tags`。
    *   在文章列表上方渲染「標籤雲」區域（Button List）。
    *   監聽 URL 參數 `?tag=...`。若有參數，則過濾 `posts` 陣列，只顯示符合的文章。
2.  **文章頁 (`public/post.js`):**
    *   讀取當前文章的 `tags`。
    *   遍歷 `posts.json`，找出擁有相同標籤的其他文章（排除自己）。
    *   在文章底部渲染「延伸閱讀」區塊，顯示 3 篇相關文章連結。

**驗收標準:**
*   首頁點擊標籤可篩選文章列表。
*   文章頁底部顯示相關推薦。

### Ticket 1.3: 修正影片發布日期 (Sync Video Date)
**優先級:** High
**類型:** Backend / Python Script
**目標:** 確保文章顯示的是影片的原始發布日，而非爬蟲抓取日。

**實作細節:**
1.  **檔案:** `scripts/fetch_ai_startup_school.py`
2.  **函式:** `crawl_playlist`
3.  **邏輯:**
    *   `yt-dlp` 的 JSON dump 中包含 `upload_date` 欄位 (格式通常為 `YYYYMMDD`)。
    *   解析該日期並轉換為 `YYYY-MM-DD` 格式。
    *   更新 `new_post` 物件中的 `date` 欄位。
    *   (可選) 寫一個一次性腳本或邏輯來更新現有 `posts.json` 中的舊日期。

**驗收標準:**
*   `posts.json` 中的 `date` 欄位準確反映 YouTube 影片的上傳時間。

---

## Phase 2: Community & Discovery (核心功能)

### Ticket 2.1: 站內搜尋 (Client-Side Search)
**優先級:** Medium
**類型:** Full Stack
**目標:** 讓使用者能透過關鍵字找到內容。

**實作細節:**
1.  **後端 (`scripts/fetch_ai_startup_school.py`):**
    *   新增函式 `generate_search_index()`。
    *   在每次執行結束前，生成一個輕量級的 `public/search-index.json`，包含 `slug`, `title`, `excerpt`, `tags` (暫不包含全文以節省流量)。
2.  **前端 (`public/main.js`):**
    *   在 Header 加入搜尋輸入框 `<input type="search">`。
    *   載入 `search-index.json`。
    *   使用簡單的字串比對 (或引入 `Fuse.js`) 進行即時過濾。

**驗收標準:**
*   輸入關鍵字（如 "Agent"）能即時顯示匹配的文章標題。

### Ticket 2.2: Giscus 留言系統整合
**優先級:** Low
**類型:** Frontend
**目標:** 建立讀者互動管道。

**實作細節:**
1.  **前置作業:** 在 GitHub Repo 開啟 Discussions 功能，並安裝 Giscus App 取得設定碼。
2.  **檔案:** `public/post.js` (動態插入) 或 `public/post.html`。
3.  **邏輯:**
    *   在文章內容容器的最下方，插入 Giscus 的 `<script>` 標籤。
    *   設定 mapping 為 `pathname` 或 `slug`。

**驗收標準:**
*   文章底部出現留言框。
*   留言後內容會同步出現在 GitHub Discussions。

---

## Phase 3: Brand & Loyalty (專業化)

### Ticket 3.1: 術語表感知翻譯 (Glossary-Aware Translation)
**優先級:** Medium
**類型:** Backend / AI Prompting
**目標:** 提升翻譯的專業度與一致性。

**實作細節:**
1.  **新增檔案:** 專案根目錄建立 `glossary.json`。
    ```json
    {
      "Agent": "智能體",
      "Scaling Law": "擴展定律",
      "Transformer": "Transformer"
    }
    ```
2.  **檔案:** `scripts/fetch_ai_startup_school.py`
3.  **邏輯:**
    *   讀取 `glossary.json`。
    *   修改 `translate_to_chinese` 和 `translate_batch` 的 System Prompt，加入：「請遵循以下術語表進行翻譯：{glossary_content}」。

**驗收標準:**
*   新生成的文章中，特定術語（如 Agent）被準確翻譯為指定詞彙（如 智能體）。