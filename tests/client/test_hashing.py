"""Tests for client hashing utilities."""

import pytest

from supernote.client.hashing import get_token_salt, hash_password, hash_with_salt


def test_hash_with_salt_returns_string() -> None:
    result = hash_with_salt("content", "salt")
    assert isinstance(result, str)
    assert len(result) == 64  # SHA256 hex digest


def test_hash_password_returns_string() -> None:
    result = hash_password("password", "rc")
    assert isinstance(result, str)


def test_get_token_salt_valid() -> None:
    # Token like "abc-def-ghi-2" → last char is '2', split gives ["abc","def","ghi","2"], parts[2]="ghi"
    token = "abc-def-ghi-2"
    assert get_token_salt(token) == "ghi"


def test_get_token_salt_index_zero() -> None:
    # Token like "first-second-third-0" → parts[0]="first"
    token = "first-second-third-0"
    assert get_token_salt(token) == "first"


def test_get_token_salt_empty_token() -> None:
    with pytest.raises(ValueError, match="empty"):
        get_token_salt("")


def test_get_token_salt_non_integer_last_char() -> None:
    with pytest.raises(ValueError, match="integer"):
        get_token_salt("abc-def-x")


def test_get_token_salt_index_out_of_bounds() -> None:
    # Token "abc-def-9" → index=9 but only 3 parts
    with pytest.raises(ValueError, match="out of bounds"):
        get_token_salt("abc-def-9")
