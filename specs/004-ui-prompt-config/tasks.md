# Tasks: UI Prompt Configuration

**Input**: Design documents from `/specs/004-ui-prompt-config/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/prompts-api.md ✅ quickstart.md ✅

**TDD**: Per Constitution §VI, tests are written FIRST and confirmed failing before implementation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: Maps to user story from spec.md
- Exact file paths included in all descriptions

---

## Phase 1: Setup

**Purpose**: No new project or dependency setup needed — existing stack used throughout.

- [X] T001 Verify existing test suite passes before starting: run `./script/test` and confirm green

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: DB models, DTOs, and `PromptConfigService` that all user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 Add `PromptConfigDO` SQLAlchemy model in `supernote/server/db/models/prompt_config.py` (fields: id, user_id, category, layer, content, create_time, update_time; unique constraint on user_id+category+layer per data-model.md)
- [X] T003 Add `prompt_hash: Mapped[str | None]` column to `NotePageContentDO` in `supernote/server/db/models/note_processing.py`
- [X] T004 Register `PromptConfigDO` import in `supernote/server/db/models/__init__.py`
- [X] T005 Write alembic migration in `supernote/alembic/versions/` — create `f_prompt_config` table and add `prompt_hash` column to `f_note_page_content`; include downgrade
- [X] T006 [P] Write failing completeness test in `tests/models/test_prompt_config_completeness.py` — round-trip serialisation for `PromptConfigDTO`, `UpsertPromptConfigDTO`, `GetPromptsResponseVO`, `PageStalenessDTO`, `FileStalenessResponseVO`, `ReprocessRequestDTO`, `ReprocessResponseVO`
- [X] T007 Define DTOs in `supernote/models/prompt_config.py`: `PromptConfigDTO`, `UpsertPromptConfigDTO`, `GetPromptsResponseVO`, `PageStalenessDTO`, `FileStalenessResponseVO`, `ReprocessRequestDTO`, `ReprocessResponseVO` — all `@dataclass` + `DataClassJSONMixin`, camelCase aliases, `omit_none=True` — confirm T006 now passes
- [X] T008 Write failing service tests in `tests/server/services/test_prompt_config_service.py`: `list_configs`, `upsert_config` (create + update), `delete_config` (success + NotFoundError), `get_effective_prompt` (DB override path + fallback path), `compute_combined_prompt_hash`, `get_all_configs_with_defaults`; use ephemeral in-process DB, no DB mocks
- [X] T009 Add `get_all_known_layers() -> dict[str, dict[str, str]]` helper to `supernote/server/utils/prompt_loader.py` — returns all layers loaded from files keyed by prompt_id
- [X] T010 Implement `PromptConfigService` in `supernote/server/services/prompt_config.py` with methods: `list_configs`, `upsert_config` (validates category/layer/content, upserts row), `delete_config` (raises `NotFoundError` if missing), `get_effective_prompt` (DB-first then fallback to `PromptLoader`), `compute_combined_prompt_hash` (sha256 of ocr_prompt + `"|"` + summary_prompt), `get_all_configs_with_defaults` (merged view) — confirm T008 passes
- [X] T011 Instantiate `PromptConfigService` in `supernote/server/app.py` and add to `app["prompt_config_service"]`; inject into `ProcessorService` constructor

**Checkpoint**: `./script/test` passes. DB models, migration, DTOs, and service are complete and tested.

---

## Phase 3: User Story 1 — View and Edit Prompts via Modal (Priority: P1) 🎯 MVP

**Goal**: Logged-in user can open a Prompts modal from the header, see current prompts (defaults shown when no override exists), edit any prompt, and save it. The AI uses the saved text on the next processing run.

**Independent Test**: Open the modal, edit the summary `monthly` layer, save, upload/reprocess a `monthly.note`, verify AI output reflects the new prompt text.

### Tests for User Story 1 ⚠️ Write FIRST — confirm FAILING

- [X] T012 Write failing route tests in `tests/server/routes/test_prompts.py` for: `GET /api/extended/prompts` (200 with merged defaults), `PUT /api/extended/prompts` (200 success, 400 empty content, 400 invalid category, 401 unauthenticated, verify user isolation — another user's config is not returned)

### Implementation for User Story 1

- [X] T013 [US1] Implement `GET /api/extended/prompts` handler in `supernote/server/routes/prompts.py` — calls `prompt_config_service.get_all_configs_with_defaults(user_id)`, returns `GetPromptsResponseVO`
- [X] T014 [US1] Implement `PUT /api/extended/prompts` handler in `supernote/server/routes/prompts.py` — validates `UpsertPromptConfigDTO` via mashumaro, calls `upsert_config`, returns 400 on validation failure
- [X] T015 [US1] Register `prompts.routes` in `supernote/server/app.py` — confirm T012 tests now pass
- [X] T016 [P] [US1] Add API client functions `fetchPrompts()` and `savePrompt(category, layer, content)` to `supernote/server/static/js/api/client.js`
- [X] T017 [US1] Create `PromptsModal.js` in `supernote/server/static/js/components/PromptsModal.js` — Options API component; two sections (OCR / Summary); each shows Common, Default, daily, weekly, monthly layers as textareas; Save button per layer calls `savePrompt`; `isOverride` styling distinguishes saved overrides from defaults; uses `useToast()` for feedback; emits `close`
- [X] T018 [US1] Add Prompts header button to `supernote/server/static/index.html` (between API Keys and Sign Out, visible when `isLoggedIn`; document/pencil SVG icon consistent with existing icons)
- [X] T019 [US1] Wire `PromptsModal` in `supernote/server/static/js/main.js`: add `showPromptsModal = ref(false)`, register component, add `<prompts-modal v-if="showPromptsModal" @close="showPromptsModal = false">` to template

**Checkpoint**: Prompts modal opens from header, shows defaults, saves overrides. `./script/test` still passes.

---

## Phase 4: User Story 2 — Manage Custom Note Types (Priority: P2)

**Goal**: User can add a new custom note type (e.g., `project`) with its own OCR/summary prompt, and delete it when no longer needed.

**Independent Test**: Create a `project` type in the modal, upload a `project.note`, verify the custom prompt is used during processing.

### Tests for User Story 2 ⚠️ Write FIRST — confirm FAILING

- [X] T020 Extend `tests/server/routes/test_prompts.py` with failing tests for: `DELETE /api/extended/prompts/{category}/{layer}` (200 success, 404 when no override exists, 401 unauthenticated); `PUT` with custom layer name (creates new type); cross-user 403 guard on DELETE

### Implementation for User Story 2

- [X] T021 [US2] Implement `DELETE /api/extended/prompts/{category}/{layer}` handler in `supernote/server/routes/prompts.py` — calls `delete_config`; returns 404 if no row exists — confirm T020 passes
- [X] T022 [US2] Add `deletePrompt(category, layer)` to `supernote/server/static/js/api/client.js`
- [X] T023 [US2] Extend `PromptsModal.js` in `supernote/server/static/js/components/PromptsModal.js`: add "Add custom type" UI (text input for name + textarea for content, Save button); add trash/delete icon on user-created custom layers (calls `deletePrompt`; removes from local state on success); prevent deletion of built-in layers (common, default, daily, weekly, monthly)

**Checkpoint**: Custom prompt types can be created, used, and deleted via the modal. `./script/test` passes.

---

## Phase 5: User Story 5 — Reprocess Stale Notes and Pages (Priority: P2)

**Goal**: After updating a prompt, the user can open a note in the viewer, see which pages used an older prompt version, and click Reprocess to queue targeted reprocessing.

**Independent Test**: Process a note, update its prompt, open the note viewer — stale indicators appear on pages. Click Reprocess; after processing completes, stale indicators disappear and AI output reflects the new prompt.

### Tests for User Story 5 ⚠️ Write FIRST — confirm FAILING

- [X] T024 Write failing tests in `tests/server/services/test_processor_prompt_hash.py`: after OCR runs with a `prompt_resolver`, `NotePageContentDO.prompt_hash` is set; `prompt_hash` is `None` when no resolver injected (backward compat); `ProcessorService.reprocess_pages` resets correct `SystemTaskDO` entries to PENDING and enqueues file; `compute_combined_prompt_hash` output matches expected sha256
- [X] T025 [P] Extend `tests/server/routes/test_prompts.py` with failing tests for: `GET /api/extended/files/{id}/staleness` (200 with per-page stale flags, NULL hash treated as stale, 401/403 guards); `POST /api/extended/files/{id}/reprocess` (200 with queued count, 409 when already processing, 401/403 guards); `POST /api/extended/files/{id}/pages/{page_id}/reprocess` (200, 400 when not stale, 401/403 guards)

### Implementation for User Story 5

- [X] T026 [US5] Modify `supernote/server/services/processor_modules/ocr.py`: accept `prompt_resolver: Callable | None = None` and `prompt_hash: str | None = None` via `**kwargs`; replace `PROMPT_LOADER.get_prompt(...)` with resolver when provided; after writing `text_content`, write `content.prompt_hash = prompt_hash` if provided
- [X] T027 [P] [US5] Modify `supernote/server/services/processor_modules/summary.py`: accept `prompt_resolver: Callable | None = None` via `**kwargs`; replace `PROMPT_LOADER.get_prompt(...)` with resolver when provided
- [X] T028 [US5] Modify `supernote/server/services/processor.py`: in `process_file()`, look up file's `user_id` and derive `note_type` from filename stem; create `prompt_resolver` closure via `prompt_config_service.get_effective_prompt`; compute `prompt_hash` via `prompt_config_service.compute_combined_prompt_hash`; pass both to all module `.run()` calls as kwargs — confirm T024 passes
- [X] T029 [US5] Add `reprocess_pages(file_id: int, page_ids: list[str]) -> int` to `supernote/server/services/processor.py`: reset `SystemTaskDO` status to PENDING for `OCR_EXTRACTION` and `EMBEDDING_GENERATION` per page and `SUMMARY_GENERATION` globally; enqueue `file_id`; return page count queued
- [X] T030 [US5] Implement `GET /api/extended/files/{file_id}/staleness` in `supernote/server/routes/prompts.py`: verify file ownership (403 if not owner); load all `NotePageContentDO` for file; compute current `prompt_hash`; return `FileStalenessResponseVO` with per-page `is_stale` flags — confirm T025 staleness tests pass
- [X] T031 [US5] Implement `POST /api/extended/files/{file_id}/reprocess` and `POST /api/extended/files/{file_id}/pages/{page_id}/reprocess` in `supernote/server/routes/prompts.py`: verify ownership; compute stale page IDs; reject non-stale page-level requests with 400; call `processor_service.reprocess_pages`; return `ReprocessResponseVO` — confirm all T025 tests pass
- [X] T032 [P] [US5] Add `fetchStaleness(fileId)`, `reprocessFile(fileId, pageIds)`, `reprocessPage(fileId, pageId)` to `supernote/server/static/js/api/client.js`
- [X] T033 [US5] Modify `supernote/server/static/js/components/FileViewer.js`: on mount call `fetchStaleness(fileId)` and store result; show stale banner in viewer header (`"X pages processed with outdated prompts"` + "Reprocess All" button) when `staleCount > 0`; add stale badge in page header div (`<div class="border-b p-3 bg-gray-50">`) for stale pages; add per-page "Reprocess" button; on reprocess click disable button and show inline spinner; re-fetch staleness after processing status returns complete

**Checkpoint**: Stale indicators appear in viewer after prompt change. Reprocess queues targeted pages. `./script/test` passes.

---

## Phase 6: User Stories 3 & 4 — Reset to Default + Common Prompt Editing (Priority: P3)

**Goal**: Users can reset any prompt override back to the server default, and the common (always-applied) layer is visible and editable alongside type-specific layers.

**Independent Test (US3)**: Edit a prompt, save, click "Reset to Default" — field reverts to server text, future processing uses server default.

**Independent Test (US4)**: Edit the common OCR prompt, save, process any note — the custom common text appears in the AI call.

### Tests for User Stories 3 & 4 ⚠️ Write FIRST — confirm FAILING

- [X] T034 Extend `tests/server/routes/test_prompts.py`: verify `DELETE /api/extended/prompts/{category}/{layer}` on a built-in layer (e.g., `summary/monthly`) removes the override row and subsequent `GET /prompts` returns server default for that layer; verify common layer override is returned by `GET /prompts` and used in `compute_combined_prompt_hash`

### Implementation for User Stories 3 & 4

- [X] T035 [US3] [US4] Extend `PromptsModal.js` in `supernote/server/static/js/components/PromptsModal.js`: show "Reset to Default" button only on fields where `isOverride === true`; clicking calls `deletePrompt(category, layer)` then reloads prompts and repopulates field with returned default; ensure the `common` layer row is always shown first in each category section — confirm T034 passes

**Checkpoint**: Reset to Default works for all layers. Common layer is editable and affects hash computation. `./script/test` passes.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T036 [P] Review all new log statements in `supernote/server/services/prompt_config.py` and `supernote/server/routes/prompts.py` — confirm prompt text content is never logged; only category, layer, and user_id appear in INFO-level logs
- [X] T037 Run `./script/lint` and resolve any ruff or mypy strict violations across all new and modified files
- [X] T038 Run end-to-end verification from `quickstart.md`: start ephemeral server, upload a `monthly.note`, edit the monthly summary prompt, open the note viewer, confirm stale indicator, reprocess, confirm indicator clears and AI output reflects new prompt

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1** (Setup): No dependencies — start immediately
- **Phase 2** (Foundational): Depends on Phase 1 — **BLOCKS all user story phases**
- **Phase 3** (US1 — View/Edit): Depends on Phase 2
- **Phase 4** (US2 — Custom Types): Depends on Phase 3 (extends the modal and DELETE endpoint)
- **Phase 5** (US5 — Reprocess): Depends on Phase 2; can run in parallel with Phases 3–4
- **Phase 6** (US3+US4 — Reset/Common): Depends on Phase 3 (reuses DELETE endpoint already implemented) and Phase 2
- **Phase 7** (Polish): Depends on all phases complete

### User Story Dependencies

- **US1 (P1)**: After Phase 2 — no dependencies on other stories
- **US2 (P2)**: After US1 — extends the modal with custom type management
- **US5 (P2)**: After Phase 2 — processor changes independent of modal UI; can proceed in parallel with US1
- **US3 (P3)**: After US1 and US2 — Reset button reuses the DELETE endpoint from US2
- **US4 (P3)**: After US1 — common layer is already returned by GET /prompts; only UI display change needed

### Parallel Opportunities

Within Phase 2: T002, T003, T006 can run in parallel (different files)
Within Phase 3: T016 (client.js) can run in parallel with T013–T015 (routes)
Within Phase 5: T024 and T025 (test files) can run in parallel; T026 and T027 (OCR + summary modules) can run in parallel; T032 (client.js) can run in parallel with T026–T031

---

## Parallel Example: Phase 5 (User Story 5)

```
# Write tests in parallel:
Task T024: tests/server/services/test_processor_prompt_hash.py
Task T025: tests/server/routes/test_prompts.py (staleness + reprocess endpoints)

