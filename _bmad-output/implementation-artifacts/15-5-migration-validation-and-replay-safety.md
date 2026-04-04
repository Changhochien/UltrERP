# Story 15.5: Migration Validation and Replay Safety

Status: ready-for-dev

## Story

As a cutover owner,
I want migration runs to emit actionable validation reports and support safe reruns,
So that cutover is blocked by real data problems while repeat imports remain auditable.

## Acceptance Criteria

**AC1:** Import validation produces operator-readable artifacts  
**Given** a migration batch completes  
**When** validation runs  
**Then** the system produces row-count reconciliation, orphan/mapping summaries, and severity-ranked discrepancy outputs  
**And** writes machine-readable artifacts that CLI and skill-driven workflows can inspect directly  
**And** operators can see which stage failed without manually reconstructing the run

**AC2:** Severity policy aligns with the approved architecture  
**Given** discrepancies are detected  
**When** the validation engine classifies them  
**Then** severity-1 issues are treated as cutover blockers  
**And** severity-2 issues remain visible for follow-up without falsely clearing the batch

**AC3:** Replay safety is provable  
**Given** the same tenant and cutoff scope is imported again  
**When** the operator reruns validation and import  
**Then** duplicate canonical records are not created  
**And** the rerun outcome is explainable from stored run metadata and lineage state

**AC4:** Validation hands off cleanly to Epic 13 shadow-mode work  
**Given** a migration batch reaches a clean import-ready state  
**When** cutover preparation continues  
**Then** the batch artifacts are suitable input to the broader shadow-mode reconciliation flow  
**And** this story does not try to replace Epic 13's longer-running discrepancy program

## Tasks / Subtasks

- [ ] **Task 1: Define and persist batch validation outputs** (AC1, AC2)
  - [ ] Store per-batch row counts, orphan totals, unresolved mappings, and import-stage failures
  - [ ] Write both operator-readable and machine-readable report artifacts and/or database records that can be reviewed after each run
  - [ ] Classify discrepancies by the approved severity policy

- [ ] **Task 2: Prove replay safety** (AC3)
  - [ ] Add idempotency checks for repeated batch IDs and repeated tenant/cutoff windows
  - [ ] Prove reruns do not create duplicate canonical records or stale success markers
  - [ ] Persist enough metadata to explain why a rerun succeeded, failed, or was skipped

- [ ] **Task 3: Document the Epic 13 handoff boundary** (AC2, AC4)
  - [ ] Keep import-run validation distinct from the broader 30-day shadow-mode reconciliation program
  - [ ] Document which artifacts from this story feed Epic 13 comparisons
  - [ ] Avoid duplicating long-horizon shadow-mode logic in the import layer

- [ ] **Task 4: Add focused tests and fixtures** (AC1, AC2, AC3, AC4)
  - [ ] Add validation tests for row-count mismatch, unresolved severity-1 blockers, and replayed batch success
  - [ ] Add a regression proving severity-2 issues remain visible without clearing severity-1 blockers

## Dev Notes

### Repo Reality

- The architecture already reserves Epic 13 for versioned reconciliation and 30-day shadow-mode.
- Story 15.5 should stop at migration-run validation and hand off clean artifacts into that later program.

### Critical Warnings

- Do **not** conflate import validation with full shadow-mode correctness.
- Do **not** allow a clean-looking rerun summary to mask duplicate canonical writes.
- Do **not** make severity levels subjective; the blocking policy must be mechanical and reviewable.

### Implementation Direction

- Prefer structured validation artifacts that can be read by operators and later automation.
- Keep the validation output stable enough that a skill can call the CLI and reason over the emitted JSON/Markdown without custom scraping.
- Use `_bmad-output/validation/` and/or persisted import-run tables for deterministic evidence.
- Keep severity policy aligned with the architecture's reconciliation model.

### Validation Follow-up

- Add at least one full-path batch test that fails on a severity-1 discrepancy and stays blocked on rerun until the underlying data issue is fixed.
- Include explicit proof that validation artifacts from Story 15.5 can seed Epic 13 reconciliation inputs.

### References

- `_bmad-output/planning-artifacts/epics.md` - Epic 15 / Story 15.5 / FR60 / FR61
- `docs/legacy/migration-plan.md` - severity policy and discrepancy posture
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md` - Section 4.5 Shadow-Mode Reconciliation
- `_bmad-output/validation/` - existing validation artifact location

## Dev Agent Record

### Agent Model Used

GitHub Copilot (GPT-5.4)

### Completion Notes List

- Story keeps import validation intentionally separate from Epic 13's broader shadow-mode program.
- Story treats replay safety as a first-class acceptance criterion, not a later optimization.
- Story now requires machine-readable validation output so agent workflows can inspect import results safely.
