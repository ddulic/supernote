# Feature Specification: Constitution Alignment

**Feature Branch**: `001-constitution-alignment`
**Created**: 2026-03-15
**Status**: Draft
**Input**: User description: "make sure the current project is aligning with the constitution"

## Clarifications

### Session 2026-03-15

- Q: How frequently should the background temp-file cleanup task run? → A: Fixed schedule, configurable interval (default: every hour)
- Q: How should used-storage be tracked for quota enforcement? → A: Running counter on the user record — incremented on upload finish, decremented on delete
- Q: What is the default per-user storage quota? → A: Fixed default (10 GB) applied to all new users; overridable via server configuration / environment variable
- Q: How should mypy errors in forked/inherited code in supernote/notebook/ be handled? → A: Fix all errors in owned code; targeted `# type: ignore[code]` with mandatory justification comment allowed only in forked/inherited code

## Overview

This specification describes the work required to bring the Supernote Knowledge Hub
codebase into full alignment with its v1.1.0 constitution. A gap analysis was
performed against all seven core principles. Three areas of non-compliance were
identified, ranked by severity and risk to users.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Type Safety Completion (Priority: P1)

A developer working in the `notebook` or `cli` modules today receives no type-checking
feedback — those modules are explicitly excluded from the project's strict type-checking
configuration. As a result, type errors can be introduced silently and only surface at
runtime. Additionally, 104 places in the `server` module use a legacy type annotation
style that the constitution explicitly prohibits.

A developer making a contribution to the notebook parser or CLI MUST receive the same
type-checking guarantees as the rest of the codebase, and all code MUST use the modern
annotation syntax consistently.

**Why this priority**: Type errors in the notebook parser translate directly to corrupt
output (PDF/PNG/SVG conversion failures). Type errors in the CLI translate to incorrect
user-facing behavior. This is the highest-risk compliance gap — the constitution marks
Strict Type Safety (Principle IV) as non-negotiable.

**Independent Test**: Can be validated in isolation by running the type checker across
the full codebase and observing zero errors, independent of all other stories.

**Acceptance Scenarios**:

1. **Given** the type checker is run against the entire `supernote/` package,
   **When** it completes,
   **Then** it reports zero errors with no modules excluded.

2. **Given** a developer adds a function to `supernote/notebook/` with a missing
   return type annotation,
   **When** the type checker runs in CI,
   **Then** the PR is blocked with a type error.

3. **Given** any file in `supernote/server/` or `supernote/models/`,
   **When** it is reviewed for annotation style,
   **Then** zero occurrences of the legacy `Optional[T]` form exist — all use `T | None`.

4. **Given** any new or modified test function introduced by this work,
   **When** it is reviewed,
   **Then** it carries explicit type annotations on all parameters and return values.

---

### User Story 2 - Security Gap Closure (Priority: P2)

Two security-relevant gaps remain open on the ROADMAP that directly affect
the constitution's Security principle (Principle VII): stale temporary upload files
are never cleaned up, and per-user storage quotas are not enforced. Both create
risk for operators running the server as a personal daily-driver.

An operator running the server for months MUST NOT accumulate gigabytes of abandoned
partial uploads in `storage/temp`. A user granted a storage allocation MUST NOT be
able to exceed it by uploading more files than their quota allows.

**Why this priority**: Stale temp files are a storage-exhaustion vector; unenforced
quotas mean per-user isolation — already a completed ROADMAP goal — is only partially
effective. Both affect the server's fitness for personal data that the user cannot
afford to lose.

**Independent Test**: Can be validated independently: (a) upload a file, abandon the
session before finishing, wait for the TTL to elapse, confirm the temp file is gone;
(b) upload files past a configured quota limit and confirm the server rejects the
request before accepting any data.

**Acceptance Scenarios**:

1. **Given** a partial upload is started but never finished,
   **When** more than the configured TTL has elapsed,
   **Then** a background cleanup task removes the temp file and its associated record.

2. **Given** a user has a configured storage quota,
   **When** they attempt to upload a file that would cause them to exceed that quota,
   **Then** the server rejects the upload with a clear quota-exceeded error before
   accepting any file data.

