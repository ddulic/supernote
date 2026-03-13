"""Tests for MCP API key management."""

from typing import Any

import pytest
from aiohttp.test_utils import TestClient

from supernote.server.mcp.api_key import ApiKeyService
from supernote.server.mcp.server import SupernoteTokenVerifier
from supernote.server.services.coordination import SqliteCoordinationService
from supernote.server.services.user import UserService

TEST_USER = "test@example.com"


# ---------------------------------------------------------------------------
# ApiKeyService unit tests
# ---------------------------------------------------------------------------


@pytest.fixture
def api_key_service(
    coordination_service: SqliteCoordinationService,
) -> ApiKeyService:
    return ApiKeyService(coordination_service)


async def test_create_key_returns_plaintext(api_key_service: ApiKeyService) -> None:
    key = await api_key_service.create_key(TEST_USER, "my key")
    assert key.startswith("snmcp_")
    assert len(key) > len("snmcp_")


async def test_create_key_is_listed(api_key_service: ApiKeyService) -> None:
    await api_key_service.create_key(TEST_USER, "listed key")
    keys = await api_key_service.list_keys(TEST_USER)
    assert len(keys) == 1
    assert keys[0]["name"] == "listed key"
    assert "id" in keys[0]
    assert "created_at" in keys[0]
    assert keys[0]["last_used_at"] is None


async def test_multiple_keys_listed(api_key_service: ApiKeyService) -> None:
    await api_key_service.create_key(TEST_USER, "key one")
    await api_key_service.create_key(TEST_USER, "key two")
    keys = await api_key_service.list_keys(TEST_USER)
    assert len(keys) == 2
    names = {k["name"] for k in keys}
    assert names == {"key one", "key two"}


async def test_verify_valid_key(api_key_service: ApiKeyService) -> None:
    key = await api_key_service.create_key(TEST_USER, "verifiable")
    user_id = await api_key_service.verify_key(key)
    assert user_id == TEST_USER


async def test_verify_invalid_key(api_key_service: ApiKeyService) -> None:
    user_id = await api_key_service.verify_key("snmcp_notarealkey")
    assert user_id is None


async def test_verify_wrong_prefix(api_key_service: ApiKeyService) -> None:
    user_id = await api_key_service.verify_key("Bearer sometoken")
    assert user_id is None


async def test_verify_updates_last_used_at(api_key_service: ApiKeyService) -> None:
    key = await api_key_service.create_key(TEST_USER, "track usage")
    keys_before = await api_key_service.list_keys(TEST_USER)
    assert keys_before[0]["last_used_at"] is None

    await api_key_service.verify_key(key)

    keys_after = await api_key_service.list_keys(TEST_USER)
    assert keys_after[0]["last_used_at"] is not None


async def test_delete_key(api_key_service: ApiKeyService) -> None:
    key = await api_key_service.create_key(TEST_USER, "to delete")
    keys = await api_key_service.list_keys(TEST_USER)
    key_id = keys[0]["id"]

    deleted = await api_key_service.delete_key(TEST_USER, key_id)
    assert deleted is True

    # Key is gone from list
    assert await api_key_service.list_keys(TEST_USER) == []

    # Key no longer verifies
    assert await api_key_service.verify_key(key) is None


async def test_delete_nonexistent_key(api_key_service: ApiKeyService) -> None:
    deleted = await api_key_service.delete_key(TEST_USER, "nonexistent")
    assert deleted is False


async def test_delete_other_users_key(api_key_service: ApiKeyService) -> None:
    await api_key_service.create_key(TEST_USER, "owner key")
    keys = await api_key_service.list_keys(TEST_USER)
    key_id = keys[0]["id"]

    deleted = await api_key_service.delete_key("other@example.com", key_id)
    assert deleted is False

    # Original key still present
    assert len(await api_key_service.list_keys(TEST_USER)) == 1


# ---------------------------------------------------------------------------
# SupernoteTokenVerifier: API key path
# ---------------------------------------------------------------------------


async def test_token_verifier_accepts_api_key(
    coordination_service: SqliteCoordinationService,
    user_service: UserService,
    create_test_user: Any,
) -> None:
    """SupernoteTokenVerifier should accept a valid API key as a Bearer token."""
    svc = ApiKeyService(coordination_service)
    key = await svc.create_key(TEST_USER, "verifier test")

    verifier = SupernoteTokenVerifier(user_service, coordination_service)
    token = await verifier.verify_token(key)

    assert token is not None
    assert token.user_id == TEST_USER
    assert token.client_id == "api_key"
    assert "supernote:all" in token.scopes


async def test_token_verifier_rejects_bad_api_key(
    coordination_service: SqliteCoordinationService,
    user_service: UserService,
    create_test_user: Any,
) -> None:
    verifier = SupernoteTokenVerifier(user_service, coordination_service)
    token = await verifier.verify_token("snmcp_invalidkey")
    assert token is None


# ---------------------------------------------------------------------------
# HTTP route integration tests
# ---------------------------------------------------------------------------


async def test_route_create_api_key(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.post(
        "/api/mcp/api-keys",
        json={"name": "test key"},
        headers=auth_headers,
    )
    assert resp.status == 200
    data = await resp.json()
    assert "key" in data
    assert data["key"].startswith("snmcp_")
    assert data["name"] == "test key"


async def test_route_create_api_key_missing_name(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.post(
        "/api/mcp/api-keys",
        json={"name": ""},
        headers=auth_headers,
    )
    assert resp.status == 400


async def test_route_list_api_keys_empty(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.get("/api/mcp/api-keys", headers=auth_headers)
    assert resp.status == 200
    data = await resp.json()
    assert data["keys"] == []


async def test_route_list_api_keys(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    await client.post(
        "/api/mcp/api-keys",
        json={"name": "listed"},
        headers=auth_headers,
    )
    resp = await client.get("/api/mcp/api-keys", headers=auth_headers)
    assert resp.status == 200
    data = await resp.json()
    assert len(data["keys"]) == 1
    assert data["keys"][0]["name"] == "listed"
    assert data["keys"][0]["last_used_at"] is None


async def test_route_delete_api_key(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    create_resp = await client.post(
        "/api/mcp/api-keys",
        json={"name": "to revoke"},
        headers=auth_headers,
    )
    assert create_resp.status == 200

    list_resp = await client.get("/api/mcp/api-keys", headers=auth_headers)
    keys = (await list_resp.json())["keys"]
    assert len(keys) == 1
    key_id = keys[0]["id"]

    del_resp = await client.delete(f"/api/mcp/api-keys/{key_id}", headers=auth_headers)
    assert del_resp.status == 200

    list_resp2 = await client.get("/api/mcp/api-keys", headers=auth_headers)
    assert (await list_resp2.json())["keys"] == []


async def test_route_delete_nonexistent_key(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.delete("/api/mcp/api-keys/nonexistent", headers=auth_headers)
    assert resp.status == 404


async def test_route_requires_auth(client: TestClient) -> None:
    resp = await client.post("/api/mcp/api-keys", json={"name": "x"})
    assert resp.status == 401

    resp = await client.get("/api/mcp/api-keys")
    assert resp.status == 401

    resp = await client.delete("/api/mcp/api-keys/someid")
    assert resp.status == 401
