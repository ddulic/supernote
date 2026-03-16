---
description: "Task list for constitution alignment"
---

# Tasks: Constitution Alignment

**Input**: Design documents from `/specs/001-constitution-alignment/`
**Prerequisites**: plan.md ✅ spec.md ✅ data-model.md ✅ contracts/ ✅ quickstart.md ✅

**TDD Note**: Per constitution Principle VI (NON-NEGOTIABLE), all test tasks MUST be
written and confirmed to FAIL before their corresponding implementation tasks begin.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: User story this task belongs to (US1, US2, US3)
- Include exact file paths in all descriptions

---

## Phase 1: Setup

**Purpose**: Baseline inventory before any changes.

- [x] T001 Run mypy with `supernote/notebook/` and `supernote/cli/` temporarily un-excluded and capture full error list to `specs/001-constitution-alignment/research-mypy-errors.md`

**Checkpoint**: Error inventory complete — US1 implementation can now begin with a full picture.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema changes that US2 quota tasks depend on. Must complete before Phase 4.

**⚠️ CRITICAL**: US2 quota implementation cannot begin until T002–T003 are complete.

- [x] T002 Add `used_capacity: Mapped[int]` column (default 0) to `UserDO` in `supernote/server/db/models/user.py`
- [x] T003 Create alembic migration in `supernote/alembic/versions/` adding `used_capacity` column with a reconciliation `UPDATE` that sets `used_capacity = SUM(active file sizes)` for all existing users

**Checkpoint**: Schema migration complete — US2 implementation can now proceed.

---

## Phase 3: User Story 1 — Type Safety Completion (Priority: P1) 🎯 MVP

**Goal**: Full mypy coverage across all modules; zero `Optional[T]` legacy syntax.

**Independent Test**: Run `./script/run-mypy.sh` — must exit 0 with no modules excluded.

### Tests for User Story 1

> **Write these first, confirm they pass (they validate the annotation style — pass once fixed)**

- [x] T004 [P] [US1] Add missing type annotations to all functions/fixtures in `tests/notebook/test_init.py`
- [x] T005 [P] [US1] Audit `tests/client/` for any unannotated test functions and add type annotations

### Implementation for User Story 1

- [x] T006 [P] [US1] Migrate `Optional[T]` → `T | None` and `List[T]`/`Set[T]` → `list[T]`/`set[T]` in `supernote/server/services/vfs.py`
- [x] T007 [P] [US1] Migrate `Optional[T]` → `T | None` in `supernote/server/services/coordination.py`
- [x] T008 [P] [US1] Migrate `Optional[T]` → `T | None` and `Any` → typed alternatives in `supernote/server/services/schedule.py`
- [x] T009 [P] [US1] Migrate `List[T]`, `Set[T]` → `list[T]`, `set[T]` in `supernote/server/services/processor.py`
- [x] T010 [P] [US1] Migrate all remaining `Optional[T]` → `T | None` across `supernote/server/` (all files not covered by T006–T009)
- [x] T011 [P] [US1] Migrate all remaining `Optional[T]` → `T | None` across `supernote/models/` and `supernote/client/`
- [x] T012 [US1] Fix all mypy errors in `supernote/cli/` (owned code; zero blanket `# type: ignore`; depends on T010–T011 for cross-module types)
- [x] T013 [US1] Fix all mypy errors in `supernote/notebook/` (fix owned code; add targeted `# type: ignore[<code>]` with justification comment only for forked/inherited parsing logic; depends on T012)
- [x] T014 [US1] Remove `supernote/notebook/` and `supernote/cli/` from the `exclude` list in `[tool.mypy]` in `pyproject.toml` (do this only after T012–T013 reach zero errors)
- [x] T015 [US1] Run `./script/run-mypy.sh` and confirm zero errors with no exclusions; run `./script/test` and confirm all tests pass

**Checkpoint**: US1 complete — mypy clean across all modules, zero `Optional[T]` remaining.

---

## Phase 4: User Story 2 — Security Gap Closure (Priority: P2)

**Goal**: Hourly temp-file TTL cleanup + per-user quota enforcement (10 GB default).

**Independent Test**: (a) Upload a note, abandon session, confirm chunk file deleted after TTL. (b) Set 1 KB quota, upload a larger file, confirm 507 before data transfer.

### Tests for User Story 2

> **Write these FIRST and confirm they FAIL before writing any implementation**

