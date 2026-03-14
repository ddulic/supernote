"""Tests for OAuthSessionService and the /api/mcp/oauth-sessions routes."""

import base64
import hashlib
import time
from typing import Any

import pytest
import yarl
from aiohttp.test_utils import TestClient

from supernote.client.login_client import LoginClient
from supernote.server.mcp.auth import SupernoteOAuthProvider
from supernote.server.mcp.models import SupernoteAccessToken, SupernoteRefreshToken
from supernote.server.mcp.oauth_session import OAuthSessionService, _session_id
from supernote.server.services.coordination import SqliteCoordinationService
from supernote.server.services.user import UserService
from tests.server.conftest import TEST_PASSWORD, TEST_USERNAME

TEST_USER = "test@example.com"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _future(seconds: int = 86400) -> int:
    return int(time.time()) + seconds


def _past(seconds: int = 86400) -> int:
    return int(time.time()) - seconds


def calculate_s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


# ---------------------------------------------------------------------------
# OAuthSessionService unit tests
# ---------------------------------------------------------------------------


@pytest.fixture
def session_service(
    coordination_service: SqliteCoordinationService,
) -> OAuthSessionService:
    return OAuthSessionService(coordination_service)


async def test_register_and_list(session_service: OAuthSessionService) -> None:
    await session_service.register(
        user_id=TEST_USER,
        token="tok1",
        client_id="client-a",
        client_name="Claude",
        expires_at=_future(),
    )
    sessions = await session_service.list_sessions(TEST_USER)
    assert len(sessions) == 1
    s = sessions[0]
    assert s["client_id"] == "client-a"
    assert s["client_name"] == "Claude"
    assert s["id"] == _session_id("tok1")
    assert "created_at" in s
    assert "expires_at" in s


async def test_list_filters_expired_sessions(
    session_service: OAuthSessionService,
) -> None:
    await session_service.register(
        user_id=TEST_USER,
        token="tok-active",
        client_id="client-active",
        client_name="Active",
        expires_at=_future(),
    )
    await session_service.register(
        user_id=TEST_USER,
        token="tok-expired",
        client_id="client-expired",
        client_name="Expired",
        expires_at=_past(),
    )
    sessions = await session_service.list_sessions(TEST_USER)
    assert len(sessions) == 1
    assert sessions[0]["client_name"] == "Active"


async def test_list_empty_for_new_user(session_service: OAuthSessionService) -> None:
    sessions = await session_service.list_sessions("nobody@example.com")
    assert sessions == []


async def test_list_uses_client_id_as_fallback_name(
    session_service: OAuthSessionService,
) -> None:
    await session_service.register(
        user_id=TEST_USER,
        token="tok2",
        client_id="client-no-name",
        client_name="",
        expires_at=_future(),
    )
    sessions = await session_service.list_sessions(TEST_USER)
    assert sessions[0]["client_name"] == "client-no-name"


async def test_revoke_removes_session(session_service: OAuthSessionService) -> None:
    await session_service.register(
        user_id=TEST_USER,
        token="tok3",
        client_id="client-b",
        client_name="Test",
        expires_at=_future(),
    )
    session_id = _session_id("tok3")
    result = await session_service.revoke(TEST_USER, session_id)
    assert result is True
    assert await session_service.list_sessions(TEST_USER) == []


async def test_revoke_returns_false_for_nonexistent(
    session_service: OAuthSessionService,
) -> None:
    result = await session_service.revoke(TEST_USER, "nonexistent-id")
    assert result is False


async def test_revoke_does_not_affect_other_users_sessions(
    session_service: OAuthSessionService,
) -> None:
    await session_service.register(
        user_id="other@example.com",
        token="tok-other",
        client_id="client-other",
        client_name="Other",
        expires_at=_future(),
    )
    session_id = _session_id("tok-other")
    # Trying to revoke under the wrong user returns False
    result = await session_service.revoke(TEST_USER, session_id)
    assert result is False
    # Other user's session is untouched
    sessions = await session_service.list_sessions("other@example.com")
    assert len(sessions) == 1


async def test_revoke_by_token(session_service: OAuthSessionService) -> None:
    await session_service.register(
        user_id=TEST_USER,
        token="tok4",
        client_id="client-c",
        client_name="ByToken",
        expires_at=_future(),
    )
    await session_service.revoke_by_token(TEST_USER, "tok4")
    assert await session_service.list_sessions(TEST_USER) == []


async def test_multiple_sessions_revoke_one(
    session_service: OAuthSessionService,
) -> None:
    await session_service.register(TEST_USER, "tok-a", "client-a", "A", _future())
    await session_service.register(TEST_USER, "tok-b", "client-b", "B", _future())
    await session_service.revoke(TEST_USER, _session_id("tok-a"))
    sessions = await session_service.list_sessions(TEST_USER)
    assert len(sessions) == 1
    assert sessions[0]["client_name"] == "B"


# ---------------------------------------------------------------------------
# HTTP route integration tests
# ---------------------------------------------------------------------------


