# Implementation Plan: GitHub Releases & Repository Cleanup

**Branch**: `003-github-releases` | **Date**: 2026-03-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-github-releases/spec.md`

## Summary

Implement fully automated GitHub releases for the Supernote project using release-please: add a `release-please.yaml` workflow that analyses conventional commits on every push to `main`, automatically creates release PRs with changelogs, and publishes a GitHub release when merged. Fix the Docker workflow to remove the duplicate tag-push trigger (keeping only `release: published`), align the PyPI publish workflow to the same event, bump `pyproject.toml` to `1.0.0` as the baseline version, and remove three stale repository files (Cruft config, Cruft workflow, Copilot instructions).

## Technical Context

**Language/Version**: N/A (no Python source changes — CI/CD configuration only)
**Primary Dependencies**: GitHub Actions (`googleapis/release-please-action`, `docker/metadata-action`, `docker/build-push-action`, `docker/login-action`)
**Storage**: N/A
**Testing**: Workflow validation via GitHub Actions run logs; no unit tests applicable to CI/CD files
**Target Platform**: GitHub Actions (ubuntu-latest runners)
**Project Type**: CI/CD configuration
**Performance Goals**: N/A
**Constraints**: Must not break existing PR builds or main-branch edge builds; `v*.*.*` tags MUST only produce images on `release: published`
**Scale/Scope**: 3 files removed, 2 workflow files modified, 1 workflow added, 2 release-please config files added, `pyproject.toml` version bumped

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
│   ├── release-please.yaml  # ADD: triggers on push to main, runs release-please
│   ├── docker.yaml          # MODIFY: remove push:tags trigger, keep release:published
│   ├── publish.yaml         # MODIFY: change types:[created] → types:[published]
│   └── cruft.yaml           # DELETE
└── copilot-instructions.md  # DELETE

.release-please-config.json  # ADD: release-please package config (initial-version: 1.0.0)
.release-please-manifest.json # ADD: release-please version manifest (empty = first run)
.cruft.json                  # DELETE (repo root)
pyproject.toml               # MODIFY: version bumped from 0.14.8 → 1.0.0
```

**Structure Decision**: Pure CI/CD and config change — no new source directories, no new Python modules. `failed-sync.md` was already absent at implementation time.

## Phase 0: Research

See [research.md](research.md) for full findings. Key decisions:

1. **Duplicate trigger fix**: Remove `push: tags: v*.*.*` from `docker.yaml`; `release: published` is the sole versioned build trigger (Finding 1).
2. **`latest` tag**: Current `latest=true` flavor is correct for the project's needs (Finding 2).
3. **PyPI workflow alignment**: Change `publish.yaml` from `types: [created]` to `types: [published]` (Finding 3).
4. **File removals**: Three stale files confirmed for deletion; `failed-sync.md` was already absent (Finding 4).
5. **Automated releases via release-please**: Replace manual `gh release create` with `googleapis/release-please-action` — analyses conventional commits, creates release PRs, and publishes GitHub releases automatically (Finding 5 — updated after implementation).

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

#### `release-please.yaml` — New automated release workflow

Triggers on every push to `main`. Runs `googleapis/release-please-action@v4` with the config and manifest files. Creates or updates a release PR; merging the PR creates the git tag and GitHub release automatically.

#### `.release-please-config.json` — Release-please package config

```json
{
  "packages": {
    ".": {
      "release-type": "python",
      "initial-version": "1.0.0",
      "extra-files": []
    }
  }
}
```

#### `.release-please-manifest.json` — Version manifest

Starts empty (`{}`) so release-please treats this as a new package and uses `initial-version: 1.0.0` for the first release.

#### Files to delete

| File | Action | Note |
|------|--------|------|
| `.github/workflows/cruft.yaml` | `git rm` | Removed |
| `.github/copilot-instructions.md` | `git rm` | Removed |
| `.github/failed-sync.md` | N/A | Already absent |
| `.cruft.json` | `git rm` | Removed |

#### `pyproject.toml` — Version bump

Version updated from `0.14.8` → `1.0.0`. Release-please will manage this file for all future version bumps.

### Automated Release Flow (Post-merge)

Once this PR merges, the full release cycle is zero-touch:

```
conventional commit merged to main
        ↓
release-please.yaml → creates/updates Release PR with changelog
        ↓
Release PR merged
        ↓
tag v1.0.0 + GitHub Release published automatically
        ↓
release: published event fires
        ↓
docker.yaml   → ghcr.io: v1.0.0 / 1.0 / 1 / latest
publish.yaml  → PyPI publish
```