- [x] T016 [P] [US2] Write `tests/server/services/test_cleanup.py`: test that `TempFileCleanupService` removes chunk files (`*.part.*`) older than the configured TTL and does NOT remove files younger than TTL
- [x] T017 [P] [US2] Write `tests/server/routes/test_upload_quota.py`: test that `POST /api/file/3/files/upload/apply` returns HTTP 507 with `E0507` error code when `used_capacity + requested_size > total_capacity`
- [x] T018 [P] [US2] Write `tests/server/services/test_user_quota.py`: test that `used_capacity` increments on upload finish and decrements on file delete, and floors at 0

### Implementation for User Story 2

- [x] T019 [US2] Implement `TempFileCleanupService` in `supernote/server/services/cleanup.py` with configurable `interval_seconds` and `ttl_seconds`; follows `ProcessorService` lifecycle pattern (`start()` / `stop()` with `asyncio.Task` + `asyncio.Event`)
- [x] T020 [P] [US2] Add `temp_cleanup_interval_seconds` and `temp_ttl_seconds` fields to `ServerConfig` in `supernote/server/config.py` with env-var overrides `SUPERNOTE_TEMP_CLEANUP_INTERVAL` and `SUPERNOTE_TEMP_TTL`
- [x] T021 [US2] Register `TempFileCleanupService` in `app.on_startup` and `app.on_shutdown` in `supernote/server/app.py` (depends on T019, T020)
- [x] T022 [US2] Add quota check to `handle_upload_apply` in `supernote/server/routes/file_device.py`: read `user.used_capacity` + `user.total_capacity`, return 507 with `E0507` if exceeded (depends on T002–T003)
- [x] T023 [US2] Add quota check to `handle_file_upload_apply` in `supernote/server/routes/file_web.py`: same logic as T022 (depends on T002–T003)
- [x] T024 [US2] Increment `used_capacity` atomically in upload-finish path in `supernote/server/services/file.py` (depends on T002–T003)
- [x] T025 [US2] Decrement `used_capacity` atomically (floor at 0) in file-delete path in `supernote/server/services/file.py` (depends on T002–T003)
- [x] T026 [US2] Apply `default_quota_bytes` (from `ServerConfig`, env: `SUPERNOTE_DEFAULT_QUOTA_BYTES`, default 10 GB) when creating new users in `supernote/server/services/user.py`

**Checkpoint**: US2 complete — quota enforced, chunk cleanup runs hourly. Verify with quickstart.md US2 steps.

---

## Phase 5: User Story 3 — Code Hygiene & Observability Safety (Priority: P3)

**Goal**: Remove dead code; document + fix VFS semantics; redact note content from trace logs.

**Independent Test**: (a) Full test suite passes after dead-code removal. (b) Trace log contains zero readable note text after processing a `.note` file.

### Tests for User Story 3

> **Write these FIRST and confirm they FAIL before writing any implementation**

- [x] T027 [P] [US3] Write `tests/server/services/test_vfs.py` (new tests): test that `VirtualFileSystem.delete_node` on a folder recursively soft-deletes all active children and creates `RecycleFileDO` entries for each
- [x] T028 [P] [US3] Write test in `tests/server/services/test_vfs.py`: test that `VirtualFileSystem.copy_node` on a folder with nested sub-directories produces a complete deep copy under the target parent
- [x] T029 [P] [US3] Write `tests/server/test_trace_redaction.py`: test that responses from summary/insight routes have their body replaced with `<note-content redacted>` in the trace log entry

### Implementation for User Story 3

- [x] T030 [US3] Remove `SqliteCoordinationService._cleanup()` stub method (lines 56–59) from `supernote/server/services/coordination.py`; confirm no call sites exist first
- [x] T031 [US3] Fix `VirtualFileSystem.delete_node` in `supernote/server/services/vfs.py` to recursively soft-delete all active descendants in a single transaction when called on a folder (use `list_recursive()`; create `RecycleFileDO` per file node)
- [x] T032 [P] [US3] Add docstring to `VirtualFileSystem.copy_node` in `supernote/server/services/vfs.py` documenting: recursive behaviour, autorename semantics, CAS storage-key sharing, and that it is safe to call concurrently with the processor pipeline
- [x] T033 [US3] Add note-content redaction guard to `trace_middleware` in `supernote/server/app.py`: replace response body with `"<note-content redacted>"` when route path matches `/api/file/insights`, `/api/summary`, or similar OCR/synthesis result routes

**Checkpoint**: All US3 tasks complete — full test suite passes with no regressions.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and ROADMAP housekeeping.

