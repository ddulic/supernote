"""Tests for TempFileCleanupService."""

import asyncio
import time
from pathlib import Path

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
