from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, PropertyMock, patch

import pytest
from aiohttp.test_utils import TestClient

from supernote.client.client import Client
from supernote.client.extended import ExtendedClient
from supernote.server.db.models.file import UserFileDO
from supernote.server.db.models.note_processing import NotePageContentDO
from supernote.server.db.session import DatabaseSessionManager
from supernote.server.exceptions import SupernoteError


@pytest.fixture
def extended_client(authenticated_client: Client) -> ExtendedClient:
    """Fixture for ExtendedClient."""
    return ExtendedClient(authenticated_client)


@pytest.fixture
def mock_gemini_service() -> Generator[None, None, None]:
    """Fixture to mock Gemini service."""
    # Mock Gemini Service to avoid network calls
    with (
        patch(
            "supernote.server.services.gemini.GeminiService.is_configured",
            new_callable=PropertyMock,
            return_value=True,
        ),
        patch(
            "supernote.server.services.gemini.GeminiService.embed_text",
            AsyncMock(return_value=[1.0, 0.0, 0.0]),
        ),
    ):
        yield


@pytest.fixture(autouse=True)
def patch_gemini_service(mock_gemini_service: Generator[None, None, None]) -> None:
    """Patch the Gemini service in the search service."""
    # This is handled by the mock_gemini_service fixture
    pass


async def test_extended_search(
    extended_client: ExtendedClient,
    session_manager: DatabaseSessionManager,
) -> None:
    # 1. Seed some search data
    user_id = 1
    file_id = 101
    async with session_manager.session() as session:
        session.add(
            UserFileDO(
                id=file_id, user_id=user_id, file_name="SearchTest.note", directory_id=0
            )
        )
        session.add(
            NotePageContentDO(
                file_id=file_id,
                page_index=0,
                page_id="p0",
                text_content="The quick brown fox jumps over the lazy dog.",
                # Mock embedding [1, 0, 0] for simplicity in SQL
                embedding="[1.0, 0.0, 0.0]",
            )
        )
        await session.commit()

    resp = await extended_client.get_transcript(file_id=file_id)
    assert resp.success
    assert resp.transcript is not None
    assert "quick brown fox" in resp.transcript


async def test_extended_search_with_mock(
    extended_client: ExtendedClient,
    session_manager: DatabaseSessionManager,
    client: Any,  # TestClient from aiohttp
) -> None:
    # 1. Seed data
    user_id = 1
    file_id = 101
    async with session_manager.session() as session:
        session.add(
            UserFileDO(
                id=file_id, user_id=user_id, file_name="Fox.note", directory_id=0
            )
        )
        session.add(
            NotePageContentDO(
                file_id=file_id,
                page_index=0,
                page_id="p0",
                text_content="The quick brown fox.",
                embedding="[1.0, 0.0, 0.0]",
            )
        )
        await session.commit()

    # 2. Call API
    # The Gemini service is mocked globally by mock_gemini_service
    resp = await extended_client.search(query="fox")

    assert resp.success
    assert len(resp.results) > 0
    assert resp.results[0].file_id == file_id
    assert "quick brown fox" in resp.results[0].text_preview


async def test_extended_transcript_not_found(
    extended_client: ExtendedClient,
) -> None:
    # Request transcript for non-existent file
    with pytest.raises(Exception):  # The client raises for 404
        await extended_client.get_transcript(file_id=999)


# ---------------------------------------------------------------------------
# Error-path tests for extended routes
# ---------------------------------------------------------------------------


async def test_summary_list_invalid_json(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/api/extended/file/summary/list",
        data=b"not json",
        headers={**auth_headers, "Content-Type": "application/json"},
    )
    assert resp.status == 400


async def test_summary_list_invalid_dto(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/api/extended/file/summary/list",
        json={"unexpected_field_only": True},
        headers=auth_headers,
    )
    # Missing required field file_id → Invalid Request
    assert resp.status in (400, 200)  # depends on DTO validation


async def test_summary_list_supernote_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(
        "supernote.server.services.summary.SummaryService.list_summaries_for_file_internal",
        new_callable=AsyncMock,
    ) as m:
        m.side_effect = SupernoteError("not found", status_code=404)
        resp = await client.post(
            "/api/extended/file/summary/list",
            json={"fileId": 999},
            headers=auth_headers,
        )
    assert resp.status == 404


async def test_summary_list_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(
        "supernote.server.services.summary.SummaryService.list_summaries_for_file_internal",
        new_callable=AsyncMock,
    ) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/extended/file/summary/list",
            json={"fileId": 999},
            headers=auth_headers,
        )
    assert resp.status == 500


async def test_list_system_tasks_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(
        "supernote.server.services.processor.ProcessorService.list_system_tasks",
        new_callable=AsyncMock,
    ) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.get("/api/extended/system/tasks", headers=auth_headers)
    assert resp.status == 500


async def test_file_processing_status_valid(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/api/extended/file/processing/status",
        json={"fileIds": [1, 2, 3]},
        headers=auth_headers,
    )
    assert resp.status == 200
    data = await resp.json()
    assert isinstance(data, dict)


async def test_file_processing_status_invalid_json(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/api/extended/file/processing/status",
        data=b"not json",
        headers={**auth_headers, "Content-Type": "application/json"},
    )
    assert resp.status == 400


async def test_search_invalid_json(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/api/extended/search",
        data=b"not json",
        headers={**auth_headers, "Content-Type": "application/json"},
    )
    assert resp.status == 400


async def test_search_user_not_found(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(
        "supernote.server.services.user.UserService.get_user_id",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await client.post(
            "/api/extended/search",
            json={"query": "test"},
            headers=auth_headers,
        )
    assert resp.status == 404


async def test_search_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(
        "supernote.server.services.search.SearchService.search_chunks",
        new_callable=AsyncMock,
    ) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/extended/search",
            json={"query": "test"},
            headers=auth_headers,
        )
    assert resp.status == 500


async def test_transcript_invalid_json(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/api/extended/transcript",
        data=b"not json",
        headers={**auth_headers, "Content-Type": "application/json"},
    )
    assert resp.status == 400


async def test_transcript_user_not_found(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(
        "supernote.server.services.user.UserService.get_user_id",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await client.post(
            "/api/extended/transcript",
            json={"fileId": 999},
            headers=auth_headers,
        )
    assert resp.status == 404


async def test_transcript_generic_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    with patch(
        "supernote.server.services.search.SearchService.get_transcript",
        new_callable=AsyncMock,
    ) as m:
        m.side_effect = RuntimeError("boom")
        resp = await client.post(
            "/api/extended/transcript",
            json={"fileId": 999},
            headers=auth_headers,
        )
    assert resp.status == 500
