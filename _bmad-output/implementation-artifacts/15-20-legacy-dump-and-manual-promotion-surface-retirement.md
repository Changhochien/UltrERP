# Story 15.20: Legacy Dump And Manual-Promotion Surface Retirement

Status: done

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

- [x] Task 1: Inventory the remaining dump-era and manual-promotion defaults (AC: 1, 2)
  - [x] Audit `backend/common/config.py` defaults such as `legacy_import_data_dir`.
  - [x] Audit operator skill docs and command maps, especially `.agents/skills/ultr-erp-dump-import/` and `.agents/skills/legacy-import/`.
  - [x] Audit README and legacy docs for places that still present dump extraction or manual promotion as the routine path.
- [x] Task 2: Define the stability gate and fallback inventory before removing defaults (AC: 1, 2, 3)
  - [x] Recorded the minimum evidence required before defaults change, including repeatable live refresh success, scheduled shadow refresh state visibility, promotion-state visibility, and shared promotion-policy alerting.
  - [x] Identified which dump-era and manual-exception surfaces remain as archival or break-glass tools after the default-path switch.
  - [x] Added a written inventory of intentionally retained fallback surfaces and the operator scenario for each one.
- [x] Task 3: Update the repo defaults to the live gated refresh path (AC: 1, 2)
  - [x] Change operator docs and skill command maps so the default path is live-stage plus reviewed refresh plus scheduled shadow refresh plus reviewed promotion evaluation.
  - [x] Demote or archive manual-promotion notes from active operator instructions; retain only reviewed exception or override paths from Story 15.18.
  - [x] If config defaults still point to `legacy-migration-pipeline/extracted_data`, move that default to an explicit archival or opt-in path instead of the routine operator workflow.
- [x] Task 4: Archive retained dump assets outside the active workflow (AC: 2, 3)
  - [x] Documented that new raw dumps and extracted CSV batches must live in an operator-managed archival directory outside the repo and be passed explicitly through `--output`, `--source-dir`, `--export-dir`, or `LEGACY_IMPORT_DATA_DIR`.
  - [x] Preserved git history and research references for `legacy-migration-pipeline/` and reclassified that tree as historical reference material instead of deleting it.
  - [x] Marked remaining historical docs as archival when they are no longer part of the routine operator path.
- [x] Task 5: Validate the cleanup and documentation switch (AC: 1, 2, 3)
  - [x] Verified command maps, config defaults, and migration docs now point to the live gated refresh workflow by default and treat dump-era paths as archival or break-glass only.
  - [x] Added focused regression coverage and doc-audit validation steps for the updated command examples and fail-closed dump-path behavior.

## Implementation Notes

- `README.md` updated with `scripts/restore/reset-dev-db.sh` documentation — the new clean-rebuild path for local dev.
- `.agents/skills/legacy-import/` still exists as untracked — to be removed in Task 4.
- `backend/scripts/run_legacy_refresh.py` created as the new reviewed refresh entry point.
- `backend/domains/legacy_import/cli.py` updated with `register_all_models()` call.

## Dev Notes

- Retirement means changing the default path, not deleting every old surface immediately.
- Story 15.7 explicitly preserved the old extractor directory to protect git history. Honor that constraint unless the team performs a deliberate archival move.
- Manual exception handling from Story 15.18 may remain as a reviewed break-glass path. What should disappear is routine approval-driven promotion as the default operator workflow.
- Coordinate any config-default changes with automation or local environments that still rely on `LEGACY_IMPORT_DATA_DIR`.
- If archival storage moves outside the repo, document the destination and operator access rules before removing routine in-repo references.

### Stability Gate Definition

The repo-level default-path switch is now governed by the following explicit gate checklist:

1. Reviewed live refresh execution must succeed through `run_legacy_refresh` with machine-readable summary output under `_bmad-output/operations/legacy-refresh/`.
2. Scheduled shadow refresh must persist durable lane state through `latest-run.json` and `latest-success.json`, with blocked runs leaving the prior success pointer untouched.
3. Promotion evaluation must remain visible through `latest-promoted.json`, append-only `promotion-results/`, and audited `promotion-overrides/` artifacts when exception overrides are used.
4. Shared promotion-policy classification and reason codes must remain the alerting contract for refresh, scheduler, and promotion surfaces; manual approval is no longer the routine path.
5. Dump-era file workflows must be opt-in only: no silent repo-local default to `legacy-migration-pipeline/extracted_data`, and operator docs must route routine work to live-stage, reviewed refresh, scheduled shadow refresh, and promotion evaluation.

