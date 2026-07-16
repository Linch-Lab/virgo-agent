"""Virgo Agent Phase 1 — 整合測試
"""
import os
import sys

# 測試環境設定 — 必須在 import main 之前
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest"
os.environ["LLM_API_KEY"] = ""
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_virgo.db"

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from main import app
from models import Base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

TEST_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_virgo.db")


# ── Engine (session-scoped, reused across tests) ──

@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Session-scoped engine — 所有測試共用同一 DB 檔案。"""
    engine = create_async_engine(f"sqlite+aiosqlite:///{TEST_DB}", echo=False)
    yield engine
    await engine.dispose()
    try:
        os.remove(TEST_DB)
    except PermissionError:
        pass  # Windows 檔案鎖容忍


@pytest_asyncio.fixture(autouse=True)
async def setup_db(db_engine):
    """每個測試前：drop all tables → recreate。"""
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Patch models
    import models
    models.engine = db_engine
    models.async_session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    yield


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client):
    reg = await client.post("/api/auth/register", json={
        "email": "proj@virgo.dev",
        "display_name": "Project User",
    })
    assert reg.status_code == 201, f"Register failed: {reg.text}"
    token = reg.json()["token"]
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["name"] == "Virgo Agent"


# ═══════════════════════════════════════════════
# Auth
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_register_and_login(client):
    resp = await client.post("/api/auth/register", json={
        "email": "test@virgo.dev",
        "display_name": "Test User",
    })
    assert resp.status_code == 201
    reg = resp.json()
    assert reg["email"] == "test@virgo.dev"
    assert "api_key" in reg
    assert "token" in reg
    api_key = reg["api_key"]

    resp2 = await client.post("/api/auth/register", json={
        "email": "test@virgo.dev", "display_name": "Dup",
    })
    assert resp2.status_code == 409

    resp3 = await client.post("/api/auth/login", json={
        "email": "test@virgo.dev", "api_key": api_key,
    })
    assert resp3.status_code == 200
    login = resp3.json()
    assert login["email"] == "test@virgo.dev"
    assert "token" in login


@pytest.mark.asyncio
async def test_login_invalid(client):
    resp = await client.post("/api/auth/login", json={
        "email": "nobody@nowhere.com", "api_key": "bad-key",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_and_list_api_keys(client):
    reg = await client.post("/api/auth/register", json={
        "email": "keys@virgo.dev", "display_name": "Key Master",
    })
    token = reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/api/auth/api-keys", json={"name": "test-key"}, headers=headers)
    assert resp.status_code == 201
    created = resp.json()
    assert "api_key" in created
    assert created["prefix"] in created["api_key"]

    resp2 = await client.get("/api/auth/api-keys", headers=headers)
    assert resp2.status_code == 200
    keys = resp2.json()
    assert len(keys) >= 2


@pytest.mark.asyncio
async def test_revoke_api_key(client):
    reg = await client.post("/api/auth/register", json={
        "email": "revoke@virgo.dev", "display_name": "Revoker",
    })
    token = reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/api/auth/api-keys", json={"name": "to-revoke"}, headers=headers)
    key_id = resp.json()["id"]

    resp2 = await client.delete(f"/api/auth/api-keys/{key_id}", headers=headers)
    assert resp2.status_code == 204

    resp3 = await client.get("/api/auth/api-keys", headers=headers)
    remaining = [k for k in resp3.json() if k["id"] == key_id]
    assert len(remaining) == 0


# ═══════════════════════════════════════════════
# Projects
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_project(client, auth_headers):
    resp = await client.post("/api/projects", json={
        "name": "Test Project", "description": "A test project",
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Project"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_projects(client, auth_headers):
    await client.post("/api/projects", json={"name": "P1"}, headers=auth_headers)
    await client.post("/api/projects", json={"name": "P2"}, headers=auth_headers)
    resp = await client.get("/api/projects", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_update_delete_project(client, auth_headers):
    resp = await client.post("/api/projects", json={"name": "Original"}, headers=auth_headers)
    proj_id = resp.json()["id"]

    resp2 = await client.get(f"/api/projects/{proj_id}", headers=auth_headers)
    assert resp2.status_code == 200
    assert resp2.json()["name"] == "Original"

    resp3 = await client.patch(f"/api/projects/{proj_id}",
                               json={"name": "Updated", "description": "New desc"},
                               headers=auth_headers)
    assert resp3.status_code == 200
    assert resp3.json()["name"] == "Updated"
    assert resp3.json()["description"] == "New desc"

    resp4 = await client.delete(f"/api/projects/{proj_id}", headers=auth_headers)
    assert resp4.status_code == 204

    resp5 = await client.get(f"/api/projects/{proj_id}", headers=auth_headers)
    assert resp5.status_code == 404


@pytest.mark.asyncio
async def test_project_isolation(client, auth_headers):
    resp = await client.post("/api/projects", json={"name": "A's Project"}, headers=auth_headers)
    proj_id = resp.json()["id"]

    reg_b = await client.post("/api/auth/register", json={
        "email": "b@virgo.dev", "display_name": "User B",
    })
    headers_b = {"Authorization": f"Bearer {reg_b.json()['token']}"}

    resp2 = await client.get(f"/api/projects/{proj_id}", headers=headers_b)
    assert resp2.status_code == 404


# ═══════════════════════════════════════════════
# Plots
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_plot(client, auth_headers):
    proj = await client.post("/api/projects", json={"name": "Plot Project"}, headers=auth_headers)
    proj_id = proj.json()["id"]

    resp = await client.post("/api/plots", json={
        "project_id": proj_id, "title": "Test Scatter", "plot_type": "scatter",
        "data": {"x": [1, 2, 3, 4], "y": [10, 20, 15, 30]},
        "xlabel": "X Axis", "ylabel": "Y Axis",
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test Scatter"
    assert data["plot_type"] == "scatter"
    assert data["image_base64"] is not None


@pytest.mark.asyncio
async def test_list_plots(client, auth_headers):
    proj = await client.post("/api/projects", json={"name": "Multi Plot"}, headers=auth_headers)
    proj_id = proj.json()["id"]

    await client.post("/api/plots", json={
        "project_id": proj_id, "title": "P1", "plot_type": "line",
        "data": {"x": [1, 2], "y": [3, 4]},
    }, headers=auth_headers)
    await client.post("/api/plots", json={
        "project_id": proj_id, "title": "P2", "plot_type": "bar",
        "data": {"labels": ["A", "B"], "values": [5, 10]},
    }, headers=auth_headers)

    resp = await client.get(f"/api/plots/project/{proj_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_all_plot_types(client, auth_headers):
    proj = await client.post("/api/projects", json={"name": "All Types"}, headers=auth_headers)
    proj_id = proj.json()["id"]

    tests = [
        ("scatter", {"x": [1, 2, 3], "y": [4, 5, 6]}),
        ("line", {"x": [1, 2, 3], "y": [4, 5, 6]}),
        ("bar", {"labels": ["a", "b"], "values": [1, 2]}),
        ("histogram", {"values": [1, 2, 2, 3, 3, 3, 4, 4, 5]}),
        ("heatmap", {"matrix": [[1, 2], [3, 4]]}),
    ]
    for ptype, data in tests:
        resp = await client.post("/api/plots", json={
            "project_id": proj_id, "title": f"Test {ptype}", "plot_type": ptype, "data": data,
        }, headers=auth_headers)
        assert resp.status_code == 201, f"Failed {ptype}: {resp.text}"
        assert resp.json()["image_base64"]


@pytest.mark.asyncio
async def test_delete_plot(client, auth_headers):
    proj = await client.post("/api/projects", json={"name": "Del Plot"}, headers=auth_headers)
    proj_id = proj.json()["id"]

    plot = await client.post("/api/plots", json={
        "project_id": proj_id, "title": "Bye", "plot_type": "scatter",
        "data": {"x": [1], "y": [2]},
    }, headers=auth_headers)
    plot_id = plot.json()["id"]

    resp = await client.delete(f"/api/plots/{plot_id}", headers=auth_headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_unauthorized(client):
    resp = await client.get("/api/projects")
    assert resp.status_code == 401
    resp = await client.post("/api/projects", json={"name": "x"})
    assert resp.status_code == 401
    resp = await client.post("/api/plots", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_chat_no_api_key(client, auth_headers):
    resp = await client.post("/api/chat/completions", json={
        "messages": [{"role": "user", "content": "Hello"}],
    }, headers=auth_headers)
    assert resp.status_code == 503