3. **Given** a user is at exactly their quota limit,
   **When** they delete a file,
   **Then** their used capacity decreases and a subsequent upload within the freed
   space succeeds.

4. **Given** the background cleanup task removes a stale temp file,
   **When** it logs the removal,
   **Then** the log line contains the file identifier and age but MUST NOT contain
   any note content or user data beyond the user identifier.

---

### User Story 3 - Code Hygiene & Observability Safety (Priority: P3)

Three lower-priority gaps affect long-term maintainability and the Observability
& Data Privacy principle (Principle V):

- The `CoordinationService` contains dead code flagged for removal on the ROADMAP,
  creating confusion about what contracts are active.
- The `VirtualFileSystem.soft_delete` and recursive copy operations are marked with
  TODOs and their intended API contract is undefined, making safe use impossible.
- The trace middleware logs raw request bodies without filtering for note content,
  which is a potential violation of the principle that note content MUST NOT appear
  in any log.

A developer modifying the VFS or coordination layer MUST have clear, documented,
tested semantics to work against. An operator enabling trace logging MUST be able
to trust that handwritten note content will never appear in their log files.

**Why this priority**: The dead code and undefined semantics are a maintainability
risk but not an immediate user-facing defect. The trace logging risk is real but is
currently mitigated by trace logging being opt-in and disabled by default.

**Independent Test**: (a) Remove dead code and confirm the full test suite passes
with zero regressions. (b) Enable trace logging, trigger a note processing cycle,
and confirm the trace log contains zero readable note text.

**Acceptance Scenarios**:

1. **Given** the `CoordinationService` dead code is removed,
   **When** the full test suite runs,
   **Then** all tests pass with no regressions and no tests are removed to achieve this.

2. **Given** `VirtualFileSystem.soft_delete` is called on a file,
   **When** the operation completes,
   **Then** the file is present in the recycle bin and absent from the active file
   listing — it is not hard-deleted.

3. **Given** `VirtualFileSystem.soft_delete` is called while the background processor
   is actively working on the same file,
   **When** both operations complete,
   **Then** neither operation corrupts data and no unhandled error is raised.

4. **Given** trace logging is enabled and a sync cycle processes a `.note` file,
   **When** the trace log is inspected,
   **Then** raw note binary content and OCR text output are absent from all
   request and response body log entries.

5. **Given** `VirtualFileSystem` recursive copy is invoked on a directory with
   nested sub-directories,
   **When** it completes,
   **Then** the full directory tree is duplicated correctly under the target path.

---

### Edge Cases

- What if the TTL cleanup runs while a slow-but-valid upload is in progress? The
  cleanup MUST NOT remove temp files younger than the configured TTL, regardless
  of whether a finish record exists.
- What if quota enforcement is introduced and existing users already exceed the new
  quota? The migration MUST be non-destructive — existing files MUST NOT be deleted,
  but further uploads MUST be blocked until the user is within their quota.
- What if `soft_delete` is called on a directory that contains files currently being
  processed? All children MUST be soft-deleted atomically or the operation MUST fail
  cleanly — partial soft-deletes are not acceptable.
- What if fixing mypy errors in `supernote/notebook/` reveals a genuine bug? The bug
  MUST be fixed (not suppressed), with a test written before the fix, following
  Principle VI.

## Requirements *(mandatory)*

### Functional Requirements

**Type Safety — Principle IV**

- **FR-001**: The type checker MUST cover `supernote/notebook/` and `supernote/cli/`
  with zero errors and zero blanket module-level ignores. In code owned by this
  project, all errors MUST be fixed. In forked or inherited code (e.g., parser logic
  derived from `supernote-tool`), targeted `# type: ignore[<error-code>]` suppressions
  are permitted provided each is accompanied by a justification comment explaining
  why a fix would be unsafe or speculative.
- **FR-002**: All annotation sites using `Optional[T]` in `supernote/server/` and
  `supernote/models/` MUST be migrated to `T | None` syntax.
