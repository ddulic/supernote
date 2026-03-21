# Data Model: Insights Block Navigation and Live Updates

**Branch**: `014-insights-scroll-autoupdate`
**Date**: 2026-03-20

## No New Database Tables

This feature requires no schema migrations. All data entities already exist.

---

## Existing Entities Used

### SummaryDO (`f_summary` table)

Unchanged. The `metadata` JSON field already stores segments:

```json
{
  "segments": [
    {
      "date_range": "Week of Oct 27",
      "summary": "...",
      "extracted_dates": ["2023-10-27"],
      "page_refs": [3, 4]
    }
  ]
}
```

- `page_refs` values are **1-indexed** page numbers.
- Frontend parses this into `pageRefs: number[]` per segment row.

### SystemTaskDO (`f_system_task` table)

Unchanged. Existing columns used by this feature:

| Column | Type | Usage |
|--------|------|-------|
| `file_id` | int | Filter tasks for the open file |
| `status` | string | PENDING / PROCESSING / COMPLETED / FAILED |
| `task_type` | string | OCR_EXTRACTION, SUMMARY, etc. |
| `update_time` | int (ms) | Stale-check on poll response |

### NotePageContentDO / PngPageVO

Unchanged. `pageNo` (1-indexed) on `PngPageVO` is the scroll target.

---

## Frontend State Model Changes

These are internal component state additions — not persisted.

### SummaryPanel.js — new reactive state

```
processingState: 'idle' | 'polling' | 'done' | 'failed'
  - idle:    no tasks found / not yet checked
  - polling: at least one task is PENDING or PROCESSING
  - done:    all tasks COMPLETED
  - failed:  at least one task FAILED, none still in progress
```

### SystemTaskVO (existing model, read-only)

No model changes. The frontend filter:

```
tasks where fileId == currentFileId
  AND status in [PENDING, PROCESSING, COMPLETED, FAILED]
```

Terminal state = all tasks for this file are COMPLETED or FAILED (none are PENDING or PROCESSING).

---

## Backend Query Change (tasks endpoint)

### Before

`GET /api/extended/system/tasks` — returns all recent tasks for the authenticated user, no filter.

### After

`GET /api/extended/system/tasks?file_id=<int>` — optional query parameter. When provided, returns only tasks where `file_id` matches. Existing calls without the parameter continue to work unchanged.

**No model changes.** `SystemTaskVO` and `SystemTaskListVO` are unchanged. The filter is applied in the service layer before constructing the response.

---

## Event Contract Between Components

### SummaryPanel → FileViewer

```
Event name: navigate-to-page
Payload:    { pageNo: number }  // 1-indexed, matches data-page-no attribute
Trigger:    User clicks an AI segment block that has at least one page_ref
```

### FileViewer scroll target

```
DOM query:  [data-page-no="${pageNo}"]  inside scrollContainerRef
Scroll:     element.scrollIntoView({ behavior: 'smooth', block: 'start' })
```
