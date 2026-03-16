# Research: GitHub Releases & Repository Cleanup

**Branch**: `003-github-releases` | **Date**: 2026-03-16
**Status**: Complete — no NEEDS CLARIFICATION items remain

---

## Finding 1: Docker Workflow Trigger Redundancy

**Decision**: Remove `push: tags: v*.*.*` trigger from `docker.yaml`; retain `release: published` as the sole trigger for versioned container builds.

**Rationale**: The current `docker.yaml` declares both `push: tags: v*.*.*` and `release: types: [published]`. When a maintainer creates a GitHub release against a tag, GitHub fires both events in sequence, causing the container image to be built and pushed twice. The `release: published` event is preferred because:
- It only fires when the release is explicitly marked published (drafts are excluded).
- It gives maintainers a window to prepare release notes before the image ships.
- It is the canonical event for "a release is ready for users".

**Alternatives considered**:
- Keep both triggers with a conditional: fragile; conditions on `github.event_name` inside a workflow with two event sources are error-prone.
- Use only `push: tags`: loses the draft-safety window and couples the release process to a raw tag push rather than an intentional release action.

---

## Finding 2: `latest` Tag Behaviour on Branch Builds

**Decision**: The `latest` tag produced by `docker/metadata-action` with `latest=true` (the current config) already applies only when building from a release event. No change needed.

**Rationale**: When `flavor: latest=true` is set, `docker/metadata-action` emits the `latest` tag for every build, including pushes to `main`. This means the `latest` image currently tracks `main`, not a release. After removing the tag-push trigger and retaining only `release: published` for the release job, the release job will correctly tag `latest`. The `main` branch build (kept for edge/dev tracking) can be left as-is — it overwrites `latest` on every merge to main, which is acceptable since the `latest` tag in this project represents the most recently built state (not a pinned stable version separate from `latest`). If strict "latest = last release only" is required, `flavor: latest=auto` would limit it; but `latest=true` is consistent with the spec's requirement that the `latest` tag always reflects the most recently published release.

**Alternatives considered**:
- `latest=auto`: Only sets `latest` on non-PR events matching the default branch or a semver tag — slightly stricter but adds complexity without clear benefit given the project's current usage.

---

## Finding 3: Publish Workflow (`publish.yaml`) Event Alignment

**Decision**: Update `publish.yaml` from `release: types: [created]` to `release: types: [published]` to align with the Docker workflow and prevent premature PyPI publishes from draft releases.

**Rationale**: `created` fires when a release is first saved (even as a draft), whereas `published` fires only when the maintainer explicitly publishes it. Using `published` in both workflows ensures Docker and PyPI artifacts ship at the same moment and are never triggered by accidental saves of draft releases.

**Alternatives considered**:
- Leave `publish.yaml` unchanged: inconsistent event semantics between the Docker and PyPI workflows; a draft save could trigger a PyPI publish prematurely.

---

## Finding 4: Files to Remove

**Decision**: Delete all four stale artifacts in a single commit.

| File | Location | Reason for removal |
|------|----------|--------------------|
| `copilot-instructions.md` | `.github/` | AI assistant config for GitHub Copilot; project no longer uses Copilot |
| `failed-sync.md` | `.github/` | Cruft sync failure artifact; no longer relevant after removing Cruft |
| `.cruft.json` | repo root | Cookiecutter template tracking config; Cruft tooling is being removed |
| `cruft.yaml` | `.github/workflows/` | Daily Cruft update automation; no longer needed |

**Alternatives considered**: None — all four files are confirmed stale with no active consumers.

---

## Finding 5: Initial v1.0.0 Release

**Decision**: Create the `v1.0.0` GitHub release after the workflow changes are merged to `main`. The release is created via the GitHub UI or `gh release create`, targeting the merge commit on `main`.

**Rationale**: The release must be created after the corrected workflow is live on `main`, so that the `release: published` trigger fires against the updated pipeline. Creating the tag before merging would use the old (potentially double-triggering) workflow.

**Alternatives considered**:
- Automate release creation in CI: adds complexity; releases require human curation of release notes.
- Tag the commit on the feature branch: tags on non-main branches do not follow the project's release conventions.
