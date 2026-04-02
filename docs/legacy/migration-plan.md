# Legacy Migration Plan

## Purpose

This document consolidates the verified legacy ERP findings into an implementation-ready migration decision record for UltrERP. It is based on the existing extraction, relationship, FK validation, and PoC analysis already present in the repository.

## Source Artifacts

- `legacy-migration-pipeline/README.md`
- `legacy-migration-pipeline/extracted_data/MANIFEST.md`
- `legacy-migration-pipeline/extracted_data/RELATIONSHIPS.md`
- `legacy-migration-pipeline/FK_VALIDATION.md`
- `research/legacy-data/03-findings.md`

## Consolidated Facts

### Scope And Structure

- Project-level migration baseline: **94 logical tables** and approximately **1.1M rows** from a 569MB SQL dump extracted at **99.996% completeness**.
- Raw extraction inventory currently lists **96 CSV files** and approximately **1.16M rows** in `MANIFEST.md`.
- This means the business-level table count and the raw-export file count are not perfectly aligned yet. Treat `94 tables / 1.1M rows` as the planning baseline and `96 CSV files / 1.16M rows` as the current extraction inventory until the duplicate or non-business artifacts are reconciled.

### Verified Relationship Model

The core migration path is stable and documented in `RELATIONSHIPS.md`:

- `tbscust` is the shared party master for both customers and suppliers.
- `tbsstock` is the product master and references supplier records in `tbscust`.
- `tbsslipx` and `tbsslipdtx` form the sales header/detail pair.
- `tbsslipj` and `tbsslipdtj` form the purchase header/detail pair.
- `tbsstkhouse` stores inventory by warehouse.

For implementation, the target order remains:

1. Parties
2. Products
3. Warehouses
4. Inventory
5. Sales and purchase headers
6. Sales and purchase lines

### FK Validation Correction

`legacy-migration-pipeline/FK_VALIDATION.md` is still useful for most relationship checks, but its most severe sales-detail conclusion is outdated.

- The original report flagged **660 orphan codes** and a **99.7% mismatch** for `tbsslipdtx`.
- `research/legacy-data/03-findings.md` proved that result compared the wrong field: `warehouse_code` instead of `product_code`.
- The corrected and implementation-relevant orphan profile is:
  - **190 orphan product codes**
  - **523 affected rows**
  - **0.09% of sales detail rows**
  - Root cause: mostly **alphanumeric product variants** that were used operationally but not added as separate product master records

`research/legacy-data/03-findings.md` supersedes the `660 orphan` conclusion for migration design.

## Migration Decisions

### 1. Staging Strategy

- Import the legacy dataset into a read-only `raw_legacy` PostgreSQL schema first.
- Use PostgreSQL `COPY` for bulk load performance.
- Preserve legacy primary keys and document numbers as source lineage columns.
- Do not write back to the legacy source under any circumstance.

### 2. Product Code Resolution Strategy

Chosen strategy: **mapping-table driven variant resolution with explicit fallback**.

Implementation rules:

1. Create `raw_legacy.product_code_mapping` for all 190 orphan codes.
2. Preload the 32 fuzzy-match candidates from the PoC as analyst-review candidates, not as auto-approved mappings.
3. Apply `variant_map` only when a base-product mapping is mechanically obvious or explicitly analyst-approved.
4. Route unresolved rows to an `UNKNOWN` placeholder product during initial migration and shadow-mode so transaction history is preserved without inventing false product certainty.

This is stricter than blindly collapsing every orphan variant into a base SKU, and it protects auditability during reconciliation.

### 3. Sentinel Date Handling

- Treat `1900-01-01` as a legacy empty-date sentinel.
- Convert it to `NULL` in staging unless the target field is non-nullable.
- When the target model requires a value, make the field nullable for import or use an explicit migration default that is visibly synthetic and documented.

### 4. Log And Low-Value Tables

- `tbslog` contains 301,460 rows and should not be treated as business-critical migration scope by default.
- Archive it separately unless a downstream audit requirement explicitly needs it in the operational ERP schema.

## Shadow-Mode Validation Plan

Shadow-mode exists to prove correctness before cutover, not to approximate success.

### Comparison Domains

- Invoices: totals, tax totals, line counts, customer linkage
- Inventory: quantity on hand by warehouse
- Payments: allocations and balances
- Customers: key master data used by invoice and order flows

### Reconciliation Flow

1. Load legacy source into `raw_legacy`.
2. Transform staged records into the new schema using explicit mapping tables.
3. Execute the new system in parallel with legacy outputs.
4. Compare outputs using a versioned reconciliation specification.
5. Emit daily discrepancy reports with severity classification.

### Severity Policy

- Severity 1: invoice total mismatch, tax mismatch, payment allocation mismatch, or other correctness blockers. These block cutover.
- Severity 2: non-blocking data quality or attribution issues such as unresolved variant mapping still routed to `UNKNOWN`.

## Rollback And Contingency

- If the import produces unresolved Severity 1 discrepancies, stop cutover and continue shadow-mode.
- If product-code mapping quality is insufficient, keep unresolved rows on `UNKNOWN` and prevent product-level analytics from being treated as authoritative.
- If staging counts do not reconcile with the planning baseline, freeze the migration pipeline and reconcile the `94 logical tables` versus `96 CSV files` discrepancy before production decisions.

## Implementation Notes

- The relationship map in `RELATIONSHIPS.md` remains the best quick reference for table linkage.
- The orphan-code correction in `03-findings.md` is the current source of truth for sales-detail migration logic.
- The old `FK_VALIDATION.md` should be read with caution until its sales-detail section is updated or explicitly marked historical.