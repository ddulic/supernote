# Feature Specification: GitHub Releases & Repository Cleanup

**Feature Branch**: `003-github-releases`
**Created**: 2026-03-16
**Status**: Draft
**Input**: User description: "implement proper releases in github, making sure that the docker containers are also correctly versioned and tagged, the initial version should be 1.0.0. also, remove .github/copilot-instructions.md, remove failed-sync.md, remove .cruft.json and the cruft workflow"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a Versioned Release (Priority: P1)

A maintainer wants to publish a new release of the project. They create a release on GitHub tagged with a version number (e.g., `v1.0.0`). Upon doing so, the project's container image is automatically built, tagged with that exact version, and published to the container registry — making it trivially discoverable and pinnable for users.

**Why this priority**: This is the core goal of the feature. All other stories depend on a working release process. Without versioned releases, users cannot reliably reference or pin specific versions of the software.

**Independent Test**: Can be fully tested by creating a GitHub release tagged `v1.0.0` and verifying that the container image appears in the registry with tags `v1.0.0`, `1.0`, `1`, and `latest`.

**Acceptance Scenarios**:

1. **Given** the project has no releases, **When** a maintainer creates the first GitHub release tagged `v1.0.0`, **Then** a container image is published with tags `v1.0.0`, `1.0`, `1`, and `latest`.
2. **Given** a release `v1.0.0` exists, **When** a maintainer creates `v1.1.0`, **Then** the container image is published with tags `v1.1.0`, `1.1`, `1`, and `latest`; the `v1.0.0` image remains available and unchanged.
3. **Given** an invalid or non-semver tag is pushed, **When** the automation runs, **Then** no versioned release image is produced and the `latest` tag is not updated.

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

1. **Given** the cleanup has been applied, **When** a maintainer browses the repository, **Then** none of the following exist: `.github/copilot-instructions.md`, `.github/failed-sync.md`, `.cruft.json`, `.github/workflows/cruft.yaml`.
2. **Given** the cruft workflow has been removed, **When** automated workflows run, **Then** no workflow referencing cruft tooling executes.

---

### Edge Cases

- What happens if a release is published without a valid semantic version tag (e.g., a tag like `beta` or `nightly`)? The versioned release pipeline must not produce a `latest` or numbered tag for non-semver tags.
- What if the container build fails during a release? The GitHub release should still exist, but the container image must not be published with the version tag until a successful build occurs.
- What happens when a major version bump (e.g., `v1.x.x` → `v2.0.0`) occurs? The `latest` tag must update to the new major version; older major version images remain available under their respective tags.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST have an initial release tagged `v1.0.0` as the baseline versioned release.
- **FR-002**: When a versioned release is published, the container image MUST be automatically built and pushed to the container registry with version-specific tags.
- **FR-003**: Container images MUST be tagged with the full version (`v1.0.0`), minor (`1.0`), major (`1`), and `latest` for each published release.
- **FR-004**: The `latest` container tag MUST always point to the most recently published release.
- **FR-005**: Older version-specific container tags MUST remain available and immutable after newer releases are published.
- **FR-006**: The release pipeline MUST only produce versioned container builds for tags following semantic versioning format (`vMAJOR.MINOR.PATCH`).
- **FR-007**: The file `.github/copilot-instructions.md` MUST be removed from the repository.
- **FR-008**: The file `.github/failed-sync.md` MUST be removed from the repository.
- **FR-009**: The file `.cruft.json` MUST be removed from the repository.
- **FR-010**: The cruft automation workflow MUST be removed from the repository.

### Key Entities

- **Release**: A named, versioned snapshot of the project published on GitHub, identified by a semantic version tag (e.g., `v1.0.0`).
- **Container Image**: A runnable, immutable artifact produced from a release, stored in the container registry and addressable by one or more version tags.
- **Version Tag**: A label applied to a container image that identifies the release it was built from (full version, minor, major, or `latest`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The first release (`v1.0.0`) is published on GitHub and a corresponding container image is available in the registry within one automated pipeline run of tagging.
- **SC-002**: 100% of published releases result in container images tagged with all four tag formats (full semver, minor, major, `latest`) within the same pipeline run.
- **SC-003**: Zero stale files (copilot-instructions, failed-sync, cruft config, cruft workflow) remain in the repository after the cleanup is applied.
- **SC-004**: Maintainers can publish a new release without any manual steps beyond creating the GitHub release — container tagging and publishing is fully automated.
- **SC-005**: A user pulling a pinned version tag (e.g., `v1.0.0`) always receives the same image, regardless of how many newer releases have been published.

## Assumptions

- The container registry in use is the GitHub Container Registry (ghcr.io), consistent with the existing Docker workflow.
- The Python package publish workflow is out of scope for this feature; only container image versioning is addressed here.
- "Proper releases" means using GitHub's native Releases feature (not just bare git tags) to ensure release notes are visible on the repository.
- The existing Docker workflow already handles semver tag triggers; this feature formalises the process and ensures the initial `v1.0.0` release is created correctly.
- `failed-sync.md` is located at `.github/failed-sync.md` based on repository inspection.
