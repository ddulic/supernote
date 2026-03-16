# Feature Specification: GitHub Releases & Repository Cleanup

**Feature Branch**: `003-github-releases`
**Created**: 2026-03-16
**Status**: Implemented
**Input**: User description: "implement proper releases in github, making sure that the docker containers are also correctly versioned and tagged, the initial version should be 1.0.0. also, remove .github/copilot-instructions.md, remove failed-sync.md, remove .cruft.json and the cruft workflow"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fully Automated Versioned Releases (Priority: P1)

A maintainer merges code to `main` using conventional commits (e.g., `feat:`, `fix:`). The release tooling automatically determines the next version, creates a release PR with a changelog, and — when that PR is merged — publishes a GitHub release and triggers the container image build with all appropriate version tags. No manual release steps are required at any point.

**Why this priority**: This is the core goal of the feature. All other stories depend on a working release process. Without versioned releases, users cannot reliably reference or pin specific versions of the software.

**Independent Test**: Can be fully tested by merging a `feat:` commit to `main`, confirming a release PR is created automatically, then merging that PR and verifying a GitHub release and container image appear with tags `v1.0.0`, `1.0`, `1`, and `latest` — without any manual steps.

**Acceptance Scenarios**:

1. **Given** a `feat:` or `fix:` commit is merged to `main`, **When** the release automation runs, **Then** a release PR is automatically created or updated with a changelog and the correct next version number.
2. **Given** a release PR exists, **When** it is merged, **Then** a GitHub release is published automatically with a tag (e.g., `v1.0.0`) and auto-generated release notes.
3. **Given** a GitHub release is published, **When** the container build pipeline runs, **Then** a container image is pushed with tags `v1.0.0`, `1.0`, `1`, and `latest`.
4. **Given** a release `v1.0.0` exists, **When** a subsequent release `v1.1.0` is published, **Then** the `v1.0.0` image remains available and unchanged.

---

### User Story 2 - Consume a Specific Container Version (Priority: P2)

A user wants to run a known, stable version of the project's container image. They can reference a specific version tag (e.g., `v1.0.0` or `1.0`) in their setup and be confident that image will never change or disappear.

**Why this priority**: Stable, immutable version tags are what make a release useful for end users. Without them, users cannot safely pin to a known-good version.

**Independent Test**: Can be fully tested by pulling the container image by a specific version tag after a release is published and verifying it matches the expected release.

**Acceptance Scenarios**:

1. **Given** a release `v1.0.0` has been published, **When** a user pulls the container image using the `v1.0.0` tag, **Then** they receive the image built from the code at that exact release.
2. **Given** a newer release `v2.0.0` exists, **When** a user pulls `v1.0.0`, **Then** they still receive the original `v1.0.0` image, unaffected by newer releases.

---

### User Story 3 - Repository Cleanup (Priority: P3)

A maintainer visits the repository and no longer sees stale, obsolete files that served previous tooling (`copilot-instructions.md`, `failed-sync.md`, `.cruft.json`, and the cruft automation workflow). The repository reflects only current, relevant tooling and documentation.

**Why this priority**: This is a housekeeping task that improves repository clarity. It is independent of the release process and delivers value by reducing confusion, but does not block the core release functionality.

**Independent Test**: Can be fully tested by inspecting the repository root and `.github/` directory and confirming the listed files and workflow are absent.

**Acceptance Scenarios**:

1. **Given** the cleanup has been applied, **When** a maintainer browses the repository, **Then** none of the following exist: `.github/copilot-instructions.md`, `.cruft.json`, `.github/workflows/cruft.yaml`. (`.github/failed-sync.md` was already absent.)
2. **Given** the cruft workflow has been removed, **When** automated workflows run, **Then** no workflow referencing cruft tooling executes.

---

### Edge Cases

- What happens if a release is published without a valid semantic version tag (e.g., a tag like `beta` or `nightly`)? The versioned release pipeline must not produce a `latest` or numbered tag for non-semver tags.
- What if the container build fails during a release? The GitHub release should still exist, but the container image must not be published with the version tag until a successful build occurs.
- What happens when a major version bump (e.g., `v1.x.x` → `v2.0.0`) occurs? The `latest` tag must update to the new major version; older major version images remain available under their respective tags.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The release process MUST be fully automated — no manual steps (tag pushing, release creation, or image publishing) are required from maintainers beyond merging PRs.
- **FR-002**: The release tooling MUST automatically determine the next semantic version from conventional commit messages (`feat:`, `fix:`, `feat!:`, etc.).
- **FR-003**: The release tooling MUST automatically create a GitHub release with a changelog when a release PR is merged to `main`.
- **FR-004**: When a GitHub release is published, the container image MUST be automatically built and pushed with version-specific tags.
- **FR-005**: Container images MUST be tagged with the full version (`v1.0.0`), minor (`1.0`), major (`1`), and `latest` for each published release.
- **FR-006**: The `latest` container tag MUST always point to the most recently published release.
- **FR-007**: Older version-specific container tags MUST remain available and immutable after newer releases are published.
- **FR-008**: The initial release version MUST be `v1.0.0`.
- **FR-009**: The file `.github/copilot-instructions.md` MUST be removed from the repository.
- **FR-010**: The file `.cruft.json` MUST be removed from the repository.
- **FR-011**: The cruft automation workflow MUST be removed from the repository.

### Key Entities

- **Release**: A named, versioned snapshot of the project published on GitHub, identified by a semantic version tag (e.g., `v1.0.0`).
- **Container Image**: A runnable, immutable artifact produced from a release, stored in the container registry and addressable by one or more version tags.
- **Version Tag**: A label applied to a container image that identifies the release it was built from (full version, minor, major, or `latest`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The first release (`v1.0.0`) is published on GitHub and a corresponding container image is available in the registry with zero manual steps beyond merging the release PR.
- **SC-002**: 100% of published releases result in container images tagged with all four tag formats (full semver, minor, major, `latest`) within the same pipeline run.
- **SC-003**: Zero stale files (copilot-instructions, cruft config, cruft workflow) remain in the repository after the cleanup is applied.
- **SC-004**: Maintainers require zero manual steps to publish a release — writing conventional commits and merging PRs is sufficient.
- **SC-005**: A user pulling a pinned version tag (e.g., `v1.0.0`) always receives the same image, regardless of how many newer releases have been published.

## Assumptions

- The container registry in use is the GitHub Container Registry (ghcr.io), consistent with the existing Docker workflow.
- The Python package publish workflow (`publish.yaml`) is aligned to the same `release: published` event and will publish to PyPI on each release, but PyPI publishing details are not the focus of this feature.
- Conventional commits (`feat:`, `fix:`, `chore:`, `feat!:` for breaking changes) are required for release-please to determine version bumps correctly.
- `failed-sync.md` was found to be already absent from the repository at implementation time.
- `pyproject.toml` version was bumped from `0.14.8` to `1.0.0` as part of this feature; release-please will manage it for all future releases.
