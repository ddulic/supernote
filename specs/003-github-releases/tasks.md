# Tasks: GitHub Releases & Repository Cleanup

**Input**: Design documents from `/specs/003-github-releases/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅

**Organization**: Tasks grouped by user story. US2 (pinnable container tags) requires no independent implementation — it is fully satisfied by the US1 workflow fix (semver metadata extraction is already correct in `docker.yaml`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup

*No shared infrastructure setup required — this is a pure CI/CD configuration and file-deletion feature.*

---

## Phase 2: Foundational (Blocking Prerequisites)

*No blocking prerequisites — workflow edits and file deletions are independent.*

---

## Phase 3: User Story 1 — Versioned Release Workflow (Priority: P1) 🎯 MVP

**Goal**: Fix the Docker workflow so that versioned container builds only trigger on `release: published`, producing tags `v1.0.0`, `1.0`, `1`, and `latest`. Align the PyPI publish workflow to the same event.

**Independent Test**: Create a GitHub release tagged `v1.0.0` after merging and confirm the container registry receives all four expected tags within the same pipeline run; confirm no double-build occurs.

### Implementation for User Story 1

- [x] T001 [US1] Remove `push: tags: v*.*.*` block from the `on:` section in `.github/workflows/docker.yaml`, leaving only `push: branches: [main]`, `pull_request: branches: [main]`, and `release: types: [published]`
- [x] T002 [US1] Change `types: [created]` to `types: [published]` in the `on: release:` block of `.github/workflows/publish.yaml`

**Checkpoint**: Both workflow files updated. The Docker workflow no longer double-triggers on a release. Ready to merge and create `v1.0.0`.

---

## Phase 4: User Story 2 — Pinnable Container Version Tags (Priority: P2)

**Goal**: Ensure users can pull and pin any specific version tag of the container image.

**Independent Test**: After the `v1.0.0` release is published, pull the image by `v1.0.0` tag and verify it matches the release commit; later, after `v1.1.0` is published, confirm `v1.0.0` is unchanged.

> **Note**: No additional implementation tasks. The `docker/metadata-action` configuration already in `docker.yaml` produces `v1.0.0`, `1.0`, `1`, and `latest` tags from a semver release. Immutability of older tags is guaranteed by the container registry. US2 is fully satisfied by T001.

---

## Phase 5: User Story 3 — Repository Cleanup (Priority: P3)

**Goal**: Remove all four stale artifacts from the repository.

**Independent Test**: After these tasks, confirm none of the following paths exist in the repository: `.github/copilot-instructions.md`, `.github/failed-sync.md`, `.cruft.json`, `.github/workflows/cruft.yaml`.

### Implementation for User Story 3

- [x] T003 [P] [US3] Delete `.github/copilot-instructions.md` (`git rm .github/copilot-instructions.md`)
- [x] T004 [P] [US3] Delete `.github/failed-sync.md` (already removed — did not exist)
- [x] T005 [P] [US3] Delete `.cruft.json` (`git rm .cruft.json`)
- [x] T006 [P] [US3] Delete `.github/workflows/cruft.yaml` (`git rm .github/workflows/cruft.yaml`)

**Checkpoint**: All four files removed. Repository contains no stale Cruft or Copilot artifacts.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T007 Commit all changes with message: `chore: proper github releases, versioned docker tags, remove stale artifacts`
- [ ] T008 Open PR from `003-github-releases` → `main` and confirm CI (lint + test) passes
- [ ] T009 After PR is merged to `main`, create the initial release: `gh release create v1.0.0 --title "v1.0.0" --notes "Initial release." --latest` — this fires `release: published` and triggers the Docker build pipeline

**Checkpoint**: `v1.0.0` release live on GitHub; container image available in ghcr.io with all four version tags.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 3 (US1)**: No dependencies — start immediately
- **Phase 4 (US2)**: No independent tasks; satisfied by T001
- **Phase 5 (US3)**: No dependencies — can run in parallel with Phase 3
- **Phase 6 (Polish)**: Depends on Phase 3 + Phase 5 completion; T009 must run after PR is merged

### User Story Dependencies

- **US1 (P1)**: No dependencies — start immediately
- **US2 (P2)**: Depends on US1 (T001) — no independent tasks
- **US3 (P3)**: No dependencies — fully parallel with US1

### Within Each User Story

- T001 and T002 are independent (different files) — can be done in parallel
- T003, T004, T005, T006 are all independent (different files) — can all be done in parallel

---

## Parallel Opportunities

```bash
# US1 + US3 can be worked simultaneously:
Task T001: Edit .github/workflows/docker.yaml
Task T002: Edit .github/workflows/publish.yaml
Task T003: git rm .github/copilot-instructions.md
Task T004: git rm .github/failed-sync.md
Task T005: git rm .cruft.json
Task T006: git rm .github/workflows/cruft.yaml

# All 6 implementation tasks touch different files → fully parallelisable
```

---

## Implementation Strategy

### MVP (User Story 1 only — 2 tasks)

1. Complete T001 + T002 (workflow fixes)
2. Commit, open PR, merge
3. Run T009 (`gh release create v1.0.0`)
4. **VALIDATE**: Confirm container image appears in ghcr.io with tags `v1.0.0`, `1.0`, `1`, `latest`

### Full Delivery (all stories — 9 tasks total)

1. Complete T001–T006 in parallel (all independent file edits)
2. T007: commit
3. T008: open PR, wait for CI, merge
4. T009: create `v1.0.0` release

---

## Notes

- T009 is a post-merge manual step — it cannot be done on the feature branch
- All 6 implementation tasks (T001–T006) touch different files and can be executed in any order or simultaneously
- No Python source changes → no pytest run required for this feature's own changes (CI still runs the full test suite on PR)
- Commit after T001–T006 as a single atomic commit for clean history
