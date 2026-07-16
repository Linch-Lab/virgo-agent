"""Virgo Agent — Supabase 遷移腳本
在 Supabase 遠端建立表格結構。

使用方法：
  export SUPABASE_URL="https://xxxxx.supabase.co"
  export SUPABASE_SERVICE_KEY="eyJ..."
  python supabase_migrate.py
"""
import os
import sys
from config import settings
from supabase_client import get_supabase, MIGRATION_SQL


def migrate():
    """在 Supabase SQL Editor 外執行 DDL（需 service_role key）。"""
    client = get_supabase()
    if client is None:
        print("ERROR: Supabase not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY.")
        sys.exit(1)

    print(f"Connected to Supabase: {settings.supabase_url}")

    # supabase-py 支援 rpc / raw SQL via REST，但 DDL 需透過 Management API
    # 簡化路徑：印出 SQL 供手動複製到 Supabase SQL Editor
    print("\n=== 請複製以下 SQL 到 Supabase SQL Editor 執行 ===\n")
    print(MIGRATION_SQL)
    print("\n=== SQL 結束 ===")
    print("\n執行後，更新 .env 中的 DATABASE_URL 為 Supabase connection string。")


if __name__ == "__main__":
    migrate()
