# Contract: System Tasks Endpoint (Extended)

**Endpoint**: `GET /api/extended/system/tasks`
**Change type**: Non-breaking extension (new optional query parameter)

## Request

### Headers (unchanged)
```
x-access-token: <jwt>
```

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_id` | integer | No | When provided, filters results to tasks for this file only. When omitted, returns all recent tasks (existing behavior preserved). |

### Example

```
GET /api/extended/system/tasks?file_id=42
```

## Response

**Schema unchanged** — `SystemTaskListVO` as before.

```json
{
  "tasks": [
    {
      "id": 101,
      "fileId": 42,
      "taskType": "OCR_EXTRACTION",
      "key": "page_1",
      "status": "COMPLETED",
      "retryCount": 0,
      "updateTime": 1742500000000,
      "lastError": null
    },
    {
      "id": 102,
      "fileId": 42,
      "taskType": "SUMMARY",
      "key": "global",
      "status": "PROCESSING",
      "retryCount": 0,
      "updateTime": 1742500001000,
      "lastError": null
    }
  ]
}
```

## Status Values

| Status | Terminal? | Meaning |
|--------|-----------|---------|
| `PENDING` | No | Queued, not started |
| `PROCESSING` | No | Actively running |
| `COMPLETED` | Yes | Finished successfully |
| `FAILED` | Yes | Finished with error |

**Polling stop condition**: All tasks for the file are in terminal state (COMPLETED or FAILED) — i.e., none are PENDING or PROCESSING.

## Frontend Polling Behavior

```
On SummaryPanel mount:
  1. Fetch summaries and OCR (existing behavior)
  2. Call GET /api/extended/system/tasks?file_id=<fileId>
  3. If any task is PENDING or PROCESSING:
       - Set processingState = 'polling'
       - Schedule next poll in 4000ms
  4. On each poll:
       - If all tasks terminal → re-fetch summaries + OCR → set processingState = 'done'/'failed'
       - If still in progress → schedule next poll
  5. On component unmount → clear poll timer

On SummaryPanel unmount:
  - Clear any pending poll timer
```

## Backwards Compatibility

Existing callers that omit `file_id` receive the same response as before. The parameter is optional with no default filter applied.
