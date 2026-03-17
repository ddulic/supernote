# Feature Specification: Note Page PNG Caching & Insights Panel Tabs

**Feature Branch**: `005-cache-png-insights-tabs`
**Created**: 2026-03-17
**Status**: Draft
**Input**: User description: "check blob_storage.exists(USER_DATA_BUCKET, png_storage_key) before converting each page, and skip conversion if the blob is already there, update insights panel to have 2 tabs, one (main one) for the AI conversion and the second one for OCR"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fast Repeat Note Loading (Priority: P1)

A user opens a large note they have viewed before. Instead of waiting for all pages to be re-converted from scratch, the pages load immediately because the previously generated images are reused.

**Why this priority**: This is the primary pain point — large notes trigger a full re-conversion on every view even when nothing has changed, causing unnecessary delay and wasted processing. Fixing this delivers immediate, visible performance improvement.

**Independent Test**: Open a large note, wait for it to load, close it, then reopen it. On the second open, the "Converting note..." loading phase should complete significantly faster (or be near-instant if images are already stored).

**Acceptance Scenarios**:

1. **Given** a note has been opened and its page images have been generated and stored, **When** the user opens the same note again without modifying it, **Then** the viewer loads the existing images without re-converting any pages.
2. **Given** a note has been opened previously, **When** the note file is updated (its content hash changes), **Then** the system detects the change and re-converts the pages since the key encodes the hash.
3. **Given** a note's page images are partially stored (some pages cached, some missing), **When** the user opens the note, **Then** only the missing pages are converted and the stored ones are reused.

---

### User Story 2 - View AI Insights and OCR Text for a Note (Priority: P2)

A user opens a note and clicks the AI Insights panel. They see two tabs: "AI" (default, active) showing the AI-generated summary/analysis, and "OCR" showing the raw text extracted from each page.

**Why this priority**: The current panel only surfaces AI summaries. Exposing OCR text directly gives users a way to verify what was extracted from their handwriting and use the raw text independently — without requiring a separate panel.

**Independent Test**: Open any note that has been processed, open the Insights panel, and verify two tabs are shown. Clicking "AI" shows existing summary content; clicking "OCR" shows per-page extracted text.

**Acceptance Scenarios**:

1. **Given** a note has AI summaries available, **When** the user opens the Insights panel, **Then** the "AI" tab is active by default and displays summary content as before.
2. **Given** a note has OCR text available for its pages, **When** the user clicks the "OCR" tab, **Then** the extracted text for each page is displayed, ordered by page number.
3. **Given** a note has no OCR text yet (still processing), **When** the user opens the "OCR" tab, **Then** an appropriate empty/processing state is shown rather than an error.
4. **Given** a note has no AI summaries available, **When** the user opens the "AI" tab, **Then** the existing empty state message is shown.

---

### Edge Cases

- What happens when the stored page image file is missing or unreadable at retrieval time? The system should fall back to re-converting that page.
- What happens if the existence check itself fails due to a storage error? The system MUST treat this as a cache miss and proceed with conversion (fail-open), keeping the user unblocked.
- What if OCR processing has not completed for some pages? Show text for available pages and indicate others are pending.
- What happens if the user switches between tabs rapidly? No duplicate requests or UI flicker should occur.
- What happens when a note has zero pages? Both tabs should show an appropriate empty state.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST check whether a stored page image already exists before converting a note page to an image.
- **FR-002**: The system MUST reuse the existing stored image when one is found, skipping the conversion step for that page.
- **FR-003**: The system MUST convert and store a new image only when no stored image exists for a given page at the expected storage location.
- **FR-004**: When a note's content changes (detected via file hash embedded in the storage key), the system MUST generate new images since the storage key will differ.
- **FR-004a**: When new page images are stored for an updated note, the system MUST delete any previously stored page images for that note that belong to the old content version (old hash).
- **FR-005**: The AI Insights panel MUST display two tabs: "AI" (primary/default) and "OCR".
- **FR-006**: The "AI" tab MUST display the same AI-generated summary content currently shown in the panel, with no regression in existing behaviour.
- **FR-007**: The "OCR" tab MUST display the raw text extracted from each page of the note, ordered by page number.
- **FR-008**: The "OCR" tab MUST show an appropriate empty or pending state when no OCR text is available for the note.
- **FR-009**: The "AI" tab MUST be the active/selected tab when the panel is first opened.
- **FR-010**: Tab selection MUST reset to "AI" when the panel is closed and reopened or when a different file is selected.

### Key Entities

- **Note Page Image**: A rendered image of a single note page, keyed by file ID, page index, and file content hash. Its presence in storage determines whether re-conversion is needed.
- **OCR Page Text**: The raw text extracted from a single note page, associated with a page index and the note file, displayed in the OCR tab ordered by page number.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Reopening a previously viewed, unchanged note displays all pages at least 80% faster compared to the first open.
- **SC-002**: Zero page conversions occur when a user reopens a note whose content has not changed since the last view.
- **SC-003**: The Insights panel shows two clearly labelled tabs ("AI" and "OCR") on every note that has been opened.
- **SC-004**: Users can read the OCR text for any processed note page directly from the Insights panel without navigating away from the note viewer.
- **SC-005**: The "AI" tab content is identical to the existing panel behaviour — no regression in displayed summaries.

## Clarifications

### Session 2026-03-17

- Q: When a note's content changes and new images are stored, should old-hash cached images be deleted immediately or left to accumulate until note deletion? → A: Delete old-hash page images for a note when new images are stored for a new content version.
- Q: Should the new OCR endpoint return all pages in a single response or reuse the existing summary endpoint filtered by type? → A: New dedicated endpoint returning all pages for a file in one response, ordered by page index.
- Q: If the storage existence check fails due to a storage error, should the system proceed with conversion or surface an error to the user? → A: Proceed with conversion (fail-open) — treat storage error as a cache miss and convert normally.

## Assumptions

- The file content hash (MD5) already stored on the note file record is sufficient to detect whether a note has changed; no additional hashing is needed.
- The existing `conversions/{user_id}/{file_id}/page_{i}_{md5}.png` storage key format encodes the file hash, so a key match implies the content is unchanged and a hash change naturally produces a new key.
- A dedicated backend endpoint to retrieve per-page OCR text by file ID does not yet exist and will need to be added as part of this feature. It will return all pages for a file in a single response, ordered by page index.
- The OCR tab displays text in read-only form; editing OCR text is out of scope.
- Dark mode support is required for all new UI elements, consistent with existing application conventions.
