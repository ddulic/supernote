# supernote Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-16

## Active Technologies
- N/A (no Python source changes) + GitHub Dependabot (native GitHub feature, no external service) (002-switch-dependabot)

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

## Recent Changes
- 002-switch-dependabot: Added N/A (no Python source changes) + GitHub Dependabot (native GitHub feature, no external service)

- 001-constitution-alignment: Added Python 3.13+ + mypy (strict), SQLAlchemy asyncio, aiohttp, mashumaro, pytest + pytest-asyncio

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
