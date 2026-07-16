"""
Virgo Agent — Auth routes (registration, login, JWT)
"""
from fastapi import APIRouter, HTTPException, Depends
import database
import auth_utils
from models import AuthRegister, AuthLogin

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
async def register(req: AuthRegister):
    """Register a new user. Returns JWT token."""
    db = await database.get_db()
    try:
        row = await db.execute("SELECT id FROM users WHERE email = ?", (req.email,))
        if await row.fetchone():
            raise HTTPException(status_code=409, detail="Email already registered")

        pwd_hash = auth_utils.hash_password(req.password)
        cursor = await db.execute(
            "INSERT INTO users (email, display_name, password_hash) VALUES (?, ?, ?)",
            (req.email, req.display_name, pwd_hash),
        )
        await db.commit()
        user_id = cursor.lastrowid

        token = auth_utils.create_access_token(user_id, req.email)
        return {
            "token": token,
            "user": {"id": user_id, "email": req.email, "display_name": req.display_name},
        }
    finally:
        await db.close()


@router.post("/login")
async def login(req: AuthLogin):
    """Login with email and password. Returns JWT token."""
    db = await database.get_db()
    try:
        row = await db.execute(
            "SELECT id, email, display_name, password_hash FROM users WHERE email = ?",
            (req.email,),
        )
        user = await row.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not auth_utils.verify_password(req.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = auth_utils.create_access_token(user["id"], user["email"])
        return {
            "token": token,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "display_name": user["display_name"],
            },
        }
    finally:
        await db.close()


@router.get("/me")
async def me(user: dict = Depends(auth_utils.require_user)):
    """Get current authenticated user profile."""
    db = await database.get_db()
    try:
        row = await db.execute(
            "SELECT id, email, display_name, created_at FROM users WHERE id = ?",
            (user["user_id"],),
        )
        u = await row.fetchone()
        if not u:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "id": u["id"],
            "email": u["email"],
            "display_name": u["display_name"],
            "created_at": u["created_at"],
        }
    finally:
        await db.close()
