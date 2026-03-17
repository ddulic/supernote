# Feature Specification: UI Prompt Configuration

**Feature Branch**: `004-ui-prompt-config`
**Created**: 2026-03-17
**Status**: Implemented

## Overview

Previously, the AI prompts used to transcribe and summarise handwritten notes were stored as static `.md` files on the server. The note type (e.g., daily, weekly, monthly) was inferred from the filename stem, which determined which hardcoded prompt file was used. Users had no way to view, edit, or customise these prompts without direct server access.

This feature moves prompt management into the UI, giving users full control over the instructions sent to the AI for both OCR transcription and summary generation — globally, per note type, or for custom note types they define themselves.

The server-side prompt `.md` files have been removed entirely. Canonical defaults are now hardcoded Python constants in the server. These defaults are used when a user has no saved override for a given layer.

The system tracks which prompt version was used to process each note and page via a combined hash. When a user updates a prompt, affected notes and pages are flagged as stale. An amber icon button appears in the note viewer header, and individual page-level reprocess buttons allow targeted reprocessing. A "Reprocess All Notes" button in the Prompts modal allows bulk reprocessing with a cost-warning confirmation step.

## Clarifications

### Session 2026-03-17

- Q: Should OCR prompt hash and summary prompt hash be tracked independently per page, or as a single combined hash? → A: Single combined hash per page — any prompt change (OCR or summary) marks the whole page stale.
- Q: Is staleness computed eagerly on prompt save, lazily at display time, or via a background job? → A: Lazy — computed at display time by comparing current effective prompt hash against the stored hash; no DB write occurs on prompt save.
- Q: Where in the UI should the stale indicator and Reprocess button appear? → A: Note viewer only — an amber icon button in the note viewer header (note level) and a Reprocess button on individual stale pages; not surfaced on file list cards.
- Q: When Reprocess is clicked at the note level, does it reprocess all pages or only stale ones? → A: Only stale pages — pages whose stored hash already matches the current effective prompt are skipped.
- Q: Should notes with no stored hash (processed before this feature) show Reprocess buttons immediately after deployment? → A: Yes — notes and pages with no stored hash are treated as stale immediately; Reprocess buttons appear in the viewer for all such items.

### Session 2026-03-17 (implementation refinements)

- Q: Should the UI offer a "Reset to Default" action or a "Remove" action for custom overrides? → A: Remove — clicking Remove deletes the user's saved override entirely; the field then shows the hardcoded default. No separate reset action exists.
- Q: Should server-side prompt files remain as fallback defaults? → A: No — the `.md` files were removed. Hardcoded Python string constants serve as the canonical defaults.
- Q: Which layers are protected (non-removable)? → A: Exactly three: `ocr/default`, `summary/default`, and `summary/common`. All other user-created layers (custom note types like "daily", "project", etc.) can be removed.
- Q: Does OCR have a "common" layer? → A: No — only Summary has a common layer. OCR has only a `default` layer plus any user-defined custom type layers.
- Q: Should there be a bulk reprocessing option in the Prompts modal? → A: Yes — a "Reprocess All Notes" button sits in the tab bar at the far right, always active, and shows an inline cost-warning confirmation before firing.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View and Edit Prompts via Modal (Priority: P1)

A logged-in user opens the Prompts modal from the header, sees their current prompt configuration (showing hardcoded defaults where no customisation exists), edits the summary prompt for "monthly" notes, saves it, and the next time their monthly note is processed the AI uses their custom text.

**Why this priority**: This is the core value delivery — it unlocks customisation and makes the system transparent to the user for the first time.

**Independent Test**: Can be fully tested by opening the modal, editing a prompt, saving, and triggering note reprocessing to verify the custom text reaches the AI.

**Acceptance Scenarios**:

1. **Given** a logged-in user with no custom prompts saved, **When** they open the Prompts modal, **Then** they see the hardcoded default text pre-populated in all prompt fields, clearly labelled as defaults (not customised).
2. **Given** a user who has edited the summary prompt for "monthly", **When** a monthly note is processed, **Then** the AI receives the user's saved text instead of the hardcoded default.
3. **Given** a user who clicks Save in the modal, **When** the save completes, **Then** a confirmation toast is shown and the changes are immediately persisted.
4. **Given** a user who closes the modal without saving, **When** they reopen it, **Then** unsaved changes are discarded and previously saved values are shown.

---