- **FR-003**: All new and modified test functions and fixtures introduced by this work
  MUST carry explicit type annotations on all parameters and return values.

**Security Gap Closure — Principle VII**

- **FR-004**: The server MUST run a background cleanup task on a fixed, configurable
  schedule (default: every hour) that removes files from `storage/temp` older than
  a configurable TTL (default: 24 hours).
- **FR-004a**: The cleanup interval MUST be independently configurable from the TTL
  (e.g., run every hour, but only remove files older than 24 hours).
- **FR-005**: The cleanup task MUST NOT remove temp files belonging to upload sessions
  that are still active (i.e., whose apply-record is younger than the TTL).
- **FR-006**: Upload requests that would cause a user to exceed their storage quota
  MUST be rejected at the apply step, before any data is transferred.
- **FR-006a**: New users MUST be assigned a default quota of 10 GB. The server-wide
  default MUST be overridable via a server configuration value or environment variable.
  Individual user quotas MAY be further overridden by an admin on a per-user basis.
- **FR-007**: File deletion MUST atomically decrement the user's used-storage counter
  so that quota headroom is accurately maintained.
- **FR-008**: Every acceptance scenario in User Story 2 MUST be covered by a test
  written before the corresponding implementation.

**Code Hygiene & Observability — Principles III, V**

- **FR-009**: Dead code in `CoordinationService` identified on the ROADMAP MUST be
  removed; the test suite MUST pass after removal.
- **FR-010**: `VirtualFileSystem.soft_delete` MUST be documented with an explicit
  contract: files moved to recycle bin (not hard-deleted), safe for concurrent use
  with the processor pipeline, covered by tests written before implementation.
- **FR-011**: `VirtualFileSystem` recursive copy MUST be documented with an explicit
  contract covering nested directory trees, covered by tests written before
  implementation.
- **FR-012**: The trace middleware MUST NOT include raw note binary content or OCR
  text output in logged request or response bodies.

### Key Entities

- **TempUploadRecord**: An in-progress upload with a creation timestamp; used to
  distinguish live uploads from abandoned ones during TTL cleanup.
- **UserStorageQuota**: The allocated and used storage capacity for a user, stored
  as a running counter on the user record. The used-storage counter MUST be
  incremented atomically on upload finish and decremented atomically on file
  deletion. A periodic reconciliation check MAY be used to detect and correct drift.
- **RecycleFileDO**: The existing soft-delete destination; `soft_delete` MUST route
  files here rather than performing a hard delete from `UserFileDO`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The type checker reports zero errors across the entire `supernote/`
  package with no modules excluded — verified in CI on every PR.
- **SC-002**: Zero occurrences of `Optional[T]` remain in `supernote/server/` or
  `supernote/models/` after migration.
- **SC-003**: A server running for 30 days with active uploads accumulates zero
  orphaned files in `storage/temp` older than the configured TTL.
- **SC-004**: A user who has consumed 100% of their storage quota (default: 10 GB,
  configurable) is unable to upload additional files, and the rejection is returned
  before any data is transferred.
- **SC-005**: The full test suite (300+ tests) continues to pass after dead code
  removal and VFS contract clarification, with zero tests removed to achieve this.
- **SC-006**: An operator who enables trace logging and processes a note file finds
  zero readable note text or binary note data in the resulting trace log.

## Assumptions

- Mypy errors in `supernote/notebook/` will be fixed in code owned by this project.
  Targeted `# type: ignore[<error-code>]` with a justification comment is permitted
  only for forked/inherited code where a fix would be unsafe or speculative. Blanket
  module-level ignores are prohibited. The pyproject.toml exclusion MUST be removed
  in the same commit that resolves the last remaining unfixed error.
- The default temp-file TTL of 24 hours is appropriate for personal/small-group use;
  making it configurable satisfies operators with different operational needs.
- "Dead code in CoordinationService" refers to the items flagged on the ROADMAP; a
  targeted audit will identify the specific symbols before implementation begins.
- Trace middleware body redaction (FR-012) targets note binary payloads and OCR text
  responses specifically — it does not require redacting all request bodies, which
  would make the trace log useless for protocol debugging.
