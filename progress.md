# Virgo Agent — 進度追蹤

> **開始日期**: 2026-07-16
> **交接來源**: `C:\Users\satb0\hermes-shared\inbox\handoff.txt`
> **技術負責**: Astraea | **文件**: Heidi | **驗收**: Ching-Hsien

## Phase 1: 後端化 (FastAPI + Supabase + API Key 後端代理) ✅ 核心完成

### Task 1: 專案結構與基礎設施 ✅
- [x] FastAPI 應用骨架 (`main.py`)
- [x] requirements.txt
- [x] 環境設定 config.py / .env.example
- [x] progress.md

### Task 2: Auth 模組 ✅
- [x] API Key 生成 (`models.py: generate_api_key()`)
- [x] JWT token 發行 (`auth.py: create_jwt()`)
- [x] Bearer token 驗證中介層
- [x] 端點：POST /api/auth/register, POST /api/auth/login
- [x] 端點：GET/POST/DELETE /api/auth/api-keys

### Task 3: Projects CRUD ✅
- [x] SQLite 資料模型 (users, projects, plots, api_keys)
- [x] CRUD 端點 (GET/POST/PATCH/DELETE /api/projects)
- [x] 使用者隔離驗證
- [x] Supabase 遷移 SQL 及 RLS 政策

### Task 4: Chat 端點 ✅
- [x] LLM API Key 代理層 (OpenRouter / OpenAI / Anthropic)
- [x] SSE 串流支援
- [x] POST /api/chat/completions, /api/chat/completions/stream

### Task 5: Plot 端點 ✅
- [x] matplotlib 科學繪圖 (scatter, line, bar, histogram, heatmap)
- [x] Base64 PNG 輸出
- [x] CRUD: POST /api/plots, GET /api/plots/project/{id}, GET/DELETE /api/plots/{id}

### Task 6: Supabase 整合 ✅
- [x] supabase_client.py — supabase-py 客戶端
- [x] supabase_migrate.py — DDL 遷移 SQL + RLS 政策
- [ ] 實際部署至 Supabase（需 SUPABASE_URL + SUPABASE_SERVICE_KEY）

### Task 7: 測試 ✅
- [x] 15 項 pytest 整合測試全通過
- [x] 涵蓋：health, auth (註冊/登入/API key CRUD), projects CRUD, 使用者隔離, plots (5 種類型), 未授權防護, chat 503

## 檔案結構
```
~/virgo-agent/
├── main.py              # FastAPI 入口 (lifespan DB init)
├── config.py            # pydantic-settings
├── models.py            # SQLAlchemy 模型 + init_db
├── auth.py              # JWT + API Key 驗證
├── routes_auth.py       # /api/auth/*
├── routes_projects.py   # /api/projects/*
├── routes_chat.py       # /api/chat/*
├── routes_plots.py      # /api/plots/*
├── supabase_client.py   # Supabase 整合層
├── supabase_migrate.py  # 遷移腳本
├── test_api.py          # 15 項整合測試
├── requirements.txt
├── .env.example
└── progress.md
```

## API 端點總覽
| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | /api/health | 健康檢查 |
| POST | /api/auth/register | 註冊（回傳 API Key + JWT） |
| POST | /api/auth/login | 登入（回傳 JWT） |
| GET | /api/auth/me | 目前使用者 |
| GET/POST | /api/auth/api-keys | API Key 列表 / 新增 |
| DELETE | /api/auth/api-keys/{id} | 撤銷 API Key |
| GET/POST | /api/projects | 專案列表 / 建立 |
| GET/PATCH/DELETE | /api/projects/{id} | 專案 CRUD |
| POST | /api/chat/completions | LLM 代理（非串流） |
| POST | /api/chat/completions/stream | LLM 代理（SSE 串流） |
| POST | /api/plots | 建立圖表（含渲染） |
| GET | /api/plots/project/{id} | 專案圖表列表 |
| GET/DELETE | /api/plots/{id} | 圖表 CRUD |

## 下一步
- [ ] Ching-Hsien 驗收
- [ ] Heidi 撰寫 API 文件
- [ ] 設定 Hostinger 部署
- [ ] Phase 2: React 前端

---

## 會議記錄 / 決策
| 日期 | 事項 | 決議 |
|------|------|------|
| 2026-07-16 | Phase 1 啟動 | Astraea 全權技術執行 |
| 2026-07-16 | Phase 1 核心完成 | 15 tests pass, 等待驗收 |

## 部署目標
- Hostinger 共享主機
- FastAPI + Uvicorn
- Supabase 雲端資料庫
