"""Tests for used_capacity accounting on UserService.

Verifies that:
- used_capacity increments by the file size after a successful upload finish.
- used_capacity decrements by the file size after a file delete.
- used_capacity floors at 0 and never goes negative when decremented below 0.
"""

import hashlib

from sqlalchemy import select

from supernote.models.user import UserRegisterDTO
from supernote.server.db.models.user import UserDO
from supernote.server.db.session import DatabaseSessionManager
from supernote.server.services.user import UserService

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_COUNTER = 0


def _unique_email() -> str:
    """Generate a unique email for test isolation."""
    global _COUNTER
    _COUNTER += 1
    return f"quota_unit_{_COUNTER}@example.com"


async def _create_user(user_service: UserService, email: str) -> UserDO:
    """Register a fresh user and return the DB row."""
    pw_md5 = hashlib.md5(email.encode()).hexdigest()
    return await user_service.create_user(
        UserRegisterDTO(email=email, password=pw_md5, user_name="Quota Unit User")
    )


async def _get_used_capacity(
    session_manager: DatabaseSessionManager, email: str
) -> int:
    """Read the current used_capacity from the DB for a user."""
    async with session_manager.session() as session:
        result = await session.execute(select(UserDO).where(UserDO.email == email))
        user = result.scalar_one_or_none()
        assert user is not None, f"User {email!r} not found"
        return user.used_capacity


# ---------------------------------------------------------------------------
# T018-1: used_capacity increments after upload finish
# ---------------------------------------------------------------------------


async def test_used_capacity_increments_on_upload_finish(
    user_service: UserService,
    session_manager: DatabaseSessionManager,
) -> None:
    """used_capacity should increase by the uploaded file's byte size."""
    email = _unique_email()
    await _create_user(user_service, email)

    file_size = 512

    # used_capacity should start at 0
    assert await _get_used_capacity(session_manager, email) == 0

    # Simulate a completed upload finish of `file_size` bytes
    await user_service.increment_used_capacity(email, file_size)

    assert await _get_used_capacity(session_manager, email) == file_size


async def test_used_capacity_increments_cumulatively(
    user_service: UserService,
    session_manager: DatabaseSessionManager,
) -> None:
    """Multiple upload-finishes accumulate used_capacity correctly."""
    email = _unique_email()
    await _create_user(user_service, email)

    await user_service.increment_used_capacity(email, 100)
    await user_service.increment_used_capacity(email, 200)
    await user_service.increment_used_capacity(email, 50)

    assert await _get_used_capacity(session_manager, email) == 350


# ---------------------------------------------------------------------------
# T018-2: used_capacity decrements after file delete
# ---------------------------------------------------------------------------


async def test_used_capacity_decrements_on_file_delete(
    user_service: UserService,
    session_manager: DatabaseSessionManager,
) -> None:
    """used_capacity should decrease by the deleted file's byte size."""
    email = _unique_email()
    await _create_user(user_service, email)

    # Seed some usage
    await user_service.increment_used_capacity(email, 1024)
    assert await _get_used_capacity(session_manager, email) == 1024

    # Delete a 300-byte file
    await user_service.decrement_used_capacity(email, 300)

    assert await _get_used_capacity(session_manager, email) == 724


# ---------------------------------------------------------------------------
# T018-3: used_capacity floors at 0 (never negative)
# ---------------------------------------------------------------------------


async def test_used_capacity_floors_at_zero(
    user_service: UserService,
    session_manager: DatabaseSessionManager,
) -> None:
    """Decrementing below 0 should result in used_capacity == 0, not negative."""
    email = _unique_email()
    await _create_user(user_service, email)

    # Start with 100 bytes used
    await user_service.increment_used_capacity(email, 100)

    # Try to decrement by more than is recorded
    await user_service.decrement_used_capacity(email, 500)

    capacity = await _get_used_capacity(session_manager, email)
    assert capacity == 0, f"used_capacity should floor at 0, got {capacity}"


async def test_used_capacity_zero_decrement_on_fresh_user(
    user_service: UserService,
    session_manager: DatabaseSessionManager,
) -> None:
    """Decrementing used_capacity from 0 should keep it at 0."""
    email = _unique_email()
    await _create_user(user_service, email)

    # Fresh user: used_capacity == 0
    assert await _get_used_capacity(session_manager, email) == 0

    await user_service.decrement_used_capacity(email, 100)

    assert await _get_used_capacity(session_manager, email) == 0