### User Story 2 - Manage Custom Note Types (Priority: P2)

A user wants to create a prompt configuration for a custom note type called "project" so that any note named `project.note` is transcribed and summarised using project-specific instructions.

**Why this priority**: Removes the hardcoded daily/weekly/monthly limitation and makes the system extensible without server changes.

**Independent Test**: Can be fully tested by creating a "project" type in the modal, adding prompt text, uploading a `project.note` file, and verifying the custom prompt is used during processing.

**Acceptance Scenarios**:

1. **Given** a user in the Prompts modal, **When** they enter a new type name (e.g., "project") and save prompt text for it, **Then** the new type appears in the modal alongside built-in types.
2. **Given** a custom note type exists, **When** a note whose filename stem matches that type is processed, **Then** the server uses the user-defined prompt for that type.
3. **Given** a custom note type, **When** the user removes it, **Then** the type disappears from the modal and future notes of that name fall back to the default prompt.
4. **Given** a user attempts to create a type with a name that already exists, **When** they save, **Then** an error is shown and no duplicate is created.

---

### User Story 3 - Remove Custom Override (Priority: P3)

A user has modified a prompt and wants to discard their customisation, reverting to the hardcoded default text.

**Why this priority**: Provides a safety net so users are never stuck with a broken or unwanted prompt.

**Independent Test**: Can be fully tested by editing a prompt, saving, then using the Remove action and verifying the hardcoded default text is shown and used on the next processing run.

**Acceptance Scenarios**:

1. **Given** a user has a saved custom override for a non-protected layer, **When** they click "Remove", **Then** the override is deleted from the database and the field reverts to displaying the hardcoded default text.
2. **Given** a user has not customised a prompt layer, **When** they view the modal, **Then** no "Remove" action is available for that layer.
3. **Given** a protected layer (`ocr/default`, `summary/default`, `summary/common`), **When** the user views it, **Then** no "Remove" action is shown regardless of whether they have a saved override.

---

### User Story 4 - Summary Common Prompt Editing (Priority: P3)

A user edits the Summary "common" prompt layer — the instructions always prepended to every summary request regardless of note type — to reflect their personal journaling style.

**Why this priority**: The common layer is shared across all note types for summary generation; making it editable extends personalisation to the baseline behaviour.

**Independent Test**: Can be tested by editing the summary common prompt and verifying its text appears in all subsequent summary requests regardless of note filename.

**Acceptance Scenarios**:

1. **Given** a user edits the summary common prompt, **When** any note is next processed, **Then** the AI receives the user's common text prepended to the type-specific summary prompt.
2. **Given** a user saves a summary common prompt, **When** they reopen the modal, **Then** their saved text is shown, not the hardcoded default.
3. **Given** the OCR tab in the Prompts modal, **When** the user views it, **Then** no "common" layer is shown — OCR has only a `default` layer (plus custom types).

---

### User Story 5 - Reprocess Stale Notes and Pages (Priority: P2)

A user updates their summary prompt for "monthly" notes. When they open a monthly note in the viewer, they see an amber reprocess icon button in the header indicating stale pages. Individual page-level Reprocess buttons appear on each stale page. The user can click either to queue targeted reprocessing. A "Reprocess All Notes" button in the Prompts modal allows bulk reprocessing of all notes.

**Why this priority**: Without this, users who update prompts have no way to apply the new prompt to existing content without a full re-upload. This closes the feedback loop between prompt editing and AI output.

**Independent Test**: Can be fully tested by processing a note, updating its prompt, observing the stale indicator and reprocess buttons, clicking Reprocess, and verifying the AI output reflects the new prompt.

**Acceptance Scenarios**:

1. **Given** a note has been processed, **When** the user opens the note viewer and the current prompt hash differs from the stored hash, **Then** an amber icon button appears in the note viewer header indicating the number of stale pages.
2. **Given** a stale note, **When** the user clicks the amber header icon button, **Then** only the stale pages are queued for reprocessing; pages whose stored hash already matches the current prompt are skipped.
3. **Given** a note where specific pages are stale, **When** the user views the note, **Then** a Reprocess button is shown at the page level for each affected page.
4. **Given** a note that was processed with the current prompt version, **When** the user views it, **Then** no amber indicator or Reprocess button is shown.
5. **Given** a user clicks Reprocess, **When** processing is already in progress for that item, **Then** duplicate queue entries are not created and the button is disabled until processing completes.
6. **Given** a user clicks "Reprocess All Notes" in the Prompts modal, **When** the inline cost warning is shown, **Then** they must confirm before any reprocessing is queued; cancelling aborts without side effects.
7. **Given** a user confirms "Reprocess All Notes", **Then** all their active `.note` files are queued for reprocessing and a toast confirms how many files were queued.

