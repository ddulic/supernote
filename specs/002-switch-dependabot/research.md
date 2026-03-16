# Research: Switch to Dependabot and Remove Stale Artifacts

**Date**: 2026-03-16
**Branch**: `002-switch-dependabot`

## Findings

### 1. Dependabot Configuration Format

**Decision**: Use `.github/dependabot.yml` with two `package-ecosystem` entries (`pip` and
`github-actions`) plus a top-level `security-updates` block.

**Rationale**: The `.github/dependabot.yml` file is the single supported location for Dependabot
version-update configuration on GitHub. Security updates are configured separately via the
`security-updates` key or enabled through GitHub repository settings; the recommended approach for
repo-as-code is to include it in the YAML.

**Key config decisions**:
- `package-ecosystem: pip` with `directory: /` covers `pyproject.toml` and `requirements_dev.txt`.
- `package-ecosystem: github-actions` with `directory: /` covers all workflow files under
  `.github/workflows/`.
- `schedule.interval: weekly` aligns with the spec.
- `groups` key used to batch all updates per ecosystem into a single PR (spec FR-008).
- `labels: ["dependencies"]` satisfies FR-007 (consistent label).
- `open-pull-requests-limit: 5` is the GitHub default and appropriate for this project's scale.

**Alternatives considered**:
- `schedule.interval: daily` — rejected; weekly is sufficient for this project cadence and reduces
  noise.
- Separate PRs per dependency (no grouping) — rejected per clarification (Option A chosen).

---

### 2. Renovate Removal

**Decision**: Delete `.github/renovate.json5`. No migration of its settings is needed.

**Rationale**: Renovate's `automerge: true` for minor/patch and `pre-commit` support are not
replicated in Dependabot by default, but the project constitution does not mandate auto-merge.
Dependabot's grouped PRs plus required CI gates are sufficient.

**Side effect**: `test.yaml` has `renovate/**` in its `on.push.branches` list (line 8). This
branch pattern was added so Renovate's branch-based auto-merge could trigger CI. It MUST be removed
alongside the Renovate config to avoid a dangling trigger.

---

### 3. `.agent/skills/developer/` Directory

**Decision**: Remove the entire `.agent/skills/developer/` directory (contains only `SKILL.md`).
If `.agent/skills/` and `.agent/` become empty after removal, remove those too.

**Rationale**: The directory is explicitly listed for removal in the feature request. It is
referenced only in `docs/CONTRIBUTING.md` (line 81); that reference must be removed.

---

### 4. ROADMAP.md Removal

**Decision**: Delete `ROADMAP.md` from the repository root. No content migration needed.

**Rationale**: All items in the roadmap are already marked `[x]` (completed). The file has no
active value. No in-repo links to `ROADMAP.md` were found in non-spec tracked files; only
`docs/CONTRIBUTING.md` references `.agent/skills`, not ROADMAP.

---

### 5. Files Requiring Updates

| File | Change Required |
|------|----------------|
| `.github/workflows/test.yaml` | Remove `- renovate/**` from `on.push.branches` (line 8) |
| `docs/CONTRIBUTING.md` | Remove/update line 81 referencing `.agent/skills` |
