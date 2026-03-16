"""Tests for FileCacheAuth authentication."""

import os
import pickle
from pathlib import Path

import pytest

from supernote.client.auth import ConstantAuth, FileCacheAuth

# ---------------------------------------------------------------------------
# ConstantAuth
# ---------------------------------------------------------------------------


async def test_constant_auth_returns_token() -> None:
    auth = ConstantAuth("my-token")
    assert await auth.async_get_access_token() == "my-token"
    assert auth.token == "my-token"


# ---------------------------------------------------------------------------
# FileCacheAuth
# ---------------------------------------------------------------------------


def test_file_cache_auth_nonexistent_file(tmp_path: Path) -> None:
    """FileCacheAuth with nonexistent cache file initializes without error."""
    cache = str(tmp_path / "nonexistent.pkl")
    auth = FileCacheAuth(cache)
    assert auth._access_token is None
    assert auth.get_host() is None


async def test_file_cache_auth_no_token_raises() -> None:
    """async_get_access_token raises ValueError when no token is cached."""
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        auth = FileCacheAuth(os.path.join(d, "no_such_file.pkl"))
        with pytest.raises(ValueError, match="No access token"):
            await auth.async_get_access_token()


def test_file_cache_auth_valid_cache(tmp_path: Path) -> None:
    """FileCacheAuth loads token and host from a valid pickle file."""
    cache = str(tmp_path / "cache.pkl")
    data = {"access_token": "tok123", "host": "http://example.com"}
    with open(cache, "wb") as f:
        pickle.dump(data, f)

    auth = FileCacheAuth(cache)
    assert auth._access_token == "tok123"
    assert auth.get_host() == "http://example.com"


async def test_file_cache_auth_returns_cached_token(tmp_path: Path) -> None:
    """async_get_access_token returns the cached token."""
    cache = str(tmp_path / "cache.pkl")
    data = {"access_token": "tok456", "host": "http://localhost"}
    with open(cache, "wb") as f:
        pickle.dump(data, f)

    auth = FileCacheAuth(cache)
    assert await auth.async_get_access_token() == "tok456"


def test_file_cache_auth_invalid_pickle(tmp_path: Path) -> None:
    """FileCacheAuth with corrupt pickle initializes gracefully (logs warning)."""
    cache = str(tmp_path / "bad.pkl")
    cache_path = Path(cache)
    cache_path.write_bytes(b"not a pickle")

    auth = FileCacheAuth(cache)
    assert auth._access_token is None


def test_file_cache_auth_not_a_dict(tmp_path: Path) -> None:
    """FileCacheAuth where pickle contains non-dict initializes gracefully."""
    cache = str(tmp_path / "bad_type.pkl")
    with open(cache, "wb") as f:
        pickle.dump("just a string", f)

    auth = FileCacheAuth(cache)
    assert auth._access_token is None


def test_file_cache_auth_missing_host(tmp_path: Path) -> None:
    """FileCacheAuth where cache is missing 'host' key initializes gracefully (no host)."""
    cache = str(tmp_path / "no_host.pkl")
    with open(cache, "wb") as f:
        pickle.dump({"access_token": "tok"}, f)

    auth = FileCacheAuth(cache)
    # Token gets set before host validation fails, so host is None
    assert auth.get_host() is None


def test_file_cache_auth_save_credentials(tmp_path: Path) -> None:
    """save_credentials writes token and host to cache file."""
    cache = str(tmp_path / "subdir" / "cache.pkl")
    auth = FileCacheAuth(cache)
    auth.save_credentials("newtoken", "http://saved.example.com")

    assert auth._access_token == "newtoken"
    assert auth.get_host() == "http://saved.example.com"

    # Verify the pickle file was written
    assert Path(cache).exists()
    with open(cache, "rb") as f:
        data = pickle.load(f)
    assert data["access_token"] == "newtoken"
    assert data["host"] == "http://saved.example.com"