---

### Edge Cases

- What happens when a user has saved a prompt for a type but the note filename changes? The new stem is used for matching; the old type config remains but is simply unused.
- What happens when the AI service is not configured? Prompt editing is still available; changes take effect once the AI service is configured.
- What if a user saves an empty prompt? The system rejects the save with a validation message; an empty prompt would cause AI processing to fail.
- What if two browser tabs edit the same prompt simultaneously? Last write wins; the modal shows the value at time of opening.
- What happens to notes processed before a prompt change? No automatic reprocessing; notes are flagged as stale and Reprocess buttons are shown in the viewer.
- What if a custom type name conflicts with a built-in type name? The system prevents this with a validation error.
- What if a prompt override is removed and the hardcoded default matches the hash stored on the page? The page is no longer considered stale and the Reprocess button is hidden.
- What if a note's type changes (file renamed) after processing? The stale check uses the note's current filename stem against the current effective prompt; a renamed note may become stale or un-stale accordingly.
- What happens if reprocessing fails? The stale indicator remains and an error toast is shown; the user can retry.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display a "Prompts" button in the top navigation header, visible only to logged-in users, styled consistently with existing header icons.
- **FR-002**: System MUST open a Prompts modal when the header Prompts button is clicked.
- **FR-003**: The Prompts modal MUST display an "OCR" tab and a "Summary" tab. The OCR tab shows a `default` field plus any user-defined custom type layers. The Summary tab shows a `common` field, a `default` field, and any user-defined custom type layers.
- **FR-004**: Each prompt field MUST be editable as free text and MUST display the current effective value — the user's saved override if one exists, otherwise the hardcoded default text.
- **FR-005**: System MUST visually distinguish fields that reflect a user-saved override (labelled "customised") from fields showing the hardcoded default.
- **FR-006**: System MUST persist saved prompt values per user so that each user's configuration is independent of other users.
- **FR-007**: System MUST allow users to add new custom note types by supplying a type name and prompt text for OCR, Summary, or both.
- **FR-008**: The three core layers (`ocr/default`, `summary/default`, `summary/common`) MUST be protected — no Remove button is shown for them regardless of customisation state. All user-created custom type layers CAN be removed.
- **FR-009**: System MUST allow users to remove their saved override for any non-protected layer via a "Remove" button; doing so deletes the DB row and reverts display to the hardcoded default.
- **FR-010**: System MUST reject saving an empty or whitespace-only prompt field with a clear validation message.
- **FR-011**: When processing a note, the server MUST resolve prompts by checking the processing user's saved configuration first, falling back to hardcoded defaults only when no user override exists for a given layer or type.
- **FR-012**: Note type matching during processing MUST use the note's filename stem, matched case-insensitively against the user's configured type names.
- **FR-013**: The server MUST NOT require a file-system change or restart to reflect a user's updated prompt configuration.
- **FR-014**: When processing a note or page, the server MUST record a single combined hash covering the full composed OCR prompt and the full composed summary prompt alongside the processing result.
- **FR-015**: Staleness MUST be determined lazily at display time by computing the current effective prompt hash and comparing it against the stored hash on each page; no additional DB writes are required when a prompt is saved.
- **FR-016**: The UI MUST display an amber icon button in the note viewer header when any pages are stale, indicating the count of stale pages; stale indicators MUST NOT appear on file list cards.
- **FR-017**: The UI MUST display a Reprocess button on individual stale pages inside the note viewer.
- **FR-018**: Clicking the amber header icon button MUST queue only the pages whose stored hash differs from the current effective prompt hash; pages that are not stale MUST be skipped.
- **FR-019**: While reprocessing is in progress, the Reprocess button MUST be disabled and a processing indicator shown; duplicate queue entries MUST NOT be created.
- **FR-020**: Once reprocessing completes successfully, the stale indicator and Reprocess button MUST be removed from that note or page.
- **FR-021**: The Prompts modal MUST include a "Reprocess All Notes" button in the tab bar, always visible and enabled, which queues all the user's active `.note` files for reprocessing.
- **FR-022**: Clicking "Reprocess All Notes" MUST show an inline cost-warning confirmation ("This will reprocess all notes and may incur substantial AI costs") before queuing any work; the user must explicitly confirm to proceed.

