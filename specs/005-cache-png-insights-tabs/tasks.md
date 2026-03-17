# Tasks: Note Page PNG Caching & Insights Panel Tabs

**Input**: Design documents from `/specs/005-cache-png-insights-tabs/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Tests**: Included — TDD is NON-NEGOTIABLE per Constitution §VI. All tests must be written and confirmed failing before implementation.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete-task dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

## Path Conventions

Single project layout — `supernote/` package at repo root, `tests/` mirrors package structure.

---

## Phase 2: Foundational (Blocking Prerequisites for US1)

**Purpose**: DB model and migration changes required before US1 tests can be run against a real schema.

**⚠️ CRITICAL**: US1 tests depend on `last_conversion_md5` existing on `UserFileDO`. Complete this phase before Phase 3.

- [x] T001 Add `last_conversion_md5: Mapped[str | None]` column to `UserFileDO` in `supernote/server/db/models/file.py`
- [x] T002 [P] Create Alembic migration `add_last_conversion_md5_to_user_file` in `supernote/alembic/versions/` (nullable String column on `f_user_file`, no server default)

**Checkpoint**: Foundation ready — US1 and US2 can now proceed in parallel

---

## Phase 3: User Story 1 — Fast Repeat Note Loading (Priority: P1) 🎯 MVP

**Goal**: Cached page images are reused on repeat views of unchanged notes; stale images from previous content versions are deleted.

**Independent Test**: Open a note in the dev server, observe "Converting note..." loading. Close and reopen — the loading phase should be negligible (near-instant). Verify in service tests that `blob_storage.exists()` is called per page and `ImageConverter.convert()` is skipped when `exists` returns `True`.

### Tests for User Story 1 ⚠️ Write FIRST — confirm they FAIL before implementing

- [x] T003 [US1] Write failing service tests for `convert_note_to_png` covering: (a) skips conversion and `put` when `exists` returns `True`, (b) converts and stores when `exists` returns `False`, (c) treats storage error on `exists` as cache miss (fail-open), (d) deletes old-hash images for all page indices when `last_conversion_md5 != node.md5`, (e) updates `node.last_conversion_md5` to current MD5 after storing new images — in `tests/server/services/test_file_service.py`

### Implementation for User Story 1

- [x] T004 [US1] Modify `FileService.convert_note_to_png` in `supernote/server/services/file.py` — wrap each page's conversion in a per-page `await self.blob_storage.exists()` check; skip `ImageConverter.convert()` and `blob_storage.put()` if `True`; wrap the `exists` call in `try/except` and log a warning on error, treating it as a cache miss (fail-open per research.md Decision 2)
- [x] T005 [US1] Add old-image cleanup and column update to `convert_note_to_png` in `supernote/server/services/file.py` — when `node.last_conversion_md5` is set and differs from `node.md5`, delete old images by calling `blob_storage.delete(USER_DATA_BUCKET, get_conversion_png_path(user_id, file_id, i, old_md5))` for `i` in `0..note.get_total_pages()-1`; after all pages are stored, set `node.last_conversion_md5 = node.md5` and commit the session

**Checkpoint**: US1 complete — repeat note views skip conversion; stale images cleaned up; all US1 tests pass

---

## Phase 4: User Story 2 — AI Insights Panel with OCR Tab (Priority: P2)

**Goal**: Insights panel shows "AI" (default) and "OCR" tabs; OCR tab displays per-page extracted text fetched from a new backend endpoint.

**Independent Test**: Open any processed note, click the lightning bolt (AI Insights panel), confirm two tabs render. "AI" tab shows existing summaries unchanged. "OCR" tab shows per-page text or an empty state if not yet processed. Verify in route tests that `POST /api/extended/file/ocr/list` returns pages ordered by `page_index` and enforces auth/ownership.

> **Note**: US2 can be worked in parallel with US1 after Phase 2 completes — all files are disjoint.

### Tests for User Story 2 ⚠️ Write FIRST — confirm they FAIL before implementing

- [x] T006 [P] [US2] Write failing endpoint tests for `POST /api/extended/file/ocr/list` covering: success with ordered pages, empty list when no OCR data, 401 without token, 403 for other user's file, 404 for unknown file, 400 for malformed body — in `tests/server/routes/test_ocr_endpoint.py`
- [x] T007 [P] [US2] Write failing model completeness/serialization tests (round-trip `from_dict`/`to_dict`) for `OcrPageVO`, `WebOcrListRequestDTO`, `WebOcrListVO` — in `tests/models/test_extended_completeness.py`

### Implementation for User Story 2

- [x] T008 [P] [US2] Add `OcrPageVO`, `WebOcrListRequestDTO`, `WebOcrListVO` dataclasses to `supernote/models/extended.py` using `@dataclass + DataClassJSONMixin`, `omit_none=True`, `BaseConfig(serialize_by_alias=True)`, camelCase JSON aliases matching `contracts/ocr-list-endpoint.md`
- [x] T009 [US2] Implement `POST /api/extended/file/ocr/list` handler in `supernote/server/routes/extended.py` — parse `WebOcrListRequestDTO`, enforce user ownership (same pattern as summary endpoint), query `NotePageContentDO` where `file_id=?` and `text_content IS NOT NULL` ordered by `page_index`, return `WebOcrListVO`; register route in app router alongside existing extended routes (depends on T008)
- [x] T010 [P] [US2] Add `fetchOcrPages(fileId)` async function to `supernote/server/static/js/api/client.js` — `POST /api/extended/file/ocr/list` with `{ fileId }`, JWT header, returns `data.pages || []`, handles 401 with logout
- [x] T011 [US2] Update `supernote/server/static/js/components/SummaryPanel.js` — add `activeTab` ref (default `'ai'`), `ocrPages`/`isOcrLoading`/`ocrError`/`ocrLoaded` refs; add two-tab bar below header title using secondary button Tailwind classes with active tab indicated by `border-b-2 border-black dark:border-white font-semibold` (no accent colors); implement `loadOcr()` called lazily on first OCR tab click; wrap existing content in `v-if="activeTab === 'ai'"` and add OCR content in `v-if="activeTab === 'ocr'"` with loading spinner and empty state; reset `activeTab` to `'ai'` and clear OCR state in `watch(() => props.fileId, ...)` (depends on T010)

**Checkpoint**: US2 complete — both tabs render; AI tab content unchanged; OCR tab loads text lazily; all US2 tests pass

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T012 [P] Run `./script/run-mypy.sh` and resolve all type errors in changed Python files (`supernote/server/db/models/file.py`, `supernote/server/services/file.py`, `supernote/server/routes/extended.py`, `supernote/models/extended.py`, `supernote/alembic/versions/<migration>.py`)
- [x] T013 [P] Run `./script/test` (full pytest suite) and confirm zero regressions; fix any failures before proceeding
- [ ] T014 Manual end-to-end verification using `./script/server` (ephemeral dev server): open a multi-page note, time the first load; close and reopen — confirm second load is significantly faster; open Insights panel and confirm both "AI" and "OCR" tabs render and display correct content

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: No dependencies — start immediately
- **US1 (Phase 3)**: Depends on Phase 2 (needs `last_conversion_md5` column and migration)
- **US2 (Phase 4)**: Depends on Phase 2 completion (can run in parallel with US1 after Phase 2)
- **Polish (Phase 5)**: Depends on Phase 3 + Phase 4 complete

### User Story Dependencies

- **US1 (P1)**: Requires Phase 2 complete. No dependency on US2.
- **US2 (P2)**: Requires Phase 2 complete. No dependency on US1. All files disjoint from US1.

### Within Each User Story

1. Tests written and confirmed FAILING (TDD — Constitution §VI non-negotiable)
2. Implementation tasks in order (models → service/handler → frontend)
3. Story complete before moving to next priority (unless parallel team)

### Parallel Opportunities

- T001 + T002: Different files — run in parallel
- T006 + T007: Different files — run in parallel (US2 tests can be written while US1 is underway)
- T008 + T010: Different files — run in parallel (models and JS client are independent)
- T012 + T013: Independent checks — run in parallel

---

## Parallel Example: US1 (Phase 3)

```bash
# Phase 2 in parallel:
Task T001: "Add last_conversion_md5 to UserFileDO in supernote/server/db/models/file.py"
Task T002: "Create Alembic migration in supernote/alembic/versions/"

