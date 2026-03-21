# Tasks: Insights Block Navigation and Live Updates

**Input**: Design documents from `/specs/014-insights-scroll-autoupdate/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Exact file paths included in every task description

---

## Phase 1: Setup

**Purpose**: Confirm dev environment baseline before any changes.

- [x] T001 Verify dev environment is working — run `./script/test` and confirm all existing tests pass, then run `./script/server` and confirm the file viewer loads

**Checkpoint**: Dev environment confirmed — user story implementation can begin

---

## Phase 2: User Story 1 — Block Click Navigation (Priority: P1) 🎯 MVP

**Goal**: Clicking an AI summary segment block navigates the note page viewer to the referenced page without a page reload.

**Independent Test**: Open a note with an existing AI summary (at least one segment with page_refs). Click a segment card — the page viewer must scroll smoothly to the referenced page. Click a segment with no page refs — nothing must happen and no error must appear.

> **Note**: US1 is pure frontend — no backend changes required. US2 can be worked in parallel.

### Implementation for User Story 1

- [x] T002 [US1] Add `navigate-to-page` to the `emits` array in `supernote/server/static/js/components/SummaryPanel.js` (emits declaration near top of component)
- [x] T003 [US1] Add click handler on AI segment card elements in the template — when `segment.pageRefs.length > 0`, emit `navigate-to-page` with `{ pageNo: segment.pageRefs[0] }` — in `supernote/server/static/js/components/SummaryPanel.js` (AI tab segment rendering, around line 231)
- [x] T004 [US1] Add `cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors` classes to segment cards conditionally when `pageRefs.length > 0`; leave non-navigable cards without cursor or hover changes — in `supernote/server/static/js/components/SummaryPanel.js`
- [x] T005 [US1] Add `@navigate-to-page="onNavigateToPage"` listener on the `<summary-panel>` element and implement `onNavigateToPage({ pageNo })` method: query `scrollContainerRef.value.querySelector('[data-page-no="' + pageNo + '"]')` and call `.scrollIntoView({ behavior: 'smooth', block: 'start' })` — in `supernote/server/static/js/components/FileViewer.js` (integration around line 268)

**Checkpoint**: US1 fully functional. Block click scrolls page viewer. No-ref blocks do nothing. Can demo independently.

---

## Phase 3: User Story 2 — Live Processing Updates (Priority: P2)

**Goal**: SummaryPanel auto-detects when note processing completes and refreshes its content, eliminating the need to reload the page.

**Independent Test**: Upload a note, immediately open the file viewer. The Insights panel shows a processing indicator (amber banner + spinner). Wait without refreshing — panel populates automatically when processing finishes. If processing fails, the spinner disappears and a static notice appears instead.

### Backend: Tasks Endpoint Extension (TDD — tests before implementation)

- [x] T006 [US2] ~~Write failing tests for the optional `file_id` query parameter~~ — **superseded**: used existing `fetchProcessingStatus` endpoint instead; no backend changes required
- [x] T007 [US2] ~~Implement optional `file_id` query parameter~~ — **superseded**: no backend changes needed
- [x] T008 [US2] ~~Verify backend coverage~~ — **superseded**: no backend changes; 829 existing tests pass

### Frontend: API Client Update

- [x] T009 [P] [US2] ~~Add `fetchSystemTasksForFile(fileId)`~~ — **superseded**: imported existing `fetchProcessingStatus` from client.js directly into SummaryPanel.js; no new client function needed

### Frontend: Polling State Machine

- [x] T010 [US2] Add `processingState` reactive data property (`'idle' | 'polling' | 'done' | 'failed'`, default `'idle'`) and `pollTimer` ref (default `null`) to the SummaryPanel component options — in `supernote/server/static/js/components/SummaryPanel.js`
- [x] T011 [US2] Implement `checkProcessingState()` async method — call `fetchSystemTasksForFile(fileId)`, filter tasks to those matching `props.fileId`, determine if any are `PENDING` or `PROCESSING` (in-progress) vs all in `COMPLETED`/`FAILED` (terminal), set `processingState` accordingly — in `supernote/server/static/js/components/SummaryPanel.js`
- [x] T012 [US2] Implement `startPolling()` — call `checkProcessingState()` immediately, then schedule `setInterval` at 4000ms; on each tick if state is terminal: clear the interval, re-fetch summaries and OCR (call existing fetch methods), update `processingState` to `'done'` or `'failed'`; if still in progress: continue — in `supernote/server/static/js/components/SummaryPanel.js`
- [x] T013 [US2] Implement `stopPolling()` — call `clearInterval(pollTimer)` and reset `pollTimer = null` — in `supernote/server/static/js/components/SummaryPanel.js`
- [x] T014 [US2] Wire polling into component lifecycle: call `startPolling()` at the end of `onMounted` (after initial summary/OCR fetch), call `stopPolling()` in `onUnmounted` — in `supernote/server/static/js/components/SummaryPanel.js`

### Frontend: Processing Indicator UI

- [x] T015 [US2] Add processing indicator to AI tab template — shown when `processingState === 'polling'` — in `supernote/server/static/js/components/SummaryPanel.js`
- [x] T016 [P] [US2] Add identical processing indicator to OCR tab template — in `supernote/server/static/js/components/SummaryPanel.js`
- [x] T017 [P] [US2] Add failed state notice to both AI and OCR tabs — in `supernote/server/static/js/components/SummaryPanel.js`

**Checkpoint**: US2 fully functional. Panel shows processing state and auto-refreshes. No page reload required.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates, dark mode audit, and manual acceptance validation.

- [x] T018 [P] Audit all new template elements in `supernote/server/static/js/components/SummaryPanel.js` — confirm every new `bg-`, `text-`, and `border-` class has a matching `dark:` variant per constitution § VIII; fix any missing dark mode variants
- [ ] T019 [P] Manual acceptance test for US1 — follow each acceptance scenario in spec.md §US1: click a block with page refs (verify scroll), click a block with multiple refs (verify first page), click a block with no refs (verify nothing happens), click a block already in view (verify page stays visible)
- [ ] T020 [P] Manual acceptance test for US2 — follow each acceptance scenario in spec.md §US2: upload a note and immediately view it (verify amber indicator appears), wait for processing completion (verify panel populates without reload), simulate failure if possible (verify spinner stops and notice appears)
- [x] T021 Run `./script/lint` and `./script/run-mypy.sh` — confirm zero errors and zero type violations
- [x] T022 Run `./script/test` — confirm 100% line coverage on all changed files in `supernote/server/routes/extended.py` and `tests/server/routes/test_extended.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **US1 (Phase 2)**: Depends on Phase 1 only — **does NOT depend on backend changes**
- **US2 (Phase 3)**: Depends on Phase 1; backend subtasks (T006–T008) must precede frontend subtasks (T009–T017)
- **Polish (Phase 4)**: Depends on US1 and US2 being complete

