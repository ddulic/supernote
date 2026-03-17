"""Tests for prompt configuration routes."""

from aiohttp.test_utils import TestClient
from sqlalchemy import select

from supernote.server.db.models.file import UserFileDO
from supernote.server.db.models.note_processing import NotePageContentDO
from supernote.server.db.models.user import UserDO
from supernote.server.db.session import DatabaseSessionManager

TEST_USER_EMAIL = "test@example.com"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _get_user_id(session_manager: DatabaseSessionManager) -> int:
    """Get the numeric user_id for the test user from the DB."""
    async with session_manager.session() as session:
        result = await session.execute(
            select(UserDO).where(UserDO.email == TEST_USER_EMAIL)
        )
        user = result.scalar_one()
        return user.id


# ---------------------------------------------------------------------------
# Authentication guard
# ---------------------------------------------------------------------------


async def test_get_prompts_unauthenticated(client: TestClient) -> None:
    """GET /api/extended/prompts returns 401 without auth."""
    resp = await client.get("/api/extended/prompts")
    assert resp.status == 401


async def test_put_prompt_unauthenticated(client: TestClient) -> None:
    """PUT /api/extended/prompts returns 401 without auth."""
    resp = await client.put(
        "/api/extended/prompts",
        json={"category": "ocr", "layer": "default", "content": "test"},
    )
    assert resp.status == 401


async def test_delete_prompt_unauthenticated(client: TestClient) -> None:
    """DELETE /api/extended/prompts/{category}/{layer} returns 401 without auth."""
    resp = await client.delete("/api/extended/prompts/ocr/default")
    assert resp.status == 401


# ---------------------------------------------------------------------------
# GET /api/extended/prompts
# ---------------------------------------------------------------------------