# After Phase 2, US1 is sequential (TDD order):
Task T003: Write failing tests in tests/server/services/test_file_service.py
Task T004: Implement exists check in supernote/server/services/file.py
Task T005: Implement cleanup + column update in supernote/server/services/file.py
```

## Parallel Example: US2 (Phase 4)

```bash
# US2 tests in parallel (different files):
Task T006: Endpoint tests in tests/server/routes/test_extended.py
Task T007: Model completeness tests in tests/models/test_extended_completeness.py

# After tests are written and failing, models + client in parallel:
Task T008: DTOs/VOs in supernote/models/extended.py
Task T010: fetchOcrPages in supernote/server/static/js/api/client.js

# Sequential after T008:
Task T009: Route handler in supernote/server/routes/extended.py

# Sequential after T010:
Task T011: SummaryPanel.js tabs
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 2: Foundational (T001, T002)
2. Complete Phase 3: US1 (T003 → T004 → T005)
3. **STOP and VALIDATE**: Reopen a large note twice; confirm second open is fast
4. Ship if ready

### Incremental Delivery

1. Phase 2 → Foundation ready
2. Phase 3 (US1) → Caching live → validate → demo
3. Phase 4 (US2) → OCR tab live → validate → demo
4. Phase 5 (Polish) → Clean mypy + full test suite

### Parallel Team Strategy

With two developers after Phase 2:
- Developer A: US1 (T003 → T004 → T005)
- Developer B: US2 (T006/T007 → T008/T010 → T009 → T011)

---

## Notes

- [P] tasks = operate on different files with no incomplete-task dependencies
- [Story] label maps each task to its user story for traceability
- Tests MUST fail before implementation — do not skip this confirmation step
- Commit after each completed task or logical group
- Stop at Phase 3 checkpoint to validate US1 independently before starting US2
- `last_conversion_md5` is `NULL` for files that have never been converted — treat `NULL` as "no previous conversion" (no cleanup needed)
- The OCR tab shows only pages where `text_content IS NOT NULL` — an empty array is valid and expected for notes still being processed
