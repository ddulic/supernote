# Data Model: Note Page PNG Caching & Insights Panel Tabs

**Feature**: 005-cache-png-insights-tabs
**Date**: 2026-03-17

---

## Database Changes

### `f_user_file` table — new column

| Column | Type | Nullable | Default | Purpose |
|--------|------|----------|---------|---------|
| `last_conversion_md5` | `String` | Yes | `NULL` | Stores the file MD5 used during the most recent `convert_note_to_png` call. Used to detect content changes and reconstruct old storage keys for cleanup. |

**Migration**: New Alembic revision under `supernote/alembic/versions/`. Follows existing pattern (`add_column` with `nullable=True`, no `server_default` needed — rows for files that have never been converted will have `NULL`, which is treated as "no previous conversion").

**SQLAlchemy model addition** (`supernote/server/db/models/file.py` — `UserFileDO`):
```python
last_conversion_md5: Mapped[str | None] = mapped_column(String, nullable=True)
"""MD5 of the file at last PNG conversion; used for stale image cleanup."""
```

---

## New DTOs / VOs (`supernote/models/extended.py`)

### `OcrPageVO`

| Field | Python type | JSON alias | Notes |
|-------|-------------|------------|-------|
| `page_index` | `int` | `pageIndex` | 0-based page number, ordered ascending |
| `text_content` | `str` | `textContent` | Raw OCR text extracted from the page |

### `WebOcrListRequestDTO`

| Field | Python type | JSON alias | Notes |
|-------|-------------|------------|-------|
| `file_id` | `int` | `fileId` | ID of the note file to retrieve OCR for |

### `WebOcrListVO`

| Field | Python type | JSON alias | Notes |
|-------|-------------|------------|-------|
| `pages` | `list[OcrPageVO]` | `pages` | All pages with OCR text, ordered by `page_index`. Empty list if none available. |

All three use `@dataclass` + `DataClassJSONMixin` with `omit_none=True` and `BaseConfig(serialize_by_alias=True)` consistent with existing models in the file.

---

## Storage Key Patterns

No new storage key formats. Existing patterns used:

| Pattern | Bucket | Usage |
|---------|--------|-------|
| `conversions/{user_id}/{file_id}/page_{page_index}_{md5}.png` | `supernote-user-data` | Cached page image. Presence = content unchanged. |

**Cleanup logic**: When `last_conversion_md5 != node.md5` (content changed), old images are deleted by reconstructing: `get_conversion_png_path(user_id, file_id, i, last_conversion_md5)` for `i` in `0..note.get_total_pages()-1`.

---

## No New Tables

No new DB tables are required. OCR text is read from the existing `f_note_page_content.text_content` column (populated by the existing OCR processing pipeline).
