"""Virgo Agent — Supabase 整合層
Phase 1 後期：將 SQLite 資料遷移至 Supabase PostgreSQL。
使用 supabase-py 客戶端。

遷移策略：
  1. 設定 SUPABASE_URL + SUPABASE_SERVICE_KEY 環境變數
  2. 執行 python supabase_migrate.py 建立遠端表格
  3. 切換 config.database_url 指向 Supabase
"""
from config import settings
from supabase import create_client, Client

_supabase: Client | None = None


def get_supabase() -> Client | None:
    """取得 Supabase 客戶端（如果已設定）。"""
    global _supabase
    if _supabase is not None:
        return _supabase

    if not settings.supabase_url or not settings.supabase_service_key:
        return None

    _supabase = create_client(settings.supabase_url, settings.supabase_service_key)
    return _supabase


# ═══════════════════════════════════════════════
# SQL → Supabase 遷移 SQL
# ═══════════════════════════════════════════════

MIGRATION_SQL = """
-- Virgo Agent Phase 1 → Supabase 遷移
-- 在 Supabase SQL Editor 中執行，或經由 supabase_migrate.py

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(128) NOT NULL,
    api_key_hash VARCHAR(128) UNIQUE NOT NULL,
    api_key_prefix VARCHAR(12) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    prefix VARCHAR(12) NOT NULL,
    key_hash VARCHAR(128) UNIQUE NOT NULL,
    name VARCHAR(128) DEFAULT 'default',
    created_at TIMESTAMPTZ DEFAULT now(),
    last_used_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS plots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    plot_type VARCHAR(32) NOT NULL,
    params_json TEXT DEFAULT '{}',
    image_base64 TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- RLS 政策（使用者只能讀寫自己的資料）
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE plots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own data" ON users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can read own API keys" ON api_keys
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can CRUD own projects" ON projects
    FOR ALL USING (auth.uid() = owner_id);

CREATE POLICY "Users can CRUD own plots" ON plots
    FOR ALL USING (
        auth.uid() = (SELECT owner_id FROM projects WHERE id = project_id)
    );
"""
