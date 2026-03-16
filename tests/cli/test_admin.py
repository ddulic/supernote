"""Tests for supernote/cli/admin.py."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from supernote.cli.admin import list_users_async


async def test_list_users_async_calls_get_json() -> None:
    """list_users_async calls client.get_json and handles exceptions gracefully."""
    mock_client = AsyncMock()
    mock_client.get_json.side_effect = Exception("blocked")
    mock_resp = AsyncMock()
    mock_resp.json = AsyncMock(return_value=[])
    mock_client.get = AsyncMock(return_value=mock_resp)

    mock_session = MagicMock()
    mock_session.client = mock_client

    @asynccontextmanager
    async def mock_create_session(
        *args: object, **kwargs: object
    ) -> AsyncGenerator[MagicMock, None]:
        yield mock_session

    with patch("supernote.cli.admin.create_session", mock_create_session):
        await list_users_async()

    mock_client.get_json.assert_called_once()
