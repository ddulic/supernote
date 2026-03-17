<!--
SYNC IMPACT REPORT
==================
Version change: 1.1.0 → 1.2.0
Modified principles: none
Added sections:
  - VIII. Frontend UI Conventions (new principle)
Removed sections: none
Templates requiring updates:
  - .specify/templates/plan-template.md — Constitution Check should include Frontend gate
      when UI changes are in scope
Deferred TODOs: none
-->

# Supernote Knowledge Hub Constitution

## Core Principles

### I. Library-First Architecture

The project MUST be structured as a layered Python library with explicit optional
extras (`notebook`, `client`, `server`, `all`). Each layer MUST be independently
installable, importable, and testable without requiring the layers above it.
New functionality MUST originate as a self-contained module within the appropriate
layer before being exposed via CLI or server endpoints. Circular dependencies
between layers are prohibited.

**Rationale**: Enables users to install only what they need (e.g., notebook
parsing without the full server stack), reduces the blast radius of changes, and
keeps the public API surface predictable.

### II. Protocol Fidelity

This project MUST remain fully compatible with the official Ratta Supernote
Private Cloud protocol. Any endpoint, data model, or authentication flow that
the Supernote device firmware depends on MUST NOT be altered in a
backwards-incompatible way without a documented migration path. Deviations from
the reference protocol MUST be isolated to extension endpoints (i.e., paths not
used by device firmware) and clearly documented in `supernote/server/ARCHITECTURE.md`.

**Rationale**: Device firmware cannot be patched by this project. Breaking
protocol compatibility renders the server unusable for the primary use case.

### III. Async-First Design

All I/O-bound operations (network, database, file system) MUST use `async`/`await`.
Synchronous blocking calls inside async contexts are prohibited. The event loop
MUST NOT be blocked for more than incidental CPU work. Background processing
tasks (OCR, synthesis, indexing) MUST be dispatched as non-blocking background
jobs and MUST expose observable progress via the existing task-monitoring
infrastructure.

**Rationale**: The server handles concurrent device syncs, AI API calls, and
web UI requests simultaneously. Blocking the event loop degrades all in-flight
operations.

### IV. Strict Type Safety

All Python source files under `supernote/` MUST pass `mypy` in strict mode as
configured in `pyproject.toml`. All new code MUST use modern Python 3.10+ type
syntax (`str | None`, `list[T]`, `typing.Protocol`). API request/response models
MUST be defined as `@dataclass` classes using `mashumaro`'s `DataClassJSONMixin`
with `omit_none=True`. Untyped functions, untyped decorators, and implicit `Any`
are prohibited without an explicit, justified `# type: ignore` comment.

**Rationale**: The server handles binary protocol parsing, JWT authentication,
and AI API integration where type errors translate directly into data corruption
or security vulnerabilities.

### V. Observability & Data Privacy

Every background processing stage (sync, OCR, synthesis, indexing) MUST emit
structured log lines via `logging.getLogger(__name__)`. User note content MUST
NOT be logged at any level. The server MUST provide a mechanism for users to
inspect the status of background tasks (currently the admin processing status
panel). AI providers MUST be invoked only with explicit user configuration
(API key required); the server MUST NOT make AI calls without a configured key.
All user data MUST remain on the operator's infrastructure — no telemetry or
external data transmission beyond the configured AI provider API.

**Rationale**: Users choose self-hosting specifically for privacy. Logging note
content or phoning home would undermine the project's core value proposition.

### VI. Test-Driven Development (NON-NEGOTIABLE)

Tests MUST be written before implementation. The Red-Green-Refactor cycle is
mandatory: write a failing test, confirm it fails, implement the minimum code to
pass, then refactor. No new feature, endpoint, service method, or bug fix may be
merged without a corresponding test that was authored before the implementation.

**Test structure mirrors source structure**:
- `tests/server/routes/` — route/endpoint tests (HTTP-level)
- `tests/server/services/` — service-layer unit and integration tests
- `tests/server/device/` — device protocol end-to-end tests
- `tests/server/web/` — web UI API tests
- `tests/models/` — data model serialization/completeness tests
- `tests/client/` — API client tests
- `tests/notebook/` — notebook parsing tests

