# Research: Insights Block Navigation and Live Updates

**Branch**: `014-insights-scroll-autoupdate`
**Date**: 2026-03-20

## Existing Architecture Findings

### Finding 1: SummaryPanel already has page-scroll infrastructure — in the wrong direction

**Decision**: Reuse the existing scroll primitives in SummaryPanel.js, but add the reverse direction (segment click → page scroll in parent).

**Context**: SummaryPanel already auto-scrolls *its own* segment list in response to `activePage` changes from the parent (`scrollAiToPage`, `scrollOcrToPage` — lines 127–145). It tracks segments by `data-ai-segment="${idx}"` and OCR pages by `data-ocr-page="${pageNo}"`. The *parent* (FileViewer.js) tracks page visibility with an IntersectionObserver on elements keyed by `data-page-no="${page.pageNo}"` in `scrollContainerRef`.

**Rationale**: The cleanest addition is a new `navigate-to-page` event emitted from SummaryPanel. FileViewer listens for it and scrolls its own `scrollContainerRef` to the matching `[data-page-no]` element with `scrollIntoView({ behavior: 'smooth' })`. No new props or shared state is needed.

**Alternatives considered**:
- Shared reactive ref passed as prop — adds coupling between components that don't need it.
- Direct DOM query from SummaryPanel — violates component boundaries; SummaryPanel has no reference to the page container.

---

### Finding 2: page_refs are 1-indexed; pageNo in the DOM is also 1-indexed

**Decision**: Use `page_refs` values directly as the scroll target `pageNo` — no index conversion required.

**Context**: Segments store `page_refs` as 1-indexed integers (matching how the AI model emits them). FileViewer renders pages with `data-page-no="${page.pageNo}"` where `pageNo` is also 1-indexed. The `activePage` prop passed to SummaryPanel is 1-indexed. Only `pageIndex` (from OCR endpoint) is 0-indexed.

**Rationale**: Direct use of `page_refs[0]` as the DOM query target eliminates an off-by-one conversion step and matches the existing conventions.

**Alternatives considered**: Converting to 0-indexed internally — unnecessary and introduces a conversion point that must be maintained.

---

### Finding 3: Existing task-status endpoint returns all tasks; filtering by fileId is needed

**Decision**: Add an optional `file_id` query parameter to `GET /api/extended/system/tasks` so the frontend can poll only the tasks relevant to the open file.

**Context**: The existing endpoint returns all recent `SystemTaskDO` rows without filtering. Each task has a `file_id` column. Polling all tasks every few seconds to find those for one file is wasteful and exposes task metadata for other users' files in a multi-user setup.

**Rationale**: A single optional query param is minimal backend work, aligns with the existing typed model approach, and is a correct RBAC boundary (users already can only see their own files). The filter can be done server-side in the existing service layer.

**Alternatives considered**:
- Client-side filter only — works functionally but leaks cross-file task info in the response payload.
- WebSocket / SSE push — would eliminate polling entirely but is a much larger infrastructure change with no existing precedent in this codebase.

---

### Finding 4: Polling is the correct live-update mechanism for this codebase

**Decision**: Poll `GET /api/extended/system/tasks?file_id=<id>` on a 4-second interval while tasks are in PENDING or PROCESSING state, then re-fetch summaries and OCR once all tasks reach a terminal state.

**Context**: The constitution (§ III Async-First) requires background tasks to "expose observable progress via the existing task-monitoring infrastructure." There is no WebSocket or SSE infrastructure. The existing task-monitoring UI (admin panel) already polls. Terminal states are COMPLETED and FAILED.

**Rationale**: 4-second polling is fine-grained enough to feel responsive (SC-003 requires ≤ 5s) while not hammering the server. Polling stops on terminal state or component unmount, so there is no runaway interval.

**Alternatives considered**:
- 1-second polling — unnecessarily frequent for a process that takes tens of seconds.
- Long-polling — no server-side support; would require new infrastructure.

---

### Finding 5: No new database tables or backend models are required

**Decision**: The only backend change is the optional `file_id` query param on the tasks endpoint plus its route handler update. All other changes are frontend-only.

**Context**: Segment data (`page_refs`) is already stored in `SummaryDO.metadata`. Task status is already in `SystemTaskDO`. Both are exposed via existing endpoints. The page DOM elements already carry `data-page-no` attributes.

**Rationale**: Minimal surface area; no migration required; no risk to existing data.

---

### Finding 6: Processing state indicator must follow constitution § VIII

**Decision**: Use the existing amber/warning button class pattern for the processing indicator — it is the only permitted non-action status indicator. For the loading spinner, use `animate-spin rounded-full h-8 w-8 border-b-2 border-black dark:border-white`.

**Context**: Constitution § VIII explicitly reserves amber for "status-driven indicators only (e.g. stale content), never for routine actions." A "processing in progress" state matches this description. Full-size spinner class is mandated verbatim.

**Alternatives considered**: Blue or green spinner — explicitly prohibited by § VIII ("Framework accent colors… MUST NOT be used for interactive controls").

---

## Summary of Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Emit `navigate-to-page` from SummaryPanel; FileViewer scrolls | Clean event boundary, no coupling |
| 2 | Use `page_refs[0]` directly as 1-indexed page target | Already 1-indexed, matches DOM |
| 3 | Add optional `file_id` query param to tasks endpoint | RBAC correctness, reduces payload |
| 4 | Poll every 4 seconds while PENDING/PROCESSING | Matches existing infra, meets SC-003 |
| 5 | No new DB tables or migrations | Already stored in existing models |
| 6 | Amber indicator + mandated spinner classes | Constitution § VIII compliance |
