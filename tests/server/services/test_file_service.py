"""Tests for FileService.convert_note_to_png — caching, cleanup, and fail-open behaviour.

Per constitution §VI: these tests are written BEFORE implementation and must FAIL
until the caching logic is added to convert_note_to_png.
"""

from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from supernote.server.db.models.file import UserFileDO
from supernote.server.db.session import DatabaseSessionManager
from supernote.server.services.blob import LocalBlobStorage
from supernote.server.services.file import FileService
from supernote.server.services.user import UserService
from supernote.server.utils.paths import get_conversion_png_path

USER_EMAIL = "test@example.com"
USER_ID = 1
FILE_ID = 42
CURRENT_MD5 = "abc123def456"
OLD_MD5 = "111222333444"
NOTE_STORAGE_KEY = "note-key-xyz"
TOTAL_PAGES = 2


@pytest.fixture
def file_service(
    storage_root: Path,
    blob_storage: LocalBlobStorage,
    user_service: UserService,
    session_manager: DatabaseSessionManager,
) -> FileService:
    return FileService(storage_root, blob_storage, user_service, session_manager)


async def _note_bytes_gen(
    *args: object, **kwargs: object
) -> AsyncGenerator[bytes, None]:
    """Async generator yielding fake note bytes."""
    yield b"FAKE_NOTE_BYTES"


def _make_mock_note(total_pages: int = TOTAL_PAGES) -> MagicMock:
    note = MagicMock()
    note.get_total_pages.return_value = total_pages
    return note


async def _seed_file(
    session_manager: DatabaseSessionManager,
    md5: str = CURRENT_MD5,
    last_conversion_md5: str | None = None,
) -> None:
    async with session_manager.session() as session:
        session.add(
            UserFileDO(
                id=FILE_ID,
                user_id=USER_ID,
                file_name="test.note",
                directory_id=0,
                md5=md5,
                storage_key=NOTE_STORAGE_KEY,
                last_conversion_md5=last_conversion_md5,
            )
        )
        await session.commit()


# ---------------------------------------------------------------------------
# T003a: Skip conversion when all pages already exist in cache
# ---------------------------------------------------------------------------


async def test_convert_skips_put_when_all_pages_cached(
    file_service: FileService,
    session_manager: DatabaseSessionManager,
    create_test_user: None,
) -> None:
    """When exists() returns True for every page, put() must never be called."""
    await _seed_file(session_manager, md5=CURRENT_MD5, last_conversion_md5=CURRENT_MD5)

    mock_put = AsyncMock()
    mock_exists = AsyncMock(return_value=True)

    with (
        patch.object(file_service.blob_storage, "get", new=_note_bytes_gen),
        patch.object(file_service.blob_storage, "exists", mock_exists),
        patch.object(file_service.blob_storage, "put", mock_put),
        patch(
            "supernote.server.services.file.load_notebook",
            return_value=_make_mock_note(),
        ),
        patch("supernote.server.services.file.ImageConverter"),
    ):
        results = await file_service.convert_note_to_png(USER_EMAIL, FILE_ID)

    mock_put.assert_not_called()
    assert len(results) == TOTAL_PAGES


# ---------------------------------------------------------------------------
# T003b: Convert and store when pages are not yet cached
# ---------------------------------------------------------------------------


async def test_convert_calls_put_when_page_not_cached(
    file_service: FileService,
    session_manager: DatabaseSessionManager,
    create_test_user: None,
) -> None:
    """When exists() returns False, put() must be called for each missing page."""
    await _seed_file(session_manager, md5=CURRENT_MD5, last_conversion_md5=None)

    mock_put = AsyncMock()
    mock_exists = AsyncMock(return_value=False)

    with (
        patch.object(file_service.blob_storage, "get", new=_note_bytes_gen),
        patch.object(file_service.blob_storage, "exists", mock_exists),
        patch.object(file_service.blob_storage, "put", mock_put),
        patch(
            "supernote.server.services.file.load_notebook",
            return_value=_make_mock_note(),
        ),
        patch("supernote.server.services.file.ImageConverter"),
    ):
        results = await file_service.convert_note_to_png(USER_EMAIL, FILE_ID)

    assert mock_put.call_count == TOTAL_PAGES
    assert len(results) == TOTAL_PAGES


# ---------------------------------------------------------------------------
# T003c: Fail-open — storage error on exists() treated as cache miss
# ---------------------------------------------------------------------------


