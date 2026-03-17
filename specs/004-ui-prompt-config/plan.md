# Implementation Plan: UI Prompt Configuration

**Branch**: `004-ui-prompt-config` | **Date**: 2026-03-17 | **Spec**: [spec.md](spec.md)

## Summary

Move AI prompt configuration from hardcoded server-side `.md` files to a per-user database-backed store, surfaced through a Prompts modal in the UI header. Record a combined prompt hash on each processed page so the viewer can detect stale processing results and offer a targeted manual Reprocess button. All prompt changes take effect on the next processing run; no automatic reprocessing occurs.

## Technical Context

**Language/Version**: Python 3.13+
**Primary Dependencies**: aiohttp (server), SQLAlchemy asyncio + aiosqlite, mashumaro, alembic; Vanilla JS (Vue 3, no build step) for frontend
**Storage**: SQLite via SQLAlchemy asyncio — new `f_prompt_config` table; new `prompt_hash` column on `f_note_page_content`
**Testing**: pytest + pytest-asyncio (auto mode); `unittest.mock.patch` only; integration tests use ephemeral in-process DB
**Target Platform**: Linux server (self-hosted)
**Project Type**: Web service + static frontend
**Performance Goals**: Staleness check at display time must complete within a single DB round-trip (one SELECT on `f_note_page_content` for the file); prompt hash computation is in-memory only
**Constraints**: All new Python code must pass mypy strict; no blocking I/O in async context; user note content must never be logged
**Scale/Scope**: Single-user or small-group self-hosted; no horizontal scale considerations required

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Library-First | ✅ Pass | New service in `supernote/server/services/`; new route in `supernote/server/routes/`; new model in `supernote/server/db/models/` and `supernote/models/`. No circular dependencies introduced. |
| II. Protocol Fidelity | ✅ Pass | All new endpoints are under `/api/extended/` — not part of the device firmware protocol. No existing device endpoints modified. |
| III. Async-First | ✅ Pass | All DB operations in `PromptConfigService` use `async with session_manager.session()`. Prompt hash computation is in-memory (no blocking). Reprocess queuing uses the existing async `ProcessorService` queue. |
| IV. Strict Type Safety | ✅ Pass | All DTOs are `@dataclass` + `DataClassJSONMixin` with `omit_none=True`. New DB models use `Mapped[T]` / `mapped_column`. All functions carry explicit type annotations. |
| V. Observability & Data Privacy | ✅ Pass | Log prompt config saves/deletes at INFO level (category + layer only; never log prompt text content). `prompt_hash` values may be logged at DEBUG level. No note content appears in logs. |
| VI. TDD (NON-NEGOTIABLE) | ✅ Pass | Every implementation task below lists its test file. Tests are written and confirmed failing before implementation code is written. |
| VII. Security (NON-NEGOTIABLE) | ✅ Pass | All new endpoints require JWT. `PromptConfigService` enforces `user_id` scoping on every query — users cannot read or modify other users' configs. File ownership checked before staleness/reprocess endpoints. Input validated via mashumaro at route boundary. |

**Post-design re-check**: No violations identified after Phase 1 design.

## Project Structure

### Documentation (this feature)

```text
specs/004-ui-prompt-config/
├── plan.md              ← this file
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── prompts-api.md
└── tasks.md             (created by /speckit.tasks)
```

### Source Code

