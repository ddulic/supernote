# Implementation Plan: Constitution Alignment

**Branch**: `001-constitution-alignment` | **Date**: 2026-03-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-constitution-alignment/spec.md`

## Summary

Bring the Supernote Knowledge Hub into full compliance with its v1.1.0 constitution
across three independently deliverable stories:

1. **Type Safety Completion (P1)**: Remove mypy exclusions for `supernote/notebook/`
   and `supernote/cli/`; migrate 104+ `Optional[T]` sites to `T | None` syntax.
2. **Security Gap Closure (P2)**: Implement hourly temp-file TTL cleanup and per-user
   storage quota enforcement (10 GB default, configurable) with a running counter on
   `UserDO`.
3. **Code Hygiene & Observability Safety (P3)**: Remove `CoordinationService._cleanup`
   dead code; document and test `VirtualFileSystem.delete_node` recursive semantics
   and `copy_node` contract; redact note content from trace middleware logs.

## Technical Context

**Language/Version**: Python 3.13+
**Primary Dependencies**: mypy (strict), SQLAlchemy asyncio, aiohttp, mashumaro, pytest + pytest-asyncio
**Storage**: SQLite (aiosqlite) via SQLAlchemy; local filesystem blob storage; alembic migrations
**Testing**: pytest + pytest-asyncio (auto mode); `unittest.mock.patch`; real in-process ephemeral DB
**Target Platform**: Linux server, self-hosted
**Project Type**: Python library + aiohttp web-service
**Performance Goals**: Quota check adds <1 DB read to upload/apply; cleanup task runs hourly off the hot path
**Constraints**: Zero breaking changes to existing API surface or device protocol; all tests pass
**Scale/Scope**: Personal / small-group (1–5 users); single-process asyncio server

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Library-First Architecture | ✅ Pass | All changes confined to `server/` layer; no new layers |
| II. Protocol Fidelity | ✅ Pass | Quota check added at `upload/apply` (existing endpoint, no protocol change); temp cleanup is server-internal |
| III. Async-First Design | ✅ Pass | Cleanup task uses `asyncio.sleep` loop; quota counter updates use async SQLAlchemy sessions |
| IV. Strict Type Safety | ✅ Pass | This story directly resolves the violation; all new code strictly typed |
| V. Observability & Data Privacy | ✅ Pass | FR-012 addresses trace log content leakage; cleanup task logs only file ID + age |
| VI. Test-Driven Development | ✅ Pass | Tests written before implementation for all new functionality (FR-008, FR-010, FR-011) |
| VII. Security | ✅ Pass | Quota enforcement + temp file cleanup close the two open security ROADMAP gaps |

No gate violations. Proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/001-constitution-alignment/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
supernote/
├── notebook/                    # US1: enable mypy coverage
│   ├── parser.py
│   ├── converter.py
│   ├── decoder.py
│   └── ...
├── cli/                         # US1: enable mypy coverage
│   ├── main.py
│   ├── client.py
│   └── ...
├── server/
│   ├── db/
│   │   ├── models/
│   │   │   └── user.py          # US2: add used_capacity column
│   │   └── migrations.py
│   ├── alembic/
│   │   └── versions/            # US2: new migration for used_capacity
│   ├── services/
│   │   ├── coordination.py      # US3: remove _cleanup dead code
│   │   ├── file.py              # US2: add quota check + used_capacity update
│   │   ├── vfs.py               # US3: fix delete_node recursion + document copy_node; US1: Optional → | None
│   │   ├── schedule.py          # US1: Optional → | None
│   │   └── cleanup.py           # US2: new — TempFileCleanupService
│   ├── routes/
│   │   └── file_device.py       # US2: quota rejection at upload/apply
│   ├── app.py                   # US2: register cleanup service startup/shutdown
│   └── utils/
│       └── app.py               # US3: trace middleware note-content redaction
├── models/                      # US1: Optional → | None across all files
└── pyproject.toml               # US1: remove notebook/ and cli/ mypy exclusions

tests/
├── server/
│   ├── services/
│   │   ├── test_cleanup.py      # US2: new — TTL cleanup tests (written first)
│   │   ├── test_user_quota.py   # US2: new — quota enforcement tests (written first)
│   │   └── test_coordination.py # US3: verify _cleanup removal doesn't regress
│   ├── routes/
│   │   └── test_upload_quota.py # US2: new — upload/apply quota rejection tests
│   └── web/
│       └── test_trace_redaction.py  # US3: trace log content tests (written first)
└── notebook/                    # US1: new type-annotated tests as coverage gaps found
```

