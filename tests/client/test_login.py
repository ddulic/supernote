"""Tests for the login flow."""

from typing import Awaitable, Callable

import aiohttp
import aiohttp.test_utils
import pytest
from aiohttp import web
from pytest_aiohttp import AiohttpClient

from supernote.client import Client
from supernote.models.auth import LoginVO, RandomCodeVO

# Pre-computed SHA256("password" + "123456") — fixed values used by test mock and test_login_flow
_TEST_LOGIN_HASH = "a4dd5658ec0219465b705ea7c7435d9786a3c66d4f448cabd7488dabceafb699"


async def handler_random_code(request: web.Request) -> web.Response:
    """Handle random code request."""
    data = await request.json()
    if "account" not in data or "countryCode" not in data:
        return web.Response(status=400)
    return web.json_response(
        {"success": True, "randomCode": "123456", "timestamp": "1600000000"}
    )


async def handler_login_new(request: web.Request) -> web.Response:
    """Handle new login request."""
    data = await request.json()
    if data.get("password") == _TEST_LOGIN_HASH:
        return web.json_response(
            {"success": True, "token": "new-access-token", "counts": "0"}
        )
    return web.json_response({"success": False, "errorMsg": "Invalid password"})


async def handler_csrf(request: web.Request) -> web.Response:
    """Handle CSRF request."""
    return web.Response(text="ok", headers={"X-XSRF-TOKEN": "test-token"})


@pytest.fixture(name="client")
async def client_fixture(aiohttp_client: AiohttpClient) -> Client:
    app = web.Application()
    app.router.add_get("/api/csrf", handler_csrf)
    app.router.add_post("/api/official/user/query/random/code", handler_random_code)
    app.router.add_post("/api/official/user/account/login/new", handler_login_new)

    test_client = await aiohttp_client(app)
    base_url = str(test_client.make_url(""))
    return Client(test_client.session, host=base_url)


async def test_login_flow(client: Client) -> None:
    """Test the full login flow."""
    # Step 1: Get random code
    code_resp = await client.post_json(
        "/api/official/user/query/random/code",
        RandomCodeVO,
        json={"account": "test@example.com", "countryCode": 1},
    )
    assert code_resp.success
    assert code_resp.random_code == "123456"

    # Step 2: Use pre-computed hash (SHA256("password" + "123456"), matching mock)
    password_hash = _TEST_LOGIN_HASH

    # Step 3: Login
    login_resp = await client.post_json(
        "/api/official/user/account/login/new",
        LoginVO,
        json={
            "account": "test@example.com",
            "password": password_hash,
            "timestamp": code_resp.timestamp,
            "loginMethod": 1,
            "countryCode": 1,
            "equipment": 1,
            "browser": "Chrome",
            "language": "en",
        },
    )
    assert login_resp.success
    assert login_resp.token == "new-access-token"


async def test_login_headers(
    aiohttp_client: Callable[
        [web.Application], Awaitable[aiohttp.test_utils.TestClient]
    ],
) -> None:
    """Test login headers."""

    async def handler_headers(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "success": True,
                "data": dict(request.headers),
            }
        )

    # Simplified CSRF handler
    async def handler_csrf(request: web.Request) -> web.Response:
        return web.Response(text="ok", headers={"X-XSRF-TOKEN": "test-token"})

    app = web.Application()
    app.router.add_get("/api/csrf", handler_csrf)
    # We hijack the login endpoint path to check headers
    app.router.add_post("/api/official/user/account/login/new", handler_headers)

    test_client = await aiohttp_client(app)
    base_url = str(test_client.make_url(""))
    client = Client(test_client.session, host=base_url.rstrip("/"))

    # Call the endpoint
    response = await client.post(
        "/api/official/user/account/login/new", json={"some": "payload"}
    )
    data = await response.json()

    headers = data["data"]
    assert headers.get("Referer") == base_url.rstrip("/")
    assert headers.get("Origin") == base_url.rstrip("/")
