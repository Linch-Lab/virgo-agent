"""Virgo Agent — Auth 路由
使用者註冊 / 登入 / API Key 管理。
"""
import hashlib
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from auth import create_jwt, hash_api_key, require_user
from models import User, APIKey, generate_api_key, async_session_factory

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ═══════════════════════════════════════════════
# Schema
# ═══════════════════════════════════════════════

class RegisterRequest(BaseModel):
    email: str = Field(..., max_length=255)
    display_name: str = Field(..., min_length=1, max_length=128)


class RegisterResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    api_key: str       # 僅建立時回傳完整 key，之後無法取回
    token: str         # JWT session token
    message: str = "Save your API key — it will not be shown again."


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=255)
    api_key: str


class LoginResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    token: str


class APIKeyOut(BaseModel):
    id: str
    prefix: str
    name: str
    created_at: datetime
    last_used_at: datetime | None


class APIKeyCreate(BaseModel):
    name: str = "default"


class APIKeyCreated(BaseModel):
    id: str
    prefix: str
    name: str
    api_key: str
    message: str = "Save this key — it will not be shown again."


# ═══════════════════════════════════════════════
# 端點
# ═══════════════════════════════════════════════

@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(body: RegisterRequest):
    """以 email 註冊新使用者，自動產生 API Key + JWT。"""
    async with async_session_factory() as session:
        # 檢查重複
        existing = await session.execute(select(User).where(User.email == body.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already registered")

        raw_key, key_hash, prefix = generate_api_key()

        user = User(
            email=body.email,
            display_name=body.display_name,
            api_key_hash=key_hash,
            api_key_prefix=prefix,
        )
        session.add(user)
        await session.flush()

        # 記錄 API Key
        apikey = APIKey(
            user_id=user.id,
            prefix=prefix,
            key_hash=key_hash,
            name="default",
        )
        session.add(apikey)
        await session.commit()

        jwt_token = create_jwt(user.id)
        return RegisterResponse(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            api_key=raw_key,
            token=jwt_token,
        )


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    """以 email + API Key 登入，取得 JWT。"""
    async with async_session_factory() as session:
        key_hash = hash_api_key(body.api_key)
        result = await session.execute(
            select(User).where(
                User.email == body.email,
                User.api_key_hash == key_hash,
            )
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid email or API key")

        jwt_token = create_jwt(user.id)
        return LoginResponse(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            token=jwt_token,
        )


@router.get("/me", response_model=RegisterResponse)
async def get_me(user: dict = Depends(require_user)):
    """取得目前使用者資訊。"""
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.id == user["user_id"]))
        u = result.scalar_one_or_none()
        if u is None:
            raise HTTPException(status_code=404, detail="User not found")
        return {"user_id": u.id, "email": u.email, "display_name": u.display_name,
                "api_key": "***hidden***", "token": "***current***"}


@router.post("/api-keys", response_model=APIKeyCreated, status_code=201)
async def create_api_key(
    body: APIKeyCreate,
    user: dict = Depends(require_user),
):
    """為目前使用者產生新的 API Key。"""
    async with async_session_factory() as session:
        raw_key, key_hash, prefix = generate_api_key()
        apikey = APIKey(
            user_id=user["user_id"],
            prefix=prefix,
            key_hash=key_hash,
            name=body.name,
        )
        session.add(apikey)
        await session.commit()
        return APIKeyCreated(
            id=apikey.id,
            prefix=prefix,
            name=body.name,
            api_key=raw_key,
        )


@router.get("/api-keys", response_model=list[APIKeyOut])
async def list_api_keys(user: dict = Depends(require_user)):
    """列出目前使用者的所有 API Key（不顯示完整 key）。"""
    async with async_session_factory() as session:
        result = await session.execute(
            select(APIKey).where(APIKey.user_id == user["user_id"])
        )
        keys = result.scalars().all()
        return [
            APIKeyOut(
                id=k.id,
                prefix=k.prefix,
                name=k.name,
                created_at=k.created_at,
                last_used_at=k.last_used_at,
            )
            for k in keys
        ]


@router.delete("/api-keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    user: dict = Depends(require_user),
):
    """撤銷 API Key。"""
    async with async_session_factory() as session:
        result = await session.execute(
            select(APIKey).where(
                APIKey.id == key_id,
                APIKey.user_id == user["user_id"],
            )
        )
        apikey = result.scalar_one_or_none()
        if apikey is None:
            raise HTTPException(status_code=404, detail="API key not found")
        await session.delete(apikey)
        await session.commit()
    return None
