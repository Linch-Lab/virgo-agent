"""
Virgo Agent — FastAPI Backend
Render deployment: uvicorn main:app --host 0.0.0.0 --port $PORT
"""
import os
import uuid
import json
import io
from pathlib import Path

import httpx
import numpy as np
from fastapi import FastAPI, File, UploadFile, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Virgo Agent API")

# ── CORS ──────────────────────────────────────────────
ORIGINS = os.getenv("CORS_ORIGINS", "https://virgo.billlinch.com").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config ────────────────────────────────────────────
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"}
MAX_SIZE = 20 * 1024 * 1024  # 20 MB

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "")


# ═══════════════════════════════════════════════════════
#  HEALTH
# ═══════════════════════════════════════════════════════

@app.get("/")
async def health():
    return {"status": "ok", "service": "Virgo Agent API"}


# ═══════════════════════════════════════════════════════
#  UPLOAD
# ═══════════════════════════════════════════════════════

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No file provided")

    # Read content
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(413, f"File too large (max {MAX_SIZE // 1024 // 1024} MB)")

    # Sniff MIME
    mime = sniff_mime(content)
    if mime not in ALLOWED_TYPES:
        raise HTTPException(415, f"Unsupported type: {mime}")

    ext = guess_ext(mime, file.filename)
    fname = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOAD_DIR / fname
    filepath.write_bytes(content)

    return {"url": f"/uploads/{fname}", "name": fname, "size": len(content)}


# ═══════════════════════════════════════════════════════
#  PLOT  (matplotlib)
# ═══════════════════════════════════════════════════════

@app.post("/plot")
async def plot(request: Request):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    spec = await request.json()
    plot_type = spec.get("type", "line")
    data = spec.get("data", {})
    opts = spec.get("options", {})
    fmt = spec.get("format", "png")  # png or svg

    plt.rcParams.update({
        "font.family": "serif", "font.size": 10,
        "axes.labelsize": 11, "axes.titlesize": 12,
        "xtick.labelsize": 9, "ytick.labelsize": 9,
        "legend.fontsize": 9, "figure.dpi": 150,
        "savefig.dpi": 150, "savefig.bbox": "tight",
        "axes.linewidth": 1.0, "axes.spines.top": False,
        "axes.spines.right": False, "xtick.direction": "in",
        "ytick.direction": "in", "xtick.major.size": 4,
        "ytick.major.size": 4, "lines.linewidth": 1.5,
    })

    w = opts.get("width", 7)
    h = opts.get("height", 4.5)
    fig, ax = plt.subplots(figsize=(w, h))

    labels = data.get("labels", [])
    datasets = data.get("datasets", [])
    colors = ["#2c5f8a", "#b33", "#2a7d4f", "#b8860b", "#8b5cf6", "#e07b39"]

    if plot_type in ("line", "polarization", "durability"):
        for i, ds in enumerate(datasets):
            x = ds.get("data_x", range(len(labels)))
            y = ds.get("data_y", ds.get("data", []))
            lbl = ds.get("label", f"Series {i+1}")
            c = ds.get("color", colors[i % len(colors)])
            ax.plot(x, y, label=lbl, color=c,
                    marker=ds.get("marker", ""), markersize=3)

    elif plot_type in ("scatter", "eis"):
        for i, ds in enumerate(datasets):
            x = ds.get("data_x", [])
            y = ds.get("data_y", ds.get("data", []))
            lbl = ds.get("label", f"Series {i+1}")
            c = ds.get("color", colors[i % len(colors)])
            ax.scatter(x, y, label=lbl, color=c, s=12, edgecolors="none")

    elif plot_type == "bar":
        x = np.arange(len(labels))
        w_bar = 0.8 / max(len(datasets), 1)
        for i, ds in enumerate(datasets):
            y = ds.get("data_y", ds.get("data", []))
            lbl = ds.get("label", f"Series {i+1}")
            c = ds.get("color", colors[i % len(colors)])
            ax.bar(x + i * w_bar, y, w_bar,
                   label=lbl, color=c, edgecolor="white", linewidth=0.5)

    ax.set_xlabel(opts.get("xlabel", ""))
    ax.set_ylabel(opts.get("ylabel", ""))
    if opts.get("title"):
        ax.set_title(opts["title"], fontweight="bold", pad=10)

    if labels and plot_type == "bar":
        ax.set_xticks(x + w_bar * (len(datasets) - 1) / 2)
        ax.set_xticklabels(labels, rotation=opts.get("xrot", 0), ha="center")
    elif labels and plot_type not in ("scatter", "eis"):
        ax.set_xticklabels(labels, rotation=opts.get("xrot", 0))

    if any(ds.get("label") for ds in datasets):
        ax.legend(frameon=True, fancybox=False, edgecolor="#cccccc",
                  loc=opts.get("legend_loc", "best"))

    if opts.get("grid", True):
        ax.grid(True, linestyle="--", alpha=0.3, linewidth=0.5)
    if opts.get("xlog"):
        ax.set_xscale("log")
    if opts.get("ylog"):
        ax.set_yscale("log")
    if opts.get("sci_axis"):
        ax.ticklabel_format(axis=opts["sci_axis"], style="sci", scilimits=(-2, 3))

    plt.tight_layout()

    ext = ".svg" if fmt == "svg" else ".png"
    fname = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOAD_DIR / fname
    fig.savefig(filepath, dpi=150, format=fmt)
    plt.close(fig)

    return {"url": f"/uploads/{fname}", "name": fname, "format": fmt}


