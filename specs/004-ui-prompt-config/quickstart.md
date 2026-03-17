# Quickstart: UI Prompt Configuration

## Development Setup

No new dependencies. Uses existing stack: Python 3.13+, aiohttp, SQLAlchemy asyncio, alembic, mashumaro, pytest + pytest-asyncio.

```bash
./script/bootstrap   # if not already set up
./script/server      # ephemeral dev server at http://localhost:8080
                     # credentials: debug@example.com / password
```

## Running Tests

```bash
./script/test
# or target just this feature's tests:
.venv/bin/pytest tests/server/routes/test_prompts.py \
                  tests/server/services/test_prompt_config_service.py \
                  tests/server/services/test_processor_prompt_hash.py \
                  -v
```

## Applying the Migration

The alembic migration runs automatically on server start via `run_migrations()`. For manual application:

```bash
.venv/bin/alembic -c supernote/alembic.ini upgrade head
```

## Key Files

| File | Purpose |
|------|---------|
| `supernote/server/db/models/prompt_config.py` | `PromptConfigDO` SQLAlchemy model |
| `supernote/server/db/models/note_processing.py` | `NotePageContentDO` — add `prompt_hash` column |
| `supernote/alembic/versions/XXX_add_prompt_config.py` | Migration: create table + add column |
| `supernote/models/prompt_config.py` | DTOs: `PromptConfigDTO`, `UpsertPromptConfigDTO`, staleness VOs |
| `supernote/server/services/prompt_config.py` | `PromptConfigService` |
| `supernote/server/routes/prompts.py` | Route handlers for prompts + staleness + reprocess |
| `supernote/server/services/processor.py` | Inject `PromptConfigService`, pass resolver + hash to modules |
| `supernote/server/services/processor_modules/ocr.py` | Accept `prompt_resolver`, write `prompt_hash` |
| `supernote/server/services/processor_modules/summary.py` | Accept `prompt_resolver` |
| `supernote/server/static/js/components/PromptsModal.js` | New modal component |
| `supernote/server/static/js/components/FileViewer.js` | Add staleness fetch + stale indicators |
| `supernote/server/static/js/api/client.js` | Add prompt and reprocess API functions |
| `supernote/server/static/index.html` | Add Prompts header button |
| `supernote/server/static/js/main.js` | Add `showPromptsModal` state + component registration |

## Feature Flag / Rollout

No feature flag needed. The feature is additive:
- Users with no saved prompt configs see identical behaviour to pre-feature (server defaults used)
- Pre-feature notes show stale indicators immediately but are not automatically reprocessed

## Verifying End-to-End

1. Start the ephemeral server
2. Log in as `debug@example.com`
3. Upload a `monthly.note` file and wait for processing to complete
4. Click the Prompts button in the header
5. Edit the summary prompt for the `monthly` layer and save
6. Open the note in the viewer — a stale indicator should appear
7. Click Reprocess on a stale page — verify it processes and the indicator clears
8. Verify the AI output in the Insights panel reflects the new prompt text