async def test_get_prompts_returns_all_layers(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /api/extended/prompts returns all known layers."""
    resp = await client.get("/api/extended/prompts", headers=auth_headers)
    assert resp.status == 200
    data = await resp.json()
    assert data["success"] is True
    assert isinstance(data["prompts"], list)
    assert len(data["prompts"]) > 0

    categories = {p["category"] for p in data["prompts"]}
    assert "ocr" in categories
    assert "summary" in categories


async def test_get_prompts_no_overrides_by_default(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /api/extended/prompts shows isOverride=False for new users."""
    resp = await client.get("/api/extended/prompts", headers=auth_headers)
    data = await resp.json()
    for prompt in data["prompts"]:
        assert prompt["isOverride"] is False


# ---------------------------------------------------------------------------
# PUT /api/extended/prompts
# ---------------------------------------------------------------------------


async def test_put_prompt_creates_override(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """PUT /api/extended/prompts saves an override."""
    resp = await client.put(
        "/api/extended/prompts",
        headers=auth_headers,
        json={
            "category": "summary",
            "layer": "monthly",
            "content": "Monthly summary text.",
        },
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["success"] is True

    # Now GET should show isOverride=True for summary/monthly
    resp2 = await client.get("/api/extended/prompts", headers=auth_headers)
    prompts = (await resp2.json())["prompts"]
    monthly_summary = next(
        (p for p in prompts if p["category"] == "summary" and p["layer"] == "monthly"),
        None,
    )
    assert monthly_summary is not None
    assert monthly_summary["isOverride"] is True
    assert monthly_summary["content"] == "Monthly summary text."


async def test_put_prompt_invalid_category(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """PUT /api/extended/prompts with invalid category returns 400."""
    resp = await client.put(
        "/api/extended/prompts",
        headers=auth_headers,
        json={"category": "invalid", "layer": "default", "content": "text"},
    )
    assert resp.status == 400
    data = await resp.json()
    assert data["success"] is False


async def test_put_prompt_empty_content(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """PUT /api/extended/prompts with empty content returns 400."""
    resp = await client.put(
        "/api/extended/prompts",
        headers=auth_headers,
        json={"category": "ocr", "layer": "default", "content": "   "},
    )
    assert resp.status == 400
    data = await resp.json()
    assert data["success"] is False


# ---------------------------------------------------------------------------
# DELETE /api/extended/prompts/{category}/{layer}
# ---------------------------------------------------------------------------


async def test_delete_prompt_existing_override(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """DELETE removes an existing override."""
    # First save one
    await client.put(
        "/api/extended/prompts",
        headers=auth_headers,
        json={"category": "ocr", "layer": "common", "content": "Override text"},
    )

    resp = await client.delete("/api/extended/prompts/ocr/common", headers=auth_headers)
    assert resp.status == 200
    data = await resp.json()
    assert data["success"] is True


async def test_delete_prompt_not_found(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """DELETE returns 404 when no override exists."""
    resp = await client.delete(
        "/api/extended/prompts/ocr/nonexistent-layer", headers=auth_headers
    )
    assert resp.status == 404
    data = await resp.json()
    assert data["success"] is False


# ---------------------------------------------------------------------------
# GET /api/extended/files/{file_id}/staleness
# ---------------------------------------------------------------------------


async def test_staleness_requires_auth(client: TestClient) -> None:
    """Staleness endpoint returns 401 without auth."""
    resp = await client.get("/api/extended/files/1/staleness")
    assert resp.status == 401


async def test_staleness_other_user_file_returns_403(
    client: TestClient,
    auth_headers: dict[str, str],
    session_manager: DatabaseSessionManager,
) -> None:
    """Staleness endpoint returns 403 for files owned by another user."""
    # Seed a file owned by user_id=9999 (not the test user)
    async with session_manager.session() as session:
        file_do = UserFileDO(
            id=5001,
            user_id=9999,
            file_name="other.note",
            is_folder="N",
        )
        session.add(file_do)
        await session.commit()

    resp = await client.get("/api/extended/files/5001/staleness", headers=auth_headers)
    assert resp.status == 403


async def test_staleness_returns_per_page_status(
    client: TestClient,
    auth_headers: dict[str, str],
    session_manager: DatabaseSessionManager,
    create_test_user: None,
) -> None:
    """Staleness endpoint returns per-page staleness data."""
    user_id = await _get_user_id(session_manager)

    async with session_manager.session() as session:
        file_do = UserFileDO(
            id=6001,
            user_id=user_id,
            file_name="monthly.note",
            is_folder="N",
        )
        session.add(file_do)
        page = NotePageContentDO(
            file_id=6001,
            page_index=0,
            page_id="P20231027120000abc",
            prompt_hash=None,  # pre-feature, treated as stale
        )
        session.add(page)
        await session.commit()

    resp = await client.get("/api/extended/files/6001/staleness", headers=auth_headers)
    assert resp.status == 200
    data = await resp.json()
    assert data["success"] is True
    assert data["totalCount"] == 1
    assert data["staleCount"] == 1
    assert data["pages"][0]["isStale"] is True
    assert data["pages"][0]["pageId"] == "P20231027120000abc"
    assert "currentPromptHash" in data


# ---------------------------------------------------------------------------
# POST /api/extended/files/{file_id}/reprocess
# ---------------------------------------------------------------------------


async def test_reprocess_requires_auth(client: TestClient) -> None:
    """Reprocess endpoint returns 401 without auth."""
    resp = await client.post("/api/extended/files/1/reprocess")
    assert resp.status == 401


async def test_reprocess_other_user_file_returns_403(
    client: TestClient,
    auth_headers: dict[str, str],
    session_manager: DatabaseSessionManager,
) -> None:
    """Reprocess endpoint returns 403 for files owned by another user."""
    async with session_manager.session() as session:
        file_do = UserFileDO(
            id=5002,
            user_id=9999,
            file_name="other.note",
            is_folder="N",
        )
        session.add(file_do)
        await session.commit()

    resp = await client.post("/api/extended/files/5002/reprocess", headers=auth_headers)
    assert resp.status == 403


async def test_reprocess_file_no_stale_pages(
    client: TestClient,
    auth_headers: dict[str, str],
    session_manager: DatabaseSessionManager,
    create_test_user: None,
) -> None:
    """Reprocess with no stale pages returns queued_page_count=0."""
    user_id = await _get_user_id(session_manager)

    # Compute what the current hash would be and stamp the page with it
    # (by first calling staleness to get the hash, then updating the row)
    async with session_manager.session() as session:
        file_do = UserFileDO(
            id=7001,
            user_id=user_id,
            file_name="monthly.note",
            is_folder="N",
        )
        session.add(file_do)
        await session.commit()

    # Get current hash
    stale_resp = await client.get(
        "/api/extended/files/7001/staleness", headers=auth_headers
    )
    current_hash = (await stale_resp.json())["currentPromptHash"]

    # Seed a page with matching hash
    async with session_manager.session() as session:
        page = NotePageContentDO(
            file_id=7001,
            page_index=0,
            page_id="P001",
            prompt_hash=current_hash,
        )
        session.add(page)
        await session.commit()

    resp = await client.post("/api/extended/files/7001/reprocess", headers=auth_headers)
    assert resp.status == 200
    data = await resp.json()
    assert data["success"] is True
    assert data["queuedPageCount"] == 0


# ---------------------------------------------------------------------------
# POST /api/extended/files/{file_id}/pages/{page_id}/reprocess
# ---------------------------------------------------------------------------


async def test_reprocess_page_requires_auth(client: TestClient) -> None:
    """Page reprocess endpoint returns 401 without auth."""
    resp = await client.post("/api/extended/files/1/pages/P001/reprocess")
    assert resp.status == 401


async def test_reprocess_page_not_stale_returns_400(
    client: TestClient,
    auth_headers: dict[str, str],
    session_manager: DatabaseSessionManager,
    create_test_user: None,
) -> None:
    """Page reprocess returns 400 when the page is not stale."""
    user_id = await _get_user_id(session_manager)

    async with session_manager.session() as session:
        file_do = UserFileDO(
            id=8001,
            user_id=user_id,
            file_name="monthly.note",
            is_folder="N",
        )
        session.add(file_do)
        await session.commit()

    # Get current hash for a fresh file
    stale_resp = await client.get(
        "/api/extended/files/8001/staleness", headers=auth_headers
    )
    current_hash = (await stale_resp.json())["currentPromptHash"]

    async with session_manager.session() as session:
        page = NotePageContentDO(
            file_id=8001,
            page_index=0,
            page_id="P8001",
            prompt_hash=current_hash,  # up-to-date
        )
        session.add(page)
        await session.commit()

    resp = await client.post(
        "/api/extended/files/8001/pages/P8001/reprocess", headers=auth_headers
    )
    assert resp.status == 400
    data = await resp.json()
    assert data["success"] is False