```text
supernote/
├── models/
│   └── prompt_config.py          # NEW — DTOs + VOs (PromptConfigDTO, staleness VOs)
├── server/
│   ├── db/
│   │   └── models/
│   │       ├── note_processing.py    # MODIFY — add prompt_hash column
│   │       └── prompt_config.py      # NEW — PromptConfigDO
│   ├── routes/
│   │   └── prompts.py               # NEW — prompts CRUD + staleness + reprocess routes
│   ├── services/
│   │   ├── prompt_config.py         # NEW — PromptConfigService
│   │   └── processor_modules/
│   │       ├── ocr.py               # MODIFY — accept prompt_resolver kwarg, write prompt_hash
│   │       └── summary.py           # MODIFY — accept prompt_resolver kwarg
│   ├── utils/
│   │   └── prompt_loader.py         # MODIFY — add get_all_known_layers() helper
│   └── app.py                       # MODIFY — inject PromptConfigService, register routes
│   └── static/
│       ├── index.html               # MODIFY — add Prompts header button
│       └── js/
│           ├── api/client.js        # MODIFY — add prompt + reprocess API functions
│           ├── components/
│           │   ├── PromptsModal.js  # NEW — prompt editor modal
│           │   └── FileViewer.js    # MODIFY — staleness fetch + indicators + reprocess
│           └── main.js              # MODIFY — showPromptsModal state + component registration
supernote/
└── alembic/versions/
    └── XXX_add_prompt_config.py     # NEW — migration: create f_prompt_config + add prompt_hash
```

**Structure Decision**: Single-project layout. New service/route/model files follow the existing naming and location conventions exactly.

---

## Implementation Phases

> **TDD Rule**: For every backend task, write the test file first, confirm it fails (`pytest -x`), then implement.

---

### Phase A — Database Layer

**A1 — DB Model: `PromptConfigDO`**
- File: `supernote/server/db/models/prompt_config.py`
- Fields: `id`, `user_id`, `category`, `layer`, `content`, `create_time`, `update_time`
- Unique constraint: `uq_prompt_config (user_id, category, layer)`
- Follow exact pattern of `NotePageContentDO` in `note_processing.py`
- Add import to `supernote/server/db/models/__init__.py`

**A2 — DB Model: `NotePageContentDO` modification**
- File: `supernote/server/db/models/note_processing.py`
- Add: `prompt_hash: Mapped[str | None] = mapped_column(String, nullable=True)`

**A3 — Alembic Migration**
- File: `supernote/alembic/versions/XXX_add_prompt_config.py`
- `upgrade()`: create `f_prompt_config` table; `op.add_column` `prompt_hash` on `f_note_page_content`
- `downgrade()`: drop column; drop table
- Test: `./script/test` (existing model completeness tests must still pass)

---

### Phase B — DTOs and Models

**B1 — DTOs**
- File: `supernote/models/prompt_config.py`
- Define: `PromptConfigDTO`, `UpsertPromptConfigDTO`, `GetPromptsResponseVO`, `PageStalenessDTO`, `FileStalenessResponseVO`, `ReprocessRequestDTO`, `ReprocessResponseVO`
- All `@dataclass` + `DataClassJSONMixin`, `omit_none=True`, camelCase aliases via `field_options`
- Test first: `tests/models/test_prompt_config_completeness.py` — round-trip serialisation for all fields

---

### Phase C — `PromptConfigService`

**C1 — Service skeleton + tests**
- Test file: `tests/server/services/test_prompt_config_service.py`
- Write failing tests for: `list_configs`, `upsert_config`, `delete_config`, `get_effective_prompt`, `compute_combined_prompt_hash`
- Tests use ephemeral in-process DB (no mocking of DB)

**C2 — Service implementation**
- File: `supernote/server/services/prompt_config.py`
- `__init__(self, session_manager, prompt_loader)` — inject both
- `list_configs(user_id: int) -> list[PromptConfigDO]`
- `upsert_config(user_id: int, category: str, layer: str, content: str) -> PromptConfigDO`
  - Validate category in `["ocr", "summary"]`; validate content not empty; validate layer pattern
  - UPSERT on unique constraint
- `delete_config(user_id: int, category: str, layer: str) -> None`
  - Raise `NotFoundError` if no row exists
- `get_effective_prompt(user_id: int, prompt_id: PromptId, note_type: str | None) -> str`
  - Check DB for user's override for common layer → type-specific layer
  - Fall back to `prompt_loader.get_prompt()` for any missing layer
  - Compose using same `Common + (Custom or Default)` logic as `PromptLoader.get_prompt()`
