"""Virgo Agent — Projects CRUD
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Project, async_session_factory
from auth import require_user

router = APIRouter(prefix="/api/projects", tags=["projects"])


# ═══════════════════════════════════════════════
# Schema
# ═══════════════════════════════════════════════

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class ProjectOut(BaseModel):
    id: str
    owner_id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime


# ═══════════════════════════════════════════════
# 端點
# ═══════════════════════════════════════════════

@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    body: ProjectCreate,
    user: dict = Depends(require_user),
):
    async with async_session_factory() as session:
        project = Project(
            owner_id=user["user_id"],
            name=body.name,
            description=body.description,
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return _to_out(project)


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    user: dict = Depends(require_user),
):
    async with async_session_factory() as session:
        result = await session.execute(
            select(Project).where(Project.owner_id == user["user_id"])
        )
        projects = result.scalars().all()
        return [_to_out(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: str,
    user: dict = Depends(require_user),
):
    async with async_session_factory() as session:
        result = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.owner_id == user["user_id"],
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return _to_out(project)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    user: dict = Depends(require_user),
):
    async with async_session_factory() as session:
        result = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.owner_id == user["user_id"],
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        if body.name is not None:
            project.name = body.name
        if body.description is not None:
            project.description = body.description
        project.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(project)
        return _to_out(project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    user: dict = Depends(require_user),
):
    async with async_session_factory() as session:
        result = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.owner_id == user["user_id"],
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        await session.delete(project)
        await session.commit()
    return None


# ═══════════════════════════════════════════════
# 輔助
# ═══════════════════════════════════════════════

def _to_out(p: Project) -> ProjectOut:
    return ProjectOut(
        id=p.id,
        owner_id=p.owner_id,
        name=p.name,
        description=p.description,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )
