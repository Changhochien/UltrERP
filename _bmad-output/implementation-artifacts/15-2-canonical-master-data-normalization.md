# Story 15.2: Canonical Master Data Normalization

Status: review

## Story

As a migration operator,
I want ROC dates, sentinel dates, and core master records normalized before canonical import,
So that downstream loads use consistent customer, supplier, product, and warehouse data.

## Acceptance Criteria

**AC1:** Date normalization follows the verified legacy rules  
**Given** raw legacy date values include ROC-encoded values and `1900-01-01` sentinels  
**When** the CLI normalization phase runs  
**Then** ROC dates convert to AD dates according to the documented rules  
**And** empty-date sentinels are converted according to the approved import policy  
**And** invalid or ambiguous inputs are surfaced explicitly rather than silently coerced

**AC2:** Shared party master is normalized deterministically  
**Given** `tbscust` contains both customers and suppliers  
**When** party normalization runs  
**Then** the pipeline produces canonical-ready party records with deterministic legacy-to-canonical keys  
**And** preserves role information needed for both customer and supplier usage  
**And** does not discard supplier semantics during customer import work

**AC3:** Product and warehouse masters are prepared for transaction import  
**Given** product and inventory tables are staged  
**When** normalization runs  
**Then** product, warehouse, and inventory-prep outputs are generated in dependency order  
**And** the normalized outputs are reusable by downstream transaction-import steps

**AC4:** Normalization remains batch-scoped and auditable  
**Given** multiple import batches may exist over time  
**When** normalized outputs are written  
**Then** they remain batch-aware and traceable to their staged source rows  
**And** the normalization step can be rerun without breaking downstream lineage

## Tasks / Subtasks

- [x] **Task 1: Productionize the verified date rules** (AC1)
  - [x] Lift ROC-date and sentinel-date handling out of the PoC into production utilities inside `backend/domains/legacy_import/`
  - [x] Expose normalization as a reviewed CLI phase rather than an ad hoc script-only step
  - [x] Add explicit handling for 10-digit ROC invoice/date encodings, AD dates, and `1900-01-01`
  - [x] Fail loudly on formats outside the documented legacy cases

- [x] **Task 2: Normalize shared party data** (AC2, AC4)
  - [x] Define canonical-prep records for parties sourced from `tbscust`
  - [x] Preserve legacy code, role usage, and batch lineage in the prep layer
  - [x] Ensure downstream imports can distinguish customer-facing and supplier-facing usage without duplicating source records blindly

- [x] **Task 3: Normalize product, warehouse, and inventory masters** (AC3, AC4)
  - [x] Prepare normalized product records from `tbsstock`
  - [x] Prepare normalized warehouse/inventory records from `tbsstkhouse` and related staging tables
  - [x] Generate deterministic key maps that downstream transaction import can reuse

- [x] **Task 4: Add focused regression coverage** (AC1, AC2, AC3, AC4)
  - [x] Add tests for ROC date edge cases and sentinel handling
  - [x] Add tests for combined customer/supplier records in `tbscust`
  - [x] Add tests proving normalized outputs keep batch lineage and deterministic identifiers

## Dev Notes

### Repo Reality

- The current canonical data model already has concrete anchors for customers, products, warehouses, and inventory.
- There is no existing normalization layer for legacy data today; Story 15.2 should establish that boundary rather than writing raw values straight into live tables.

### Critical Warnings

- `tbscust` is a shared party master. Do **not** flatten it into customers-only logic and lose supplier behavior.
- Do **not** leave `1900-01-01` values flowing into canonical business fields without an explicit import policy.
- Do **not** make normalized outputs batch-agnostic; replay and discrepancy work depends on batch traceability.

### Implementation Direction

- Prefer a canonical-prep layer (tables, views, or import-owned models) that isolates legacy cleanup from live-domain writes.
- Keep normalization behind the same CLI workflow established in Story 15.1 so agents and operators use one stable interface.
- Use deterministic mapping tables or lookup records so later transaction import does not rediscover keys heuristically.

