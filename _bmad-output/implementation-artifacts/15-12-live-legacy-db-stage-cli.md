# Story 15.12: Live Legacy DB Stage CLI

Status: review

## Story

As a migration operator,
I want a `legacy-import live-stage` command that stages selected tables from the live legacy DB over Tailscale,
So that I can run the migration pipeline without generating a SQL dump or extracted CSV set first.

## Acceptance Criteria

1. Given live DB settings are configured and the connector contract is approved, when I run `legacy-import live-stage --batch-id <id> [--table ...]`, then the CLI discovers `public` tables or limits to the requested subset and stages them into `raw_legacy` through the shared orchestration path.
2. Given a live-stage run completes, when operator summaries and control tables are inspected, then the command returns the same operator-friendly batch/table summary shape as file-based `stage` and records non-secret live-source metadata in `legacy_import_runs` and `legacy_import_table_runs`.
3. Given operators or agents need to use the new flow safely, when docs and skills are updated, then `.env.example` and the legacy-import skill document the `live-stage` command and required `LEGACY_DB_*` settings without embedding credentials.
4. Given the live connection, table discovery, or table load fails, when the command aborts, then the operator receives clear diagnostics that distinguish the failure type and no partial committed stage snapshot is left behind for that batch attempt.

## Tasks / Subtasks

- [x] Task 1 (AC: 1, 2, 4)
  - [x] Add the `live-stage` subcommand and runner to the legacy-import CLI.
  - [x] Implement live table discovery, selected-table filtering, and shared staging invocation through the approved source adapter.
- [x] Task 2 (AC: 2, 4)
  - [x] Preserve batch-atomic stage semantics and control-table audit behavior for live runs.
  - [x] Add focused CLI/staging tests for success, selected-table scope, and failure diagnostics.
- [x] Task 3 (AC: 3)
  - [x] Update `.env.example` and legacy-import skill documentation for the new command.
  - [x] Keep operator-facing source metadata non-secret in console output and persisted control tables.

### Review Findings

- [x] [Review][Patch] Live-source queries now apply deterministic ordering before `_source_row_number` assignment so live reruns do not depend on arbitrary heap order [backend/domains/legacy_import/staging.py:556]
- [x] [Review][Patch] Explicit `--table` scope now bypasses full required-table presence checks so subset staging works for both live and file sources [backend/domains/legacy_import/staging.py:341, 857]
- [x] [Review][Patch] Connect-time asyncpg server errors (for example invalid catalog/auth failures) now surface as connection failures instead of misleading query failures [backend/domains/legacy_import/cli.py:581]

## Dev Notes

- The new CLI should feel like `stage`, not like a separate import subsystem; source acquisition changes, but raw staging semantics must not.
- The live-source command should reuse the shared orchestration from Story 15.11 instead of introducing a parallel loader path.
- Documentation updates belong in the same story because Story 15.6 already established the skill as the safe operator-facing wrapper over the CLI.

### Project Structure Notes

- Expected code touch points are `backend/domains/legacy_import/cli.py`, `backend/domains/legacy_import/staging.py`, `.agents/skills/legacy-import/`, and focused tests.
- Any optional live probe used during validation should remain separate from normal runtime behavior and should never persist credentials.

### References

- `backend/docs/SPEC-dual-source-staging.md`
- `backend/domains/legacy_import/cli.py`
- `backend/domains/legacy_import/staging.py`
- `.agents/skills/legacy-import/SKILL.md`
- `_bmad-output/planning-artifacts/epic-15.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `cd backend && uv run pytest tests/domains/legacy_import/test_cli.py tests/domains/legacy_import/test_staging.py tests/test_legacy_import_skill.py -q`
- `cd backend && uv run pytest tests/domains/legacy_import -q`
- `cd backend && uv run ruff check domains/legacy_import/cli.py domains/legacy_import/__init__.py tests/domains/legacy_import/test_cli.py tests/domains/legacy_import/test_staging.py tests/test_legacy_import_skill.py`
- `cd backend && uv run python -m domains.legacy_import.cli live-stage --help`
- `cd backend && uv run pytest tests/domains/legacy_import/test_cli.py tests/domains/legacy_import/test_staging.py tests/test_legacy_import_skill.py -q && uv run ruff check domains/legacy_import/cli.py domains/legacy_import/staging.py tests/domains/legacy_import/test_cli.py tests/domains/legacy_import/test_staging.py tests/test_legacy_import_skill.py`
- `cd backend && uv run pytest -q` (fails during collection on the pre-existing duplicate `test_service.py` module names under `tests/domains/intelligence/` and `tests/domains/product_analytics/`)
- `cd backend && uv run ruff check` (fails on pre-existing repo-wide lint violations outside this story's files)

### Completion Notes List

- Added the `legacy-import live-stage` CLI command with default `public` source discovery, repeatable `--table` filtering, and shared `run_live_stage_import()` orchestration.
- Added operator-facing live-stage diagnostics that distinguish connection, discovery/contract, compatibility, and table-load failures without exposing secrets.
- Extended focused coverage for the new CLI path, live selected-table scoping, and skill/documentation expectations; the targeted and full legacy-import test slices pass.
- Updated the legacy-import skill, command map, safety guidance, and `.env.example` to document `live-stage` and the required `LEGACY_DB_*` environment variables.
- Review follow-up hardened live-stage reruns by making live query ordering deterministic before `_source_row_number` assignment.
- Review follow-up aligned explicit `--table` scope with the CLI contract for both live and file staging instead of requiring the full configured table set first.
- Review follow-up now classifies connect-time asyncpg server rejections as connection failures and locks the behavior with focused CLI regressions.
- Repo-wide backend `pytest -q` and `ruff check` still fail on unrelated pre-existing issues outside the Story 15.12 change set.

### File List

- `.agents/skills/legacy-import/SKILL.md`
- `.agents/skills/legacy-import/command-map.md`
- `.agents/skills/legacy-import/safety-and-validation.md`
- `.env.example`
- `backend/domains/legacy_import/__init__.py`
- `backend/domains/legacy_import/cli.py`
- `backend/tests/domains/legacy_import/test_cli.py`
- `backend/tests/domains/legacy_import/test_staging.py`
- `backend/tests/test_legacy_import_skill.py`
- `_bmad-output/implementation-artifacts/15-12-live-legacy-db-stage-cli.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-04-18: Added the `legacy-import live-stage` CLI surface, live-source error classification, and selected-table coverage on top of the shared staging adapter path.
- 2026-04-18: Updated legacy-import operator docs and environment guidance for `live-stage` and the required `LEGACY_DB_*` settings.
- 2026-04-18: Applied review follow-ups for deterministic live row ordering, explicit selected-table subset staging, and accurate connect-time error classification; focused Story 15.12 pytest and Ruff now pass cleanly.
