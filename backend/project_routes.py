"""
Virgo Agent — Project CRUD routes
/api/projects — full CRUD with JWT auth
"""
from fastapi import APIRouter, HTTPException, Depends
import database
import auth_utils
from models import ProjectCreate, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _row_to_dict(row) -> dict:
    """Convert aiosqlite.Row to plain dict."""
    return dict(row) if row else {}


@router.post("", status_code=201)
async def create_project(
    req: ProjectCreate,
    user: dict = Depends(auth_utils.require_user),
):
    """Create a new project for the authenticated user."""
    db = await database.get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO projects (user_id, title, description, sections)
               VALUES (?, ?, ?, ?)""",
            (user["user_id"], req.title, req.description, req.sections),
        )
        await db.commit()
        pid = cursor.lastrowid

        row = await db.execute("SELECT * FROM projects WHERE id = ?", (pid,))
        project = await row.fetchone()
        return _row_to_dict(project)
    finally:
        await db.close()


@router.get("")
async def list_projects(
    user: dict = Depends(auth_utils.require_user),
):
    """List all projects for the authenticated user."""
    db = await database.get_db()
    try:
        rows = await db.execute(
            "SELECT * FROM projects WHERE user_id = ? ORDER BY updated_at DESC",
            (user["user_id"],),
        )
        projects = await rows.fetchall()
        return [_row_to_dict(p) for p in projects]
    finally:
        await db.close()


@router.get("/{project_id}")
async def get_project(
    project_id: int,
    user: dict = Depends(auth_utils.require_user),
):
    """Get a single project by ID (must belong to user)."""
    db = await database.get_db()
    try:
        row = await db.execute(
            "SELECT * FROM projects WHERE id = ? AND user_id = ?",
            (project_id, user["user_id"]),
        )
        project = await row.fetchone()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return _row_to_dict(project)
    finally:
        await db.close()


@router.put("/{project_id}")
async def update_project(
    project_id: int,
    req: ProjectUpdate,
    user: dict = Depends(auth_utils.require_user),
):
    """Update a project (partial update — only supplied fields change)."""
    db = await database.get_db()
    try:
        row = await db.execute(
            "SELECT * FROM projects WHERE id = ? AND user_id = ?",
            (project_id, user["user_id"]),
        )
        project = await row.fetchone()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        updates = []
        values = []
        for field in ("title", "description", "sections"):
            val = getattr(req, field, None)
            if val is not None:
                updates.append(f"{field} = ?")
                values.append(val)

        if updates:
            updates.append("updated_at = datetime('now')")
            values.extend([project_id, user["user_id"]])
            await db.execute(
                f"UPDATE projects SET {', '.join(updates)} WHERE id = ? AND user_id = ?",
                values,
            )
            await db.commit()

        row = await db.execute(
            "SELECT * FROM projects WHERE id = ? AND user_id = ?",
            (project_id, user["user_id"]),
        )
        updated = await row.fetchone()
        return _row_to_dict(updated)
    finally:
        await db.close()


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    user: dict = Depends(auth_utils.require_user),
):
    """Delete a project (must belong to user)."""
    db = await database.get_db()
    try:
        cursor = await db.execute(
            "DELETE FROM projects WHERE id = ? AND user_id = ?",
            (project_id, user["user_id"]),
        )
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Project not found")
        return None
    finally:
        await db.close()
