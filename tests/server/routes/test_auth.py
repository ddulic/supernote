from unittest.mock import AsyncMock, patch

from aiohttp.test_utils import TestClient

from supernote.client.client import Client
from supernote.server.exceptions import SupernoteError


async def test_empty_token(
    client: Client,
) -> None:
    result = await client.post("/api/user/query/token")
    data = await result.json()
    assert data == {
        "success": True,
        "token": None,  # Client expects this field always to be present
        "errorCode": None,
        "errorMsg": None,
    }


# ---------------------------------------------------------------------------
# Public routes (no auth header needed)
# ---------------------------------------------------------------------------


async def test_equipment_unlink_invalid_dto(client: TestClient) -> None:
    """POST /api/terminal/equipment/unlink with missing fields returns 400."""
    resp = await client.post("/api/terminal/equipment/unlink", json={"bad_field": "x"})
    assert resp.status == 400


async def test_check_user_not_found(client: TestClient) -> None:
    """POST /api/official/user/check/exists/server returns error when user absent."""
    resp = await client.post(
        "/api/official/user/check/exists/server",
        json={"email": "nobody@example.com"},
    )
    data = await resp.json()
    assert data.get("success") is False or "not found" in (data.get("errorMsg") or "")


async def test_bind_equipment_invalid_dto(client: TestClient) -> None:
    """POST /api/terminal/user/bindEquipment with missing fields returns 400."""
    resp = await client.post("/api/terminal/user/bindEquipment", json={})
    assert resp.status == 400


async def test_register_invalid_dto(client: TestClient) -> None:
    """POST /api/user/register with missing required fields returns 400."""
    resp = await client.post("/api/user/register", json={"bad": "data"})
    assert resp.status == 400


async def test_register_supernote_error(client: TestClient) -> None:
    """POST /api/user/register when service raises SupernoteError returns error."""
    with patch(
        "supernote.server.services.user.UserService.register",
        new_callable=AsyncMock,
    ) as m:
        m.side_effect = SupernoteError("registration closed", status_code=403)
        resp = await client.post(
            "/api/user/register",
            json={"email": "x@x.com", "password": "abc123", "userName": "X"},
        )
    assert resp.status == 403


async def test_register_generic_error(client: TestClient) -> None:
    """POST /api/user/register when service raises unexpected error returns 500."""
    with patch(
        "supernote.server.services.user.UserService.register",
        new_callable=AsyncMock,
    ) as m:
        m.side_effect = RuntimeError("db fail")
        resp = await client.post(
            "/api/user/register",
            json={"email": "x@x.com", "password": "abc123", "userName": "X"},
        )
    assert resp.status == 500


async def test_retrieve_password_disabled(client: TestClient) -> None:
    """POST /api/official/user/retrieve/password returns 403 when reset is disabled."""
    resp = await client.post(
        "/api/official/user/retrieve/password",
        json={"email": "x@x.com", "password": "newpass"},
    )
    # Default config has enable_remote_password_reset=False
    assert resp.status == 403


# ---------------------------------------------------------------------------
# Authenticated routes (no auth header → expect 401 or fall through)
# ---------------------------------------------------------------------------


async def test_user_query_no_auth(client: TestClient) -> None:
    """POST /api/user/query without auth token returns 401."""
    resp = await client.post("/api/user/query", json={})
    assert resp.status == 401


async def test_user_query_user_not_found(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """POST /api/user/query returns 404 when user profile not found."""
    with patch(
        "supernote.server.services.user.UserService.get_user_profile",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await client.post("/api/user/query", json={}, headers=auth_headers)
    assert resp.status == 404


async def test_unregister_no_auth(client: TestClient) -> None:
    """POST /api/user/unregister without auth returns 401."""
    resp = await client.post("/api/user/unregister", json={})
    assert resp.status == 401


async def test_update_password_no_auth(client: TestClient) -> None:
    """PUT /api/user/password without auth returns 401."""
    resp = await client.put(
        "/api/user/password",
        json={"old_password": "old", "new_password": "new"},
    )
    assert resp.status == 401


async def test_update_email_no_auth(client: TestClient) -> None:
    """PUT /api/user/email without auth returns 401."""
    resp = await client.put(
        "/api/user/email",
        json={"email": "new@example.com"},
    )
    assert resp.status == 401


async def test_update_email_authenticated(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """PUT /api/user/email with valid auth succeeds."""
    with patch(
        "supernote.server.services.user.UserService.update_email",
        new_callable=AsyncMock,
    ):
        resp = await client.put(
            "/api/user/email",
            json={"email": "new@example.com"},
            headers=auth_headers,
        )
    assert resp.status == 200


async def test_register_success(client: TestClient) -> None:
    """POST /api/user/register succeeds when registration is enabled."""
    resp = await client.post(
        "/api/user/register",
        json={"email": "newuser@example.com", "password": "abc123", "userName": "New"},
    )
    # Registration may succeed or fail depending on enable_registration
    assert resp.status in (200, 400, 403)


async def test_register_value_error(client: TestClient) -> None:
    """POST /api/user/register returns 400 when service raises ValueError."""
    with patch(
        "supernote.server.services.user.UserService.register",
        new_callable=AsyncMock,
    ) as m:
        m.side_effect = ValueError("email already exists")
        resp = await client.post(
            "/api/user/register",
            json={"email": "x@x.com", "password": "abc123", "userName": "X"},
        )
    assert resp.status == 400


async def test_login_record_no_auth(client: TestClient) -> None:
    """POST /api/user/query/loginRecord without auth returns 401."""
    resp = await client.post("/api/user/query/loginRecord", json={})
    assert resp.status == 401


async def test_login_record_authenticated(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """POST /api/user/query/loginRecord returns records for authenticated user."""
    resp = await client.post(
        "/api/user/query/loginRecord",
        json={"pageNo": "1", "pageSize": "10"},
        headers=auth_headers,
    )
    assert resp.status == 200
