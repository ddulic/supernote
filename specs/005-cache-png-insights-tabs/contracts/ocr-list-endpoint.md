# Contract: OCR Page List Endpoint

**Endpoint**: `POST /api/extended/file/ocr/list`
**Auth**: Required — `x-access-token: <JWT>` header
**Ownership**: Users may only retrieve OCR for files they own; cross-user access returns 403.

---

## Request

**Content-Type**: `application/json`

```json
{
  "fileId": 12345
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `fileId` | integer | Yes | ID of the note file |

---

## Response — 200 OK

```json
{
  "pages": [
    { "pageIndex": 0, "textContent": "Handwriting extracted from page 1..." },
    { "pageIndex": 1, "textContent": "Handwriting extracted from page 2..." }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `pages` | array | Ordered by `pageIndex` ascending. Empty array if no OCR available. Only pages with non-null text are included. |
| `pages[].pageIndex` | integer | 0-based page position in the note |
| `pages[].textContent` | string | Raw OCR text from that page |

---

## Error Responses

| Status | Condition |
|--------|-----------|
| 400 | Malformed JSON body or missing `fileId` |
| 401 | Missing or invalid JWT |
| 403 | File belongs to a different user |
| 404 | File not found |
| 500 | Unexpected server error |

---

## Notes

- Returns an empty `pages` array (not a 404) when the file exists but has no OCR data yet (processing pending).
- Does not paginate — all available pages returned in a single response.
- Follows the same convention as `POST /api/extended/file/summary/list`.