async def test_route_list_sessions_empty(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.get("/api/mcp/oauth-sessions", headers=auth_headers)
    assert resp.status == 200
    data = await resp.json()
    assert data["sessions"] == []


async def test_route_list_sessions_after_oauth_flow(
    client: TestClient,
    auth_headers: dict[str, str],
    create_test_user: Any,
) -> None:
    """A full OAuth code exchange should register a session visible via the API."""
    login_client = LoginClient(
        __import__("supernote.client.client", fromlist=["Client"]).Client(
            client.session, host=str(client.make_url("/"))
        )
    )
    token = await login_client.login(TEST_USERNAME, TEST_PASSWORD)

    verifier = "v" * 50
    client_id = "http://localhost:3000"
    redirect_uri = "http://localhost:3000/callback"

    # /authorize -> /login-bridge
    resp1 = await client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": "s",
            "code_challenge": calculate_s256(verifier),
            "code_challenge_method": "S256",
        },
        allow_redirects=False,
    )
    bridge_path = yarl.URL(resp1.headers["Location"]).path_qs

    # POST to bridge with token -> auth code
    resp2 = await client.post(bridge_path, headers={"x-access-token": token})
    code = yarl.URL((await resp2.json())["redirect_url"]).query["code"]

    # Token exchange
    token_resp = await client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
        },
    )
    assert token_resp.status == 200

    # Session should now appear
    sessions_resp = await client.get("/api/mcp/oauth-sessions", headers=auth_headers)
    assert sessions_resp.status == 200
    sessions = (await sessions_resp.json())["sessions"]
    assert len(sessions) == 1
    assert sessions[0]["client_id"] == client_id


async def test_route_delete_session(
    client: TestClient,
    auth_headers: dict[str, str],
    session_service: OAuthSessionService,
    create_test_user: Any,
) -> None:
    await session_service.register(
        user_id=TEST_USER,
        token="delete-me",
        client_id="client-d",
        client_name="ToDelete",
        expires_at=_future(),
    )
    session_id = _session_id("delete-me")

    resp = await client.delete(
        f"/api/mcp/oauth-sessions/{session_id}", headers=auth_headers
    )
    assert resp.status == 200

    sessions = (
        await (await client.get("/api/mcp/oauth-sessions", headers=auth_headers)).json()
    )["sessions"]
    assert sessions == []


async def test_route_delete_session_not_found(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.delete(
        "/api/mcp/oauth-sessions/nonexistent", headers=auth_headers
    )
    assert resp.status == 404


async def test_route_sessions_requires_auth(client: TestClient) -> None:
    resp = await client.get("/api/mcp/oauth-sessions")
    assert resp.status == 401

    resp = await client.delete("/api/mcp/oauth-sessions/some-id")
    assert resp.status == 401


# ---------------------------------------------------------------------------
# SupernoteOAuthProvider.revoke_token unit tests
# ---------------------------------------------------------------------------


@pytest.fixture
def provider(
    user_service: UserService,
    coordination_service: SqliteCoordinationService,
    session_service: OAuthSessionService,
) -> SupernoteOAuthProvider:
    return SupernoteOAuthProvider(
        user_service=user_service,
        coordination_service=coordination_service,
        issuer_url="http://localhost:8001",
        session_service=session_service,
    )


async def test_revoke_token_refresh(
    provider: SupernoteOAuthProvider,
    coordination_service: SqliteCoordinationService,
    session_service: OAuthSessionService,
) -> None:
    """revoke_token on a refresh token deletes it from KV and session index."""
    refresh_token = SupernoteRefreshToken(
        token="rt-to-revoke",
        user_id=TEST_USER,
        client_id="client-x",
        scopes=["supernote:all"],
        expires_at=_future(),
    )
    await coordination_service.set_value(
        "mcp:refresh_token:rt-to-revoke",
        refresh_token.model_dump_json(),
        ttl=3600,
    )
    await session_service.register(
        user_id=TEST_USER,
        token="rt-to-revoke",
        client_id="client-x",
        client_name="X",
        expires_at=_future(),
    )

    await provider.revoke_token(refresh_token)

    assert (
        await coordination_service.get_value("mcp:refresh_token:rt-to-revoke") is None
    )
    assert await session_service.list_sessions(TEST_USER) == []


async def test_revoke_token_access(
    provider: SupernoteOAuthProvider,
    coordination_service: SqliteCoordinationService,
) -> None:
    """revoke_token on an access token deletes it from KV."""
    access_token = SupernoteAccessToken(
        token="at-to-revoke",
        user_id=TEST_USER,
        client_id="client-x",
        scopes=["supernote:all"],
        expires_at=_future(),
    )
    await coordination_service.set_value(
        "mcp:access_token:at-to-revoke",
        access_token.model_dump_json(),
        ttl=3600,
    )

    await provider.revoke_token(access_token)

    assert await coordination_service.get_value("mcp:access_token:at-to-revoke") is None
