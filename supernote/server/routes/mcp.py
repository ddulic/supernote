"""Routes for managing MCP API keys and OAuth sessions."""

from aiohttp import web

from supernote.models.base import BaseResponse, create_error_response
from supernote.server.mcp.api_key import ApiKeyService
from supernote.server.mcp.oauth_session import OAuthSessionService

routes = web.RouteTableDef()


@routes.post("/api/mcp/api-keys")
async def handle_create_api_key(request: web.Request) -> web.Response:
    """Create a new MCP API key.

    The plaintext key is returned only in this response and cannot be
    retrieved again.

    Request body:
        {"name": "My key"}

    Response:
        {"key": "snmcp_...", "name": "My key"}
    """
    account = request.get("user")
    if not account:
        return web.json_response(
            create_error_response("Unauthorized").to_dict(), status=401
        )

    req_data = await request.json()
    name = req_data.get("name", "").strip()
    if not name:
        return web.json_response(
            create_error_response("name is required").to_dict(), status=400
        )

    api_key_service: ApiKeyService = request.app["api_key_service"]
    key = await api_key_service.create_key(str(account), name)
    return web.json_response({"key": key, "name": name})


@routes.get("/api/mcp/api-keys")
async def handle_list_api_keys(request: web.Request) -> web.Response:
    """List all MCP API keys for the authenticated user.

    Returns key metadata only — plaintext keys are never stored.

    Response:
        {"keys": [{"id": "<sha256>", "name": "...", "created_at": <unix>}]}
    """
    account = request.get("user")
    if not account:
        return web.json_response(
            create_error_response("Unauthorized").to_dict(), status=401
        )

    api_key_service: ApiKeyService = request.app["api_key_service"]
    keys = await api_key_service.list_keys(str(account))
    return web.json_response({"keys": keys})


@routes.delete("/api/mcp/api-keys/{key_id}")
async def handle_delete_api_key(request: web.Request) -> web.Response:
    """Revoke an MCP API key by its ID (SHA-256 hash).

    Returns 404 if the key does not exist or belongs to another user.
    """
    account = request.get("user")
    if not account:
        return web.json_response(
            create_error_response("Unauthorized").to_dict(), status=401
        )

    key_id = request.match_info["key_id"]
    api_key_service: ApiKeyService = request.app["api_key_service"]
    deleted = await api_key_service.delete_key(str(account), key_id)
    if not deleted:
        return web.json_response(
            create_error_response("Key not found").to_dict(), status=404
        )
    return web.json_response(BaseResponse().to_dict())


@routes.get("/api/mcp/oauth-sessions")
async def handle_list_oauth_sessions(request: web.Request) -> web.Response:
    """List active OAuth sessions (connected MCP clients) for the authenticated user.

    Response:
        {"sessions": [{"id": "...", "client_name": "...", "created_at": <unix>, "expires_at": <unix>}]}
    """
    account = request.get("user")
    if not account:
        return web.json_response(
            create_error_response("Unauthorized").to_dict(), status=401
        )

    session_service: OAuthSessionService = request.app["oauth_session_service"]
    sessions = await session_service.list_sessions(str(account))
    return web.json_response({"sessions": sessions})


@routes.delete("/api/mcp/oauth-sessions/{session_id}")
async def handle_delete_oauth_session(request: web.Request) -> web.Response:
    """Revoke an OAuth session by its ID.

    Returns 404 if the session does not exist or belongs to another user.
    """
    account = request.get("user")
    if not account:
        return web.json_response(
            create_error_response("Unauthorized").to_dict(), status=401
        )

    session_id = request.match_info["session_id"]
    session_service: OAuthSessionService = request.app["oauth_session_service"]
    deleted = await session_service.revoke(str(account), session_id)
    if not deleted:
        return web.json_response(
            create_error_response("Session not found").to_dict(), status=404
        )
    return web.json_response(BaseResponse().to_dict())
