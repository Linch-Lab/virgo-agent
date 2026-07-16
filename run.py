#!/usr/bin/env python3
"""
Virgo Agent — Stable server entry point
Run from project root: python run.py
"""
import sys
from pathlib import Path

# Ensure backend/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

import os
import uuid
import argparse

import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse

# Local imports (all live in backend/ dir on sys.path)
import database
import auth_utils
from models import ChatMessage, ChatRequest, PlotSpec, AuthRegister, AuthLogin, ProjectCreate, ProjectUpdate
from auth_routes import router as auth_router
from project_routes import router as project_router

# --- Config ---
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
ALLOWED_UPLOAD_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"}
MAX_UPLOAD_SIZE = 20 * 1024 * 1024

# --- App ---
app = FastAPI(title="Virgo Agent API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router)
app.include_router(project_router)


@app.on_event("startup")
async def startup():
    await database.init_db()


# ==== Routes ====

@app.get("/")
async def serve_frontend():
    return FileResponse(BASE_DIR / "virgo_mvp.html")


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "service": "virgo-agent",
            "api_key_set": bool(DEEPSEEK_API_KEY), "base_url": DEEPSEEK_BASE_URL}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=503, detail="DEEPSEEK_API_KEY not configured")
    payload = {"model": req.model, "messages": [m.model_dump() for m in req.messages],
               "temperature": req.temperature, "max_tokens": req.max_tokens, "stream": req.stream}
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json",
               "Accept": "text/event-stream" if req.stream else "application/json"}
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            if req.stream:
                async def stream_response():
                    async with client.stream("POST", f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
                                             json=payload, headers=headers) as resp:
                        if resp.status_code != 200:
                            yield f'data: {{"error":"DeepSeek API error: {resp.status_code}"}}\n\n'
                            yield "data: [DONE]\n\n"; return
                        async for line in resp.aiter_lines():
                            if line: yield line + "\n"
                return StreamingResponse(stream_response(), media_type="text/event-stream")
            else:
                resp = await client.post(f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
                                         json=payload, headers=headers)
                if resp.status_code != 200:
                    raise HTTPException(status_code=502,
                                        detail=f"DeepSeek API error: {resp.status_code} — {resp.text[:500]}")
                return JSONResponse(content=resp.json())
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="DeepSeek API timeout")
        except httpx.ConnectError:
            raise HTTPException(status_code=502, detail="Cannot connect to DeepSeek API")


_MIME_BY_EXT = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml"}


def sniff_mime(data: bytes, ext: str) -> str:
    if data[:4] == b'\x89PNG': return "image/png"
    if data[:2] == b'\xff\xd8': return "image/jpeg"
    if data[:6] in (b'GIF87a', b'GIF89a'): return "image/gif"
    if data[:4] in (b'RIFF', b'WEBP'): return "image/webp"
    if data[:4] == b'<svg' or data[:4] == b'<?xm': return "image/svg+xml"
    return _MIME_BY_EXT.get(ext.lower(), "image/png")


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower() if file.filename else ".png"
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 20 MB)")
    mime = file.content_type or sniff_mime(contents, ext)
    if mime not in ALLOWED_UPLOAD_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported type: {mime}")
    fname = f"{uuid.uuid4().hex}{ext}"
    (UPLOAD_DIR / fname).write_bytes(contents)
    return {"url": f"/uploads/{fname}", "name": fname, "size": len(contents)}


@app.post("/api/plot")
async def plot(spec: PlotSpec):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt; import numpy as np
    data, opts = spec.data, spec.options
    plt.rcParams.update({"font.family": "serif", "font.size": 10, "axes.labelsize": 11,
                         "axes.titlesize": 12, "xtick.labelsize": 9, "ytick.labelsize": 9,
                         "legend.fontsize": 9, "figure.dpi": 300, "savefig.dpi": 300,
                         "savefig.bbox": "tight", "axes.linewidth": 1.0, "axes.spines.top": False,
                         "axes.spines.right": False, "xtick.direction": "in", "ytick.direction": "in",
                         "xtick.major.size": 4, "ytick.major.size": 4, "lines.linewidth": 1.5})
    w, h = opts.get("width", 7), opts.get("height", 4.5)
    fig, ax = plt.subplots(figsize=(w, h))
    labels = data.get("labels", [])
    datasets = data.get("datasets", [])
    colors = ["#2c5f8a", "#b33", "#2a7d4f", "#b8860b", "#8b5cf6", "#e07b39"]
    pt = spec.type
    if pt in ("line", "polarization", "durability"):
        for i, ds in enumerate(datasets):
            x = ds.get("data_x", list(range(len(labels))))
            y = ds.get("data_y", ds.get("data", []))
            ax.plot(x, y, label=ds.get("label", f"S{i+1}"),
                    color=ds.get("color", colors[i % 6]), marker=ds.get("marker", ""), markersize=3)
    elif pt in ("scatter", "eis"):
        for i, ds in enumerate(datasets):
            ax.scatter(ds.get("data_x", []), ds.get("data_y", ds.get("data", [])),
                       label=ds.get("label", f"S{i+1}"), color=ds.get("color", colors[i % 6]),
                       s=12, edgecolors="none")
    elif pt == "bar":
        x = np.arange(len(labels)); w_bar = 0.8 / max(len(datasets), 1)
        for i, ds in enumerate(datasets):
            y = ds.get("data_y", ds.get("data", []))
            ax.bar(x + i * w_bar, y, w_bar, label=ds.get("label", f"S{i+1}"),
                   color=ds.get("color", colors[i % 6]), edgecolor="white", linewidth=0.5)
        if labels:
            ax.set_xticks(x + w_bar * (len(datasets) - 1) / 2)
            ax.set_xticklabels(labels, rotation=opts.get("xrot", 0), ha="center")
    elif labels and pt not in ("scatter", "eis"):
        ax.set_xticklabels(labels, rotation=opts.get("xrot", 0))
    ax.set_xlabel(opts.get("xlabel", "")); ax.set_ylabel(opts.get("ylabel", ""))
    if opts.get("title"): ax.set_title(opts["title"], fontweight="bold", pad=10)
    if any(ds.get("label") for ds in datasets):
        ax.legend(frameon=True, fancybox=False, edgecolor="#ccc", loc=opts.get("legend_loc", "best"))
    if opts.get("grid", True): ax.grid(True, linestyle="--", alpha=0.3, linewidth=0.5)
    if opts.get("xlog"): ax.set_xscale("log")
    if opts.get("ylog"): ax.set_yscale("log")
    if opts.get("sci_axis"): ax.ticklabel_format(axis=opts["sci_axis"], style="sci", scilimits=(-2, 3))
    plt.tight_layout()
    fname = f"{uuid.uuid4().hex}.png"
    fig.savefig(UPLOAD_DIR / fname, dpi=300); plt.close(fig)
    return {"url": f"/uploads/{fname}", "name": fname}


# ==== Main ====
if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
    key_status = "YES" if DEEPSEEK_API_KEY else "NOT SET"
    print(f"\n  Virgo Agent v0.1.0  |  http://{args.host}:{args.port}")
    print(f"  API: /api/chat | /api/upload | /api/plot | /api/auth/* | /api/projects/*")
    print(f"  Key: {key_status}\n")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
