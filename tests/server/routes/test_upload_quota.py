"""Tests for upload quota enforcement on upload/apply endpoints.

Verifies that POST /api/file/3/files/upload/apply and POST /api/file/upload/apply
return HTTP 507 with error code E0507 when the requested upload size would exceed
the user's storage quota.
"""

import hashlib

import jwt
import pytest
from aiohttp.test_utils import TestClient
from sqlalchemy import update

from supernote.models.file_device import FileUploadApplyLocalDTO
from supernote.server.config import ServerConfig
from supernote.server.db.models.user import UserDO
from supernote.server.db.session import DatabaseSessionManager
from supernote.server.services.coordination import SqliteCoordinationService
from supernote.server.services.user import JWT_ALGORITHM, UserService

# Quota test constants
SMALL_QUOTA = "1024"  # 1 KiB total
USED_CAPACITY = 900  # 900 bytes already used
OVERSIZE_REQUEST = 200  # 900 + 200 = 1100 > 1024  → quota exceeded
UNDERSIZE_REQUEST = 100  # 900 + 100 = 1000 ≤ 1024  → ok


@pytest.fixture
async def quota_user_email() -> str:
    """Email address for the quota-constrained test user."""
    return "quota_test@example.com"


@pytest.fixture
async def quota_user(
    user_service: UserService,
    session_manager: DatabaseSessionManager,
    quota_user_email: str,
) -> None:
    """Create a user with a very small quota and pre-set used_capacity."""
    pw_md5 = hashlib.md5(b"quotapassword").hexdigest()

    from supernote.models.user import UserRegisterDTO

    if await user_service.check_user_exists(quota_user_email):
        await user_service.unregister(quota_user_email)

    result = await user_service.create_user(
        UserRegisterDTO(
            email=quota_user_email,
            password=pw_md5,
            user_name="Quota Test User",
        )
    )
    assert result.id

    # Set the small total_capacity and the pre-used capacity directly in the DB
    async with session_manager.session() as session:
        await session.execute(
            update(UserDO)
            .where(UserDO.email == quota_user_email)
            .values(total_capacity=SMALL_QUOTA, used_capacity=USED_CAPACITY)
        )
        await session.commit()


@pytest.fixture
async def quota_auth_headers(
    server_config: ServerConfig,
    coordination_service: SqliteCoordinationService,
    quota_user: None,
    quota_user_email: str,
) -> dict[str, str]:
    """Auth headers for the quota-constrained user."""
    secret = server_config.auth.secret_key
    token = jwt.encode({"sub": quota_user_email}, secret, algorithm=JWT_ALGORITHM)

    session_val = f"{quota_user_email}|"
    await coordination_service.set_value(f"session:{token}", session_val, ttl=3600)

    return {
        "x-access-token": token,
        "Authorization": f"Bearer {token}",
    }


# ---------------------------------------------------------------------------
# Device API: POST /api/file/3/files/upload/apply
# ---------------------------------------------------------------------------


async def test_device_upload_apply_quota_exceeded_returns_507(
    client: TestClient,
    quota_auth_headers: dict[str, str],
) -> None:
    """POST /api/file/3/files/upload/apply should return 507 when over quota."""
    payload = FileUploadApplyLocalDTO(
        equipment_no="TEST",
        file_name="bigfile.note",
        path="/",
        size=str(OVERSIZE_REQUEST),
    ).to_dict()

    resp = await client.post(
        "/api/file/3/files/upload/apply",
        json=payload,
        headers=quota_auth_headers,
    )
    assert resp.status == 507

    data = await resp.json()
    assert data.get("errorCode") == "E0507"
    assert data.get("success") is False


async def test_device_upload_apply_quota_ok_returns_200(
    client: TestClient,
    quota_auth_headers: dict[str, str],
) -> None:
    """POST /api/file/3/files/upload/apply should succeed when within quota."""
    payload = FileUploadApplyLocalDTO(
        equipment_no="TEST",
        file_name="smallfile.note",
        path="/",
        size=str(UNDERSIZE_REQUEST),
    ).to_dict()

    resp = await client.post(
        "/api/file/3/files/upload/apply",
        json=payload,
        headers=quota_auth_headers,
    )
    assert resp.status == 200

    data = await resp.json()
    assert data.get("success") is not False  # success is omitted or True on happy path


# ---------------------------------------------------------------------------
# Web API: POST /api/file/upload/apply
# ---------------------------------------------------------------------------


async def test_web_upload_apply_quota_exceeded_returns_507(
    client: TestClient,
    quota_auth_headers: dict[str, str],
) -> None:
    """POST /api/file/upload/apply should return 507 when over quota."""
    payload = {
        "fileName": "bigfile.note",
        "size": OVERSIZE_REQUEST,
        "directoryId": 0,
        "md5": "d41d8cd98f00b204e9800998ecf8427e",
    }

    resp = await client.post(
        "/api/file/upload/apply",
        json=payload,
        headers=quota_auth_headers,
    )
    assert resp.status == 507

    data = await resp.json()
    assert data.get("errorCode") == "E0507"
    assert data.get("success") is False


async def test_web_upload_apply_quota_ok_returns_200(
    client: TestClient,
    quota_auth_headers: dict[str, str],
) -> None:
    """POST /api/file/upload/apply should succeed when within quota."""
    payload = {
        "fileName": "smallfile.note",
        "size": UNDERSIZE_REQUEST,
        "directoryId": 0,
        "md5": "d41d8cd98f00b204e9800998ecf8427e",
    }

    resp = await client.post(
        "/api/file/upload/apply",
        json=payload,
        headers=quota_auth_headers,
    )
    assert resp.status == 200
