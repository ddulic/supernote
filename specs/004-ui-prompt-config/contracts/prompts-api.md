# API Contracts: Prompt Configuration

All endpoints are under the `extended` route module (`/api/extended/`). All require a valid `x-access-token` JWT header. Users may only access their own prompt configurations; cross-user access returns 403.

---

## Prompt Configuration Endpoints

### GET `/api/extended/prompts`

Returns all effective prompt configurations for the authenticated user. The response includes every known `(category, layer)` combination — built-in layers from the server files plus any user-defined custom layers — merged with the user's saved overrides.

**Auth**: JWT required

**Response 200**:
```json
{
  "success": true,
  "prompts": [
    {
      "category": "ocr",
      "layer": "common",
      "content": "...current effective text...",
      "isOverride": true,
      "defaultContent": "...server file text..."
    },
    {
      "category": "ocr",
      "layer": "default",
      "content": "...server file text...",
      "isOverride": false,
      "defaultContent": "...server file text..."
    },
    {
      "category": "ocr",
      "layer": "daily",
      "content": "...server file text...",
      "isOverride": false,
      "defaultContent": "...server file text..."
    },
    {
      "category": "summary",
      "layer": "common",
      "content": "...current effective text...",
      "isOverride": false,
      "defaultContent": "...server file text..."
    }
  ]
}
```

**Notes**:
- Built-in layers always appear (common, default, daily, weekly, monthly) for both categories
- User-defined custom layers also appear when saved
- `isOverride: true` means a `f_prompt_config` row exists for this user + category + layer
- `defaultContent` always contains the server file text for Reset support

---

### PUT `/api/extended/prompts`

Save or update a single prompt configuration for the authenticated user. Creates a new `f_prompt_config` row or updates the existing one (upsert on `(user_id, category, layer)`).

**Auth**: JWT required

**Request body**:
```json
{
  "category": "summary",
  "layer": "monthly",
  "content": "This is a Monthly Log for bullet journaling. Summarise by week..."
}
```

**Validation**:
- `category`: required, must be `"ocr"` or `"summary"`
- `layer`: required, 1–64 characters, alphanumeric + hyphens only
- `content`: required, must not be empty or whitespace-only

**Response 200**:
```json
{
  "success": true
}
```

**Response 400** (validation failure):
```json
{
  "success": false,
  "errorCode": "INVALID_INPUT",
  "errorMsg": "content must not be empty"
}
```

---

### DELETE `/api/extended/prompts/{category}/{layer}`

Remove the user's saved override for a specific `(category, layer)`, reverting it to the server default. For user-defined custom layers, this fully removes the type. For built-in layers, this just removes the override row.

**Auth**: JWT required

**Path parameters**:
- `category`: `"ocr"` or `"summary"`
- `layer`: layer name

**Response 200**:
```json
{
  "success": true
}
```

**Response 404** (no override exists to delete):
```json
{
  "success": false,
  "errorCode": "NOT_FOUND",
  "errorMsg": "No override found for ocr/monthly"
}
```

---

## Staleness & Reprocess Endpoints

### GET `/api/extended/files/{file_id}/staleness`

Computes the current effective prompt hash for this file's note type and compares it against the stored `prompt_hash` on each page. Returns per-page staleness status.

**Auth**: JWT required. User must own the file (403 otherwise).

**Response 200**:
```json
{
  "success": true,
  "currentPromptHash": "a3f1e9c2...",
  "staleCount": 2,
  "totalCount": 12,
  "pages": [
    {
      "pageId": "P20231027120000abc",
      "pageIndex": 0,
      "storedHash": "a3f1e9c2...",
      "isStale": false
    },
    {
      "pageId": "P20231028090000xyz",
      "pageIndex": 1,
      "storedHash": null,
      "isStale": true
    }
  ]
}
```

**Notes**:
- `storedHash: null` means the page was processed before this feature; treated as stale
- If the file has no processed pages yet, returns `staleCount: 0, totalCount: 0`

---

### POST `/api/extended/files/{file_id}/reprocess`

Queues stale pages of a note for reprocessing. Resets `SystemTaskDO` status for `OCR_EXTRACTION`, `EMBEDDING_GENERATION` (per page) and `SUMMARY_GENERATION` (global) for stale pages only, then enqueues the file.

**Auth**: JWT required. User must own the file (403 otherwise).

**Request body** (optional):
```json
{
  "pageIds": ["P20231028090000xyz"]
}
```
If `pageIds` is omitted or null, all stale pages for the file are queued.

**Validation**:
- If `pageIds` is provided, only pages with `is_stale: true` are accepted; non-stale page IDs in the list are silently skipped (consistent with spec FR-018).

**Response 200**:
```json
{
  "success": true,
  "queuedPageCount": 1
}
```

**Response 409** (processing already in progress for this file):
```json
{
  "success": false,
  "errorCode": "ALREADY_PROCESSING",
  "errorMsg": "This file is already queued for processing"
}
```

---

### POST `/api/extended/files/{file_id}/pages/{page_id}/reprocess`

Queues a single page for reprocessing. Resets task status for OCR and embedding for the specified page, and resets the summary task at file level.

**Auth**: JWT required. User must own the file (403 otherwise).

**Response 200**:
```json
{
  "success": true,
  "queuedPageCount": 1
}
```

**Response 400** (page is not stale):
```json
{
  "success": false,
  "errorCode": "NOT_STALE",
  "errorMsg": "This page does not require reprocessing"
}
```