**Structure Decision**: Single project (existing layout). No new top-level directories.
All new service code goes in `supernote/server/services/`; all new tests mirror that path.

---

## Phase 0: Research

### R1 — mypy error inventory for `supernote/notebook/` and `supernote/cli/`

**Decision**: Enable mypy incrementally by removing the exclusions and running
`script/run-mypy.sh` to capture the full error list before writing any fixes.

**Findings from code audit**:
- `supernote/server/services/vfs.py` line 2: `from typing import Optional` — 1 site
- `supernote/server/services/coordination.py` line 10: `from typing import Optional` — 4 sites
- `supernote/server/services/schedule.py` lines 1, 117: `Optional`, `Any`, `List` from typing — multiple sites
- `supernote/server/services/processor.py` lines 4-5: `List`, `Set` from typing — multiple sites
- Pattern: nearly all `Optional` usages import from `typing` rather than using bare `| None`

**Rationale**: Fix owned code first (all `server/`, `models/`, `client/`), then tackle
`notebook/` and `cli/`. For `notebook/`, which is a fork of `supernote-tool`, allow
targeted `# type: ignore[<code>]` with justification comments for inherited parsing logic
where a type fix would require understanding upstream binary-format semantics.

**Alternatives considered**:
- Blanket `# type: ignore` per file — rejected (constitution prohibits blanket ignores)
- `--ignore-missing-imports` flag — already configured; not relevant here

---

### R2 — Quota enforcement integration point

**Decision**: Enforce quota at `POST /api/file/3/files/upload/apply` (device) and
`POST /api/file/upload/apply` (web), before generating the signed upload URL.
Track used storage as a `used_capacity` integer column on `UserDO`.

**Findings from code audit**:
- `UserDO` already has `total_capacity: Mapped[str]` (stored as string, default 10 GB)
- `UserDO` has NO `used_capacity` field — needs schema migration
- `VFS.create_file` has `# Check quota (TODO: Implement Capacity check)` comment at line 102
- `VFS.get_total_usage()` exists (lines 495–504) and computes usage by summing file sizes
  — useful for the initial migration reconciliation, not for hot-path checks
- The upload apply handlers call into `FileService` to generate a signed URL; quota
  check must happen before the signed URL is issued

**Rationale**: Checking at apply-step (before data transfer) satisfies FR-006 and
avoids wasting bandwidth on a doomed upload. A running counter on `UserDO` (incremented
at upload finish, decremented at delete) is O(1) per check, consistent with the
clarified data model. An alembic migration will add `used_capacity` with a default of 0
and a reconciliation step to populate it from existing file sizes.

**Alternatives considered**:
- Compute-on-demand via `VFS.get_total_usage()` — rejected for quota checks (full table
  scan on every upload), but retained for admin reporting and reconciliation
- Separate quota ledger table — rejected (adds complexity without benefit at this scale)

---

### R3 — Temp file cleanup service design

**Decision**: Implement `TempFileCleanupService` as a standalone `asyncio` background
service following the `ProcessorService` pattern (start/stop with `asyncio.Task` +
shutdown event). It runs on a configurable interval (default: 3600 s) and removes blob
chunks (`{path}.part.{n}`) older than a configurable TTL (default: 86400 s).

**Findings from code audit**:
- Chunk files are stored as `{object_name}.part.{part_number}` keys in `USER_DATA_BUCKET`
  via `get_file_chunk_path()` in `supernote/server/utils/paths.py`
- `LocalBlobStorage` stores files in `{storage_root}/{bucket}/{key}` on the filesystem
  with standard `mtime` available — no separate DB record for chunk timestamps needed