- `compute_combined_prompt_hash(user_id: int, note_type: str | None) -> str`
  - `ocr_prompt = get_effective_prompt(user_id, OCR_TRANSCRIPTION, note_type)`
  - `summary_prompt = get_effective_prompt(user_id, SUMMARY_GENERATION, note_type)`
  - `return sha256_string(ocr_prompt + "|" + summary_prompt)`
- `get_all_configs_with_defaults(user_id: int) -> list[PromptConfigDTO]`
  - Returns merged view: all known layers from prompt_loader, overlaid with user's DB rows
  - Calls `prompt_loader.get_all_known_layers()` (new helper — see Phase D)

**C3 — `PromptLoader` helper**
- File: `supernote/server/utils/prompt_loader.py`
- Add: `get_all_known_layers() -> dict[str, dict[str, str]]` — returns `{prompt_id: {layer: default_text}}` for all layers loaded from files
- This powers the "show all layers with defaults pre-populated" response

---

### Phase D — Processor Integration

**D1 — Tests for prompt-aware processing**
- Test file: `tests/server/services/test_processor_prompt_hash.py`
- Write failing tests:
  - OCR module stores `prompt_hash` on `NotePageContentDO` after processing
  - Summary module uses resolved prompt text (not file-based loader) when `prompt_resolver` provided
  - `ProcessorService.process_file()` passes correct hash for the file's user + note type
  - `prompt_hash` is `None` for pages processed without a resolver (backward compat)

**D2 — OCR module modification**
- File: `supernote/server/services/processor_modules/ocr.py`
- `process()` accepts `prompt_resolver: Callable[[PromptId, str | None], str] | None = None` and `prompt_hash: str | None = None` via `**kwargs`
- Replace `PROMPT_LOADER.get_prompt(...)` with `prompt_resolver(...)` if provided, else fall back to `PROMPT_LOADER.get_prompt(...)`
- After writing `text_content`, also write `content.prompt_hash = prompt_hash` if provided

**D3 — Summary module modification**
- File: `supernote/server/services/processor_modules/summary.py`
- Same `prompt_resolver` kwarg pattern as OCR module
- Replace `PROMPT_LOADER.get_prompt(...)` call with resolver if provided

**D4 — `ProcessorService` modification**
- File: `supernote/server/services/processor.py`
- Inject `PromptConfigService` (add to `__init__`)
- In `process_file(file_id)`:
  - Look up `file_do` to get `user_id` and `file_name`
  - Derive `note_type = Path(file_do.file_name).stem.lower()`
  - Create `prompt_resolver = lambda prompt_id, custom_type: prompt_config_service.get_effective_prompt(user_id, prompt_id, custom_type or note_type)`
  - Compute `prompt_hash = await prompt_config_service.compute_combined_prompt_hash(user_id, note_type)`
  - Pass `prompt_resolver=prompt_resolver, prompt_hash=prompt_hash` to all module `.run()` calls via kwargs
- In `app.py`: instantiate `PromptConfigService` and pass to `ProcessorService`

**D5 — Reprocess service method**
- Add `reprocess_pages(file_id: int, page_ids: list[str]) -> int` to `ProcessorService`
  - For each `page_id` in list: reset `SystemTaskDO` for `OCR_EXTRACTION` and `EMBEDDING_GENERATION` to PENDING
  - Reset `SystemTaskDO` for `SUMMARY_GENERATION` (global key) to PENDING
  - Enqueue `file_id` via existing `self.queue.put_nowait(file_id)`
  - Return count of pages queued
- Test: `tests/server/services/test_processor_prompt_hash.py` (extend existing test file)

---

### Phase E — Routes

