"""Tests for supernote/cli/client.py."""

from unittest.mock import AsyncMock, patch

import pytest

from supernote.cli.client import async_cloud_login


async def test_async_cloud_login_exits_when_token_is_none() -> None:
    """async_cloud_login calls sys.exit(1) when access_token is None."""
    mock_sn = AsyncMock()
    mock_sn.token = None
    mock_sn.__aenter__ = AsyncMock(return_value=mock_sn)
    mock_sn.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("supernote.cli.client.Supernote.login", AsyncMock(return_value=mock_sn)),
        pytest.raises(SystemExit) as exc_info,
    ):
        await async_cloud_login("test@example.com", "password", "http://localhost")

    assert exc_info.value.code == 1