- `ProcessorService` provides the pattern: `asyncio.Task` workers, `asyncio.Event` for
  shutdown, `start()` / `stop()` lifecycle methods registered in `app.on_startup` /
  `app.on_shutdown`
- An "active upload" is one whose signed URL nonce has not yet been consumed in
  `CoordinationService`. However, to avoid coupling cleanup to the nonce store, the
  simpler safe heuristic is: file mtime < (now - TTL) → orphaned

**Rationale**: Using filesystem `mtime` avoids a new DB table, is robust against server
restarts (mtime survives), and is already available through `aiofiles` / `asyncio.to_thread`.
The TTL (24 h) is large enough that any legitimate slow upload completes well within it.

**Alternatives considered**:
- DB-tracked `TempUploadDO` with explicit apply-record — richer but adds schema change;
  deferred because mtime-based cleanup is sufficient for the stated safety requirements
- Event-driven cleanup on abandoned upload — rejected (no reliable abandon signal in
  the protocol; device may retry without notifying the server)

---

### R4 — Dead code in CoordinationService

**Decision**: Remove `SqliteCoordinationService._cleanup()` (lines 56–59). It is a
stub with a pass body and an inline comment acknowledging it is unused. The lazy
expiry-on-access in `get_value()` and `increment()` already handles expired key
cleanup adequately for the server's scale.

**Findings from code audit**: `_cleanup` is a private method that is never called
from any site in the codebase (grep confirms 0 call sites).

**Alternatives considered**: Implement periodic cleanup of expired KV rows — deferred
as a separate operational improvement; not required for this story.

---

### R5 — VFS.delete_node recursive semantics

**Decision**: The existing `delete_node` implementation (lines 149–173 in `vfs.py`)
already soft-deletes a single node correctly (sets `is_active = "N"`, creates
`RecycleFileDO`). The TODO comment refers to recursive folder deletion. The contract
to implement and document: when `delete_node` is called on a folder, all active
children MUST be soft-deleted atomically in the same transaction.

**Findings from code audit**:
- `delete_node` currently marks only the top-level node; children remain active (`is_active = "Y"`)
  with an orphaned `directory_id` — this is the bug the TODO refers to
- `list_recursive()` already walks the full tree (lines 66–88) and can be reused
- The processor pipeline holds a `Set[int]` of `processing_files` file IDs; a file
  being processed when `delete_node` is called would be soft-deleted in the DB but
  the processor would continue working on the cached data and eventually write results
  to `NotePageContentDO` — this is safe (stale processing result is harmless) and
  requires no locking

**Alternatives considered**: Hard delete with cascade — rejected (breaks recycle bin
invariant and would lose data if delete is accidental)

---

### R6 — Trace middleware note-content redaction

**Decision**: Add a content-type guard in `trace_middleware` (`app.py`) so that
response bodies whose `Content-Type` is `application/json` AND whose route path
matches known OCR/synthesis result patterns (e.g., `/api/file/insights`,
`/api/summary`) are replaced with `"<note-content redacted>"` in the trace log.
Binary note bodies (`application/octet-stream`, already guarded by `is_binary_content_type`)
are already excluded.

**Findings from code audit**:
- `app.py` lines 113–121: binary content types are already replaced with `<binary data>`
- JSON responses from insight/summary endpoints contain OCR text — currently logged in full
- The trace log is opt-in (requires `config.trace_log_file` to be set); risk is low but
  the constitution requires the invariant unconditionally

**Alternatives considered**: Redact all JSON response bodies — rejected (would make
trace log useless for protocol debugging, per the spec assumption)

---

## Phase 1: Design & Contracts

### Data Model

See [`data-model.md`](data-model.md).

### API Contracts

No new public API endpoints. Changes to existing endpoints are additive error responses
(quota exceeded → 507 Insufficient Storage). See [`contracts/quota-enforcement.md`](contracts/quota-enforcement.md).

### Agent Context

Updated via `.specify/scripts/bash/update-agent-context.sh claude` after this plan.

---

## Complexity Tracking

No constitution violations requiring justification. All changes are minimal,
contained within existing layer boundaries, and follow existing patterns.
