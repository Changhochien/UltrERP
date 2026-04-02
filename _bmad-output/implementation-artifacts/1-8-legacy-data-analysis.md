# Story 1.8: Legacy Data Analysis

Status: completed

## Story

As a developer,
I want to understand the legacy database structure,
So that I can plan the migration strategy.

## Context

Based on the existing legacy migration research already present in the repository:
- **Legacy system:** Access + SQL Server 2008 with 94 tables, 1.1M rows
- **Corrected orphan profile:** 190 orphan product codes affecting 523 transaction rows (0.09%)
- **Existing artifacts:** extracted CSVs, relationship docs, FK validation, and migration findings already exist under `legacy-migration-pipeline/` and `research/legacy-data/`
- **Goal:** consolidate verified findings into an implementation-ready migration decision and shadow-mode plan

**Note:** This is no longer a greenfield discovery story. It is a consolidation and decision story built on verified analysis already in the repo.

## Acceptance Criteria

**Given** the existing legacy analysis artifacts are available
**When** I review and consolidate them
**Then** I have a complete ERD of 94 tables
**And** I have row counts for all tables
**And** I have confirmed the corrected orphan profile of 190 orphan codes affecting 523 rows
**And** I have documented the migration strategy for shadow-mode validation

## Technical Requirements

### Legacy Database Analysis

Consolidate the following from existing artifacts:
- Table groups and primary relationships
- Verified row counts and extraction completeness
- Foreign key validation findings
- Known data quality issues that affect migration design

### Orphan Row Analysis

Confirm and document:
- 190 orphan product codes
- 523 affected transaction rows
- likely variant-style root cause
- recommended resolution path for migration

### Migration Strategy

Document the approach for shadow-mode validation:
1. Read from legacy database (read-only)
2. Transform data to new schema
3. Write to new database
4. Compare results without affecting production

## Tasks

- [x] Task 1: Consolidate legacy structure documentation
  - [x] Subtask: Reference existing ERD and relationship documentation
  - [x] Subtask: Summarize row counts and extraction completeness
  - [x] Subtask: Capture FK validation results relevant to migration
- [x] Task 2: Confirm orphan-code findings
  - [x] Subtask: Reference the corrected orphan analysis
  - [x] Subtask: Document the 190-code/523-row profile and variant root cause
  - [x] Subtask: Record the chosen resolution strategy for implementation
- [x] Task 3: Create migration decision record
  - [x] Subtask: Document shadow-mode approach with ETL pipeline
  - [x] Subtask: Document validation strategy (comparing outputs)
  - [x] Subtask: Document rollback and contingency plan

## Dev Notes

### Critical Implementation Details

1. **Read-only access** - Never write to legacy database
2. **Shadow-mode** - New system runs parallel, doesn't affect production
3. **Validation** - Compare outputs before cutover
4. **Use verified repo artifacts first** - Do not repeat analysis already completed unless findings are disputed

### PRD References

- Section 2.2: Legacy system details (94 tables, 1.1M rows)
- Section 2.2: 523 orphan rows requiring resolution

### Architecture References

- Section 5: Migration strategy
- Section 8: Data quality issues

## File List

- legacy-migration-pipeline/extracted_data/RELATIONSHIPS.md
- legacy-migration-pipeline/FK_VALIDATION.md
- research/legacy-data/03-findings.md
- docs/legacy/migration-plan.md

## Validation Evidence

- The consolidation document at `docs/legacy/migration-plan.md` was created from the verified repo artifacts and passes markdown diagnostics.
- The corrected orphan profile and shadow-mode strategy were checked against the existing migration research already present in the repository.

## Review Outcome

- Story 1.8 remains a consolidation-and-decision story, not a fresh discovery exercise.
- The migration plan now captures the chosen variant-resolution strategy, shadow-mode validation targets, and rollback posture.