**E1 — Tests for prompt routes**
- Test file: `tests/server/routes/test_prompts.py`
- Write failing tests for all 5 endpoints (see contracts)
- Include security tests: unauthenticated → 401; other user's file → 403
- Test input validation: empty content → 400; invalid category → 400

**E2 — Route implementation**
- File: `supernote/server/routes/prompts.py`
- `GET /api/extended/prompts` → `prompt_config_service.get_all_configs_with_defaults(user_id)`
- `PUT /api/extended/prompts` → validate via mashumaro `UpsertPromptConfigDTO`, call `upsert_config`
- `DELETE /api/extended/prompts/{category}/{layer}` → call `delete_config`; return 404 if not found
- `GET /api/extended/files/{file_id}/staleness` → verify ownership; load pages; compute current hash; return per-page diff
- `POST /api/extended/files/{file_id}/reprocess` → verify ownership; compute stale page IDs; call `processor_service.reprocess_pages`
- `POST /api/extended/files/{file_id}/pages/{page_id}/reprocess` → verify ownership; check page is stale; call `reprocess_pages([page_id])`
- Register `prompts.routes` in `app.py`

---

### Phase F — Frontend

> Frontend tasks do not require pre-written tests but should be manually verified against the quickstart end-to-end scenario.

**F1 — API client functions**
- File: `supernote/server/static/js/api/client.js`
- Add: `fetchPrompts()`, `savePrompt(category, layer, content)`, `deletePrompt(category, layer)`, `fetchStaleness(fileId)`, `reprocessFile(fileId, pageIds)`, `reprocessPage(fileId, pageId)`

**F2 — `PromptsModal.js`**
- File: `supernote/server/static/js/components/PromptsModal.js`
- Options API component, string template (matches existing style)
- Two tabs: OCR / Summary (or two collapsible sections)
- Each section shows: Common, Default, and any custom type layers
- Each layer shows: textarea (editable), Save button, Reset to Default button (only when `isOverride: true`)
- Add custom type: text input for name + textarea; Save creates the new layer
- Delete custom type: trash icon on user-created layers
- Uses `useToast()` for save/error feedback
- Emits `close` event; parent controls visibility with `v-if`

**F3 — `FileViewer.js` modification**
- On mount, call `fetchStaleness(fileId)` and store result
- Show stale banner in viewer header if `staleCount > 0`: `"X pages processed with outdated prompts"` + "Reprocess All" button
- In page header (`<div class="border-b p-3 bg-gray-50">`), add stale badge next to page number when `page.isStale`
- Add per-page "Reprocess" button in stale page headers
- On reprocess click: disable button, call API, poll processing status, re-fetch staleness on completion
- While reprocessing: show spinner inline (consistent with existing processing overlay pattern)

**F4 — Header button + wiring**
- File: `supernote/server/static/index.html`
- Add Prompts button icon to header (between API Keys and Sign Out), visible only when `isLoggedIn`
- SVG icon: document/pencil style consistent with existing header icons
- File: `supernote/server/static/js/main.js`
- Add `showPromptsModal = ref(false)`
- Register `PromptsModal` component
- Add `<prompts-modal v-if="showPromptsModal" @close="showPromptsModal = false">` to template

---

## Complexity Tracking

No constitution violations. All changes fit within existing architectural patterns.

---

## Testing Strategy Summary

| Test File | Coverage |
|-----------|----------|
| `tests/models/test_prompt_config_completeness.py` | DTO round-trip serialisation |
| `tests/server/services/test_prompt_config_service.py` | Service CRUD, prompt resolution, hash computation, fallback to defaults |
| `tests/server/services/test_processor_prompt_hash.py` | Hash written to DB after OCR, resolver passed through pipeline, reprocess task reset |
| `tests/server/routes/test_prompts.py` | All 5 endpoints: happy path + 401/403/400/404 error cases |

Existing tests must all continue to pass — OCR and summary modules fall back to `PROMPT_LOADER` when no resolver is injected, preserving pre-feature behaviour.
