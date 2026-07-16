"""Virgo Agent — 科學繪圖端點
支援 scatter, line, bar, histogram, heatmap。
"""
import io
import json
import base64
from datetime import datetime, timezone
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from models import Plot, Project, async_session_factory
from auth import require_user

router = APIRouter(prefix="/api/plots", tags=["plots"])


# ═══════════════════════════════════════════════
# Schema
# ═══════════════════════════════════════════════

class PlotData(BaseModel):
    x: list[float] | None = None
    y: list[float] | None = None
    labels: list[str] | None = None
    values: list[float] | None = None
    matrix: list[list[float]] | None = None     # 熱力圖


class PlotCreate(BaseModel):
    project_id: str
    title: str = Field(..., min_length=1, max_length=255)
    plot_type: str = Field(..., pattern="^(scatter|line|bar|histogram|heatmap)$")
    data: PlotData
    xlabel: str = ""
    ylabel: str = ""
    color: str = "#4C72B0"
    figsize: tuple[int, int] = (8, 5)


class PlotOut(BaseModel):
    id: str
    project_id: str
    title: str
    plot_type: str
    image_base64: str | None
    created_at: datetime


# ═══════════════════════════════════════════════
# 繪圖引擎
# ═══════════════════════════════════════════════

def render_plot(body: PlotCreate) -> str:
    """渲染 matplotlib 圖表，回傳 base64 PNG。"""
    fig, ax = plt.subplots(figsize=body.figsize)

    match body.plot_type:
        case "scatter":
            ax.scatter(body.data.x or [], body.data.y or [], c=body.color, alpha=0.7)
        case "line":
            ax.plot(body.data.x or [], body.data.y or [], color=body.color, linewidth=2)
        case "bar":
            ax.bar(body.data.labels or [], body.data.values or [], color=body.color, alpha=0.8)
        case "histogram":
            ax.hist(body.data.values or [], bins=20, color=body.color, alpha=0.7, edgecolor="white")
        case "heatmap":
            matrix = body.data.matrix or []
            im = ax.imshow(matrix, cmap="viridis", aspect="auto")
            plt.colorbar(im, ax=ax)

    ax.set_title(body.title)
    if body.xlabel:
        ax.set_xlabel(body.xlabel)
    if body.ylabel:
        ax.set_ylabel(body.ylabel)
    ax.grid(True, alpha=0.3)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


# ═══════════════════════════════════════════════
# 端點
# ═══════════════════════════════════════════════

@router.post("", response_model=PlotOut, status_code=201)
async def create_plot(
    body: PlotCreate,
    user: dict = Depends(require_user),
):
    # 驗證 project 所有權
    async with async_session_factory() as session:
        result = await session.execute(
            select(Project).where(
                Project.id == body.project_id,
                Project.owner_id == user["user_id"],
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        # 渲染
        try:
            img_b64 = render_plot(body)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Plot rendering failed: {str(e)}")

        # 儲存
        plot = Plot(
            project_id=body.project_id,
            title=body.title,
            plot_type=body.plot_type,
            params_json=body.model_dump_json(exclude={"data"}),
            image_base64=img_b64,
        )
        session.add(plot)
        await session.commit()
        await session.refresh(plot)

        return PlotOut(
            id=plot.id,
            project_id=plot.project_id,
            title=plot.title,
            plot_type=plot.plot_type,
            image_base64=plot.image_base64,
            created_at=plot.created_at,
        )


@router.get("/project/{project_id}", response_model=list[PlotOut])
async def list_plots(
    project_id: str,
    user: dict = Depends(require_user),
):
    async with async_session_factory() as session:
        # 驗證所有權
        proj = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.owner_id == user["user_id"],
            )
        )
        if proj.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Project not found")

        result = await session.execute(
            select(Plot).where(Plot.project_id == project_id)
        )
        plots = result.scalars().all()
        return [
            PlotOut(
                id=p.id,
                project_id=p.project_id,
                title=p.title,
                plot_type=p.plot_type,
                image_base64=p.image_base64,
                created_at=p.created_at,
            )
            for p in plots
        ]


@router.get("/{plot_id}", response_model=PlotOut)
async def get_plot(
    plot_id: str,
    user: dict = Depends(require_user),
):
    async with async_session_factory() as session:
        result = await session.execute(select(Plot).where(Plot.id == plot_id))
        plot = result.scalar_one_or_none()
        if plot is None:
            raise HTTPException(status_code=404, detail="Plot not found")

        # 驗證所有權
        proj = await session.execute(
            select(Project).where(
                Project.id == plot.project_id,
                Project.owner_id == user["user_id"],
            )
        )
        if proj.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Plot not found")

        return PlotOut(
            id=plot.id,
            project_id=plot.project_id,
            title=plot.title,
            plot_type=plot.plot_type,
            image_base64=plot.image_base64,
            created_at=plot.created_at,
        )


@router.delete("/{plot_id}", status_code=204)
async def delete_plot(
    plot_id: str,
    user: dict = Depends(require_user),
):
    async with async_session_factory() as session:
        result = await session.execute(select(Plot).where(Plot.id == plot_id))
        plot = result.scalar_one_or_none()
        if plot is None:
            raise HTTPException(status_code=404, detail="Plot not found")

        proj = await session.execute(
            select(Project).where(
                Project.id == plot.project_id,
                Project.owner_id == user["user_id"],
            )
        )
        if proj.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Plot not found")

        await session.delete(plot)
        await session.commit()
    return None
