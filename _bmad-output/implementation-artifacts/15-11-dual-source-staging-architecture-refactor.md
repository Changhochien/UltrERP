# Story 15.11: Dual-Source Staging Architecture Refactor

Status: ready-for-dev

## Story

As a migration operator,
I want file and live source staging to share one orchestration path,
So that both source modes preserve the same batch semantics, control-table behavior, and `raw_legacy` contracts.

## Acceptance Criteria

1. Given file-based staging already exists, when the staging domain is refactored around source adapters plus a shared loader/orchestration layer, then `legacy-import stage` remains backward compatible for manifest-backed CSV imports.
2. Given either a file adapter or live adapter supplies discovered tables and row streams, when the shared orchestration stages them, then attempt numbering, overlapping-table cleanup, raw-table recreation, lineage fields, validation hooks, and control-table persistence remain consistent with the current file-based behavior.
3. Given the current stage result and audit structures assume a permanent source directory, when the refactor is complete, then shared stage summaries and persisted source metadata use a source-agnostic descriptor that works for both file and live runs without leaking secrets.
4. Given the shared orchestration becomes the durable implementation boundary, when focused tests run, then adapter-independent behavior is covered for reruns, failures, control-table persistence, and stage-summary output.

## Tasks / Subtasks

- [ ] Task 1 (AC: 1, 2)
  - [ ] Extract source-adapter interfaces and shared orchestration from `run_stage_import()`.
  - [ ] Preserve the current file-based adapter behavior for manifest validation and selected-table filtering.
- [ ] Task 2 (AC: 2, 3)
  - [ ] Refactor shared stage result and source metadata types so they no longer depend on `source_dir` semantics alone.
  - [ ] Ensure `legacy_import_runs.source_path` stores non-secret source descriptors that remain useful for validation and operator audits.
- [ ] Task 3 (AC: 2, 4)
  - [ ] Keep the existing raw-table loader semantics for `_batch_id`, `_source_row_number`, `_legacy_pk`, and table-level validation.
  - [ ] Add regression tests for adapter-neutral rerun and failure handling.

## Dev Notes

- `run_stage_import()` currently combines file discovery with staging orchestration, transaction control, and control-table writes in one function.
- The safest refactor is to keep one shared raw-loader/audit path and treat file-based and live-db reads as pluggable source adapters.
- Validation and downstream phases already depend on the staged-table contract rather than the original source type, so this refactor should avoid touching normalization or canonical import behavior.

### Project Structure Notes

- Primary touch points are `backend/domains/legacy_import/staging.py`, `backend/domains/legacy_import/cli.py`, `backend/common/models/legacy_import.py`, and the staging/CLI tests.
- This story should not require a new epic; it extends Epic 15's existing staging architecture.

### References

- `backend/domains/legacy_import/staging.py`
- `backend/common/models/legacy_import.py`
- `backend/domains/legacy_import/cli.py`
- `backend/tests/domains/legacy_import/test_staging.py`
- `backend/tests/domains/legacy_import/test_cli.py`
- `_bmad-output/planning-artifacts/epic-15.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Planning-only story creation; no runtime logs yet.

### Completion Notes List

- Story created to isolate the shared staging boundary before the live adapter and CLI are added.

### File List

- `_bmad-output/planning-artifacts/epic-15.md`
- `_bmad-output/implementation-artifacts/15-11-dual-source-staging-architecture-refactor.md`

