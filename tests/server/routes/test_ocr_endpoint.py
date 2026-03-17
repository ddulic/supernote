"""Tests for POST /api/extended/file/ocr/list endpoint.

Per constitution §VI: written before implementation; must FAIL until endpoint is added.
Per constitution §VII: includes auth and ownership security tests.
"""

from unittest.mock import AsyncMock, patch

from aiohttp.test_utils import TestClient

from supernote.server.db.models.file import UserFileDO
from supernote.server.db.models.note_processing import NotePageContentDO
from supernote.server.db.session import DatabaseSessionManager

USER_ID = 1
OTHER_USER_ID = 2
FILE_ID = 200
OTHER_FILE_ID = 201
OCR_ENDPOINT = "/api/extended/file/ocr/list"


# ---------------------------------------------------------------------------
# Happy path: returns pages ordered by page_index
# ---------------------------------------------------------------------------


async def test_ocr_list_returns_pages_ordered(
    client: TestClient,
    auth_headers: dict[str, str],
    session_manager: DatabaseSessionManager,
    create_test_user: None,
) -> None:
    async with session_manager.session() as session:
        session.add(
            UserFileDO(id=FILE_ID, user_id=USER_ID, file_name="n.note", directory_id=0)
        )
        session.add(
            NotePageContentDO(
                file_id=FILE_ID, page_index=1, page_id="p1", text_content="Page two"
            )
        )
        session.add(
            NotePageContentDO(
                file_id=FILE_ID, page_index=0, page_id="p0", text_content="Page one"
            )
        )
        await session.commit()

    resp = await client.post(
        OCR_ENDPOINT, json={"fileId": FILE_ID}, headers=auth_headers
    )
    assert resp.status == 200
    data = await resp.json()
    assert "pages" in data
    assert len(data["pages"]) == 2
    assert data["pages"][0]["pageIndex"] == 0
    assert data["pages"][0]["textContent"] == "Page one"
    assert data["pages"][1]["pageIndex"] == 1
    assert data["pages"][1]["textContent"] == "Page two"


# ---------------------------------------------------------------------------
# Empty result: file exists but no OCR text
# ---------------------------------------------------------------------------


async def test_ocr_list_empty_when_no_ocr_data(
    client: TestClient,
    auth_headers: dict[str, str],
    session_manager: DatabaseSessionManager,
    create_test_user: None,
) -> None:
    async with session_manager.session() as session:
        session.add(
            UserFileDO(id=FILE_ID, user_id=USER_ID, file_name="n.note", directory_id=0)
        )
        session.add(
            NotePageContentDO(
                file_id=FILE_ID, page_index=0, page_id="p0", text_content=None
            )
        )
        await session.commit()

    resp = await client.post(
        OCR_ENDPOINT, json={"fileId": FILE_ID}, headers=auth_headers
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["pages"] == []


# ---------------------------------------------------------------------------
# Security: 401 without token
# ---------------------------------------------------------------------------


async def test_ocr_list_unauthorized_without_token(client: TestClient) -> None:
    resp = await client.post(OCR_ENDPOINT, json={"fileId": FILE_ID})
    assert resp.status == 401


# ---------------------------------------------------------------------------
# Security: 403 when file belongs to another user
# ---------------------------------------------------------------------------


async def test_ocr_list_forbidden_for_other_users_file(
    client: TestClient,
    auth_headers: dict[str, str],
    session_manager: DatabaseSessionManager,
    create_test_user: None,
) -> None:
    """File owned by OTHER_USER_ID (2) — authenticated user (1) must receive 403."""
    async with session_manager.session() as session:
        session.add(
            UserFileDO(
                id=OTHER_FILE_ID,
                user_id=OTHER_USER_ID,
                file_name="other.note",
                directory_id=0,
            )
        )
        await session.commit()

    resp = await client.post(
        OCR_ENDPOINT, json={"fileId": OTHER_FILE_ID}, headers=auth_headers
    )
    assert resp.status == 403


# ---------------------------------------------------------------------------
# 404: file not found
# ---------------------------------------------------------------------------


async def test_ocr_list_not_found_for_unknown_file(
    client: TestClient,
    auth_headers: dict[str, str],
    create_test_user: None,
) -> None:
    resp = await client.post(OCR_ENDPOINT, json={"fileId": 99999}, headers=auth_headers)
    assert resp.status == 404


# ---------------------------------------------------------------------------
# 400: malformed / missing body
# ---------------------------------------------------------------------------


async def test_ocr_list_invalid_json(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        OCR_ENDPOINT,
        data=b"not json",
        headers={**auth_headers, "Content-Type": "application/json"},
    )
    assert resp.status == 400


async def test_ocr_list_missing_file_id(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        OCR_ENDPOINT, json={"unexpected": True}, headers=auth_headers
    )
    assert resp.status == 400


# ---------------------------------------------------------------------------
# 500: generic unexpected error
# ---------------------------------------------------------------------------


async def test_ocr_list_generic_error(
    client: TestClient, auth_headers: dict[str, str], create_test_user: None
) -> None:
    with patch(
        "supernote.server.services.user.UserService.get_user_id",
        new_callable=AsyncMock,
        side_effect=RuntimeError("boom"),
    ):
        resp = await client.post(
            OCR_ENDPOINT, json={"fileId": FILE_ID}, headers=auth_headers
        )
    assert resp.status == 500