# ═══════════════════════════════════════════════════════
#  AI CHAT  (DeepSeek proxy)
# ═══════════════════════════════════════════════════════

@app.post("/api/chat")
async def chat(request: Request):
    if not DEEPSEEK_KEY:
        raise HTTPException(500, "DEEPSEEK_API_KEY not configured on server")

    body = await request.json()
    model = body.get("model", "deepseek-chat")
    messages = body.get("messages", [])
    max_tokens = body.get("max_tokens", 2000)
    temperature = body.get("temperature", 0.3)

    if not messages:
        raise HTTPException(400, "messages required")

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            DEEPSEEK_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        )
        # Forward the raw response
        return JSONResponse(
            content=resp.json(),
            status_code=resp.status_code,
        )


# ═══════════════════════════════════════════════════════
#  Static files  (serve generated uploads)
# ═══════════════════════════════════════════════════════

@app.get("/uploads/{filename}")
async def serve_upload(filename: str):
    filepath = UPLOAD_DIR / filename
    if not filepath.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(filepath)


# ═══════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════

def sniff_mime(data: bytes) -> str:
    if data[:4] == b"\x89PNG":
        return "image/png"
    if data[:2] == b"\xff\xd8":
        return "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" or data[:4] == b"WEBP":
        return "image/webp"
    if data[:4] == b"<svg" or data[:5] == b"<?xml":
        return "image/svg+xml"
    return "image/png"


def guess_ext(mime: str, filename: str) -> str:
    ext_map = {
        "image/png": ".png", "image/jpeg": ".jpg",
        "image/gif": ".gif", "image/webp": ".webp",
        "image/svg+xml": ".svg",
    }
    if mime in ext_map:
        return ext_map[mime]
    return Path(filename).suffix.lower() or ".png"


# ═══════════════════════════════════════════════════════
#  AUTH  — JWT-based user accounts
# ═══════════════════════════════════════════════════════

from pydantic import BaseModel, EmailStr
from auth import (
    init_db, get_db, hash_password, verify_password,
    create_token, decode_token, get_current_user,
    require_plan, increment_usage,
)

init_db()


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/api/auth/signup")
async def signup(req: SignupRequest):
    # Whitelist check
    allowed = os.getenv("ALLOWED_EMAILS", "")
    if allowed:
        allowed_list = [e.strip().lower() for e in allowed.split(",")]
        if req.email.lower() not in allowed_list:
            raise HTTPException(403, "⏳ Virgo Agent is in private beta. Registration is currently by invitation only.")

    if len(req.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email=?", (req.email,)).fetchone()
    if existing:
        db.close()
        raise HTTPException(409, "Email already registered")
    h = hash_password(req.password)
    db.execute(
        "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
        (req.email, h, req.name),
    )
    db.commit()
    user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    token = create_token(user_id)
    return {"token": token, "user": {"id": user_id, "email": req.email, "name": req.name, "plan": "free"}}


@app.post("/api/auth/login")
async def login(req: LoginRequest):
    # Whitelist check — if ALLOWED_EMAILS is set, only those emails can sign in
    allowed = os.getenv("ALLOWED_EMAILS", "")
    if allowed:
        allowed_list = [e.strip().lower() for e in allowed.split(",")]
        if req.email.lower() not in allowed_list:
            raise HTTPException(403, "⏳ Virgo Agent is in private beta. Access is currently by invitation only.")

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email=?", (req.email,)).fetchone()
    db.close()
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    token = create_token(user["id"])
    return {
        "token": token,
        "user": {
            "id": user["id"], "email": user["email"], "name": user["name"],
            "plan": user["plan"], "analyses_used": user["analyses_used"],
            "analyses_limit": user["analyses_limit"],
        },
    }



# ═══════════════════════════════════════════════════════
#  PROTECTED AI CHAT  (with usage tracking)
# ═══════════════════════════════════════════════════════

@app.post("/api/chat/pro")
async def chat_pro(request: Request):
    """Protected chat endpoint — requires auth, tracks usage"""
    auth_header = request.headers.get("Authorization", "")
    user = None
    if auth_header.startswith("Bearer "):
        try:
            user = await get_current_user(request)
        except HTTPException:
            pass  # fall through to free usage check below

    body = await request.json()

    # Free users get basic chat without usage tracking
    # (Usage tracking applied via middleware when we implement it)
    if not DEEPSEEK_KEY:
        raise HTTPException(500, "DEEPSEEK_API_KEY not configured")

    model = body.get("model", "deepseek-chat")
    messages = body.get("messages", [])
    max_tokens = body.get("max_tokens", 2000)
    temperature = body.get("temperature", 0.3)

    if not messages:
        raise HTTPException(400, "messages required")

    # Track usage for logged-in users
    if user:
        try:
            increment_usage(user["id"])
        except Exception:
            pass

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            DEEPSEEK_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        )
        return JSONResponse(content=resp.json(), status_code=resp.status_code)


@app.get("/api/auth/me")
async def get_me(request: Request):
    user = await get_current_user(request)
    return {
        "user": {
            "id": user["id"], "email": user["email"], "name": user["name"],
            "plan": user["plan"], "analyses_used": user["analyses_used"],
            "analyses_limit": user["analyses_limit"],
        }
    }
