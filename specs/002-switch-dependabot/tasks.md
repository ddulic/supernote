# Tasks: Switch to Dependabot and Remove Stale Artifacts

**Input**: Design documents from `/specs/002-switch-dependabot/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅

**Organization**: Tasks are grouped by user story. All three user stories are independent and can be implemented in any order or in parallel.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Verification)

**Purpose**: Confirm current repository state before making changes

- [x] T001 Verify `.github/renovate.json5` exists and note its contents in `.github/`
- [x] T002 [P] Verify `.agent/skills/developer/` directory exists and contains only `SKILL.md`
- [x] T003 [P] Verify `ROADMAP.md` exists at repository root
- [x] T004 [P] Verify `docs/CONTRIBUTING.md` line 81 references `.agent/skills`
- [x] T005 [P] Verify `.github/workflows/test.yaml` contains `renovate/**` in push branches

**Checkpoint**: Current state confirmed — implementation of all three stories can now proceed independently

---

## Phase 2: User Story 1 - Dependabot Setup and Renovate Removal (Priority: P1) 🎯 MVP

**Goal**: Replace Renovate with Dependabot covering Python and GitHub Actions ecosystems, grouped by ecosystem on a weekly schedule with security updates enabled.

**Independent Test**: Verify `.github/dependabot.yml` exists and is valid YAML; verify `.github/renovate.json5` is absent; verify `.github/workflows/test.yaml` no longer contains `renovate/**`.

### Implementation for User Story 1

- [x] T006 [US1] Create `.github/dependabot.yml` with `pip` ecosystem entry: `directory: /`, `schedule.interval: weekly`, `groups.python-dependencies` covering all pip updates, `labels: ["dependencies"]`
- [x] T007 [US1] Add `github-actions` ecosystem entry to `.github/dependabot.yml`: `directory: /`, `schedule.interval: weekly`, `groups.github-actions-dependencies` covering all Actions updates, `labels: ["dependencies"]`
- [x] T008 [US1] Add `open-pull-requests-limit: 5` to each ecosystem entry in `.github/dependabot.yml`
- [x] T009 [US1] Delete `.github/renovate.json5`
- [x] T010 [US1] Update `.github/workflows/test.yaml`: remove `- renovate/**` from `on.push.branches` list

**Checkpoint**: Dependabot is configured and Renovate is fully removed. No CI branch triggers reference Renovate.

---

## Phase 3: User Story 2 - Remove Stale Developer Skills File (Priority: P2)

**Goal**: Remove `.agent/skills/developer/` directory and clean up its reference in `docs/CONTRIBUTING.md`.

**Independent Test**: Verify `.agent/skills/developer/` does not exist; verify `docs/CONTRIBUTING.md` contains no reference to `.agent/skills`.

### Implementation for User Story 2

- [x] T011 [US2] Delete `.agent/skills/developer/SKILL.md`
- [x] T012 [US2] Delete the now-empty `.agent/skills/developer/` directory
- [x] T013 [US2] Delete `.agent/skills/` if it is now empty; delete `.agent/` if it is also empty
- [x] T014 [US2] Update `docs/CONTRIBUTING.md`: remove or rewrite line 81 that references `.agent/skills` (the AI skills section is no longer valid)

**Checkpoint**: `.agent/skills/developer/` is fully removed and CONTRIBUTING.md contains no broken references.

---

## Phase 4: User Story 3 - Remove ROADMAP File (Priority: P3)

**Goal**: Delete `ROADMAP.md` from the repository root.

**Independent Test**: Verify `ROADMAP.md` does not exist at the repository root; verify no tracked file in the repository contains a link to `ROADMAP.md`.

### Implementation for User Story 3

- [x] T015 [US3] Delete `ROADMAP.md` from the repository root
- [x] T016 [P] [US3] Search all tracked files for links or references to `ROADMAP.md` and remove any found (confirmed none in non-spec files, but validate)

**Checkpoint**: `ROADMAP.md` is absent and no tracked file links to it.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all three stories

- [x] T017 [P] Validate `.github/dependabot.yml` parses as valid YAML (`python -c "import yaml; yaml.safe_load(open('.github/dependabot.yml'))"`)
- [x] T018 [P] Confirm no remaining references to `renovate` in `.github/workflows/` files (also fixed `lint.yaml` which had `renovate/**`)
- [x] T019 [P] Confirm `.agent/` directory is fully absent from the repository
- [x] T020 Run `script/lint` to confirm no linting regressions from file removals

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **User Stories (Phase 2–4)**: Depend on Phase 1 completion; all three are independent of each other
- **Polish (Phase 5)**: Depends on all three user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Independent — no dependency on US2 or US3
- **User Story 2 (P2)**: Independent — no dependency on US1 or US3
- **User Story 3 (P3)**: Independent — no dependency on US1 or US2

### Parallel Opportunities

- T002, T003, T004, T005 can all run in parallel during Phase 1
- US1, US2, and US3 phases can be executed in parallel once Phase 1 is complete
- T017, T018, T019 in the Polish phase can run in parallel

---

## Parallel Example: All User Stories

```bash
# After Phase 1 (Setup) completes, all three stories can run in parallel:
Story 1: T006 → T007 → T008 → T009 → T010
Story 2: T011 → T012 → T013 → T014
Story 3: T015 → T016
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verification)
2. Complete Phase 2: User Story 1 (Dependabot + Renovate removal)
3. **STOP and VALIDATE**: Confirm Dependabot config is valid, Renovate is gone, test.yaml is clean
4. Merge if ready; Stories 2 and 3 are low-risk follow-ups

### Incremental Delivery

1. Complete Phase 1 → Verified state
2. Complete US1 → Dependency management migrated (MVP)
3. Complete US2 → Stale skills file removed
4. Complete US3 → Stale roadmap removed
5. Complete Phase 5 → Final polish and validation

---

## Notes

- [P] tasks operate on different files and have no inter-dependencies
- No Python source changes — no tests required for this feature
- Commit after each user story phase for clean, reviewable history
- US2 must check whether `.agent/` parent directories become empty before deleting them
