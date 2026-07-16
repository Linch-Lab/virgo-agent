"""Virgo Agent — Auth 模組
- API Key 生成與驗證
- JWT token 發行
- FastAPI 中介層 (middleware / dependency)
"""
import hashlib
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from config import settings

security_scheme = HTTPBearer(auto_error=False)


# ═══════════════════════════════════════════════
# JWT (短期 session token)
# ═══════════════════════════════════════════════

def create_jwt(user_id: str, expires_delta: timedelta = timedelta(hours=24)) -> str:
    payload = {
        "sub": user_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + expires_delta,
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ═══════════════════════════════════════════════
# API Key 驗證
# ═══════════════════════════════════════════════

def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def verify_api_key(
    key: str,
    session: AsyncSession,
) -> dict | None:
    """驗證 API Key 並回傳 user 資料，失敗回傳 None。"""
    from models import APIKey, User

    key_hash = hash_api_key(key)
    result = await session.execute(
        select(APIKey, User)
        .join(User, APIKey.user_id == User.id)
        .where(APIKey.key_hash == key_hash)
    )
    row = result.first()
    if row is None:
        return None

    apikey, user = row
    # 更新 last_used_at
    apikey.last_used_at = datetime.now(timezone.utc)
    await session.commit()
    return {"user_id": user.id, "email": user.email, "display_name": user.display_name}


# ═══════════════════════════════════════════════
# FastAPI Dependencies
# ═══════════════════════════════════════════════

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security_scheme),
    session: AsyncSession = Depends(lambda: None),  # injected by route
) -> dict:
    """從 Bearer token 取得當前使用者。
    支援 JWT (短期 session) 或 API Key。
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization header required")

    token = credentials.credentials

    # 試 API Key 格式
    if token.startswith(settings.api_key_prefix):
        from models import APIKey, User
        from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession as AS
        from models import async_session_factory

        user_info = None
        async with async_session_factory() as s:
            user_info = await verify_api_key(token, s)
        if user_info:
            return user_info
        raise HTTPException(status_code=401, detail="Invalid API key")

    # 試 JWT
    try:
        payload = decode_jwt(token)
        return {"user_id": payload["sub"]}
    except HTTPException:
        raise HTTPException(status_code=401, detail="Invalid token")


async def require_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security_scheme),
) -> dict:
    """簡化版 — 僅驗證 token 存在與格式，用於不需要 session 的端點。"""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization header required")

    token = credentials.credentials
    if token.startswith(settings.api_key_prefix):
        return {"user_id": "api_key_user"}  # 實際驗證在依賴 session 的端點做

    try:
        payload = decode_jwt(token)
        return {"user_id": payload["sub"]}
    except HTTPException:
        raise HTTPException(status_code=401, detail="Invalid token")
