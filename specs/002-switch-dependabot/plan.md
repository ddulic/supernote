# Implementation Plan: Switch to Dependabot and Remove Stale Artifacts

**Branch**: `002-switch-dependabot` | **Date**: 2026-03-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-switch-dependabot/spec.md`

## Summary

Replace the existing Renovate bot configuration with a Dependabot configuration covering Python
(`pyproject.toml`) and GitHub Actions ecosystems, grouped by ecosystem on a weekly schedule with
immediate security updates enabled. Remove three stale artifacts: `.github/renovate.json5`,
`.agent/skills/developer/`, and `ROADMAP.md`. Update two files that reference the removed artifacts
(`docs/CONTRIBUTING.md` and `.github/workflows/test.yaml`).

## Technical Context

**Language/Version**: N/A (no Python source changes)
**Primary Dependencies**: GitHub Dependabot (native GitHub feature, no external service)
**Storage**: N/A
**Testing**: N/A (configuration-only change; verified by file presence/absence)
**Target Platform**: GitHub repository
**Project Type**: Repository configuration / housekeeping
**Performance Goals**: N/A
**Constraints**: Dependabot config must use the YAML format at `.github/dependabot.yml`
**Scale/Scope**: 2 ecosystems (pip, github-actions); 1 weekly schedule; 1 security-updates config

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Library-First Architecture | ✅ Pass | No Python source changes |
| II. Protocol Fidelity | ✅ Pass | No server/endpoint changes |
| III. Async-First Design | ✅ Pass | No I/O code changes |
| IV. Strict Type Safety | ✅ Pass | No Python source changes |
| V. Observability & Data Privacy | ✅ Pass | No logging or data paths affected |
| VI. Test-Driven Development | ✅ Pass | No code to test; config-only changes verified by file presence |
| VII. Security | ✅ Pass | Enabling Dependabot security updates is a positive security improvement |

**All gates pass. No violations.**

## Project Structure

### Documentation (this feature)

```text
specs/002-switch-dependabot/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Files Changed (repository root)

```text
# Added
.github/dependabot.yml          # New Dependabot configuration

# Removed
.github/renovate.json5          # Existing Renovate configuration
.agent/skills/developer/        # Stale developer skills directory (+ SKILL.md inside)
ROADMAP.md                      # Stale roadmap document

# Updated
.github/workflows/test.yaml     # Remove renovate/** push trigger branch
docs/CONTRIBUTING.md            # Remove reference to .agent/skills on line 81
```

## Complexity Tracking

No constitution violations. No complexity justification required.
