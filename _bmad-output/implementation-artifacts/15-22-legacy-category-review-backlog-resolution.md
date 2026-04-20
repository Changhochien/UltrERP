# Story 15.22: Legacy Category Review Backlog Resolution

Status: done

## Story

As a migration operator,
I want the live legacy category-review backlog closed with grounded rules and auditable review decisions,
so that the refreshed batch reaches a clean validation state without hiding unresolved category debt behind unsafe heuristics.

## Context

Story 15.9 introduced the derived-category rule engine, provenance fields, override tables, and CLI-backed review workflow, but the live `cao50001-live-refresh` batch still carried a long provisional tail after the initial hardening passes. The remaining work split into two buckets:

- small evidence-backed family slices that could safely move out of fallback by code and name heuristics
- a residual ambiguous tail that could not be promoted to narrower product families with enough confidence and therefore needed explicit analyst-style review decisions

This story records the final closure pass that turned the batch from a warning state into a clean validated checkpoint.

## Acceptance Criteria

1. Given the live `cao50001-live-refresh` batch still contains category-review candidates after Story 15.9, when the final closure pass runs, then any safe evidence-backed family rules are added first and validated with focused normalization tests before being applied to staging.
2. Given high-confidence non-merchandise exclusions or unresolved fallback rows remain after heuristic cleanup, when no stronger category evidence exists, then they are resolved through the existing category-review export/import workflow with auditable keep-current decisions instead of ad hoc SQL mutation.
3. Given the backlog is fully resolved, when canonical import and validation rerun, then the latest attempt reports `status=clean`, `blockers=0`, and `0` remaining category-review candidates for the batch.

## Tasks / Subtasks

- [x] Task 1: Close grounded family tails with deterministic rules (AC: 1)
  - [x] Added `FON*`, `FOZ*`, and exact `FO037` handling as grounded `V-Belts` families.
  - [x] Added focused regression coverage for those family tails in `test_normalization.py`.
  - [x] Applied the new rules to staging and replayed the reduced state.

- [x] Task 2: Route obvious consumables and belt hardware out of fallback (AC: 1, 2)
  - [x] Added `PK-*` exclusion handling plus printer toner, printer ribbon, paper, and `皮帶勾` name-token routing.
  - [x] Validated those rules with focused normalization tests.
  - [x] Applied the slice to staging and confirmed the `皮帶勾` hardware row left review while the non-merchandise rows were correctly reclassified but still surfaced as `excluded_path` candidates.

- [x] Task 3: Resolve the remaining review backlog through the audited operator path (AC: 2)
  - [x] Created a review CSV for the 10 high-confidence `excluded_path` non-merchandise rows and imported `keep_current` decisions.
  - [x] Generated and imported a second review CSV for the remaining 91 fallback candidates, approving `Other Power Transmission` as the reviewed broad catch-all category where no narrower evidence-backed family could be justified.
  - [x] Preserved the review workflow semantics instead of changing `_review_reason_for_derivation()` to silently suppress `excluded_path` candidates globally.

- [x] Task 4: Replay and validate the resolved batch state (AC: 3)
  - [x] Validated attempt 20 at `102` remaining candidates after the grounded `FON/FOZ/FO037` reduction.
  - [x] Replayed and validated attempt 21 at `91` remaining candidates after the consumables slice plus excluded-path review import.
  - [x] Replayed and validated attempt 22 with `status=clean`, `blockers=0`, and `0` remaining category-review candidates.

## Dev Notes

### Scope Boundary

- This story is an operational closure pass for Story 15.9, not a new category-taxonomy redesign.
- The fix deliberately distinguishes between:
  - grounded heuristic improvements that belong in `normalization.py`
  - residual ambiguity that should be resolved through the reviewed category-review workflow
- The story does not claim additional evidence for ambiguous families such as `X346`, `TR04`, `A-2`, or `LHS-55`; those rows were reviewed and explicitly accepted as `Other Power Transmission`.

### Key Decisions

- Kept `excluded_path` review behavior intact after confirming tests and workflow semantics intentionally rely on those rows being exportable/importable for analyst review.
- Used `keep_current` review imports for both the high-confidence non-merchandise exclusions and the ambiguous fallback tail so the final batch state remains fully auditable in `raw_legacy.product_category_override`.
- Preserved the review decision CSVs under `_bmad-output/validation/legacy-import/` as reusable audit artifacts.

### Validation Evidence

- `cd backend && uv run pytest -q tests/domains/legacy_import/test_normalization.py -k 'grounded_remaining_family_tails'`
- `cd backend && uv run pytest -q tests/domains/legacy_import/test_normalization.py -k 'consumables_and_belt_hooks or routes_belt_joint_supplies or flags_non_merchandise'`
- `cd backend && uv run pytest -q tests/domains/legacy_import/test_normalization.py tests/domains/legacy_import/test_category_review.py` -> `32 passed`
- `cd backend && uv run python -m domains.legacy_import.cli validate-import --batch-id cao50001-live-refresh --attempt-number 20 --tenant-id 00000000-0000-0000-0000-000000000001 --schema raw_legacy`
- `cd backend && uv run python -m domains.legacy_import.cli validate-import --batch-id cao50001-live-refresh --attempt-number 21 --tenant-id 00000000-0000-0000-0000-000000000001 --schema raw_legacy`
- `cd backend && uv run python -m domains.legacy_import.cli validate-import --batch-id cao50001-live-refresh --attempt-number 22 --tenant-id 00000000-0000-0000-0000-000000000001 --schema raw_legacy` -> `status=clean, blockers=0`

## Dev Agent Record

### Agent Model Used

GitHub Copilot (GPT-5.4)

### Completion Notes List

- Added a grounded `V-Belts` family rule for `FON*`, `FOZ*`, and exact `FO037` legacy codes.
- Added conservative consumable routing for `PK-*`, printer toner, printer ribbon, paper, and `皮帶勾`.
- Confirmed `excluded_path` rows are intentionally reviewable and resolved them through CSV-backed review imports instead of weakening the review predicate.
- Resolved the remaining ambiguous fallback tail by approving `Other Power Transmission` through the same review workflow.
- Promoted the batch from attempt 20 (`102` candidates) to attempt 21 (`91` candidates) and finally to attempt 22 (`0` candidates, `status=clean`).

### File List

- `_bmad-output/implementation-artifacts/15-22-legacy-category-review-backlog-resolution.md`
- `_bmad-output/validation/legacy-import/cao50001-live-refresh-excluded-path-review.csv`
- `_bmad-output/validation/legacy-import/cao50001-live-refresh-fallback-tail-review.csv`
- `backend/domains/legacy_import/normalization.py`
- `backend/tests/domains/legacy_import/test_normalization.py`