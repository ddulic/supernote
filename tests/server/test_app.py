"""Tests for application-level functionality including proxy header handling.

These tests verify that the server correctly handles X-Forwarded-* headers
when deployed behind a reverse proxy, with different proxy modes.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp.test_utils import TestClient

from supernote.models.file_device import FileUploadApplyLocalDTO
from supernote.server.app import bootstrap_ephemeral_user


# Test for default proxy mode (disabled)
async def test_proxy_headers_ignored_by_default(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Verify that proxy headers are ignored when proxy_mode is None (default)."""

    payload = FileUploadApplyLocalDTO(
        equipment_no="TEST_DEVICE",
        file_name="test_default.note",
        path="/",
        size="1234",
    ).to_dict()

    # Send proxy headers (should be ignored)
    proxy_headers = {
        "X-Forwarded-Proto": "https",
        "X-Forwarded-Host": "malicious-domain.com",
        **auth_headers,
    }

    resp = await client.post(
        "/api/file/3/files/upload/apply", json=payload, headers=proxy_headers
    )
    assert resp.status == 200
    data = await resp.json()

    full_upload_url = data.get("fullUploadUrl")
    assert full_upload_url is not None

    # Should NOT use forwarded headers, should use actual test client host
    from urllib.parse import urlparse

    parsed_url = urlparse(full_upload_url)
    assert not parsed_url.netloc.startswith("malicious-domain.com"), (
        f"Proxy headers should be ignored by default, got: {full_upload_url}"
    )
    # Should use the test server's actual scheme and host
    assert parsed_url.hostname == "127.0.0.1" or parsed_url.hostname == "localhost"


@pytest.mark.parametrize("proxy_mode", ["relaxed"])
async def test_upload_url_proxy_headers_relaxed(
    client: TestClient, auth_headers: dict[str, str], proxy_mode: str
) -> None:
    """Verify that upload URLs respect X-Forwarded headers in relaxed mode."""

    # Payload for upload apply
    payload = FileUploadApplyLocalDTO(
        equipment_no="TEST_DEVICE",
        file_name="test_proxy.note",
        path="/",
        size="1234",
    ).to_dict()

    # Headers mocking a proxy
    proxy_headers = {
        "X-Forwarded-Proto": "https",
        "X-Forwarded-Host": "my-public-domain.com",
        **auth_headers,
    }

    resp = await client.post(
        "/api/file/3/files/upload/apply", json=payload, headers=proxy_headers
    )
    assert resp.status == 200
    data = await resp.json()

    full_upload_url = data.get("fullUploadUrl")
    assert full_upload_url is not None

    # Verification: Should use forwarded headers
    from urllib.parse import urlparse

    parsed_url = urlparse(full_upload_url)
    assert parsed_url.netloc == "my-public-domain.com", f"Got URL: {full_upload_url}"


@pytest.mark.parametrize("proxy_mode", ["relaxed"])
async def test_upload_url_no_proxy_headers(
    client: TestClient, auth_headers: dict[str, str], proxy_mode: str
) -> None:
    """Verify that upload URLs work without proxy headers."""

    payload = FileUploadApplyLocalDTO(
        equipment_no="TEST_DEVICE",
        file_name="test_no_proxy.note",
        path="/",
        size="1234",
    ).to_dict()

    resp = await client.post(
        "/api/file/3/files/upload/apply", json=payload, headers=auth_headers
    )
    assert resp.status == 200
    data = await resp.json()

    full_upload_url = data.get("fullUploadUrl")
    assert full_upload_url is not None

    # Should use the test client's host (127.0.0.1 or similar)
    assert "http://127.0.0.1:" in full_upload_url


@pytest.mark.parametrize("proxy_mode", ["relaxed"])
async def test_upload_url_with_port_in_forwarded_host(
    client: TestClient, auth_headers: dict[str, str], proxy_mode: str
) -> None:
    """Verify that upload URLs respect X-Forwarded-Host with port."""

    payload = FileUploadApplyLocalDTO(
        equipment_no="TEST_DEVICE",
        file_name="test_port.note",
        path="/",
        size="1234",
    ).to_dict()

    # Headers with port in host
    proxy_headers = {
        "X-Forwarded-Proto": "http",
        "X-Forwarded-Host": "localhost:9888",
        **auth_headers,
    }

    resp = await client.post(
        "/api/file/3/files/upload/apply", json=payload, headers=proxy_headers
    )
    assert resp.status == 200
    data = await resp.json()

    full_upload_url = data.get("fullUploadUrl")
    assert full_upload_url is not None

    # Should use forwarded host with port
    assert full_upload_url.startswith("http://localhost:9888"), (
        f"Got URL: {full_upload_url}"
    )


async def test_static_js_no_cache_header(client: TestClient) -> None:
    """JS files must be served with Cache-Control: no-store so that Firefox's
    ES module registry does not serve stale code when DevTools cache is disabled."""
    resp = await client.get("/static/js/main.js")
    assert resp.status == 200
    assert resp.headers.get("Cache-Control") == "no-store"


async def test_static_css_no_cache_header(client: TestClient) -> None:
    """style.css should also carry Cache-Control: no-store."""
    resp = await client.get("/static/style.css")
    assert resp.status == 200
    assert resp.headers.get("Cache-Control") == "no-store"


async def test_static_non_js_no_cache_header_absent(client: TestClient) -> None:
    """Non-JS/CSS static assets (e.g. favicon) should not have the no-store header."""
    resp = await client.get("/static/favicon.ico")
    assert resp.status == 200
    assert resp.headers.get("Cache-Control") != "no-store"


async def test_bootstrap_ephemeral_user_creates_user_when_not_exists() -> None:
    """bootstrap_ephemeral_user creates debug@example.com when the user does not exist."""
    user_service = MagicMock()
    user_service.check_user_exists = AsyncMock(return_value=False)
    user_service.create_user = AsyncMock()

    app: dict[str, object] = {"user_service": user_service}
    await bootstrap_ephemeral_user(app)  # type: ignore[arg-type]

    user_service.check_user_exists.assert_awaited_once_with("debug@example.com")
    user_service.create_user.assert_awaited_once()
    call_dto = user_service.create_user.call_args.args[0]
    assert call_dto.email == "debug@example.com"
    assert call_dto.user_name == "Debug User"


async def test_bootstrap_ephemeral_user_skips_when_user_exists() -> None:
    """bootstrap_ephemeral_user does nothing when debug@example.com already exists."""
    user_service = MagicMock()
    user_service.check_user_exists = AsyncMock(return_value=True)
    user_service.create_user = AsyncMock()

    app: dict[str, object] = {"user_service": user_service}
    await bootstrap_ephemeral_user(app)  # type: ignore[arg-type]

    user_service.check_user_exists.assert_awaited_once_with("debug@example.com")
    user_service.create_user.assert_not_awaited()