### Validation Follow-up

- Keep date parsing tests independent from transaction import so parsing regressions fail early.
- Add at least one regression proving supplier semantics survive the customer-centric target model.

### References

- `_bmad-output/planning-artifacts/epics.md` - Epic 15 / Story 15.2 / FR57
- `docs/legacy/migration-plan.md` - relationship order and sentinel-date policy
- `research/legacy-data/03-findings.md` - corrected orphan context and ROC-date handling summary
- `research/legacy-data/02-poc/import_legacy.py` - verified parsing logic to productionize
- `backend/domains/customers/models.py` - current customer anchor
- `backend/common/models/product.py` - current product anchor
- `backend/common/models/warehouse.py` - current warehouse anchor
- `backend/common/models/inventory_stock.py` - current inventory anchor

## Dev Agent Record

### Agent Model Used

GitHub Copilot (GPT-5.4)

### Completion Notes List

- Story isolates normalization from live writes so later migration steps can reuse deterministic prep outputs.
- Story explicitly protects the shared customer/supplier nature of `tbscust`.
- Added a `normalize` CLI phase that writes batch-scoped `normalized_parties`, `normalized_products`, `normalized_warehouses`, and `normalized_inventory_prep` tables inside `raw_legacy`.
- Implemented deterministic UUID generation plus production normalization helpers for ROC dates, AD dates, `1900-01-01` sentinels, decimals, and shared party roles.
- Normalization currently uses one synthetic default warehouse so downstream transaction-import stories can consume consistent inventory prep rows before richer warehouse mapping lands.
- Live validation staged `tbscust`, `tbsstock`, and `tbsstkhouse`, then normalized batch `normalize-probe-001` into `1022` parties, `6611` products, `1` warehouse, and `6588` inventory-prep rows.
- Live validation exposed a false-negative in the shared staging parser for rows that mix SQL-style escaped quotes with unquoted numeric literals; the parser now accepts the real export format and has regression coverage.
- BMAD review follow-up moved normalization clear-plus-copy work behind one asyncpg transaction and validates staged source rows before deleting normalized outputs, so bad or partial reruns no longer erase the last good normalized batch for that tenant.
- BMAD review follow-up scoped normalized prep table primary keys and cleanup to `tenant_id + batch_id`, matching the CLI contract and preventing cross-tenant batch collisions.
- BMAD review follow-up added focused regression coverage for customer-role normalization, tenant-scoped normalized-table DDL, transactional rerun behavior, no-clear-on-missing-stage behavior, and comma-bearing legacy staging rows.
- Review evidence on warehouse granularity: the current `tbsstkhouse` extract has `6588` rows, `6588` unique product codes, `0` repeated product rows, and an empty third field on every sampled/exported row, so richer warehouse derivation remains blocked on a trustworthy warehouse-identity source rather than on the normalization logic alone.
- Focused backend validation after the review fixes: `.venv/bin/pytest tests/domains/legacy_import` -> `26 passed`.

### File List

- backend/domains/legacy_import/__init__.py
- backend/domains/legacy_import/cli.py
- backend/domains/legacy_import/normalization.py
- backend/domains/legacy_import/staging.py
- backend/tests/domains/legacy_import/test_normalization.py
- backend/tests/domains/legacy_import/test_staging.py

### Change Log

- 2026-04-05: Implemented Story 15.2 master-data normalization with CLI support, batch-scoped normalized prep tables, focused tests, and live stage-plus-normalize validation against `tbscust`, `tbsstock`, and `tbsstkhouse`.
- 2026-04-05: Completed BMAD review follow-up for Story 15.2 by making normalization transactional and tenant-scoped, extending normalization/staging regression coverage, and documenting the current warehouse-source limitation in `tbsstkhouse`.
