"""Virgo Agent — 資料庫模型
Phase 1: SQLite (aiosqlite)，預留 Supabase 遷移介面。
"""
import uuid
import secrets
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Float, Integer
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from config import settings


class Base(DeclarativeBase):
    pass


# ── 引擎與 session factory ──
engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ═══════════════════════════════════════════════
# 模型
# ═══════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(128), nullable=False)
    api_key_hash = Column(String(128), unique=True, nullable=False)
    api_key_prefix = Column(String(12), nullable=False)  # 前6碼明文供 UI 顯示
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="projects")
    plots = relationship("Plot", back_populates="project", cascade="all, delete-orphan")


class Plot(Base):
    __tablename__ = "plots"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    title = Column(String(255), nullable=False)
    plot_type = Column(String(32), nullable=False)   # scatter, line, bar, histogram, heatmap
    params_json = Column(Text, default="{}")          # matplotlib params as JSON
    image_base64 = Column(Text, nullable=True)        # cached render
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="plots")


class APIKey(Base):
    """已發出的 API Key 記錄 — 用於撤銷與審計"""
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    prefix = Column(String(12), nullable=False)       # 前6碼
    key_hash = Column(String(128), unique=True, nullable=False)
    name = Column(String(128), default="default")     # 使用者自訂標籤
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_used_at = Column(DateTime, nullable=True)


# ═══════════════════════════════════════════════
# 輔助
# ═══════════════════════════════════════════════

async def init_db():
    """建立所有資料表（開發期使用，正式部署用 Alembic）。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def generate_api_key() -> tuple[str, str, str]:
    """產生 API Key。回傳 (完整key, hash, prefix)。"""
    raw = f"{settings.api_key_prefix}{secrets.token_urlsafe(32)}"
    # hash for storage
    import hashlib
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    prefix = raw[:12]
    return raw, hashed, prefix
