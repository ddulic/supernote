"""API key management for Supernote MCP."""

import hashlib
import json
import secrets
import time

from supernote.server.services.coordination import CoordinationService

_API_KEY_PREFIX = "snmcp_"


def _generate_api_key() -> str:
    return _API_KEY_PREFIX + secrets.token_urlsafe(32)


def _hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


class ApiKeyService:
    """Manages MCP API keys backed by the coordination service.

    Keys are stored as SHA-256 hashes so that a compromised database
    does not expose usable credentials. The plaintext key is only
    returned at creation time.
    """

    def __init__(self, coordination_service: CoordinationService) -> None:
        self._coordination = coordination_service

    async def create_key(self, user_id: str, name: str) -> str:
        """Create a new API key.

        Returns the plaintext key. This is the only time it is available.
        """
        key = _generate_api_key()
        key_hash = _hash_api_key(key)
        now = int(time.time())

        await self._coordination.set_value(
            f"mcp:api_key:{key_hash}",
            json.dumps(
                {
                    "user_id": user_id,
                    "name": name,
                    "created_at": now,
                    "last_used_at": None,
                }
            ),
        )

        index = await self._get_index(user_id)
        index.append(
            {"id": key_hash, "name": name, "created_at": now, "last_used_at": None}
        )
        await self._coordination.set_value(f"mcp:api_keys:{user_id}", json.dumps(index))

        return key

    async def list_keys(self, user_id: str) -> list[dict]:
        """Return metadata for all API keys belonging to a user (no plaintext keys).

        last_used_at is read from the live record so it reflects actual usage.
        """
        index = await self._get_index(user_id)
        result = []
        for entry in index:
            key_id = entry["id"]
            data = await self._coordination.get_value(f"mcp:api_key:{key_id}")
            if data:
                record = json.loads(data)
                result.append(
                    {
                        "id": key_id,
                        "name": record.get("name", entry["name"]),
                        "created_at": record.get("created_at", entry["created_at"]),
                        "last_used_at": record.get("last_used_at"),
                    }
                )
        return result

    async def delete_key(self, user_id: str, key_id: str) -> bool:
        """Revoke a key by its hash ID.

        Returns False if the key does not exist or does not belong to the user.
        """
        data = await self._coordination.get_value(f"mcp:api_key:{key_id}")
        if not data:
            return False
        record = json.loads(data)
        if record.get("user_id") != user_id:
            return False

        await self._coordination.delete_value(f"mcp:api_key:{key_id}")
        index = [k for k in await self._get_index(user_id) if k["id"] != key_id]
        await self._coordination.set_value(f"mcp:api_keys:{user_id}", json.dumps(index))
        return True

    async def verify_key(self, key: str) -> str | None:
        """Verify an API key. Returns the user_id (email) if valid, else None.

        Updates last_used_at on every successful verification.
        """
        if not key.startswith(_API_KEY_PREFIX):
            return None
        key_hash = _hash_api_key(key)
        storage_key = f"mcp:api_key:{key_hash}"
        data = await self._coordination.get_value(storage_key)
        if not data:
            return None
        record = json.loads(data)
        record["last_used_at"] = int(time.time())
        await self._coordination.set_value(storage_key, json.dumps(record))
        return str(record["user_id"]) if "user_id" in record else None

    async def _get_index(self, user_id: str) -> list[dict]:
        data = await self._coordination.get_value(f"mcp:api_keys:{user_id}")
        return json.loads(data) if data else []
