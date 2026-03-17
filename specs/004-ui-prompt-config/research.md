# Research: UI Prompt Configuration

## Decision 1: Prompt Config Storage

**Decision**: New `f_prompt_config` DB table with `(user_id, category, layer)` unique constraint.

**Rationale**: Fits the existing SQLAlchemy asyncio + alembic migration pattern. Per-user rows mean no lock contention; upsert semantics keep the API simple. Server-side prompt files remain untouched as fallback.

**Alternatives considered**: Key-value store via existing `KeyValueDO` (rejected — untyped, no query by category/layer); JSON blob on `UserDO` (rejected — no fine-grained access or per-row indexing).

---

## Decision 2: Prompt Hash Scope

**Decision**: Single SHA-256 hash per page computed over the full composed OCR prompt concatenated with the full composed summary prompt for the note's type. Stored in a new `prompt_hash` column on `NotePageContentDO`.

**Rationale**: Confirmed by clarification Q1. A single hash avoids tracking two separate hashes per page and simplifies the staleness comparison to a single equality check. SHA-256 (already used in `supernote/server/utils/hashing.py`) is appropriate; MD5 is reserved for protocol-compatibility uses.

**Hash input**: `sha256(ocr_prompt_text + "|" + summary_prompt_text)` where each prompt is the fully composed string (common layer + type-specific layer) as it would be sent to the AI.

**Alternatives considered**: Separate OCR hash + summary hash per page (rejected per clarification); hashing only the user-override portion (rejected — does not detect changes to server-side defaults).

---

## Decision 3: Staleness Detection Timing

**Decision**: Lazy — computed at request time. The staleness API endpoint computes the current effective prompt hash and compares against stored `prompt_hash` per page. No DB write on prompt save.

**Rationale**: Confirmed by clarification Q2. Avoids a potentially expensive scan-all-notes operation on every prompt save. The hash computation is a fast in-memory string operation followed by a single DB read (all pages for a file).

**Alternatives considered**: Eager scan on save (rejected — expensive for users with many notes); background async job (rejected — adds complexity and a new task type for marginal benefit given fast lazy computation).

---

## Decision 4: Prompt Resolution Architecture

**Decision**: Introduce `PromptConfigService` which wraps `PromptLoader`. `ProcessorService` is injected with `PromptConfigService` and creates a per-file `prompt_resolver` callable before dispatching. Existing module call sites replace `PROMPT_LOADER.get_prompt(...)` with `prompt_resolver(prompt_id, custom_type)`.

**Rationale**: Minimal invasive change to existing processor modules. The resolver pattern is a clean dependency inversion — modules remain testable in isolation by injecting a mock resolver. `PROMPT_LOADER` singleton is preserved as the fallback inside `PromptConfigService`.

**Alternatives considered**: Pass `user_id` directly into every module method (rejected — bloats signatures, harder to test); replace `PROMPT_LOADER` singleton with a request-scoped service (rejected — processor modules run outside the HTTP request context).

---

## Decision 5: Reprocess Mechanism

**Decision**: Reset `SystemTaskDO` status to PENDING for `OCR_EXTRACTION` and `EMBEDDING_GENERATION` for targeted pages, plus `SUMMARY_GENERATION` at the global level, then enqueue the `file_id` via the existing `ProcessorService` queue. `run_if_needed()` checks for COMPLETED status, so resetting to PENDING causes modules to re-run.

**Rationale**: Reuses the entire existing pipeline with zero changes to the processing flow. Idempotency is preserved. The existing `recover_stalled_tasks` polling loop provides resilience if a reprocess is interrupted.

**Alternatives considered**: A separate reprocess-only code path (rejected — duplicates pipeline logic); marking the page as deleted and re-creating it (rejected — loses existing content during the window before reprocessing completes).

---

## Decision 6: Stale Indicator Location

**Decision**: Note viewer only. A new `GET /api/extended/files/{file_id}/staleness` endpoint is called on FileViewer mount. Stale indicators appear in page headers within the viewer. A note-level Reprocess button appears in the viewer header if `stale_count > 0`.

**Rationale**: Confirmed by clarification Q3. Keeps the file list clean; users who don't care about prompt staleness are not distracted. The viewer is the natural place to see per-page detail.

---

## Decision 7: Pre-feature Notes (No Stored Hash)

**Decision**: `prompt_hash IS NULL` is treated identically to a hash mismatch — the page is stale. Reprocess buttons appear immediately for all such pages on first view after deployment.

**Rationale**: Confirmed by clarification Q5. Consistent with the spec assumption. Users retain full control — nothing is reprocessed automatically.

---

## Decision 8: Note-level Reprocess Scope

**Decision**: Note-level Reprocess queues only pages where `stored_hash != current_hash OR stored_hash IS NULL`. Up-to-date pages are skipped.

**Rationale**: Confirmed by clarification Q4. Avoids wasting AI tokens on pages that don't need it.

---

## Decision 9: Built-in Layer Names

**Decision**: Built-in layers (`common`, `default`, `daily`, `weekly`, `monthly`) are never written to `f_prompt_config` unless the user explicitly overrides them. The UI pre-populates these fields from `GET /api/extended/prompts/defaults` (server file content) for display only.

**Rationale**: Zero behavioural change for users who never open the modal. Existing `PromptLoader` file-based resolution continues to serve all users until they actively save an override.
