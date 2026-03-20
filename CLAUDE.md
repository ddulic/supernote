# supernote Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-20

## Active Technologies
- N/A (no Python source changes) + GitHub Dependabot (native GitHub feature, no external service) (002-switch-dependabot)
- N/A (no Python source changes — CI/CD configuration only) + GitHub Actions (`docker/metadata-action`, `docker/build-push-action`, `docker/login-action`) (003-github-releases)
- Python 3.13+ + aiohttp (server), SQLAlchemy asyncio + aiosqlite, mashumaro, alembic; Vanilla JS (Vue 3, no build step) for frontend (004-ui-prompt-config)
- SQLite via SQLAlchemy asyncio — new `f_prompt_config` table; new `prompt_hash` column on `f_note_page_content` (004-ui-prompt-config)
- Python 3.13+ (backend), Vanilla JS / Vue 3 ESM (frontend) + aiohttp, SQLAlchemy asyncio + aiosqlite, mashumaro, alembic (005-cache-png-insights-tabs)
- SQLite (DB via SQLAlchemy), LocalBlobStorage (disk — `supernote-user-data` bucket) (005-cache-png-insights-tabs)
- Python 3.13+ (backend), Vanilla JS / Vue 3 ESM (frontend — no build step) + aiohttp (server), SQLAlchemy asyncio + aiosqlite, mashumaro; Vue 3 ESM (frontend) (014-insights-scroll-autoupdate)
- SQLite via SQLAlchemy (existing `f_summary`, `f_system_task` tables — no schema changes) (014-insights-scroll-autoupdate)

- Python 3.13+ + mypy (strict), SQLAlchemy asyncio, aiohttp, mashumaro, pytest + pytest-asyncio (001-constitution-alignment)

## Project Structure

```text
supernote/
├── notebook/        # Binary .note parser (fork of supernote-tool)
├── cli/             # CLI entry points (supernote / supernote-server)
├── client/          # Async aiohttp cloud API client
├── models/          # mashumaro DataClassJSONMixin DTOs (shared client/server)
├── server/
│   ├── routes/      # Thin aiohttp route handlers
│   ├── services/    # Business logic (FileService, UserService, ProcessorService…)
│   ├── db/          # SQLAlchemy models + alembic migrations
│   ├── mcp/         # MCP server + OAuth/IndieAuth
│   └── utils/       # UrlSigner, RateLimiter, hashing, paths
tests/               # Mirrors supernote/ layout; 300+ tests
```

## Commands

```bash
./script/bootstrap          # Set up venv + pre-commit hooks
./script/test               # Run full pytest suite
./script/lint               # Run pre-commit (ruff, mypy, etc.)
./script/server             # Start ephemeral dev server
./script/run-mypy.sh        # Run mypy standalone
supernote serve --ephemeral # Ephemeral server with debug@example.com / password
```

## Code Style

- **Types**: strict mypy; use `T | None` not `Optional[T]`; `list[T]` not `List[T]`
- **Models**: `@dataclass` + `mashumaro.DataClassJSONMixin`; `omit_none=True`
- **Async**: all I/O must be `async`/`await`; use `asyncio.to_thread` for blocking ops
- **Testing**: `unittest.mock.patch` only (no `monkeypatch`); all test functions/fixtures must have type annotations; tests written before implementation
- **Logging**: `logging.getLogger(__name__)`; NEVER log note content

## Frontend UI Conventions (constitution §VIII)

Button Tailwind classes — use verbatim:

| Category | Classes |
|---|---|
| Primary (save/confirm) | `px-4 py-2 bg-black border border-black rounded text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50 transition-colors` |
| Secondary/cancel | `px-4 py-2 bg-white dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-500 transition-colors` |
| Danger (delete/remove) | `px-3 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 border border-red-200 dark:border-red-700 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 rounded transition-colors disabled:opacity-50` |
| Icon-only (header) | `text-gray-400 hover:text-black dark:hover:text-white transition-colors` |
| Amber/warning | `p-2 text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/30 disabled:opacity-50 rounded transition-colors border border-amber-300 dark:border-amber-600` — status indicators only |

- **No accent colors**: indigo, blue, green etc. are prohibited for interactive controls
- **Focus rings**: `focus:ring-2 focus:ring-black dark:focus:ring-white`
- **Spinners**: `animate-spin rounded-full h-8 w-8 border-b-2 border-black dark:border-white`
- **Dark mode**: every interactive element must have `dark:` variants

## Recent Changes
- 014-insights-scroll-autoupdate: Added Python 3.13+ (backend), Vanilla JS / Vue 3 ESM (frontend — no build step) + aiohttp (server), SQLAlchemy asyncio + aiosqlite, mashumaro; Vue 3 ESM (frontend)
- 005-cache-png-insights-tabs: Added Python 3.13+ (backend), Vanilla JS / Vue 3 ESM (frontend) + aiohttp, SQLAlchemy asyncio + aiosqlite, mashumaro, alembic
- 004-ui-prompt-config: Added Python 3.13+ + aiohttp (server), SQLAlchemy asyncio + aiosqlite, mashumaro, alembic; Vanilla JS (Vue 3, no build step) for frontend


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
