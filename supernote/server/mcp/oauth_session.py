"""OAuth session tracking for Supernote MCP.

Refresh tokens represent long-lived "sessions" (up to 30 days).  This service
maintains a per-user index so that sessions can be listed and revoked from the UI
without scanning the entire key-value store.
"""

import hashlib
import json
import time

from supernote.server.services.coordination import CoordinationService


def _session_id(token: str) -> str:
    """Derive a stable, opaque session ID from a refresh token string."""
    return hashlib.sha256(token.encode()).hexdigest()


class OAuthSessionService:
    """Tracks OAuth refresh-token sessions backed by the coordination service."""

    def __init__(self, coordination_service: CoordinationService) -> None:
        self._coordination = coordination_service

    async def register(
        self,
        user_id: str,
        token: str,
        client_id: str,
        client_name: str,
        expires_at: int,
    ) -> None:
        """Record a new OAuth session (called after authorization code exchange)."""
        session = {
            "id": _session_id(token),
            "token": token,
            "client_id": client_id,
            "client_name": client_name,
            "created_at": int(time.time()),
            "expires_at": expires_at,
        }
        index = await self._get_index(user_id)
        index.append(session)
        await self._coordination.set_value(
            f"mcp:oauth_sessions:{user_id}", json.dumps(index)
        )

    async def list_sessions(self, user_id: str) -> list[dict]:
        """Return metadata for all active (non-expired) sessions."""
        index = await self._get_index(user_id)
        now = int(time.time())
        result = []
        for entry in index:
            if entry.get("expires_at", 0) > now:
                result.append(
                    {
                        "id": entry["id"],
                        "client_id": entry["client_id"],
                        "client_name": entry.get("client_name") or entry["client_id"],
                        "created_at": entry["created_at"],
                        "expires_at": entry["expires_at"],
                    }
                )
        return result

    async def revoke(self, user_id: str, session_id: str) -> bool:
        """Revoke a session by its opaque ID.

        Returns False if the session is not found for this user.
        """
        index = await self._get_index(user_id)
        entry = next((s for s in index if s["id"] == session_id), None)
        if not entry:
            return False

        await self._coordination.delete_value(f"mcp:refresh_token:{entry['token']}")
        index = [s for s in index if s["id"] != session_id]
        await self._coordination.set_value(
            f"mcp:oauth_sessions:{user_id}", json.dumps(index)
        )
        return True

    async def revoke_by_token(self, user_id: str, token: str) -> None:
        """Revoke a session by its raw refresh token string."""
        await self.revoke(user_id, _session_id(token))

    async def _get_index(self, user_id: str) -> list[dict]:
        data = await self._coordination.get_value(f"mcp:oauth_sessions:{user_id}")
        return json.loads(data) if data else []
