# Product Requirements Document (PRD): My Blog - YC AI Startup School Knowledge Platform

**版本**: 1.1
**狀態**: 進行中
**最後更新**: 2025-05-20

---

## 1. 專案概述 (Executive Summary)
本專案旨在將現有的自動化部落格（專注於 YC AI Startup School 內容）轉型為一個具備深度觀點、社群互動與高專業度的知識平台。目前的系統已具備高度自動化的內容生成能力（爬蟲、翻譯、摘要），下一階段將著重於從「內容聚合」轉向「知識策展」，建立個人品牌權威性。

## 2. 目標受眾 (Target Audience)
*   **創業家 (The Founder)**：尋找 AI 創業的商業模式、護城河與策略洞察。
*   **工程師 (The Engineer)**：關注技術實作細節、Scaling Laws 與架構設計。
*   **投資人/分析師 (The Analyst)**：追蹤 YC 觀點與 AI 產業趨勢。

## 3. 成功指標 (Success Metrics)
*   **參與度 (Engagement)**：平均頁面停留時間 > 3 分鐘（反映讀者深度閱讀逐字稿與點評）。
*   **回訪率 (Retention)**：回訪使用者佔比提升 20%。
*   **搜尋能見度 (SEO)**：針對特定 AI 關鍵字（如 "AI Agent 創業"）的自然搜尋排名進入首頁。

## 4. 現況分析 (Current State Analysis)

### 核心優勢 (Strengths)
*   **自動化內容流**：已打通「發現 -> 下載 -> 翻譯 -> 摘要 -> 部署」全流程，營運成本極低。
*   **利基市場**：專注於高品質 YC 內容，受眾精準且含金量高。
*   **雙模態內容**：提供「快速摘要」與「深度逐字稿」，滿足不同閱讀場景。

### 成長機會 (Opportunities)
*   **缺乏原創觀點**：目前僅為資訊搬運，缺乏站長的深度解讀，難以建立品牌黏性。
*   **互動性為零**：缺乏評論與社群功能，讀者看完即走。
*   **內容孤島**：缺乏標籤與搜尋，舊文章難以被發掘。

---

## 5. 產品路線圖 (Product Roadmap)

### Phase 1: 內容價值與數據正確性 (Content Value & Hygiene)
**目標**：利用現有資源，以最小工程成本快速提升專業度與閱讀體驗。

#### 1.1 編輯點評 (Editor's Take)
*   **User Story**: 作為讀者，我希望在閱讀長篇逐字稿前，先看到站長對該影片的獨到見解與重點畫線，以決定是否深入閱讀。
*   **功能規格**:
    *   修改 Python 爬蟲，在 Markdown 生成時預留 `<!-- my_take -->` 區塊。
    *   前端樣式需區隔「AI 摘要」與「編輯點評」，後者應具備更強烈的個人風格（如引用樣式）。

#### 1.2 標籤雲與關聯推薦 (Tag Cloud & Related Posts)
*   **User Story**: 作為讀者，當我讀完一篇關於 "LLM" 的文章後，我希望能自動看到其他關於 "LLM" 的 YC 課程，以便進行主題式學習。
*   **功能規格**:
    *   **列表頁**: 支援 URL 參數篩選 (e.g., `?tag=Agent`)。
    *   **文章頁**: 底部新增「延伸閱讀」區塊，邏輯為：同標籤 > 同講者 > 時間相近。

#### 1.3 修正影片發布日期 (Data Integrity)
*   **User Story**: 作為讀者，我需要知道這場演講的「原始發生時間」而非「部落格抓取時間」，以判斷技術的時效性。
*   **功能規格**:
    *   Python 腳本需從 `yt-dlp` metadata 提取 `upload_date`。
    *   若無 metadata，則 fallback 至當前日期並標記。

---

### Phase 2: 社群互動與檢索 (Community & Discovery)
**目標**：增加使用者停留時間，將單向閱讀轉化為雙向交流。

#### 2.1 站內搜尋 (Site Search)
*   **User Story**: 作為讀者，我想搜尋「Scaling Laws」並找到所有相關段落，而不僅僅是標題匹配。
*   **功能規格**:
    *   **後端**: Python 生成 `search-index.json` (包含 slug, title, tags, summary)。
    *   **前端**: 整合 `Fuse.js` 進行客戶端模糊搜尋，提供即時 (Instant) 搜尋體驗。

#### 2.2 留言系統 (Comment System)
*   **User Story**: 作為讀者，我想針對文章內容提問或分享我的實作經驗。
*   **功能規格**:
    *   整合 **Giscus** (基於 GitHub Discussions)。
    *   優點：無廣告、免費、過濾垃圾訊息能力強、適合開發者受眾。

---

### Phase 3: 品牌深化與訂閱 (Brand & Loyalty)
**目標**：建立長期讀者關係，提升內容專業度。

#### 3.1 術語表感知翻譯 (Glossary-Aware Translation)
*   **User Story**: 作為專業讀者，我不希望看到 "Agent" 被翻譯成「代理人」這種生硬詞彙，希望看到「智能體」等更符合語境的翻譯。
*   **功能規格**:
    *   建立 `glossary.json` (e.g., `{"Agent": "智能體", "Scaling Law": "擴展定律"}`)。
    *   Python 腳本在呼叫 OpenAI API 時，動態注入術語表至 System Prompt。

#### 3.2 電子報訂閱 (Newsletter)
*   **User Story**: 作為忠實讀者，我希望在新課程上線時收到 Email 通知。
*   **功能規格**:
    *   頁尾嵌入訂閱表單 (Substack / ConvertKit)。
    *   自動化工作流：新文章部署 -> 觸發 Webhook -> 發送電子報 (可選)。

---

## 6. 非功能性需求 (Non-Functional Requirements)
*   **效能 (Performance)**: Google Lighthouse Performance 分數需 > 90。
*   **SEO**: 每篇文章需自動生成 Open Graph Image (可使用影片封面圖) 與 Meta Description。
*   **可維護性**: Python 腳本需具備 Error Handling，OpenAI API 額度不足時需有 Graceful Degradation (如保留原文)。

## 7. 風險評估 (Risks & Mitigation)
*   **Risk**: YouTube 字幕品質不佳或無字幕。
    *   *Mitigation*: 整合 Whisper API 作為 fallback，自行生成字幕（成本較高，需監控）。
*   **Risk**: OpenAI API 成本失控。
    *   *Mitigation*: 實作 Token 預估與預算上限警告；針對長影片進行摘要而非全文翻譯。

## 8. 技術架構 (Technical Architecture)
*   **Core Script**: `scripts/fetch_ai_startup_school.py` (Orchestrator)
*   **Frontend**: Vanilla JS + Tailwind CSS (保持輕量，無須 React/Vue)
*   **Database**: `public/posts/posts.json` (Flat file database)
*   **Hosting**: Vercel (CI/CD 自動化)