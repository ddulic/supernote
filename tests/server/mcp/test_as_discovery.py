import json

from aiohttp.test_utils import TestClient

from supernote.server.config import ServerConfig


async def test_as_metadata_discovery(
    client: TestClient, server_config: ServerConfig
) -> None:
    """Test that the Authorization Server metadata endpoint is accessible."""
    # The issuer URL is the MCP server base URL (auth routes are hosted there)
    expected_issuer = server_config.mcp_base_url

    resp = await client.get("/.well-known/oauth-authorization-server")
    assert resp.status == 200, (
        f"Expected 200, got {resp.status}. Body: {await resp.text()}"
    )

    data = await resp.json()
    assert data["issuer"] == f"{expected_issuer}/"
    assert data["authorization_endpoint"] == f"{expected_issuer}/authorize"
    assert data["token_endpoint"] == f"{expected_issuer}/token"
    assert data["registration_endpoint"] == f"{expected_issuer}/register"
    assert "code" in data["response_types_supported"]
    assert "none" in data["token_endpoint_auth_methods_supported"]
    assert "S256" in data["code_challenge_methods_supported"]
    assert "supernote:all" in data["scopes_supported"]


async def test_as_authorize_endpoint_reachable(client: TestClient) -> None:
    """Test that the /authorize endpoint returns a redirect (as currently stubbed)."""
    # We need to provide the required OAuth params or it might return 400.
    params = {
        "response_type": "code",
        "client_id": "test-client",
        "redirect_uri": "http://localhost/callback",
        "state": "xyz",
        "code_challenge": "abc",
        "code_challenge_method": "S256",
    }
    resp = await client.get("/authorize", params=params)

    # Returns 400 because get_client returns None for a non-URL client_id.
    # This still proves the request reached the AS app and passed the JWT middleware.
    assert resp.status in (200, 302, 400)


async def test_dynamic_client_registration(client: TestClient) -> None:
    """Test that dynamic client registration (RFC 7591) works."""
    registration_data = {
        "redirect_uris": ["https://claude.ai/callback"],
        "client_name": "Claude",
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
        "scope": "supernote:all",
    }
    resp = await client.post(
        "/register",
        data=json.dumps(registration_data),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status == 201, (
        f"Expected 201, got {resp.status}. Body: {await resp.text()}"
    )

    data = await resp.json()
    assert "client_id" in data
    assert data["redirect_uris"] == ["https://claude.ai/callback"]


async def test_registered_client_can_authorize(client: TestClient) -> None:
    """Test that a dynamically registered client can be used in the authorize flow."""
    # Register a client
    registration_data = {
        "redirect_uris": ["http://localhost:3000/callback"],
        "client_name": "Test Client",
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
        "scope": "supernote:all",
    }
    reg_resp = await client.post(
        "/register",
        data=json.dumps(registration_data),
        headers={"Content-Type": "application/json"},
    )
    assert reg_resp.status == 201
    client_id = (await reg_resp.json())["client_id"]

    # Use the registered client_id in /authorize — should reach login-bridge, not 400
    resp = await client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": "http://localhost:3000/callback",
            "state": "test-state",
            "code_challenge": "mock-challenge",
            "code_challenge_method": "S256",
        },
        allow_redirects=False,
    )
    # Should redirect to login-bridge (not 400 invalid_client)
    assert resp.status in (302, 307), f"Expected redirect, got {resp.status}"
    assert "login-bridge" in resp.headers.get("Location", "")


async def test_login_bridge_return_to_uses_issuer_url(
    client: TestClient, server_config: ServerConfig
) -> None:
    """Test that login-bridge builds return_to from issuer_url, not from request.url.

    When behind a TLS-terminating reverse proxy, request.url has the internal
    http:// scheme while the public issuer_url is https://. The return_to URL must
    use the issuer_url base so the SPA can POST back without a mixed-content block.
    """
    from urllib.parse import parse_qs, unquote, urlparse

    # Hit /login-bridge directly with OAuth params but no auth token.
    # It should redirect to the main login page with a return_to parameter.
    bridge_resp = await client.get(
        "/login-bridge",
        params={
            "client_id": "test-client",
            "redirect_uri": "https://claude.ai/api/mcp/auth_callback",
            "state": "test-state",
            "code_challenge": "mock-challenge",
            "code_challenge_method": "S256",
        },
        allow_redirects=False,
    )
    assert bridge_resp.status in (302, 307), (
        f"Expected redirect from login-bridge, got {bridge_resp.status}"
    )
    location = bridge_resp.headers.get("Location", "")
    assert "return_to=" in location, f"Expected return_to in Location: {location}"

    # The Location is: {main_base_url}/#login?return_to=<encoded-bridge-url>
    # Extract the encoded return_to value from the fragment.
    parsed = urlparse(location)
    fragment_query = parsed.fragment.split("?", 1)[-1] if "?" in parsed.fragment else ""
    params = parse_qs(fragment_query)
    return_to = unquote(params.get("return_to", [""])[0])

    # return_to must start with the public mcp_base_url (issuer_url), not request.url
    assert return_to.startswith(server_config.mcp_base_url), (
        f"return_to should start with mcp_base_url '{server_config.mcp_base_url}', "
        f"got: {return_to}"
    )
    assert "/login-bridge" in return_to