These gates define the minimum evidence expected before an operator treats the live gated path as the durable default in a configured environment. The story scope is to encode that contract and retire repo defaults that bypass it.

### Retained Fallback Inventory

The following surfaces intentionally remain after retirement, but only as archival or break-glass paths:

- `domains.legacy_import.cli extract`: archival SQL-dump decoding when an operator starts from a preserved raw dump.
- `domains.legacy_import.cli stage --source-dir ...`: break-glass replay from preserved CSV exports; now requires an explicit archival directory or `LEGACY_IMPORT_DATA_DIR`.
- `domains.legacy_import.cli currency-import --export-dir ...`: archival replay of `tbscurrency.csv`; now requires an explicit archival directory or `LEGACY_IMPORT_DATA_DIR`.
- `legacy-migration-pipeline/`: historical research, schema notes, and git-preserved extraction evidence; no longer part of the routine operator workflow.
- `scripts.run_legacy_promotion --allow-exception-override ...`: reviewed exception path for `exception-required` batches; not a default manual approval model.
- `scripts.apply_reconciliation_corrections --csv ... --approved-by ...`: explicit operator-approved correction application; never part of automatic refresh or promotion.

### Validation Evidence

- `cd backend && uv run pytest tests/domains/legacy_import/test_staging.py -k 'explicit_source_dir' tests/domains/legacy_import/test_currency.py -k 'explicit_export_dir' tests/domains/legacy_import/test_cli.py -k 'missing_dump or currency_import_cli_invokes_import or stage_cli_invokes_stage_import' -q` -> `4 passed`
- Doc audit: reviewed `backend/common/config.py`, `.agents/skills/legacy-import/`, `.agents/skills/ultr-erp-dump-import/`, `docs/legacy/migration-plan.md`, and `legacy-migration-pipeline/README.md` to confirm dump-era surfaces are archival or break-glass only and the live gated refresh path is the documented default.

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

GitHub Copilot (GPT-5.4)

### Debug Log References

- 2026-04-24 focused validation: `cd /Users/changtom/Downloads/UltrERP/backend && uv run pytest tests/domains/legacy_import/test_staging.py -k 'explicit_source_dir' tests/domains/legacy_import/test_currency.py -k 'explicit_export_dir' tests/domains/legacy_import/test_cli.py -k 'missing_dump or currency_import_cli_invokes_import or stage_cli_invokes_stage_import' -q`

### Completion Notes List

- Retired the repo-local dump default by making file-based staging and currency import fail closed unless operators pass an explicit archival directory or set `LEGACY_IMPORT_DATA_DIR` deliberately.
- Reclassified dump-era skill surfaces as archival or break-glass only and kept the live-stage, reviewed refresh, scheduled shadow refresh, and promotion evaluation path as the documented default.
- Added an explicit stability-gate definition and retained-fallback inventory so future cleanup decisions can be evaluated against one written contract instead of implicit assumptions.
- Preserved `legacy-migration-pipeline/` for historical research and git history, but marked it as archival reference material rather than a routine workflow surface.
- Closed the Epic 15 bookkeeping gap by documenting validation evidence and syncing sprint status with the implemented story state.

### File List

- `_bmad-output/implementation-artifacts/15-20-legacy-dump-and-manual-promotion-surface-retirement.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `.agents/skills/legacy-import/SKILL.md`
- `.agents/skills/legacy-import/command-map.md`
- `.agents/skills/ultr-erp-dump-import/SKILL.md`
- `.agents/skills/ultr-erp-dump-import/command-map.md`
- `backend/common/config.py`
- `backend/domains/legacy_import/cli.py`
- `backend/domains/legacy_import/currency.py`
- `backend/domains/legacy_import/shared.py`
- `backend/domains/legacy_import/staging.py`
- `backend/tests/domains/legacy_import/test_cli.py`
- `backend/tests/domains/legacy_import/test_currency.py`
- `backend/tests/domains/legacy_import/test_staging.py`
- `docs/legacy/migration-plan.md`
- `legacy-migration-pipeline/README.md`