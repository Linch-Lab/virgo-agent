"""Virgo Agent — 設定模組
從環境變數載入設定，支援 .env 檔案。
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    # ── 應用 ──
    app_name: str = "Virgo Agent"
    app_version: str = "0.1.0"
    debug: bool = False
    secret_key: str = "change-me-in-production-use-a-real-secret"
    api_key_prefix: str = "vg-"

    # ── 資料庫 ──
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'virgo.db'}"
    # Phase 1 後期遷移 → Supabase:
    supabase_url: str = ""
    supabase_service_key: str = ""

    # ── LLM 代理 ──
    llm_provider: str = "openrouter"  # openrouter | openai | anthropic
    llm_api_key: str = ""
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_default_model: str = "deepseek/deepseek-chat"

    # ── CORS ──
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── 速率限制 ──
    rate_limit_per_minute: int = 60

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
