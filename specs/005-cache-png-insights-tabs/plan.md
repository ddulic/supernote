# Implementation Plan: Note Page PNG Caching & Insights Panel Tabs

**Branch**: `005-cache-png-insights-tabs` | **Date**: 2026-03-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-cache-png-insights-tabs/spec.md`

## Summary

Cache converted note page PNG images on first view so subsequent opens of unchanged notes are near-instant, and extend the AI Insights panel with a second tab exposing raw OCR text per page. Caching is implemented by checking storage before each conversion; cleanup of stale images uses a new `last_conversion_md5` column on `UserFileDO`. The OCR tab is backed by a new dedicated backend endpoint.

## Technical Context

**Language/Version**: Python 3.13+ (backend), Vanilla JS / Vue 3 ESM (frontend)
**Primary Dependencies**: aiohttp, SQLAlchemy asyncio + aiosqlite, mashumaro, alembic
**Storage**: SQLite (DB via SQLAlchemy), LocalBlobStorage (disk — `supernote-user-data` bucket)
**Testing**: pytest + pytest-asyncio (auto mode); `unittest.mock.patch` for mocking
**Target Platform**: Linux server (self-hosted)
**Project Type**: Web service + SPA frontend (no build step)
**Performance Goals**: Repeat note views 80%+ faster; zero redundant conversions for unchanged notes
**Constraints**: All I/O async; strict mypy; every endpoint JWT-authenticated; no content logging
**Scale/Scope**: Single-user instances to small teams; typical notes are 1–200 pages

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Library-First | ✅ Pass | Changes in `server/services/` and `server/routes/`; no new cross-layer circular deps |
| II. Protocol Fidelity | ✅ Pass | New endpoint is extension-only (`/api/extended/`); device protocol untouched |
| III. Async-First | ✅ Pass | `blob_storage.exists()` is async; all I/O remains awaited; no blocking calls added |
| IV. Strict Type Safety | ✅ Pass | New DTOs use `@dataclass + DataClassJSONMixin`; `last_conversion_md5: Mapped[str | None]` typed correctly |
| V. Observability & Privacy | ✅ Pass | OCR text MUST NOT be logged; `last_conversion_md5` is a hash, not content |
| VI. TDD (NON-NEGOTIABLE) | ✅ Pass | Tests must be written first; red-green-refactor required |
| VII. Security (NON-NEGOTIABLE) | ✅ Pass | New OCR endpoint requires JWT + user ownership check; same pattern as summary endpoint |
| VIII. Frontend UI Conventions | ✅ Pass | Tab buttons use black/gray palette; no accent colors; dark: variants required |

**Post-design re-check**: All gates remain clear. The `last_conversion_md5` column addition follows the Alembic migration pattern used in `b2c3d4e5f6a7_add_prompt_config.py`. No new accepted security risks.

## Project Structure

### Documentation (this feature)

```text
specs/005-cache-png-insights-tabs/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/
│   └── ocr-list-endpoint.md  # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
supernote/
├── models/
│   └── extended.py                         # Add OcrPageVO, WebOcrListRequestDTO, WebOcrListVO
├── server/
│   ├── routes/
│   │   └── extended.py                     # Add POST /api/extended/file/ocr/list handler
│   ├── services/
│   │   └── file.py                         # Modify convert_note_to_png (exists check + cleanup)
│   └── db/
│       └── models/
│           └── file.py                     # Add last_conversion_md5 to UserFileDO
├── alembic/
│   └── versions/
│       └── <hash>_add_last_conversion_md5.py  # New Alembic migration
└── server/
    └── static/
        └── js/
            ├── components/
            │   └── SummaryPanel.js         # Add tabs, OCR fetch, reset on file change
            └── api/
                └── client.js              # Add fetchOcrPages(fileId)

tests/
├── server/
│   ├── routes/
│   │   └── test_extended.py               # Add OCR endpoint tests (auth, ownership, empty, data)
│   └── services/
│       └── test_file_service.py           # Add caching + cleanup behaviour tests
└── models/
    └── test_extended_completeness.py      # Add OcrPageVO round-trip test
```

**Structure Decision**: Single project layout (existing). All changes are additive within the established `supernote/` package hierarchy.

## Implementation Approach

### Part 1 — PNG Caching (`FileService.convert_note_to_png`)

**File**: `supernote/server/services/file.py`

Replace the unconditional convert-and-store loop with:

1. Load notebook and build `converter` as today.
2. Check whether page 0 key exists with current MD5. This determines if content has changed.
3. **If content changed** (page 0 doesn't exist OR `node.last_conversion_md5 != node.md5` and both are set): delete old images by iterating `i in 0..total_pages-1` and calling `blob_storage.delete(USER_DATA_BUCKET, get_conversion_png_path(user_id, file_id, i, old_md5))`.
4. **Per-page loop**: call `blob_storage.exists()` (fail-open: wrap in `try/except`, log warning, treat error as cache miss). Skip conversion if `True`; convert and store if `False`.
5. After all pages written: if `node.last_conversion_md5 != node.md5`, update `node.last_conversion_md5 = node.md5` and commit the session.
6. Return `ConversionsVO` list as today (signed URLs via existing OSS route).

### Part 2 — OCR Endpoint

**Files**: `supernote/models/extended.py`, `supernote/server/routes/extended.py`

Add `OcrPageVO`, `WebOcrListRequestDTO`, `WebOcrListVO` to `supernote/models/extended.py` following the mashumaro + `BaseConfig(serialize_by_alias=True)` + `omit_none=True` pattern.

Add handler in `extended.py`:
```
POST /api/extended/file/ocr/list
  → parse WebOcrListRequestDTO
  → enforce user ownership (same pattern as summary endpoint)
  → query NotePageContentDO WHERE file_id=? AND text_content IS NOT NULL ORDER BY page_index ASC
  → return WebOcrListVO(pages=[OcrPageVO(page_index=r.page_index, text_content=r.text_content) ...])
```

Register route in the application router (same location as existing extended routes).

### Part 3 — DB Migration

**File**: `supernote/alembic/versions/<hash>_add_last_conversion_md5.py`

```python
def upgrade() -> None:
    op.add_column("f_user_file", sa.Column("last_conversion_md5", sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column("f_user_file", "last_conversion_md5")
```

### Part 4 — Frontend: SummaryPanel tabs

**Files**: `supernote/server/static/js/components/SummaryPanel.js`, `supernote/server/static/js/api/client.js`

**`client.js`**: Add `fetchOcrPages(fileId)` — `POST /api/extended/file/ocr/list` with `{ fileId }`, returns `data.pages || []`.

**`SummaryPanel.js`** changes:
- Add `activeTab = ref('ai')`, `ocrPages = ref([])`, `isOcrLoading = ref(false)`, `ocrError = ref(null)`, `ocrLoaded = ref(false)`.
- `watch(() => props.fileId, () => { activeTab.value = 'ai'; ocrPages.value = []; ocrLoaded.value = false; })`.
- Add `loadOcr()` async function: called when user clicks OCR tab (lazy), sets `isOcrLoading`, fetches, stores result.
- Tab bar replaces the title row (or sits below it). Two buttons using secondary Tailwind classes. Active tab: add `border-b-2 border-black dark:border-white font-semibold` to highlight (no accent colors).
- Template: `v-if="activeTab === 'ai'"` wraps existing content; `v-if="activeTab === 'ocr'"` renders OCR pages list with loading/empty states.
- OCR list: one card per page showing page number and `textContent` in pre-wrap or prose.

## Complexity Tracking

No constitution violations. No complexity justification required.
