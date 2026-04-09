# Story 13.1: Versioned Reconciliation Spec

Status: planning

## Story

As a system,
I want to use a versioned reconciliation specification,
So that we can track what should be compared during shadow-mode.

## Acceptance Criteria

**AC1:** Comparison follows versioned reconciliation spec  
**Given** shadow-mode is running  
**When** comparing systems  
**Then** the comparison follows the versioned reconciliation spec  
**And** spec covers: invoice totals/tax, payments, inventory movements, customer balances, order status

**AC2:** Severity levels are defined  
**Given** a discrepancy is detected during comparison  
**When** results are classified  
**Then** severity_1 (blocking) and severity_2 (warning) levels are assigned  
**And** severity_1 blocks cutover  
**And** severity_2 produces warnings but does not block

**AC3:** Spec is versioned and auditable  
**Given** a reconciliation run executes  
**When** results are recorded  
**Then** the spec version used is logged with the results  
**And** spec changes are tracked in version control

## Tasks / Subtasks

- [ ] **Task 1: Design reconciliation spec schema**
  - [ ] Define `reconciliation_spec` table with version, effective_date, created_at, created_by
  - [ ] Define `reconciliation_spec_line` table with spec_id, domain, field_path, comparison_method, severity, tolerance
  - [ ] Create Alembic migration for both tables
  - [ ] Add tenant_id to both tables for multi-tenant readiness (NFR31)

- [ ] **Task 2: Populate initial spec with coverage areas**
  - [ ] Invoice domain: invoice total, tax total, line item sums, customer reference
  - [ ] Payment domain: payment amount, payment date, matched invoice reference
  - [ ] Inventory domain: stock movement quantity, warehouse reference, movement type
  - [ ] Customer domain: account balance, credit limit, outstanding amount
  - [ ] Order domain: order status, total amount, line item status

- [ ] **Task 3: Implement spec versioning**
  - [ ] Add `spec_version` column to reconciliation_run_results table
  - [ ] Log spec version when each reconciliation run starts
  - [ ] Prevent reconciliation runs with stale specs from executing silently
  - [ ] Add admin API endpoints: GET /reconciliation/specs, POST /reconciliation/specs, GET /reconciliation/specs/{id}

- [ ] **Task 4: Add comparison method definitions**
  - [ ] EXACT: field values must match exactly
  - [ ] NUMERIC_TOLERANCE: numeric values within configured tolerance (e.g., 0.01 for currency)
  - [ ] DATE_TOLERANCE: dates within N days
  - [ ] REFERENCE_MATCH: foreign key references must resolve to same entity

- [ ] **Task 5: Add focused tests for spec versioning**
  - [ ] Test spec creation with valid line items
  - [ ] Test spec version is recorded in reconciliation results
  - [ ] Test severity classification from spec
  - [ ] Test tolerance application in numeric comparisons

## Dev Notes

### Repo Reality

- The shadow-mode reconciliation system is referenced in AR9: "Shadow-mode reconciliation system (versioned reconciliation spec, discrepancy alerts)"
- The reconciliation spec must integrate with the existing `canonical_record_lineage` infrastructure from Epic 15/16 for source data access
- Severity classification aligns with NFR20 (shadow-mode validation) and AR20 (severity-1 blocks cutover)

### Critical Warnings

- Do **not** hard-code comparison logic without referencing the spec version
- Do **not** skip tenant_id on reconciliation tables (NFR31 compliance)
- Do **not** use floating-point comparison for currency fields; use NUMERIC_TOLERANCE with explicit tolerance values

### Implementation Direction

- Spec schema follows the lineage table pattern established in Epic 15: canonical_record_lineage
- Comparison engine reads spec version at run start, executes comparisons, and records results with spec reference
- Initial spec can be seeded as a migration fixture, with admin API for future updates

### Validation Follow-up

- Confirm that a reconciliation run with a missing spec version raises an error rather than proceeding silently
- Confirm that NUMERIC_TOLERANCE comparisons handle edge cases (zero, negative values, precision loss)
- Confirm that severity classification is deterministic across spec versions

### References

- `_bmad-output/planning-artifacts/epics.md` - Epic 13 / Story 13.1
- `_bmad-output/planning-artifacts/prd.md` - NFR20 shadow-mode validation, NFR31 tenant_id
- `_bmad-output/implementation-artifacts/15-4-canonical-historical-transaction-import.md` - Epic 15 lineage pattern
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md` - AR9 shadow-mode reconciliation
- `backend/domains/legacy_import/canonical.py` - lineage infrastructure reference