**Mandatory rules**:
- All test functions and fixtures MUST carry explicit type annotations.
- Mocking MUST use `unittest.mock.patch`; `monkeypatch` is prohibited.
- `pytest-asyncio` auto mode is the only supported async test runner.
- Integration tests MUST exercise real in-process server state (ephemeral DB);
  mocking the database is prohibited.
- Completeness tests (e.g., `test_*_completeness.py`) MUST be maintained
  alongside every model module to ensure all fields are round-trip serializable.
- **100% line coverage is required on all new and changed code before committing.**
  Every branch, error path, and early return MUST have a corresponding test.
  Code MUST NOT be committed until coverage is verified locally.

**Rationale**: The existing test suite (80+ test files spanning routes, services,
device protocol, MCP, security, and models) demonstrates that comprehensive tests
catch regressions that type checking alone cannot. Given the sensitivity of user
data handled, untested code is unacceptable.

### VII. Security (NON-NEGOTIABLE)

Security controls are not optional hardening — they are first-class requirements.
Every new endpoint, service, or data-access path MUST be accompanied by
security-focused tests (see `tests/server/routes/test_*_security*.py` and
`tests/server/utils/` for precedents).

**Mandatory controls**:

- **Authentication**: All device and web API routes MUST require a valid JWT
  (`x-access-token`). The challenge-response login flow (salted SHA256 over the
  stored MD5 + random code) MUST NOT be bypassed or simplified.
- **Session revocation**: JWT sessions MUST be tracked in the `CoordinationService`;
  revocation MUST be enforced on every authenticated request, not just at login.
- **Signed single-use URLs**: Direct file access (upload/download via OSS routes)
  MUST use signed URLs with a nonce that is consumed atomically on first use
  (burn-after-reading). Reuse of a nonce MUST be rejected with a 4xx response.
- **MCP API keys**: API key plaintext MUST be shown only once at creation time
  and MUST NOT be persisted. Storage MUST use SHA-256 hashes. Keys MUST carry
  the `snmcp_` prefix and `last_used_at` MUST be updated on every use.
- **Log redaction**: Sensitive query parameters (`signature`, `token`) MUST be
  redacted in all trace/access logs. Note content MUST NEVER appear in any log.
- **RBAC**: Admin-only endpoints MUST be gated on the `admin` role. Users MUST
  only be able to access their own files and settings; cross-user access MUST
  be rejected with a 403.
- **Registration / password reset**: Public registration MUST default to
  disabled. Remote self-service password reset MUST default to disabled.
  Enabling either MUST require explicit operator configuration.
- **Accepted risks (documented)**: MD5 password storage is an accepted protocol
  compatibility risk (see `docs/security.md`); no new accepted risks may be
  introduced without documentation in `docs/security.md` and a PR review.
- **Input validation**: All inputs at API boundaries (request bodies, query
  params, path params) MUST be validated via typed `mashumaro` models before
  reaching service layer logic.

**Rationale**: The server stores private handwritten notes, personal journals,
and AI-derived insights. A single authorization bypass or credential leak would
expose highly sensitive personal data. Security must be designed in, not bolted on.

### VIII. Frontend UI Conventions

The frontend is Vanilla JS with Vue 3 (ESM browser build, no build step). All
components live in `supernote/server/static/js/components/` and are served as
static files. UI changes MUST follow the established visual language exactly
so the interface remains consistent across features.

**Button styles** (Tailwind CSS — MUST be used verbatim for each category):

| Category | Required classes |
|---|---|
| Primary (save / confirm) | `px-4 py-2 bg-black border border-black rounded text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50 transition-colors` |
| Secondary / cancel | `px-4 py-2 bg-white dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-500 disabled:opacity-50 transition-colors` |
| Danger (delete / remove) | `px-3 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 border border-red-200 dark:border-red-700 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 rounded transition-colors disabled:opacity-50` |
| Icon-only (header / toolbar) | `text-gray-400 hover:text-black dark:hover:text-white transition-colors` |
| Amber / warning | `p-2 text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/30 disabled:opacity-50 rounded transition-colors border border-amber-300 dark:border-amber-600` — reserved for status-driven indicators only (e.g. stale content), never for routine actions |

