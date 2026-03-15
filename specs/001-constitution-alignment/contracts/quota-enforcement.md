# Contract: Quota Enforcement

## Affected Endpoints

### POST /api/file/3/files/upload/apply (device)
### POST /api/file/upload/apply (web)

No changes to request or response structure for the happy path.
One new error response added.

---

## New Error Response — Quota Exceeded

**Condition**: `user.used_capacity + request.size > int(user.total_capacity)`

**HTTP Status**: `507 Insufficient Storage`

**Response body** (existing `BaseResponse` / error envelope pattern):

```json
{
  "errorCode": "E0507",
  "errorMsg": "Storage quota exceeded",
  "success": false
}
```

**When returned**: Before a signed upload URL is generated. No data is transferred.

**Client behaviour**: The Supernote device firmware does not handle 507 natively;
it will surface a generic sync error to the user. This is acceptable — quota
exhaustion is an operator-configured limit, not a device firmware concern.

---

## Quota State Transitions

| Event | Effect on `used_capacity` |
|-------|--------------------------|
| `POST /api/file/2/files/upload/finish` succeeds | `used_capacity += file.size` (atomic DB update) |
| `DELETE` / `POST .../delete_folder_v3` succeeds | `used_capacity -= file.size` (floor at 0; atomic) |
| File overwritten (same name, upload finish) | `used_capacity += (new_size - old_size)` (net delta) |
| Admin resets user quota via CLI | `used_capacity` unchanged; only `total_capacity` updated |

---

## Configuration

| Config key | Env var | Default | Notes |
|-----------|---------|---------|-------|
| `auth.default_quota_bytes` | `SUPERNOTE_DEFAULT_QUOTA_BYTES` | `10737418240` (10 GB) | Applied to all new users at creation time |
| `storage.temp_cleanup_interval_seconds` | `SUPERNOTE_TEMP_CLEANUP_INTERVAL` | `3600` (1 hour) | How often the cleanup task runs |
| `storage.temp_ttl_seconds` | `SUPERNOTE_TEMP_TTL` | `86400` (24 hours) | Age threshold for orphaned chunk files |
