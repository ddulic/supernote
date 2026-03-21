# Feature Specification: Insights Block Navigation and Live Updates

**Feature Branch**: `014-insights-scroll-autoupdate`
**Created**: 2026-03-20
**Status**: Draft
**Input**: User description: "when I click on a block in insights, it should scroll down to the related note page. update insights when processing is done so I dont have to refresh the page"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Click Block to Navigate to Note Page (Priority: P1)

A user is viewing a note file with the Insights panel open. The AI Summary tab shows blocks (segments), each linked to one or more note pages. When the user clicks a block, the note page viewer smoothly scrolls to the first note page referenced by that block, making it immediately visible.

**Why this priority**: This is the primary navigation request. Users can already read summaries but cannot jump to the source content. This closes that gap and is independently usable from live updates.

**Independent Test**: Open a note with an existing AI summary that has segments with page references. Click a segment block and verify the page viewer scrolls to the correct page. Delivers full value without the auto-update feature.

**Acceptance Scenarios**:

1. **Given** a note file is open and the Insights panel displays AI summary blocks with page references, **When** the user clicks any block, **Then** the note page viewer scrolls to the first page referenced in that block, and that page is clearly in view.
2. **Given** a block references multiple pages, **When** the user clicks that block, **Then** the viewer scrolls to the first (lowest-numbered) referenced page.
3. **Given** a block has no page references, **When** the user clicks that block, **Then** nothing happens (no scroll), and no error is shown.
4. **Given** the user clicks a block that references a page already in view, **When** the scroll completes, **Then** the page remains visible (no unnecessary jump).

---

### User Story 2 - Insights Panel Auto-Updates After Processing (Priority: P2)

A user uploads a note or opens a note whose processing is still in progress. While they wait on the file viewer page, the Insights panel automatically populates with AI summary and OCR content once processing finishes — without requiring a page refresh.

**Why this priority**: Eliminates a key friction point where users must manually reload to see newly generated insights. Depends on no other feature and can be demonstrated independently.

**Independent Test**: Open a note that is currently being processed. Wait for processing to complete. Verify the Insights panel shows new content without any manual refresh. Delivers clear value without the block-click navigation.

**Acceptance Scenarios**:

1. **Given** a note is being processed and the Insights panel shows a loading or "processing" state, **When** processing completes successfully, **Then** the Insights panel automatically displays the newly generated AI summary and OCR content within a few seconds.
2. **Given** the Insights panel is already showing content for a note, **When** the note is re-processed (e.g., after update), **Then** the panel refreshes and shows updated content without a page reload.
3. **Given** processing fails for a note, **When** the failure is detected, **Then** the Insights panel shows an appropriate error or empty state — no perpetual loading indicator.
4. **Given** the user navigates away from the file viewer before processing completes, **When** they return to the same note later, **Then** the completed insights are shown immediately on load (standard load behavior, no polling needed).

---

### Edge Cases

- What happens when a block's referenced page index is out of range (e.g., page was deleted after the summary was generated)?
- How does the system behave if an insights update arrives while the user is actively scrolling?
- What if insights finish processing for one file while the user has already navigated to a different file in the same session?
- What if the network connection drops while waiting for a processing update?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When a user clicks an AI summary block in the Insights panel, the note page viewer MUST scroll to the first note page referenced by that block.
- **FR-002**: The scroll behavior MUST be smooth and bring the target page into view without abrupt jumps.
- **FR-003**: Blocks with no page references MUST be non-navigable — clicking them produces no scroll action and no error.
- **FR-004**: The Insights panel MUST automatically detect when note processing completes for the currently viewed file.
- **FR-005**: When note processing completes, the Insights panel MUST update its displayed content (both AI summary and OCR tabs) without requiring the user to reload the page.
- **FR-006**: While a note is being processed, the Insights panel MUST display a visible indicator (e.g., loading state or "processing" message) so the user knows content is incoming.
- **FR-007**: If processing fails, the Insights panel MUST transition from loading state to an appropriate empty or error state rather than loading indefinitely.
- **FR-008**: Live updates MUST only apply to the currently viewed note file; updates for other files MUST be ignored.

### Key Entities

- **Insight Block (Segment)**: A unit of AI summary content tied to a date range and one or more note page references. Clicking it triggers navigation.
- **Note Page**: A single page within a .note file, rendered visually in the file viewer. Pages are identified by their position index.
- **Processing Task**: A background job that generates AI summaries and OCR content for a note file. Has statuses: pending, processing, completed, failed.
- **Insights Panel**: The side panel in the file viewer displaying AI and OCR tabs. Manages both block navigation and live content updates.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of clicked blocks with valid page references navigate the viewer to the correct note page.
- **SC-002**: Navigation scroll completes and the target page is in view within 1 second of the user clicking a block.
- **SC-003**: Newly generated insights appear in the panel within 5 seconds of processing completion, without any user action.
- **SC-004**: Zero manual page reloads are required by the user to see insights after processing finishes.
- **SC-005**: A processing indicator is visible at all times while background processing is in progress, so users are never left guessing whether content will appear.

## Assumptions

- "Blocks" refers to AI summary segments, each of which already carries page reference data identifying which note pages the summary content is drawn from.
- The note page viewer already renders pages in a scrollable list; the scroll target is identifiable by page index.
- Background processing status is queryable from the frontend via an existing task-status endpoint; polling is the assumed mechanism since no real-time push infrastructure is evident in the codebase.
- The polling interval for processing status is reasonable (e.g., every 3–5 seconds) and stops once processing reaches a terminal state (completed or failed).
- Auto-update applies only to the AI summary and OCR content in the Insights panel; no other UI state is affected.
- Only the currently open file's processing status is polled; there is no need to track multiple files simultaneously.