**Prohibited**: Framework accent colors (indigo, blue, green, etc.) MUST NOT
be used for interactive controls. The permitted palette for interactive elements
is black / gray / red / amber only, as defined above.

**Disabled state**: Always `disabled:opacity-50`; add `disabled:cursor-not-allowed`
only when a full-width button is used (e.g. form submission).

**Modal overlay pattern**: `fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[N] p-4` with `@click.self="$emit('close')"`. Modal close (×) buttons MUST use the icon-only style above.

**Focus rings**: `focus:ring-2 focus:ring-black dark:focus:ring-white` — color-specific rings (indigo, blue, etc.) are prohibited.

**Loading spinners**: `animate-spin rounded-full h-8 w-8 border-b-2 border-black dark:border-white` (full-size) or `animate-spin w-4 h-4` with an SVG spinner inline (compact, inside a button).

**Dark mode**: Every interactive element MUST declare a `dark:` variant for all
background, text, and border properties. An element without a dark mode class
MUST NOT be merged.

**Rationale**: A consistent visual language makes the application feel coherent
and reduces cognitive overhead. Because there is no design system or component
library, the Tailwind class strings above serve as the single source of truth.
Deviating without updating this constitution creates drift that compounds
across features.

## Technology Stack

- **Runtime**: Python 3.13+, managed with `uv`
- **Async framework**: `asyncio`, `aiohttp` (client), Starlette/ASGI (server)
- **Data models**: `mashumaro` (`DataClassJSONMixin`) — MUST be used for all
  DTOs and VOs; plain dicts for API payloads are prohibited
- **Database**: SQLite via `SQLAlchemy[asyncio]` + `aiosqlite`; schema
  migrations via `alembic`
- **AI providers**: Google Gemini (`google-genai`) and Mistral AI (`mistralai`);
  both are optional at runtime and selected via environment variables
- **MCP integration**: `mcp` library; exposed at `/mcp` with IndieAuth
- **Frontend**: Vanilla JS (no build step); served as static files from
  `supernote/server/static/`
- **Linting**: `ruff` (config in `.ruff.toml`)
- **Type checking**: `mypy` (config in `pyproject.toml`)
- **Testing**: `pytest` + `pytest-asyncio` (auto mode); mocking via
  `unittest.mock.patch` — `monkeypatch` is prohibited

## Development Workflow

All standard operations MUST use the scripts in `script/` following the
"Scripts to Rule Them All" convention:

| Script | Purpose |
|--------|---------|
| `script/bootstrap` | Create venv, install all deps, set up pre-commit hooks |
| `script/test` | Run full test suite (`pytest`) |
| `script/lint` | Run linters via `pre-commit` |
| `script/server` | Start ephemeral development server |

**Ephemeral mode** (`supernote serve --ephemeral`) MUST be used for local
development and integration testing. It starts with a clean state and a
pre-seeded debug user and MUST NOT persist data between runs.

Pull requests MUST pass all CI gates (lint, type check, tests, coverage) before merge.
New and changed code MUST achieve 100% line coverage; PRs that reduce patch
coverage below 100% MUST NOT be merged without explicit justification.
The `main` branch is the source of truth; GitHub Pages documentation is
auto-deployed on every push to `main` via `pdoc`.

## Governance

This constitution supersedes all other development guidelines. Where a
conflict exists between this document and inline code comments, READMEs, or
informal conventions, this constitution takes precedence.

**Amendment procedure**:
1. Open a PR with the proposed change to this file.
2. Increment `CONSTITUTION_VERSION` using semantic versioning:
   - MAJOR: removal or redefinition of a principle; incompatible governance change.
   - MINOR: new principle or section added; material expansion of guidance.
   - PATCH: clarification, wording, or typo fix.
3. Update `LAST_AMENDED_DATE` to the merge date.
4. Propagate changes to dependent templates in `.specify/templates/` as needed.
5. Document the change in the Sync Impact Report HTML comment at the top of
   this file.

**Compliance**: All PRs and code reviews MUST verify that changes comply with
all seven Core Principles. Complexity that violates a principle MUST be
explicitly justified in the PR description with reference to the specific
principle and why the simpler alternative was rejected.

**Version**: 1.2.0 | **Ratified**: 2026-03-15 | **Last Amended**: 2026-03-17
