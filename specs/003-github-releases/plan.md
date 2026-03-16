# Implementation Plan: GitHub Releases & Repository Cleanup

**Branch**: `003-github-releases` | **Date**: 2026-03-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-github-releases/spec.md`

## Summary

Implement proper versioned GitHub releases for the Supernote project: fix the Docker workflow to remove the duplicate tag-push trigger (keeping only `release: published`), align the PyPI publish workflow to the same event, remove four stale repository files (Cruft config, Cruft workflow, Copilot instructions, failed-sync artifact), and create the initial `v1.0.0` release after the changes are merged.

## Technical Context

**Language/Version**: N/A (no Python source changes — CI/CD configuration only)
**Primary Dependencies**: GitHub Actions (`docker/metadata-action`, `docker/build-push-action`, `docker/login-action`)
**Storage**: N/A
**Testing**: Workflow validation via GitHub Actions run logs; no unit tests applicable to CI/CD files
**Target Platform**: GitHub Actions (ubuntu-latest runners)
**Project Type**: CI/CD configuration
**Performance Goals**: N/A
**Constraints**: Must not break existing PR builds or main-branch edge builds; `v*.*.*` tags MUST only produce images on `release: published`
**Scale/Scope**: 4 files removed, 2 workflow files modified, 1 release created

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Applicability | Status |
|-----------|--------------|--------|
| I. Library-First Architecture | N/A — no Python source changes | PASS |
| II. Protocol Fidelity | N/A — no server or protocol changes | PASS |
| III. Async-First Design | N/A — no async I/O code | PASS |
| IV. Strict Type Safety | N/A — no Python code written | PASS |
| V. Observability & Data Privacy | N/A — no logging or data paths touched | PASS |
| VI. Test-Driven Development | N/A — CI/CD YAML has no unit-testable logic; workflow correctness is validated by running the workflow | PASS |
| VII. Security | Relevant: ensure no secrets are hardcoded in workflow files; use `secrets.GITHUB_TOKEN` only | PASS |

No violations. No complexity justification required.

## Project Structure

### Documentation (this feature)

```text
specs/003-github-releases/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit.tasks — not created here)
```

### Source Code Changes (repository root)

```text
.github/
├── workflows/
│   ├── docker.yaml      # MODIFY: remove push:tags trigger, keep release:published
│   ├── publish.yaml     # MODIFY: change types:[created] → types:[published]
│   └── cruft.yaml       # DELETE
├── copilot-instructions.md  # DELETE
└── failed-sync.md           # DELETE

.cruft.json                  # DELETE (repo root)
```

**Structure Decision**: Pure CI/CD change — no new source directories, no new Python modules.

## Phase 0: Research

See [research.md](research.md) for full findings. Key decisions:

1. **Duplicate trigger fix**: Remove `push: tags: v*.*.*` from `docker.yaml`; `release: published` is the sole versioned build trigger (Finding 1).
2. **`latest` tag**: Current `latest=true` flavor is correct for the project's needs (Finding 2).
3. **PyPI workflow alignment**: Change `publish.yaml` from `types: [created]` to `types: [published]` (Finding 3).
4. **File removals**: Four stale files confirmed for deletion (Finding 4).
5. **Release sequence**: `v1.0.0` release is created via `gh release create` after the PR is merged to `main` (Finding 5).

## Phase 1: Design

### No Data Model

This feature introduces no new data entities, database schema, or structured data formats.

### No API Contracts

This feature introduces no new endpoints, CLI commands, or public interfaces.

### Workflow Changes (Detailed)

#### `docker.yaml` — Remove duplicate tag-push trigger

**Before** (triggers section):
```yaml
on:
  push:
    branches:
      - main
    tags:
      - "v*.*.*"
  pull_request:
    branches:
      - main
  release:
    types:
      - published
```

**After** (triggers section):
```yaml
on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main
  release:
    types:
      - published
```

No other changes to `docker.yaml`. The semver metadata extraction, tag patterns, and push conditions are already correct.

#### `publish.yaml` — Align release event type

**Before**:
```yaml
on:
  release:
    types: [created]
```

**After**:
```yaml
on:
  release:
    types: [published]
```

#### Files to delete

| File | Action |
|------|--------|
| `.github/workflows/cruft.yaml` | `git rm` |
| `.github/copilot-instructions.md` | `git rm` |
| `.github/failed-sync.md` | `git rm` |
| `.cruft.json` | `git rm` |

### Post-merge Release Step

After the PR is merged to `main`, create the initial release:

```bash
gh release create v1.0.0 \
  --title "v1.0.0" \
  --notes "Initial release." \
  --latest
```

This fires `release: published`, which triggers the Docker workflow to build and push:
- `ghcr.io/ddulic/supernote:v1.0.0`
- `ghcr.io/ddulic/supernote:1.0`
- `ghcr.io/ddulic/supernote:1`
- `ghcr.io/ddulic/supernote:latest`