- [ ] T034 [P] Run `./script/test` and confirm all 300+ tests pass with zero failures or removals
- [ ] T035 [P] Run `./script/run-mypy.sh` and confirm zero errors across the full `supernote/` package
- [ ] T036 [P] Run `./script/lint` and confirm zero lint violations
- [x] T037 Update `ROADMAP.md` to mark completed items: static analysis (mypy for notebook/ and cli/), temp file cleanup, capacity/quota enforcement, VFS semantics, dead code removal

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (mypy inventory informs migration scope for US1, though schema work can start immediately)
- **US1 (Phase 3)**: Depends on Phase 1 (error inventory from T001)
- **US2 (Phase 4)**: Depends on Phase 2 (schema migration T002–T003 MUST complete first)
- **US3 (Phase 5)**: No blocking dependencies — can start after Phase 1
- **Polish (Phase 6)**: Depends on all story phases complete

### User Story Dependencies

- **US1 (P1)**: Starts after T001 (error inventory). T006–T011 fully parallel. T012 depends on T010–T011. T013 depends on T012. T014 depends on T013.
- **US2 (P2)**: Starts after T002–T003. T016–T018 (tests) fully parallel. T019–T026 sequential where noted.
- **US3 (P3)**: T027–T029 (tests) fully parallel from Phase 1. T030–T033 independent of US1 and US2.

### Within Each User Story

- **TDD order**: Tests (T_xx) MUST be written and confirmed failing before implementation
- **US1**: `Optional` migration (T006–T011) → cli fixes (T012) → notebook fixes (T013) → exclusion removal (T014) → verify (T015)
- **US2**: Schema (T002–T003) → tests (T016–T018) → service (T019) → config (T020) → wiring (T021) → routes (T022–T023) → counter updates (T024–T025) → user creation (T026)
- **US3**: Tests (T027–T029) → dead code (T030) → VFS fix (T031) → docstring (T032) → trace guard (T033)

### Parallel Opportunities

```bash
# Phase 3 (US1) — all Optional migrations in parallel:
Task T006: supernote/server/services/vfs.py
Task T007: supernote/server/services/coordination.py
Task T008: supernote/server/services/schedule.py
Task T009: supernote/server/services/processor.py
Task T010: remaining supernote/server/ files
Task T011: supernote/models/ + supernote/client/

# Phase 4 (US2) — all tests in parallel:
Task T016: tests/server/services/test_cleanup.py
Task T017: tests/server/routes/test_upload_quota.py
Task T018: tests/server/services/test_user_quota.py

# Phase 5 (US3) — all tests in parallel:
Task T027: tests/server/services/test_vfs.py (delete_node)
Task T028: tests/server/services/test_vfs.py (copy_node)
Task T029: tests/server/test_trace_redaction.py

# Phase 6 — all validations in parallel:
Task T034: pytest
Task T035: mypy
Task T036: lint
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: T001 (error inventory)
2. Complete Phase 3: T004–T015 (full type safety)
3. **STOP and VALIDATE**: `./script/run-mypy.sh` exits 0, all tests pass
4. This alone closes the highest-risk constitution gap (Principle IV)

### Incremental Delivery

1. Phase 1 + Phase 2 → inventory and schema ready
2. Phase 3 (US1) → type safety clean → validate independently
3. Phase 4 (US2) → security gaps closed → validate with quickstart.md US2 steps
4. Phase 5 (US3) → hygiene complete → validate with quickstart.md US3 steps
5. Phase 6 → final sign-off

### Parallel Team Strategy

With multiple developers:
- Dev A: US1 (T001, then T006–T015)
- Dev B: Phase 2 schema + US2 tests (T002–T003, T016–T018) in parallel with Dev A
- Dev C: US3 tests (T027–T029) in parallel with both
- Once US1 and Phase 2 complete: Dev B continues US2 implementation (T019–T026)
- Dev C continues US3 implementation (T030–T033) independently

---

## Notes

- `[P]` tasks operate on different files — safe to run in parallel
- TDD is non-negotiable (constitution Principle VI): every test task MUST fail before its implementation task starts
- T014 (remove pyproject.toml exclusions) MUST be the last US1 commit — not the first
- T002–T003 (schema) are foundational for US2 but independent of US1 and US3
- US3 is entirely independent of US1 and US2 — can start at any time after Phase 1
- Commit after each task or logical group; each story phase should be one reviewable PR
