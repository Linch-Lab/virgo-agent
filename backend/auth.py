"""
Virgo Agent — Auth module (JWT + SQLite)
"""
import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi import HTTPException, Request

# ── Config ────────────────────────────────────────────
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 720  # 30 days
DB_PATH = Path(os.getenv("DB_PATH", "virgo_users.db"))


def get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    return db


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT DEFAULT '',
            plan TEXT DEFAULT 'free',
            analyses_used INTEGER DEFAULT 0,
            analyses_limit INTEGER DEFAULT 5,
            stripe_customer_id TEXT DEFAULT '',
            stripe_subscription_id TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    db.commit()
    db.close()


# ── Password hashing ──────────────────────────────────
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200000)
    return f"{salt}${h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt, h = stored.split("$")
    h2 = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200000)
    return h == h2.hex()


# ── JWT ────────────────────────────────────────────────
def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


# ── Auth middleware ────────────────────────────────────
async def get_current_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    token = auth[7:]
    payload = decode_token(token)
    user_id = int(payload["sub"])

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    db.close()
    if not user:
        raise HTTPException(401, "User not found")
    return dict(user)


def require_plan(min_plan: str = "free"):
    plan_rank = {"free": 0, "pro": 1, "enterprise": 2}

    async def checker(request: Request):
        user = await get_current_user(request)
        if plan_rank.get(user["plan"], 0) < plan_rank.get(min_plan, 0):
            raise HTTPException(403, f"Requires {min_plan} plan or higher")
        if user["plan"] == "free" and user["analyses_used"] >= user["analyses_limit"]:
            raise HTTPException(429, f"Free tier limit reached ({user['analyses_limit']}/mo). Upgrade to Pro.")
        return user

    return checker


def increment_usage(user_id: int) -> None:
    db = get_db()
    db.execute(
        "UPDATE users SET analyses_used = analyses_used + 1, updated_at = datetime('now') WHERE id = ?",
        (user_id,),
    )
    db.commit()
    db.close()