# Once tests are failing, implement in parallel:
Task T026: processor_modules/ocr.py  (prompt_resolver + prompt_hash write)
Task T027: processor_modules/summary.py  (prompt_resolver)
Task T032: api/client.js  (fetchStaleness, reprocessFile, reprocessPage)

# Then sequentially (dependencies):
Task T028: processor.py  (pass resolver + hash to modules)
Task T029: processor.py  (reprocess_pages method)
Task T030: routes/prompts.py  (staleness endpoint)
Task T031: routes/prompts.py  (reprocess endpoints)
Task T033: FileViewer.js  (stale indicators + reprocess buttons)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only — ~11 tasks)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002–T011)
3. Complete Phase 3: User Story 1 (T012–T019)
4. **STOP and VALIDATE**: Modal opens, prompts editable, saves override, AI uses it
5. Deploy/demo if ready

### Incremental Delivery

1. Phase 2 → Foundation ready (DB + service + DTOs)
2. Phase 3 → US1: Modal with view/edit/save **[MVP]**
3. Phase 4 → US2: Custom types (extends modal with add/delete)
4. Phase 5 → US5: Stale detection + reprocess (processor + viewer changes)
5. Phase 6 → US3+US4: Reset to default + common layer editing (UI polish)
6. Phase 7 → Polish, lint, e2e

### Total Task Count

| Phase | Tasks | Stories |
|-------|-------|---------|
| Phase 1: Setup | 1 | — |
| Phase 2: Foundational | 10 | — |
| Phase 3: US1 (P1) | 8 | US1 |
| Phase 4: US2 (P2) | 4 | US2 |
| Phase 5: US5 (P2) | 10 | US5 |
| Phase 6: US3+US4 (P3) | 2 | US3, US4 |
| Phase 7: Polish | 3 | — |
| **Total** | **38** | |
