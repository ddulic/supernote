import hashlib

import pytest

from supernote.models.user import UserRegisterDTO
from supernote.server.services.user import RANDOM_CODE_TTL, UserService
from supernote.server.utils.hashing import hash_with_salt


@pytest.fixture
async def registered_user(user_service: UserService) -> str:
    email = "hashtest@example.com"
    pw_md5 = hashlib.md5(b"password").hexdigest()
    await user_service.register(UserRegisterDTO(email=email, password=pw_md5))
    return email


async def test_verify_login_hash_exact_timestamp(
    registered_user: str, user_service: UserService
) -> None:
    code, ts = await user_service.generate_random_code(registered_user)
    pw_md5 = hashlib.md5(b"password").hexdigest()
    client_hash = hash_with_salt(pw_md5, code)
    assert await user_service.verify_login_hash(registered_user, client_hash, ts)


async def test_verify_login_hash_small_clock_skew(
    registered_user: str, user_service: UserService
) -> None:
    code, ts = await user_service.generate_random_code(registered_user)
    pw_md5 = hashlib.md5(b"password").hexdigest()
    client_hash = hash_with_salt(pw_md5, code)
    # Simulate device clock 30 seconds ahead of server
    skewed_ts = str(int(ts) + 30_000)
    assert await user_service.verify_login_hash(registered_user, client_hash, skewed_ts)


async def test_verify_login_hash_skew_exceeds_ttl(
    registered_user: str, user_service: UserService
) -> None:
    code, ts = await user_service.generate_random_code(registered_user)
    pw_md5 = hashlib.md5(b"password").hexdigest()
    client_hash = hash_with_salt(pw_md5, code)
    # Simulate device clock 1 hour ahead — exceeds the 5-minute TTL window
    skewed_ts = str(int(ts) + int(RANDOM_CODE_TTL.total_seconds() * 1000) + 1)
    assert not await user_service.verify_login_hash(
        registered_user, client_hash, skewed_ts
    )


async def test_verify_login_hash_non_numeric_timestamp(
    registered_user: str, user_service: UserService
) -> None:
    code, _ts = await user_service.generate_random_code(registered_user)
    pw_md5 = hashlib.md5(b"password").hexdigest()
    client_hash = hash_with_salt(pw_md5, code)
    assert not await user_service.verify_login_hash(
        registered_user, client_hash, "not-a-number"
    )


async def test_verify_login_hash_no_challenge(
    registered_user: str, user_service: UserService
) -> None:
    # Never call generate_random_code — no challenge stored
    pw_md5 = hashlib.md5(b"password").hexdigest()
    assert not await user_service.verify_login_hash(registered_user, pw_md5, "12345678")


async def test_verify_login_hash_wrong_hash(
    registered_user: str, user_service: UserService
) -> None:
    _code, ts = await user_service.generate_random_code(registered_user)
    assert not await user_service.verify_login_hash(registered_user, "deadbeef" * 8, ts)


async def test_verify_login_hash_unknown_user(user_service: UserService) -> None:
    assert not await user_service.verify_login_hash(
        "nobody@example.com", "hash", "12345678"
    )
