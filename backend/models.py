"""
Virgo Agent — Shared Pydantic models
"""
from pydantic import BaseModel
from typing import Optional, List


class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 4096
    stream: bool = False


class PlotSpec(BaseModel):
    type: str = "line"  # line, scatter, bar, polarization, durability, eis
    data: dict = {}
    options: dict = {}


class AuthRegister(BaseModel):
    email: str
    password: str
    display_name: str = ""


class AuthLogin(BaseModel):
    email: str
    password: str


class ProjectCreate(BaseModel):
    title: str = "Untitled Project"
    description: str = ""
    sections: str = "[]"


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    sections: Optional[str] = None


class ProjectCreate(BaseModel):
    title: str = "Untitled Project"
    description: str = ""
    sections: str = "[]"


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    sections: Optional[str] = None
