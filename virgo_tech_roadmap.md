# Virgo Agent — 技術路線圖：MVP → 正式產品

> 2026-06-18 | Ching-Hsien  
> 定位：實驗數據工作站（非文獻搜尋引擎）

---

## 一、現狀盤點（virgo_mvp.html）

| 層次 | 現況 | 評估 |
|------|------|------|
| **前端** | 單一 HTML + Vanilla JS + IndexedDB | 🟡 Demo 可用，但無法 scale |
| **後端** | `server.py`（簡易 HTTP + `/upload` + `/plot`） | 🔴 缺少 API 層 |
| **LLM** | 前端直連 DeepSeek API（Key 存 IndexedDB） | 🔴 資安風險 |
| **資料庫** | IndexedDB（瀏覽器內） | 🔴 無法跨裝置、雲端同步 |
| **繪圖** | Python matplotlib（server 端呼叫） | 🟢 已到位 |
| **簡報** | CSS 16:9 Present 模式 | 🟢 已到位，需打磨 |
| **授權** | 無 | 🔴 無法收費 |

---

## 二、競品對比：你不需要複製他們

| 競品功能 | 他們怎麼做 | Virgo 需要嗎？ | 原因 |
|----------|-----------|:---:|------|
| 學術資料庫 API | OpenAlex / Semantic Scholar | ❌ | 你不是文獻搜尋引擎 |
| 向量資料庫 | Pinecone / Qdrant | ⚠️ 未來 | 用戶上傳自有論文做內部 RAG（v2） |
| RAG 架構 | LangChain + Embedding | ⚠️ 未來 | 同上 |
| 文獻引用分析 | Scite.ai Smart Citations | ❌ | 非核心場景 |
| 前端框架 | Next.js + React + Tailwind | ✅ | 需要，Vue 亦可 |
| 後端 API | Python FastAPI | ✅ | 核心 |
| LLM 調用 | 後端代理 API call | ✅ | 安全 + API key 管理 |
| 雲端資料庫 | PostgreSQL / Supabase | ✅ | 取代 IndexedDB |
| 科學繪圖 | 無（他們不畫圖） | ✅ | **你的核心差異化** |
| 簡報模式 | 無 | ✅ | **你的核心差異化** |
| 用戶/訂閱系統 | Auth0 / Stripe | ✅ | 商業化必備 |

---

## 三、正式產品技術架構

```
┌─────────────────────────────────────────────────────┐
│                    Frontend                          │
│  React / Vue + Tailwind                             │
│  ├── Dashboard（專案列表）                            │
│  ├── 側欄導航（Purpose→Lit→Goals→Exp→Results）       │
│  ├── 科學繪圖區（Chart.js / 自訂 canvas）             │
│  ├── Present Mode                                   │
│  └── Skills 市集                                     │
├─────────────────────────────────────────────────────┤
│                  Backend (FastAPI)                   │
│  ├── /api/auth        用戶認證                       │
│  ├── /api/projects    CRUD 專案                      │
│  ├── /api/analyses    數據分析 + AI 生成              │
│  ├── /api/plot        matplotlib 繪圖                │
│  ├── /api/skills      Skills 管理                    │
│  └── /api/billing     Stripe 訂閱                    │
├─────────────────────────────────────────────────────┤
│                  Data Layer                          │
│  ├── PostgreSQL / Supabase   用戶 + 專案 + 數據       │
│  └── S3 / R2                 圖片儲存                 │
├─────────────────────────────────────────────────────┤
│                  AI Layer                            │
│  ├── DeepSeek / OpenAI / Claude API（後端代理）        │
│  └── matplotlib（Python subprocess）                  │
└─────────────────────────────────────────────────────┘
```

---

## 四、分階段路線圖

### Phase 1：後端化（1-2 週）

| 任務 | 說明 |
|------|------|
| FastAPI 後端 | 把 `server.py` 重構為 FastAPI |
| API Key 管理 | API key 從前端移到後端環境變數 |
| PostgreSQL 取代 IndexedDB | 用戶資料、專案、分析全上雲 |
| 用戶註冊/登入 | JWT or Supabase Auth |

**產出**：前端仍用 `virgo_mvp.html`，但 API call 全部走後端

### Phase 2：前端重建（2-3 週）

| 任務 | 說明 |
|------|------|
| React / Vue 重寫 | 保留現有 UI 設計語言 |
| 路由 | React Router，支援直接連結分享 |
| 響應式 | 手機/平板可用 |
| 狀態管理 | Zustand / Pinia |

**產出**：正式 SPA，可部署到 Vercel / Netlify

### Phase 3：訂閱商業化（1 週）

| 任務 | 說明 |
|------|------|
| Stripe 整合 | Free / Personal / Pro / Enterprise |
| 功能開關 | 依 tier 顯示/隱藏功能 |
| 用量限制 | API call 次數、專案數量 |

### Phase 4：Skills 市集（2-3 週）

| 任務 | 說明 |
|------|------|
| Skills 模板系統 | 後端存儲、前端編輯器 |
| 社群上傳 | 用戶可發布自訂 Skill |
| 版本管理 | Skill 更新不影響舊專案 |

### Phase 5：進階功能（持續）

| 任務 | 說明 |
|------|------|
| 協作模式 | 多人同時編輯專案 |
| 內部 RAG | 用戶上傳論文建私有知識庫 |
| 本機部署版 | Docker image 給資安敏感客戶 |
| API 開放 | 第三方可串接 Virgo 繪圖/分析 |

---

## 五、MVP 保留 vs 重建

| 功能 | 處理方式 |
|------|---------|
| Block Editor（Notion-like） | 🟢 保留邏輯，React 重寫 |
| 側欄導航 + 分頁系統 | 🟢 保留架構 |
| Present 模式 | 🟢 保留 CSS，打磨動畫 |
| AI Goals/Experimental 生成 | 🟢 保留 prompt，移到後端 |
| matplotlib `/plot` | 🟢 保留，加 cache |
| 檔案拖放上傳 | 🟢 保留 |
| IndexedDB 三層防護 | 🔴 廢棄，改用 PostgreSQL |
| `safeJSONParse` | 🟢 保留 |
| Chart.js fallback | 🟢 保留 |

---

## 六、立即可以做的小改進

不重寫架構，MVP 就能加：

1. **後端代理 DeepSeek API** — `server.py` 加 `/api/chat` 端點，前端不再曝露 API Key
2. **SQLite 過渡** — 先用 SQLite 代替 IndexedDB，後端管理，為 PostgreSQL 做準備
3. **匯出 PPTX** — Present 模式加「匯出 .pptx」按鈕（python-pptx）
4. **Skills JSON Schema** — 標準化 Skill 定義格式，為市集做準備
