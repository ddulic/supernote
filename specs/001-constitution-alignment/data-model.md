# Data Model: Constitution Alignment

## Entities

### UserDO (modified)

Existing table `users`. One new column added.

| Field | Type | Nullable | Default | Notes |
|-------|------|----------|---------|-------|
| `id` | Integer PK | No | — | Existing |
| `email` | String UNIQUE | No | — | Existing |
| `password_md5` | String | No | — | Existing |
| `is_active` | Boolean | No | True | Existing |
| `display_name` | String | Yes | NULL | Existing |
| `total_capacity` | String | No | `str(10 * 1024³)` | Existing — allocated quota in bytes (stored as string for protocol compat) |
| `used_capacity` | Integer | No | 0 | **New** — running counter of bytes used, updated atomically on upload finish and delete |
| `is_admin` | Boolean | No | False | Existing |

**State transitions for `used_capacity`**:
- Upload finish → `used_capacity += file.size`
- File delete (soft or hard) → `used_capacity -= file.size` (floor at 0)
- Quota check → `used_capacity + requested_size > int(total_capacity)` → reject

**Migration note**: Alembic migration adds column with `DEFAULT 0`. A one-time
reconciliation query populates existing users' `used_capacity` from their current
active file sizes (`SUM(size) WHERE is_active='Y' AND is_folder='N'`).

---

### TempChunkFile (virtual — filesystem only, no new DB table)

Represents a chunk file on disk awaiting assembly. Identified by filename pattern:
`{object_name}.part.{part_number}` in `USER_DATA_BUCKET`.

| Attribute | Source | Notes |
|-----------|--------|-------|
| `path` | Filesystem key | `{object_name}.part.{N}` |
| `created_at` | `mtime` (filesystem) | Used for TTL comparison |
| `age` | `now - mtime` | If `age > TTL` and not in active upload window → orphaned |

**Lifecycle**:
1. Created by `handle_oss_upload_part` via `blob_storage.put()`
2. Merged into final file at last chunk by implicit-merge logic in `oss.py`
3. Deleted by merge logic after successful assembly
4. **Orphaned** if upload session abandoned before last chunk arrives
5. Cleaned up by `TempFileCleanupService` when `age > TTL`

---

### VirtualFileSystem.delete_node (contract clarification — no schema change)

Existing `UserFileDO` and `RecycleFileDO` tables. Behavioral contract amended:

| Scenario | Before (buggy) | After (correct) |
|----------|----------------|-----------------|
| `delete_node` on a **file** | Sets `is_active='N'`, creates `RecycleFileDO` ✅ | Unchanged |
| `delete_node` on a **folder** | Sets only the folder node to `is_active='N'`; children remain active (orphaned) ❌ | Recursively sets all active descendants to `is_active='N'`; creates one `RecycleFileDO` per descendant file; entire operation in a single DB transaction |

**Concurrency safety**: The processor pipeline tracks `processing_files: Set[int]`. A
file being processed when `delete_node` is called will be soft-deleted in the DB. The
processor will complete its current work and write results to `NotePageContentDO` — this
is safe because the stale processing result is simply never surfaced to the user (the
file is no longer active). No locking is required.

---

### CoordinationService (dead code removal)

`SqliteCoordinationService._cleanup()` method removed entirely. It was a no-op stub
(body: `pass`) that was never called from any site in the codebase.

The lazy expiry-on-access already implemented in `get_value()` and `increment()` is
sufficient for cleanup at the server's scale.
