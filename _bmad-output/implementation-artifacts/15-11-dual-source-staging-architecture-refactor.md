# Story 15.11: Dual-Source Staging Architecture Refactor

Status: completed

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

- [x] Task 1 (AC: 1, 2)
  - [x] Extract source-adapter interfaces and shared orchestration from `run_stage_import()`.
  - [x] Preserve the current file-based adapter behavior for manifest validation and selected-table filtering.
- [x] Task 2 (AC: 2, 3)
  - [x] Refactor shared stage result and source metadata types so they no longer depend on `source_dir` semantics alone.
  - [x] Ensure `legacy_import_runs.source_path` stores non-secret source descriptors that remain useful for validation and operator audits.
- [x] Task 3 (AC: 2, 4)
  - [x] Keep the existing raw-table loader semantics for `_batch_id`, `_source_row_number`, `_legacy_pk`, and table-level validation.
  - [x] Add regression tests for adapter-neutral rerun and failure handling.

### Review Findings

- [x] [Review][Patch] Record a failed stage attempt and close the source adapter when discovery fails before any table staging begins [backend/domains/legacy_import/staging.py:1410]

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

### Implementation Plan

- Extract a shared source-adapter boundary so file-backed staging and future live-db staging can both call the same orchestration path.
- Move batch metadata to a source-agnostic descriptor so stage summaries and `legacy_import_runs.source_path` remain useful without assuming a permanent directory.
- Lock the refactor with adapter-neutral rerun/failure tests plus a live-adapter integration test that exercises the shared raw loader semantics.

### Debug Log References

- Added `StageSourceDescriptor`, file/live source adapters, and the shared `run_stage_import_from_source()` orchestration in `backend/domains/legacy_import/staging.py`.
- Verified backward-compatible CLI output for file staging and source-agnostic summary output in `backend/domains/legacy_import/cli.py` plus `backend/tests/domains/legacy_import/test_cli.py`.
- Added adapter-neutral rerun/failure coverage and a focused live-adapter integration test in `backend/tests/domains/legacy_import/test_staging.py`.
- Fixed the AP payment holding-row call sites to pass `row_identity`, which kept the full legacy-import regression slice green after the staging refactor validation run.
- Focused validation passed with `cd backend && uv run python -m pytest tests/domains/legacy_import/test_staging.py tests/domains/legacy_import/test_cli.py -q` (`41 passed in 0.34s`) and `cd backend && uv run python -m ruff check domains/legacy_import/staging.py tests/domains/legacy_import/test_staging.py` (`All checks passed`).
- Full legacy-import regression passed with `cd backend && uv run python -m pytest tests/domains/legacy_import -q` (`112 passed in 0.32s`).

### Completion Notes List

- Added a shared staging orchestration boundary that accepts pluggable source adapters while preserving existing file-based manifest validation, selected-table filtering, attempt numbering, rerun cleanup, and raw-table loading semantics.
- Added a live legacy source adapter plus `run_live_stage_import()` as the durable implementation boundary for Story 15.12 without changing the existing `legacy-import stage` CLI contract.
- Refactored `StageBatchResult` and control-table source metadata to use non-secret source descriptors such as `legacy-db:cao50001/public` instead of assuming a filesystem-only `source_dir`.
- Added regression coverage for adapter-neutral reruns, failure persistence, source-agnostic stage summaries, and the live-adapter shared-loader path.
- Fixed adjacent legacy-import validation blockers so the full `tests/domains/legacy_import` slice now passes cleanly.
- Review follow-up now records failed attempts even when source discovery fails before table staging starts, and guarantees the source adapter closes on that path.

### File List

- `backend/domains/legacy_import/staging.py`
- `backend/domains/legacy_import/cli.py`
- `backend/domains/legacy_import/ap_payment_import.py`
- `backend/tests/domains/legacy_import/test_staging.py`
- `backend/tests/domains/legacy_import/test_cli.py`
- `backend/tests/domains/legacy_import/test_currency.py`
- `_bmad-output/implementation-artifacts/15-11-dual-source-staging-architecture-refactor.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-04-18: Refactored legacy staging around shared source adapters and source-agnostic batch descriptors while preserving the file-stage CLI behavior.
- 2026-04-18: Added adapter-neutral and live-adapter staging regressions, then fixed adjacent legacy-import test blockers so the full legacy-import suite passes.
