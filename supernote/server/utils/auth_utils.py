"""Authentication utilities for both aiohttp and Starlette."""

from typing import Any, Protocol


class RequestLike(Protocol):
    """Protocol for objects that look like a request with headers, etc."""

    @property
    def headers(self) -> Any: ...


def get_token_from_request(request: Any) -> str | None:
    """Extract token from aiohttp or Starlette request.

    Checks:
    1. x-access-token header
    2. token query parameter (for WebSocket connections that cannot set headers)
    """
    # Header check (case-insensitive usually handled by the framework objects)
    if token := request.headers.get("x-access-token"):
        return str(token)

    # Query parameter check (used by WebSocket/socket.io connections)
    if hasattr(request, "query") and (token := request.query.get("token")):
        return str(token)

    return None
