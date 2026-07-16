"""Virgo Agent — LLM Chat 代理
API Key 後端代理：接收前端請求，轉送至 LLM provider，回傳回應。
支援串流 (SSE) 與非串流模式。
"""
import json
import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from config import settings
from auth import require_user

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ═══════════════════════════════════════════════
# Schema
# ═══════════════════════════════════════════════

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str | None = None
    stream: bool = False
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=4096, ge=1, le=32768)


class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str | None = None


class ChatUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatChoice]
    usage: ChatUsage | None = None


# ═══════════════════════════════════════════════
# 核心
# ═══════════════════════════════════════════════

def _build_openai_messages(messages: list[ChatMessage]) -> list[dict]:
    return [{"role": m.role, "content": m.content} for m in messages]


@router.post("/completions", response_model=ChatResponse)
async def chat_completions(
    body: ChatRequest,
    user: dict = Depends(require_user),
):
    """代理 LLM Chat Completions。非串流模式。"""
    if not settings.llm_api_key:
        raise HTTPException(status_code=503, detail="LLM API key not configured")

    model = body.model or settings.llm_default_model
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": _build_openai_messages(body.messages),
        "temperature": body.temperature,
        "max_tokens": body.max_tokens,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{settings.llm_base_url}/chat/completions",
            json=payload,
            headers=headers,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:1000])

    data = resp.json()
    return ChatResponse(**data)


@router.post("/completions/stream")
async def chat_completions_stream(
    body: ChatRequest,
    user: dict = Depends(require_user),
):
    """代理 LLM Chat Completions — SSE 串流模式。"""
    if not settings.llm_api_key:
        raise HTTPException(status_code=503, detail="LLM API key not configured")

    model = body.model or settings.llm_default_model
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": _build_openai_messages(body.messages),
        "temperature": body.temperature,
        "max_tokens": body.max_tokens,
        "stream": True,
    }

    async def event_stream():
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST",
                f"{settings.llm_base_url}/chat/completions",
                json=payload,
                headers=headers,
            ) as resp:
                if resp.status_code != 200:
                    error_body = await resp.aread()
                    yield f"data: {json.dumps({'error': error_body.decode()[:500]})}\n\n"
                    return
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        yield f"{line}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
