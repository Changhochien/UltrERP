# Story 15.12: Live Legacy DB Stage CLI

Status: ready-for-dev

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

- [ ] Task 1 (AC: 1, 2, 4)
  - [ ] Add the `live-stage` subcommand and runner to the legacy-import CLI.
  - [ ] Implement live table discovery, selected-table filtering, and shared staging invocation through the approved source adapter.
- [ ] Task 2 (AC: 2, 4)
  - [ ] Preserve batch-atomic stage semantics and control-table audit behavior for live runs.
  - [ ] Add focused CLI/staging tests for success, selected-table scope, and failure diagnostics.
- [ ] Task 3 (AC: 3)
  - [ ] Update `.env.example` and legacy-import skill documentation for the new command.
  - [ ] Keep operator-facing source metadata non-secret in console output and persisted control tables.

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

- Planning-only story creation; no runtime logs yet.

### Completion Notes List

- Story created for the operator-facing `live-stage` CLI surface and its documentation handoff.

### File List

- `_bmad-output/planning-artifacts/epic-15.md`
- `_bmad-output/implementation-artifacts/15-12-live-legacy-db-stage-cli.md`

