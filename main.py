"""Virgo Agent — 主應用入口
FastAPI 應用 + 生命週期管理。
啟動: uvicorn main:app --reload
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from models import init_db

# ── 匯入路由 ──
from routes_auth import router as auth_router
from routes_projects import router as projects_router
from routes_chat import router as chat_router
from routes_plots import router as plots_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """啟動時初始化資料庫。"""
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 路由註冊 ──
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(chat_router)
app.include_router(plots_router)


# ── 健康檢查 ──
@app.get("/api/health")
async def health():
    return {"status": "ok", "version": settings.app_version, "name": settings.app_name}


# ── 根路徑 ──
@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/health",
    }