### User Story Dependencies

- **US1 (P1)**: Fully independent — pure frontend, no backend required
- **US2 (P2)**: Independent of US1 — shares `SummaryPanel.js` but in different methods/template sections

### Within US2

- T006 (write failing tests) → T007 (implement) → T008 (verify coverage) — sequential per TDD
- T009 (API client) can run in parallel with T006–T008 (different file)
- T010–T014 (state machine) must run after T009 (depends on fetchSystemTasksForFile)
- T015–T017 (UI indicators) can run in parallel with T010–T014 (different section of same file)

---

## Parallel Execution Examples

### US1 (all tasks in sequence — single developer, ~1 hour)

```
T002 → T003 → T004 → T005
(SummaryPanel emits → SummaryPanel click → SummaryPanel styling → FileViewer handler)
```

### US2 Backend + API Client in parallel

```
[T006 → T007 → T008]   # Backend TDD cycle (extended.py)
[T009]                  # API client function (client.js) — parallel, different file
```

### US2 Frontend state machine + UI in parallel (after T009)

```
[T010 → T011 → T012 → T013 → T014]   # State machine wiring
[T015, T016, T017]                    # UI indicators (parallel with each other)
```

---

## Implementation Strategy

### MVP First (US1 Only — ~4 tasks, ~1 hour)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: US1 (T002–T005)
3. **STOP and validate**: Test block click navigation manually per spec acceptance scenarios
4. Demo or ship US1 independently

### Incremental Delivery

1. T001: Setup → baseline confirmed
2. T002–T005: US1 complete → block navigation works → demo
3. T006–T017: US2 complete → live updates work → demo
4. T018–T022: Polish → all gates pass → merge

### Parallel Team Strategy (2 developers)

Once T001 is done:
- **Developer A**: US1 (T002–T005) — pure frontend
- **Developer B**: US2 backend (T006–T008) and API client (T009) — backend + client.js

After both finish, merge and Developer A takes US2 frontend (T010–T017).

---

## Notes

- [P] tasks touch different files or independent sections — safe to parallelise
- Constitution § VI mandates TDD: T006 (write failing tests) MUST precede T007 (implement) — do not skip this order
- Constitution § VIII: all amber indicator classes in T015–T017 must be used verbatim; do not substitute other colors
- SummaryPanel.js is modified by both US1 (T002–T004) and US2 (T009–T017) — complete US1 tasks before starting US2 frontend tasks to avoid merge conflicts within the file, OR work on clearly separated sections simultaneously
- Commit after each checkpoint to keep history clean