async def test_convert_failopen_on_exists_error(
    file_service: FileService,
    session_manager: DatabaseSessionManager,
    create_test_user: None,
) -> None:
    """When exists() raises OSError, the page must still be converted (fail-open)."""
    await _seed_file(session_manager, md5=CURRENT_MD5, last_conversion_md5=CURRENT_MD5)

    mock_put = AsyncMock()
    mock_exists = AsyncMock(side_effect=OSError("storage unavailable"))

    with (
        patch.object(file_service.blob_storage, "get", new=_note_bytes_gen),
        patch.object(file_service.blob_storage, "exists", mock_exists),
        patch.object(file_service.blob_storage, "put", mock_put),
        patch(
            "supernote.server.services.file.load_notebook",
            return_value=_make_mock_note(),
        ),
        patch("supernote.server.services.file.ImageConverter"),
    ):
        results = await file_service.convert_note_to_png(USER_EMAIL, FILE_ID)

    # Fail-open: put must still be called for each page despite exists() failing
    assert mock_put.call_count == TOTAL_PAGES
    assert len(results) == TOTAL_PAGES


# ---------------------------------------------------------------------------
# T003d: Old-image cleanup when last_conversion_md5 differs from current md5
# ---------------------------------------------------------------------------


async def test_convert_deletes_old_images_on_md5_change(
    file_service: FileService,
    session_manager: DatabaseSessionManager,
    create_test_user: None,
) -> None:
    """When MD5 changed, delete() must be called for each old-hash page image."""
    await _seed_file(session_manager, md5=CURRENT_MD5, last_conversion_md5=OLD_MD5)

    mock_delete = AsyncMock()
    mock_put = AsyncMock()
    mock_exists = AsyncMock(return_value=False)

    with (
        patch.object(file_service.blob_storage, "get", new=_note_bytes_gen),
        patch.object(file_service.blob_storage, "exists", mock_exists),
        patch.object(file_service.blob_storage, "put", mock_put),
        patch.object(file_service.blob_storage, "delete", mock_delete),
        patch(
            "supernote.server.services.file.load_notebook",
            return_value=_make_mock_note(),
        ),
        patch("supernote.server.services.file.ImageConverter"),
    ):
        await file_service.convert_note_to_png(USER_EMAIL, FILE_ID)

    expected_old_keys = [
        get_conversion_png_path(
            user_id=USER_ID, file_id=FILE_ID, page_index=i, file_md5=OLD_MD5
        )
        for i in range(TOTAL_PAGES)
    ]
    actual_delete_keys = [call.args[1] for call in mock_delete.call_args_list]
    assert sorted(actual_delete_keys) == sorted(expected_old_keys)


async def test_convert_does_not_delete_when_md5_unchanged(
    file_service: FileService,
    session_manager: DatabaseSessionManager,
    create_test_user: None,
) -> None:
    """When MD5 unchanged, delete() must NOT be called."""
    await _seed_file(session_manager, md5=CURRENT_MD5, last_conversion_md5=CURRENT_MD5)

    mock_delete = AsyncMock()
    mock_exists = AsyncMock(return_value=True)

    with (
        patch.object(file_service.blob_storage, "get", new=_note_bytes_gen),
        patch.object(file_service.blob_storage, "exists", mock_exists),
        patch.object(file_service.blob_storage, "put", AsyncMock()),
        patch.object(file_service.blob_storage, "delete", mock_delete),
        patch(
            "supernote.server.services.file.load_notebook",
            return_value=_make_mock_note(),
        ),
        patch("supernote.server.services.file.ImageConverter"),
    ):
        await file_service.convert_note_to_png(USER_EMAIL, FILE_ID)

    mock_delete.assert_not_called()


# ---------------------------------------------------------------------------
# T003e: last_conversion_md5 updated after successful conversion
# ---------------------------------------------------------------------------


async def test_convert_updates_last_conversion_md5(
    file_service: FileService,
    session_manager: DatabaseSessionManager,
    create_test_user: None,
) -> None:
    """After converting, last_conversion_md5 must equal the file's current md5."""
    await _seed_file(session_manager, md5=CURRENT_MD5, last_conversion_md5=None)

    with (
        patch.object(file_service.blob_storage, "get", new=_note_bytes_gen),
        patch.object(
            file_service.blob_storage, "exists", AsyncMock(return_value=False)
        ),
        patch.object(file_service.blob_storage, "put", AsyncMock()),
        patch(
            "supernote.server.services.file.load_notebook",
            return_value=_make_mock_note(),
        ),
        patch("supernote.server.services.file.ImageConverter"),
    ):
        await file_service.convert_note_to_png(USER_EMAIL, FILE_ID)

    async with session_manager.session() as session:
        from sqlalchemy import select

        node = (
            await session.execute(select(UserFileDO).where(UserFileDO.id == FILE_ID))
        ).scalar_one()
    assert node.last_conversion_md5 == CURRENT_MD5
