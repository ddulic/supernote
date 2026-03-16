# Feature Specification: Switch to Dependabot and Remove Stale Artifacts

**Feature Branch**: `002-switch-dependabot`
**Created**: 2026-03-16
**Status**: Draft
**Input**: User description: "implement dependabot, remove current renovate, remove .agent/skills/developer, remove the roadmap"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automated Dependency Updates via Dependabot (Priority: P1)

A maintainer wants dependency update pull requests to be automatically created by Dependabot instead of Renovate, so that the project uses GitHub's native tooling without requiring an external service.

**Why this priority**: Dependency management automation is the core ask; everything else is cleanup. Without this, the project has no automated dependency updates.

**Independent Test**: Can be tested by verifying that Dependabot configuration exists, Renovate configuration is absent, and a dependency update PR is created by Dependabot on the next scheduled run.

**Acceptance Scenarios**:

1. **Given** the repository has no Dependabot configuration, **When** the Dependabot config is added, **Then** Dependabot creates pull requests for outdated dependencies on the defined schedule.
2. **Given** Renovate is configured in the repository, **When** Renovate configuration is removed, **Then** no Renovate bot activity occurs on future dependency changes.
3. **Given** Dependabot is active, **When** a new version of a dependency is published, **Then** Dependabot opens a pull request targeting the main branch within the scheduled window.

---

### User Story 2 - Remove Stale Developer Skills File (Priority: P2)

A contributor browsing the repository no longer encounters a stale `.agent/skills/developer` file that does not reflect current tooling or practices.

**Why this priority**: Removing outdated artifacts reduces confusion for contributors but does not affect runtime behaviour.

**Independent Test**: Can be tested by confirming the file (and its parent directory if empty) no longer exists in the repository.

**Acceptance Scenarios**:

1. **Given** the file `.agent/skills/developer` exists, **When** it is deleted, **Then** the file is absent from the repository and no references to it remain in active documentation.
2. **Given** the `.agent/` directory exists solely for that file, **When** the file is removed, **Then** the empty directory is also removed.

---

### User Story 3 - Remove ROADMAP File (Priority: P3)

A contributor browsing the repository no longer encounters a `ROADMAP.md` file that contains outdated or misleading future plans.

**Why this priority**: Roadmap removal is housekeeping; it reduces maintenance burden but has no functional impact.

**Independent Test**: Can be tested by confirming no roadmap file exists at the repository root.

**Acceptance Scenarios**:

1. **Given** a `ROADMAP.md` file exists at the repository root, **When** it is deleted, **Then** the file is absent and no links to it remain in `README.md` or other active documentation.

---

### Edge Cases

- What if Dependabot configuration already partially exists? The new config must fully replace any prior configuration.
- What if `.agent/skills/developer` is referenced from another tracked file? All such references must be removed.
- What if `ROADMAP.md` is linked from within the repository? All in-repo links must be removed or updated; external links (e.g., GitHub description) are out of scope.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The repository MUST include a valid Dependabot configuration covering all package ecosystems in use (Python packages and GitHub Actions workflows).
- **FR-002**: Dependabot MUST be configured to open pull requests targeting the main branch on a weekly schedule.
- **FR-003**: All Renovate configuration files (e.g., `renovate.json`, `.renovaterc`) MUST be removed from the repository.
- **FR-004**: The file `.agent/skills/developer` MUST be deleted; the parent directory MUST be removed if it becomes empty.
- **FR-005**: The `ROADMAP.md` file MUST be removed from the repository root.
- **FR-006**: Any in-repository links or references to removed files MUST be updated or removed.
- **FR-007**: The Dependabot configuration MUST assign a consistent label to its pull requests to distinguish them from manually created PRs.
- **FR-008**: Dependabot updates MUST be grouped by ecosystem: all Python dependency updates in one PR and all GitHub Actions updates in a separate PR, reducing total weekly PR volume.
- **FR-009**: Dependabot security updates MUST be enabled and configured to open pull requests immediately upon disclosure of a vulnerability, independent of the weekly schedule.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero Renovate-generated pull requests appear in the repository after the migration is merged.
- **SC-002**: At least one Dependabot pull request is opened within the first scheduled window after the configuration is merged.
- **SC-003**: No references to removed files (`ROADMAP.md`, `.agent/skills/developer`) remain in any tracked file in the repository.
- **SC-004**: The repository passes automated link-checking with zero broken internal links caused by the removals.

## Clarifications

### Session 2026-03-16

- Q: Should Dependabot PRs be grouped or individual? → A: Group by ecosystem (one PR for all Python updates, one PR for all GitHub Actions updates).
- Q: Should Dependabot security updates be enabled separately from scheduled version updates? → A: Yes — enable automated security updates (immediate PRs on CVE disclosure).

## Assumptions

- The project is hosted on GitHub; Dependabot is available without additional cost or configuration outside this repository.
- Dependency ecosystems to cover are Python (`pyproject.toml`) and GitHub Actions (`.github/workflows/`).
- A weekly update schedule is acceptable for this project's cadence.
- Renovate is the only third-party dependency-update service currently configured; no other bots require removal.
- The content of `ROADMAP.md` does not need to be migrated elsewhere (e.g., GitHub Issues or Projects).
- Removing `.agent/skills/developer` does not require a deprecation notice or migration guide for contributors.
