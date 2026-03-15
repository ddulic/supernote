"""Periodic cleanup service for orphaned temp chunk files."""

import asyncio
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class TempFileCleanupService:
    """Periodically removes orphaned chunk files (*.part.*) older than TTL."""

    def __init__(
        self,
        scan_dir: Path,
        interval_seconds: int = 3600,
        ttl_seconds: int = 86400,
    ) -> None:
        self.scan_dir = scan_dir
        self.interval_seconds = interval_seconds
        self.ttl_seconds = ttl_seconds

        self._task: asyncio.Task[None] | None = None
        self._shutdown_event = asyncio.Event()

    def is_running(self) -> bool:
        """Return True if the background task is active."""
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        """Start the background cleanup task."""
        self._shutdown_event.clear()
        self._task = asyncio.create_task(self._cleanup_loop())
        logger.info(
            "TempFileCleanupService started (interval=%ds, ttl=%ds)",
            self.interval_seconds,
            self.ttl_seconds,
        )

    async def stop(self) -> None:
        """Stop the background cleanup task."""
        if self._task is None or self._task.done():
            return
        self._shutdown_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("TempFileCleanupService stopped.")

    async def _cleanup_loop(self) -> None:
        """Main cleanup loop."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

            if self._shutdown_event.is_set():
                break

            try:
                await self.run_once()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error during temp file cleanup: %s", e, exc_info=True)

    async def run_once(self) -> None:
        """Find and delete orphaned chunk files.

        Pattern: find all files matching *.part.* in the scan directory.
        Check mtime — if age > ttl_seconds, delete.
        """
        now = time.time()

        def _scan_and_delete() -> int:
            deleted = 0
            if not self.scan_dir.exists():
                return deleted
            for path in self.scan_dir.iterdir():
                # Match files whose name contains ".part." (e.g. abc123.part.1)
                if path.is_file() and ".part." in path.name:
                    try:
                        mtime = path.stat().st_mtime
                        age = now - mtime
                        if age > self.ttl_seconds:
                            path.unlink(missing_ok=True)
                            deleted += 1
                            logger.debug("Deleted expired chunk file: %s", path)
                    except FileNotFoundError:
                        pass  # Already gone
                    except Exception as e:
                        logger.warning("Failed to delete chunk file %s: %s", path, e)
            return deleted

        deleted = await asyncio.to_thread(_scan_and_delete)
        if deleted:
            logger.info(
                "TempFileCleanupService: deleted %d expired chunk file(s).", deleted
            )