### Key Entities

- **PromptConfig**: A user-owned prompt override. Attributes: owning user, prompt category (`ocr` or `summary`), layer (`default`, `common`, or a named custom type string such as `daily`), prompt text content, created and updated timestamps.
- **NoteType**: A named classification for notes determined by filename stem. May be a built-in type (daily, weekly, monthly) or a user-defined custom string. Represented implicitly by the layer value on a PromptConfig — not a separate stored entity.
- **PromptHash**: A single fingerprint of the full composed prompt covering both OCR and summary layers used during a processing run. Stored once per page. Any change to either prompt for a note's type marks the whole page stale.
- **ProtectedLayer**: One of `ocr/default`, `summary/default`, or `summary/common`. These layers always exist (backed by hardcoded defaults), are editable (users can save overrides), but cannot be removed via the UI or API.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can open the Prompts modal, edit a prompt, and save their changes within 60 seconds without guidance.
- **SC-002**: A user-saved prompt is used by the server on the very next processing run for a matching note, with zero server restarts or file changes required.
- **SC-003**: A user with no saved prompts receives identical AI output to the pre-feature behaviour (hardcoded defaults produce the same results as the previous server-side prompt files).
- **SC-004**: The Prompts modal is reachable within 2 clicks from any page in the application.
- **SC-005**: All existing built-in note types (daily, weekly, monthly, default, common) remain fully functional after the migration, whether or not the user has saved custom overrides.
- **SC-006**: After a user saves a prompt change, stale indicators appear on affected notes on next open of the note viewer.
- **SC-007**: A user can trigger reprocessing of a single stale page without reprocessing the entire note.
- **SC-008**: Clicking "Reprocess All Notes" without confirming the cost warning does not queue any reprocessing work.

## Scope

### In Scope

- Prompts modal UI with OCR and Summary tabs, view, edit, save, and remove-custom-override actions
- Per-user persistence of prompt configurations
- Server-side prompt resolution that checks user config before falling back to hardcoded defaults
- Support for both OCR and Summary prompt categories
- Summary has `common` + `default` + custom type layers; OCR has `default` + custom type layers only
- Hardcoded default constants replacing the previous server-side `.md` prompt files
- Three protected layers (`ocr/default`, `summary/default`, `summary/common`) that are editable but not removable
- Prompt hash recorded alongside every processing result
- Stale detection: comparison of current effective prompt hash against stored processing hash
- Amber icon button in note viewer header showing stale page count
- Individual page-level Reprocess buttons in note viewer
- "Reprocess All Notes" button in the Prompts modal tab bar with inline cost-warning confirmation

### Out of Scope

- Automatic reprocessing of previously processed notes when a prompt changes (stale detection is automatic; reprocessing requires explicit user action)
- Sharing or exporting prompt configurations between users
- Version history of prompt edits
- Live preview or test functionality (trying a prompt against a specific note in the modal)
- Admin-level management of global defaults across all users

## Assumptions

- The existing filename-stem matching convention (e.g., `daily.note` → type `daily`) is retained; this feature makes the registered types dynamic rather than changing the matching mechanism itself.
- For Summary, the common layer prompt is always prepended to the type-specific prompt. OCR has no common layer.
- The previous server-side prompt `.md` files have been removed. Hardcoded Python string constants (`DEFAULT_OCR_PROMPT`, `DEFAULT_SUMMARY_COMMON_PROMPT`, `DEFAULT_SUMMARY_PROMPT`) serve as canonical defaults.
- Built-in type names (daily, weekly, monthly) are not pre-populated in the DB; they are only written when a user explicitly saves a customisation for them and can be removed like any other custom type.
- All existing users start with zero saved prompt configs, meaning no behavioural change occurs until a user actively saves something.
- The modal follows the same visual conventions as existing modals in the application.
- Notes and pages processed before this feature is deployed have no stored prompt hash; they are treated as stale immediately upon deployment, and Reprocess buttons are shown in the note viewer for all such items. No automatic reprocessing occurs.
- The prompt hash covers the full composed prompt text (common layer + type-specific layer) as sent to the AI, not the individual stored PromptConfig entries.
