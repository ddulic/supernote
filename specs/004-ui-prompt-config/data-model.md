# Data Model: UI Prompt Configuration

## New Table: `f_prompt_config`

Stores per-user prompt overrides. A row only exists when the user has explicitly saved a customisation for that `(category, layer)` combination.

### `PromptConfigDO`

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| `id` | BigInteger PK | No | `next_id()` default |
| `user_id` | BigInteger | No | Indexed. FK to `f_user.id` (not enforced at DB level, consistent with project pattern) |
| `category` | String | No | `"ocr"` or `"summary"` |
| `layer` | String | No | `"common"`, `"default"`, or any user-defined type name (e.g. `"daily"`, `"project"`) |
| `content` | Text | No | Full prompt text for this layer |
| `create_time` | BigInteger | No | Epoch milliseconds |
| `update_time` | BigInteger | No | Epoch milliseconds, auto-updated on write |

**Unique constraint**: `uq_prompt_config` on `(user_id, category, layer)`

**Validation rules**:
- `content` MUST NOT be empty
- `category` MUST be one of `["ocr", "summary"]`
- `layer` MUST NOT be empty; max 64 characters; alphanumeric + hyphens only
- `layer` names `"common"` and `"default"` are valid layer values for built-in overrides

---

## Modified Table: `f_note_page_content`

Add one nullable column to the existing `NotePageContentDO`.

### New column: `prompt_hash`

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| `prompt_hash` | String | Yes | SHA-256 hex digest of the full composed OCR prompt + `"\|"` + full composed summary prompt used during the last successful processing run. `NULL` means the page was processed before this feature was deployed (treated as stale). |

---

## State Transitions: `PromptConfigDO`

```
[No row] ---(user saves override)---> [row exists: content = user text]
[row exists] ---(user resets to default)---> [No row]  (row deleted)
[row exists] ---(user edits)---> [row exists: content = updated text]
[No row] ---(user creates custom type)---> [row exists: layer = custom name]
[row exists: custom type] ---(user deletes type)---> [No row]
```

---

## State Transitions: `NotePageContentDO.prompt_hash`

```
NULL (not yet processed or pre-feature)
  ---(successful OCR + summary processing run)---> hash_v1 (sha256 of composed prompts at time of processing)

hash_v1 (user changes a prompt, lazy check detects mismatch)
  ---> page marked stale in UI (no DB write)
  ---(user triggers reprocess, processing completes)---> hash_v2 (updated sha256)
```

---

## DTO Definitions

### `PromptConfigDTO` (API response item)

```python
@dataclass
class PromptConfigDTO(DataClassJSONMixin):
    category: str           # "ocr" | "summary"
    layer: str              # "common" | "default" | custom
    content: str            # effective text (user override if present, else server default)
    is_override: bool       # True if a user-saved row exists for this (category, layer)
    default_content: str    # server-file default text (always present for reset support)
```

### `UpsertPromptConfigDTO` (request body for save/update)

```python
@dataclass
class UpsertPromptConfigDTO(DataClassJSONMixin):
    category: str
    layer: str
    content: str
```

### `GetPromptsResponseVO` (GET /api/extended/prompts response)

```python
@dataclass
class GetPromptsResponseVO(BaseResponse):
    prompts: list[PromptConfigDTO] = field(default_factory=list)
```

### `PageStalenessDTO` (per-page staleness info)

```python
@dataclass
class PageStalenessDTO(DataClassJSONMixin):
    page_id: str
    page_index: int
    stored_hash: str | None     # None = pre-feature, treated as stale
    is_stale: bool
```

### `FileStalenessResponseVO` (GET /api/extended/files/{id}/staleness)

```python
@dataclass
class FileStalenessResponseVO(BaseResponse):
    current_prompt_hash: str
    pages: list[PageStalenessDTO] = field(default_factory=list)
    stale_count: int = 0
    total_count: int = 0
```

### `ReprocessRequestDTO` (POST /api/extended/files/{id}/reprocess body, optional)

```python
@dataclass
class ReprocessRequestDTO(DataClassJSONMixin):
    page_ids: list[str] | None = None   # None = all stale pages
```

### `ReprocessResponseVO`

```python
@dataclass
class ReprocessResponseVO(BaseResponse):
    queued_page_count: int = 0
```

---

## Alembic Migration

Single migration covers both changes:

1. **Create** `f_prompt_config` with all columns and unique constraint
2. **Add column** `prompt_hash` (String, nullable=True, no server_default) to `f_note_page_content`

Downgrade: drop `prompt_hash` column, drop `f_prompt_config` table.
