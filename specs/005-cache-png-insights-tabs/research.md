# Research: Note Page PNG Caching & Insights Panel Tabs

**Feature**: 005-cache-png-insights-tabs
**Date**: 2026-03-17

---

## Decision 1: PNG caching — existence check location

**Decision**: Add `await self.blob_storage.exists(USER_DATA_BUCKET, png_storage_key)` inside `FileService.convert_note_to_png` in `supernote/server/services/file.py`, per-page, before calling `ImageConverter.convert()`. Skip conversion and `put()` if the key already exists.

**Rationale**: All the necessary information (bucket, key) is available at that point in the loop. The key already encodes user_id, file_id, page_index, and file MD5, so a successful `exists()` means the content is unchanged and the cached image is valid.

**Alternatives considered**:
- Check at route level before calling service — rejected: service should own caching logic.
- Cache in memory (LRU dict) — rejected: server restarts would invalidate it; disk cache is durable.

---

## Decision 2: Fail-open on storage existence check errors

**Decision**: Wrap the `exists()` call in a `try/except`. On any `OSError` or storage exception, log a warning and proceed with conversion (treat as cache miss). This is per clarification Q3.

**Rationale**: A transient storage error should not block the user from viewing their note. Re-converting and re-storing the image is a safe recovery path.

**Alternatives considered**:
- Fail-closed (surface error to user) — rejected: poor UX for a cache lookup failure.

---

## Decision 3: Old-image cleanup via `last_conversion_md5` column

**Decision**: Add `last_conversion_md5: Mapped[str | None]` (nullable String) to `UserFileDO` in `supernote/server/db/models/file.py`, backed by an Alembic migration. When `convert_note_to_png` detects that the current MD5 differs from `last_conversion_md5` (or that page 0 doesn't exist at the current MD5 key), it:
1. Deletes old images by reconstructing keys with the old MD5 (`get_conversion_png_path(user_id, file_id, i, old_md5)` for i in 0..n-1).
2. Converts and stores new images.
3. Updates `node.last_conversion_md5 = node.md5` and commits.

**Rationale**: No `list_by_prefix` method exists on `BlobStorage` (nor is one practical with the current `_get_path` path sanitization, which strips directory components). Storing the previous MD5 in the DB is the only approach that allows exact key reconstruction for deletion without changing the storage interface. Alembic migration is the established pattern for schema changes in this project.

**Known limitation**: `LocalBlobStorage._get_path` uses `Path(key).name` to sanitize keys, which strips all directory components (e.g., `conversions/1/101/page_0_abc.png` → stored as `pa/page_0_abc.png`). This is a pre-existing behavior that could cause key collisions between different users' files. This feature does not fix this; the cleanup logic works correctly in the common case and degrades gracefully in the collision scenario.

**Alternatives considered**:
- Add `list_by_prefix` to `BlobStorage` — requires fixing `_get_path` path sanitization first, which is a backward-incompatible storage layout change; deferred to a future refactor.
- Delete all per-file images on note upload event — requires coupling sync pipeline to view layer; rejected.

---

## Decision 4: New dedicated OCR endpoint

**Decision**: Add `POST /api/extended/file/ocr/list` in `supernote/server/routes/extended.py`. Request DTO: `WebOcrListRequestDTO { file_id: int (alias: fileId) }`. Response VO: `WebOcrListVO { pages: list[OcrPageVO] }` where `OcrPageVO { page_index: int (alias: pageIndex), text_content: str (alias: textContent) }`. DTOs/VOs defined in `supernote/models/extended.py`. The handler queries `NotePageContentDO` by `file_id`, ordered by `page_index`, and returns only rows where `text_content IS NOT NULL`.

**Rationale**: Dedicated endpoint is cleaner than filtering the summary list by type. Single response (no pagination) is sufficient given typical note page counts. Follows existing extended endpoint conventions (POST with JSON body, mashumaro DTOs, `x-access-token` JWT auth, user ownership enforcement). Per clarification Q2.

**Alternatives considered**:
- Reuse summary endpoint with `dataSource=ocr` filter — rejected: couples unrelated data models; OCR source is not a `SummaryItem`.
- GET with path param — rejected: existing extended endpoints use POST+JSON body convention.

---

## Decision 5: SummaryPanel tab implementation

**Decision**: Add `activeTab` ref (default `'ai'`) to `SummaryPanel.js` setup. Add a two-button tab bar in the header area below the existing "AI Insights" title. Each button uses secondary-style Tailwind classes with an active state indicator (border-b or background highlight in black/gray, no accent colors). OCR data is fetched lazily when the user first clicks the "OCR" tab, using a new `fetchOcrPages(fileId)` API client function. Reset `activeTab` to `'ai'` on `watch(() => props.fileId, ...)`.

**Rationale**: Lazy fetch avoids loading OCR data for users who never open that tab. Reset on file change matches existing tab patterns and the spec (FR-010). Button styles must use the established button palette (no indigo/blue/green).

**Alternatives considered**:
- Eager fetch both tabs on mount — rejected: wastes bandwidth for users who only need AI tab.
- Separate component per tab — rejected: over-engineering for two tabs sharing one panel.

---

## Pre-existing finding (no action this feature)

`LocalBlobStorage._get_path` strips directory components from keys via `Path(key).name`. All blobs whose keys share the same filename component will map to the same physical file. Example: `conversions/1/101/page_0_abc.png` and `conversions/2/202/page_0_abc.png` both map to `supernote-user-data/pa/page_0_abc.png`. This is a pre-existing collision risk; mitigation is tracked separately and not in scope here.
