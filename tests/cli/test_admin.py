"""Tests for supernote/cli/admin.py."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from supernote.cli.admin import (
    add_user_async,
    list_users_async,
    reset_password_async,
)


async def test_list_users_async_calls_get_json() -> None:
    """list_users_async calls client.get_json and handles exceptions gracefully."""
    mock_client = AsyncMock()
    mock_client.get_json.side_effect = Exception("blocked")
    mock_resp = AsyncMock()
    mock_resp.json = AsyncMock(return_value=[])
    mock_client.get = AsyncMock(return_value=mock_resp)

    mock_session = MagicMock()
    mock_session.client = mock_client

    @asynccontextmanager
    async def mock_create_session(
        *args: object, **kwargs: object
    ) -> AsyncGenerator[MagicMock, None]:
        yield mock_session

    with patch("supernote.cli.admin.create_session", mock_create_session):
        await list_users_async()

    mock_client.get_json.assert_called_once()


async def test_list_users_async_successful_listing() -> None:
    """list_users_async successfully lists users when API call succeeds."""
    # Mock user data
    mock_users = [
        {"email": "user1@example.com", "userName": "User One", "totalCapacity": "100"},
        {"email": "user2@example.com", "userName": "User Two", "totalCapacity": "200"},
    ]

    mock_client = AsyncMock()
    mock_client.get_json.side_effect = Exception("blocked")  # First call fails
    mock_resp = AsyncMock()
    mock_resp.json = AsyncMock(return_value=mock_users)
    mock_client.get = AsyncMock(return_value=mock_resp)

    mock_session = MagicMock()
    mock_session.client = mock_client

    @asynccontextmanager
    async def mock_create_session(
        *args: object, **kwargs: object
    ) -> AsyncGenerator[MagicMock, None]:
        yield mock_session

    with patch("supernote.cli.admin.create_session", mock_create_session):
        # Capture print output
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            await list_users_async()

        output = f.getvalue()

        # Verify the output contains user data
        assert "Total Users: 2" in output
        assert "user1@example.com" in output
        assert "user2@example.com" in output
        assert "User One" in output
        assert "User Two" in output


async def test_add_user_async_success() -> None:
    """Test add_user_async successful user creation."""
    # Mock the AdminClient methods directly
    with patch("supernote.cli.admin.AdminClient") as mock_admin_client_class:
        mock_admin_instance = AsyncMock()
        mock_admin_instance.register = AsyncMock()  # Public registration succeeds
        mock_admin_client_class.return_value = mock_admin_instance

        mock_session = MagicMock()
        mock_session.client = MagicMock()

        @asynccontextmanager
        async def mock_create_session(
            *args: object, **kwargs: object
        ) -> AsyncGenerator[MagicMock, None]:
            yield mock_session

        with patch("supernote.cli.admin.create_session", mock_create_session):
            # Capture print output
            import io
            from contextlib import redirect_stdout

            f = io.StringIO()
            with redirect_stdout(f):
                await add_user_async(
                    "http://test.com", "test@example.com", "password123", "Test User"
                )

            output = f.getvalue()
            assert "Success! User created (Public Registration)" in output


async def test_add_user_async_admin_fallback() -> None:
    """Test add_user_async falls back to admin creation when public registration fails."""
    # Mock the AdminClient methods directly
    from supernote.client.exceptions import ApiException

    with patch("supernote.cli.admin.AdminClient") as mock_admin_client_class:
        mock_admin_instance = AsyncMock()
        mock_admin_instance.register = AsyncMock(
            side_effect=ApiException("Public registration disabled")
        )
        mock_admin_instance.admin_create_user = AsyncMock()  # Admin creation succeeds
        mock_admin_client_class.return_value = mock_admin_instance

        mock_session = MagicMock()
        mock_session.client = MagicMock()

        @asynccontextmanager
        async def mock_create_session(
            *args: object, **kwargs: object
        ) -> AsyncGenerator[MagicMock, None]:
            yield mock_session

        with patch("supernote.cli.admin.create_session", mock_create_session):
            # Capture print output
            import io
            from contextlib import redirect_stdout

            f = io.StringIO()
            with redirect_stdout(f):
                await add_user_async(
                    "http://test.com", "test@example.com", "password123", "Test User"
                )

            output = f.getvalue()
            assert "Public registration failed or disabled" in output
            assert "Success! User created (Admin API)" in output


async def test_reset_password_async_success() -> None:
    """Test reset_password_async successful password reset."""
    # Mock the AdminClient methods directly
    with patch("supernote.cli.admin.AdminClient") as mock_admin_client_class:
        mock_admin_instance = AsyncMock()
        mock_admin_instance.admin_reset_password = AsyncMock()
        mock_admin_client_class.return_value = mock_admin_instance

        mock_session = MagicMock()
        mock_session.client = MagicMock()

        @asynccontextmanager
        async def mock_create_session(
            *args: object, **kwargs: object
        ) -> AsyncGenerator[MagicMock, None]:
            yield mock_session

        with patch("supernote.cli.admin.create_session", mock_create_session):
            # Capture print output
            import io
            from contextlib import redirect_stdout

            f = io.StringIO()
            with redirect_stdout(f):
                await reset_password_async(
                    "http://test.com", "test@example.com", "newpassword123"
                )

            output = f.getvalue()
            assert "Success! Password Reset" in output
