"""Tests for TempFileCleanupService."""

import asyncio
import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from supernote.server.services.cleanup import TempFileCleanupService

# The service should:
# - Have start() / stop() lifecycle methods
# - Run periodic cleanup of files matching *.part.* pattern
# - Delete files older than ttl_seconds
# - NOT delete files younger than ttl_seconds


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for chunk files."""
    chunk_dir = tmp_path / "temp_chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    return chunk_dir


@pytest.fixture
def cleanup_service(temp_dir: Path) -> TempFileCleanupService:
    """Create a TempFileCleanupService for testing."""
    return TempFileCleanupService(
        scan_dir=temp_dir, ttl_seconds=60, interval_seconds=3600
    )


async def test_cleanup_removes_old_chunk_files(
    cleanup_service: TempFileCleanupService,
    temp_dir: Path,
) -> None:
    """Files matching *.part.* older than TTL should be deleted."""
    # Create an old chunk file
    old_chunk = temp_dir / "abc123.part.1"
    old_chunk.write_bytes(b"old chunk data")

    # Backdate the file's modification time to be older than TTL (60s)
    old_mtime = time.time() - 120  # 2 minutes ago
    import os

    os.utime(old_chunk, (old_mtime, old_mtime))

    await cleanup_service.run_once()

    assert not old_chunk.exists(), "Old chunk file should have been deleted"


async def test_cleanup_does_not_remove_young_chunk_files(
    cleanup_service: TempFileCleanupService,
    temp_dir: Path,
) -> None:
    """Files matching *.part.* younger than TTL should NOT be deleted."""
    # Create a fresh chunk file (just now)
    young_chunk = temp_dir / "def456.part.2"
    young_chunk.write_bytes(b"fresh chunk data")

    # File was just created — mtime is now, well within the 60s TTL
    await cleanup_service.run_once()

    assert young_chunk.exists(), "Young chunk file should NOT have been deleted"


async def test_cleanup_does_not_remove_non_chunk_files(
    cleanup_service: TempFileCleanupService,
    temp_dir: Path,
) -> None:
    """Files that do NOT match *.part.* should not be deleted even if old."""
    # Create an old non-chunk file
    old_regular = temp_dir / "somefile.txt"
    old_regular.write_bytes(b"regular file")

    import os

    old_mtime = time.time() - 120
    os.utime(old_regular, (old_mtime, old_mtime))

    await cleanup_service.run_once()

    assert old_regular.exists(), "Non-chunk files should not be deleted"


async def test_cleanup_removes_only_expired_chunks_among_mixed(
    cleanup_service: TempFileCleanupService,
    temp_dir: Path,
) -> None:
    """Only old chunk files are removed; fresh chunks and non-chunks survive."""
    import os

    old_chunk = temp_dir / "old.part.1"
    old_chunk.write_bytes(b"old")
    old_mtime = time.time() - 120
    os.utime(old_chunk, (old_mtime, old_mtime))

    young_chunk = temp_dir / "young.part.2"
    young_chunk.write_bytes(b"young")

    non_chunk = temp_dir / "data.bin"
    non_chunk.write_bytes(b"binary")
    os.utime(non_chunk, (old_mtime, old_mtime))

    await cleanup_service.run_once()

    assert not old_chunk.exists(), "Old chunk should be deleted"
    assert young_chunk.exists(), "Young chunk should survive"
    assert non_chunk.exists(), "Non-chunk file should survive"


async def test_service_start_stop_lifecycle(
    temp_dir: Path,
) -> None:
    """Service should start and stop cleanly without errors."""
    service = TempFileCleanupService(
        scan_dir=temp_dir,
        ttl_seconds=60,
        # Very long interval so the background loop doesn't run during the test
        interval_seconds=9999,
    )

    await service.start()
    # Give the event loop a tick to ensure the background task has started
    await asyncio.sleep(0)

    await service.stop()
    # After stop(), the service should be in a stopped state with no pending tasks
    assert not service.is_running(), "Service should not be running after stop()"


async def test_service_stop_is_idempotent(
    temp_dir: Path,
) -> None:
    """Calling stop() multiple times should not raise an error."""
    service = TempFileCleanupService(
        scan_dir=temp_dir,
        ttl_seconds=60,
        interval_seconds=9999,
    )

    await service.start()
    await asyncio.sleep(0)
    await service.stop()
    # Second stop should be a no-op
    await service.stop()


async def test_run_once_handles_missing_scan_dir(tmp_path: Path) -> None:
    """run_once should not raise if the scan directory does not exist."""
    missing = tmp_path / "does_not_exist"
    service = TempFileCleanupService(scan_dir=missing, ttl_seconds=60)
    # Should return without error even though the directory is absent
    await service.run_once()
    assert not missing.exists()


async def test_run_once_handles_file_disappearing_between_stat_and_unlink(
    temp_dir: Path,
) -> None:
    """FileNotFoundError from stat() during processing should be silently ignored."""
    import stat as stat_module

    chunk = temp_dir / "race.part.1"
    chunk.write_bytes(b"data")
    old_mtime = time.time() - 120
    os.utime(chunk, (old_mtime, old_mtime))

    original_stat = Path.stat

    def stat_then_delete(self: Path, *args: object, **kwargs: object) -> object:
        result = original_stat(self)
        # Use st_mode to identify regular files without calling is_file() (which
        # would recurse). Only delete .part.* files to avoid touching the scan dir.
        if stat_module.S_ISREG(result.st_mode) and ".part." in self.name:
            self.unlink(missing_ok=True)
        return result

    service = TempFileCleanupService(scan_dir=temp_dir, ttl_seconds=60)
    with patch.object(Path, "stat", stat_then_delete):
        await service.run_once()  # Should not raise


async def test_run_once_handles_unexpected_exception_during_delete(
    temp_dir: Path,
) -> None:
    """Unexpected exceptions from unlink() should be logged, not propagated."""
    chunk = temp_dir / "broken.part.2"
    chunk.write_bytes(b"data")
    old_mtime = time.time() - 120
    os.utime(chunk, (old_mtime, old_mtime))

    service = TempFileCleanupService(scan_dir=temp_dir, ttl_seconds=60)

    # Patch unlink to raise PermissionError — caught by the broad except clause
    with patch.object(Path, "unlink", side_effect=PermissionError("denied")):
        await service.run_once()  # Should not raise

    # File should still exist since unlink() raised before deletion
    assert chunk.exists()


async def test_cleanup_loop_calls_run_once(temp_dir: Path) -> None:
    """The cleanup loop should call run_once() after each interval elapses."""
    service = TempFileCleanupService(
        scan_dir=temp_dir,
        ttl_seconds=60,
        interval_seconds=0,  # 0-second sleep so the loop body executes immediately
    )

    call_count = 0

    async def mock_run_once() -> None:
        nonlocal call_count
        call_count += 1
        service._shutdown_event.set()  # Stop the loop after first run

    service.run_once = mock_run_once  # type: ignore[method-assign]

    await service.start()
    await asyncio.sleep(0.05)
    await service.stop()

    assert call_count >= 1, "run_once() should have been called by the cleanup loop"


async def test_cleanup_loop_handles_run_once_exception(temp_dir: Path) -> None:
    """An exception raised by run_once() should be logged, not crash the loop."""
    service = TempFileCleanupService(
        scan_dir=temp_dir,
        ttl_seconds=60,
        interval_seconds=0,
    )

    call_count = 0

    async def failing_run_once() -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("transient error")
        service._shutdown_event.set()

    service.run_once = failing_run_once  # type: ignore[method-assign]

    await service.start()
    await asyncio.sleep(0.05)
    await service.stop()

    assert call_count >= 2, "Loop should have continued after run_once raised"


async def test_cleanup_loop_exits_via_shutdown_check_after_sleep(
    temp_dir: Path,
) -> None:
    """When shutdown is set during sleep, the post-sleep check breaks before run_once."""
    import supernote.server.services.cleanup as cleanup_module

    service = TempFileCleanupService(
        scan_dir=temp_dir, ttl_seconds=60, interval_seconds=0
    )

    run_once_called = False

    async def mock_run_once() -> None:
        nonlocal run_once_called
        run_once_called = True

    service.run_once = mock_run_once  # type: ignore[method-assign]

    async def shutdown_during_sleep(_: float) -> None:
        service._shutdown_event.set()

    with patch.object(cleanup_module.asyncio, "sleep", shutdown_during_sleep):
        await service._cleanup_loop()

    assert not run_once_called, (
        "run_once should not be called when shutdown set after sleep"
    )


async def test_cleanup_loop_exits_on_cancelled_error_from_run_once(
    temp_dir: Path,
) -> None:
    """CancelledError raised by run_once() exits the loop cleanly."""
    service = TempFileCleanupService(
        scan_dir=temp_dir, ttl_seconds=60, interval_seconds=0
    )

    async def cancelling_run_once() -> None:
        raise asyncio.CancelledError()

    service.run_once = cancelling_run_once  # type: ignore[method-assign]

    # _cleanup_loop should handle CancelledError and return without propagating
    await service._cleanup_loop()


async def test_run_once_ignores_stat_file_not_found(temp_dir: Path) -> None:
    """FileNotFoundError from path.stat() during scan should be silently ignored."""
    chunk = temp_dir / "vanishing.part.1"
    chunk.write_bytes(b"data")

    service = TempFileCleanupService(scan_dir=temp_dir, ttl_seconds=60)

    original_stat = Path.stat

    def stat_raising(self: Path, *args: object, **kwargs: object) -> object:
        # is_file() passes follow_symlinks as a keyword arg; the direct stat() call
        # at line 88 of cleanup.py passes no kwargs — raise only for that case.
        if ".part." in self.name and "follow_symlinks" not in kwargs:
            raise FileNotFoundError("already gone")
        return original_stat(self, *args, **kwargs)  # type: ignore[arg-type]

    with patch.object(Path, "stat", stat_raising):
        await service.run_once()  # Must not raise
