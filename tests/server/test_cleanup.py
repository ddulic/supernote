"""Tests for TempFileCleanupService."""

from pathlib import Path

from supernote.server.services.cleanup import TempFileCleanupService


async def test_stop_handles_cancelled_error(tmp_path: Path) -> None:
    """stop() awaits the cancelled task and swallows CancelledError."""
    service = TempFileCleanupService(tmp_path, interval_seconds=9999)
    await service.start()
    assert service.is_running()
    await service.stop()
    assert not service.is_running()
    assert service._task is None
