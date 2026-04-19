# Story 15.20: Legacy Dump And Manual-Promotion Surface Retirement

Status: in-progress

## Story

As a platform maintainer,
I want obsolete dump-era and manual-promotion legacy surfaces retired behind explicit stability gates,
so that the repo defaults to the live gated refresh path and no longer carries duplicate operational workflows.

## Context

Story 15.7 unified the SQL-dump extraction path into the backend CLI, but intentionally preserved `legacy-migration-pipeline/` and other dump-era assets to avoid breaking history. Stories 15.12, 15.15, and 15.16 then established the live-stage, full refresh, and scheduled shadow-refresh path from the live legacy database. Stories 15.17 and 15.18 make that live path the reviewed default by adding automatic promotion and explicit promotion policy.

The repo still contains defaults and operator guidance that point to dump-era extracts or manual-promotion thinking. This story is the cleanup boundary: once the live gated refresh path proves stable, operator-facing defaults should move to the live path while archival dump assets and break-glass fallbacks are retained only where they are still justified.

## Acceptance Criteria

1. Given the live refresh plus automatic promotion path has met agreed stability gates, when the deprecation story executes, then the repository stops defaulting operators to dump-era sources or manual approval-driven promotion steps and docs, skills, and commands point to the live gated refresh workflow as the default path.
2. Given dump-era imports, manual promotion notes, or transitional remediation scripts still exist, when a cleanup pass is evaluated, then a surface may only be removed after its logic is absorbed into the standard refresh, promotion, alerting, or exception workflow and the cleanup records which fallback surfaces intentionally remain.
3. Given archived CSV extracts or raw dumps still need retention for audit, when active repo cleanup happens, then those artifacts are archived outside the working repo before deletion from default developer workflows.

## Tasks / Subtasks

- [ ] Task 1: Inventory the remaining dump-era and manual-promotion defaults (AC: 1, 2)
  - [ ] Audit `backend/common/config.py` defaults such as `legacy_import_data_dir`.
  - [ ] Audit operator skill docs and command maps, especially `.agents/skills/UltrERP-dump-import/` and `.agents/skills/legacy-import/`.
  - [ ] Audit README and legacy docs for places that still present dump extraction or manual promotion as the routine path.
- [ ] Task 2: Define the stability gate and fallback inventory before removing defaults (AC: 1, 2, 3)
  - [ ] Record the minimum evidence required before defaults change, such as repeatable live-stage success, scheduled shadow refresh stability, promotion-state visibility, and automatic promotion behavior with alerts.
  - [ ] Identify which dump-era and manual-exception surfaces remain as archival or break-glass tools after the default-path switch.
  - [ ] Keep a written inventory of intentionally retained fallback surfaces and the operator scenario for each one.
- [ ] Task 3: Update the repo defaults to the live gated refresh path (AC: 1, 2)
  - [ ] Change operator docs and skill command maps so the default path is live-stage plus reviewed refresh plus scheduled shadow refresh plus reviewed promotion evaluation.
  - [ ] Demote or archive manual-promotion notes from active operator instructions; retain only reviewed exception or override paths from Story 15.18.
  - [ ] If config defaults still point to `legacy-migration-pipeline/extracted_data`, move that default to an explicit archival or opt-in path instead of the routine operator workflow.
- [ ] Task 4: Archive retained dump assets outside the active workflow (AC: 2, 3)
  - [ ] Archive raw dumps and CSV extracts outside the active repo workflow before deleting or demoting default references.
  - [ ] Preserve git history and research references for `legacy-migration-pipeline/` rather than deleting blindly.
  - [ ] Mark remaining historical docs as archival when they are no longer part of the routine operator path.
- [ ] Task 5: Validate the cleanup and documentation switch (AC: 1, 2, 3)
  - [ ] Verify command maps, config defaults, and migration docs no longer present dump-era or manual-promotion surfaces as the default.
  - [ ] Add smoke checks or doc-validation steps for any updated command examples.

## Dev Notes

- Retirement means changing the default path, not deleting every old surface immediately.
- Story 15.7 explicitly preserved the old extractor directory to protect git history. Honor that constraint unless the team performs a deliberate archival move.
- Manual exception handling from Story 15.18 may remain as a reviewed break-glass path. What should disappear is routine approval-driven promotion as the default operator workflow.
- Coordinate any config-default changes with automation or local environments that still rely on `LEGACY_IMPORT_DATA_DIR`.
- If archival storage moves outside the repo, document the destination and operator access rules before removing routine in-repo references.

### Project Structure Notes

- Existing files likely touched:
  - `backend/common/config.py`
  - `.agents/skills/UltrERP-dump-import/SKILL.md`
  - `.agents/skills/UltrERP-dump-import/command-map.md`
  - `.agents/skills/legacy-import/command-map.md`
  - `docs/legacy/migration-plan.md`
  - `README.md`

### References

- `_bmad-output/planning-artifacts/epic-15.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-18.md`
- `_bmad-output/implementation-artifacts/15-7-unified-extract-and-import-cli.md`
- `_bmad-output/implementation-artifacts/15-12-live-legacy-db-stage-cli.md`
- `_bmad-output/implementation-artifacts/15-15-legacy-refresh-orchestrator.md`
- `_bmad-output/implementation-artifacts/15-16-scheduled-shadow-refresh-and-batch-state-tracking.md`
- `backend/common/config.py`
- `.agents/skills/UltrERP-dump-import/command-map.md`
- `.agents/skills/legacy-import/command-map.md`
- `docs/legacy/migration-plan.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

### Completion Notes List

### File List