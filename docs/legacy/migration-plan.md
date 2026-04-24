# Legacy Migration Plan

## Purpose

This document consolidates the verified legacy ERP findings into an implementation-ready migration decision record for UltrERP. It is based on the existing extraction, relationship, FK validation, and PoC analysis already present in the repository.

Routine operator workflows no longer default to dump-era extracts or manual approval-driven promotion. The reviewed default path is the live legacy DB flow through `run_legacy_refresh`, scheduled shadow refresh, and promotion evaluation. Dump-era extraction and file-based staging remain archival or break-glass tools only.

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

### Reviewed Refresh Command

- The reviewed operator entry point for a full live shadow refresh is
  `cd backend && uv run python -m scripts.run_legacy_refresh ...`.
- It runs the live-stage, normalize, map-products, optional review export/import,
  canonical-import, validate-import, the closed-month `sales_monthly` refresh,
  stock backfills, and reconciliation report in one controlled order, then writes
  a machine-readable summary under
  `_bmad-output/operations/legacy-refresh/`.
- Each summary now carries one shared `promotion_policy` record with explicit
  `classification` (`eligible`, `blocked`, or `exception-required`),
  `reason_codes`, machine-readable gate details, and operator-facing text.
- A run can complete with `promotion_readiness=false` when unresolved product mappings
  still require analyst review, even if the shadow dataset itself was refreshed.
- This command is intentionally limited to refresh plus evidence generation. Scheduling,
  promotion into the working lane, and automatic correction application stay outside this
  workflow.

### Reviewed Scheduled Shadow Refresh Wrapper

- The reviewed cron-safe wrapper for unattended shadow refreshes is
  `cd backend && uv run python -m scripts.run_scheduled_legacy_shadow_refresh ...`.
- It generates one immutable UTC batch id per invocation, reuses
  `scripts.run_legacy_refresh`, and writes durable lane state under
  `_bmad-output/operations/legacy-refresh/state/<schema>-<tenant>-<source-schema>/`.
- `latest-run.json` records every scheduled attempt, including overlap-blocked,
  validation-blocked, reconciliation-blocked, and failed outcomes.
- `latest-success.json` advances only for `completed` and
  `completed-review-required`, because shadow freshness and promotion eligibility are
  separate concerns.
- `latest-run.json` and `latest-success.json` now copy the refresh summary
  `promotion_policy` outcome so scheduler-side alerts and operator tooling reuse the
  same reviewed gate classification.
- A pre-existing `scheduler.lock` blocks a second run for the same lane until an
  operator resolves the overlap or stale-lock condition. The wrapper leaves the prior
  durable success state untouched in that case.
- The scheduled wrapper itself does not mutate the working lane directly. It produces
  the candidate batch and durable state consumed by downstream promotion gate
  evaluation.
- Under the updated Epic 15 plan, eligible shadow batches may be promoted
  automatically by the downstream promotion step, while blocked batches leave the
  previously promoted working batch unchanged and trigger operator-visible alerts.
- Operators should distinguish the latest successful shadow batch from the latest
  promoted working batch; those are related but not identical states.

Reviewed cron example:

```bash
0 2 * * * cd /path/to/UltrERP/backend && uv run python -m scripts.run_scheduled_legacy_shadow_refresh --tenant-id <tenant-uuid> --schema raw_legacy --source-schema public --batch-prefix legacy-shadow --lookback-days 10000 --reconciliation-threshold 0
```

### Reviewed Promotion Evaluation

- The reviewed operator entry point for advancing the working lane is
  `cd backend && uv run python -m scripts.run_legacy_promotion ...`.
- It consumes the lane's `latest-success.json` record plus the referenced Story 15.15
  summary JSON and does not rerun staging, normalization, canonical import, or
  reconciliation.
- The reviewed working-lane pointer is `latest-promoted.json` under the same per-lane
  state root used by the scheduled wrapper.
- Every evaluation attempt also writes one append-only result artifact under
  `promotion-results/`, so operators can audit promoted, blocked, and noop outcomes
  separately from the current pointer.
- Promotion artifacts now include `promotion_policy_classification`,
  `promotion_policy_reason_codes`, `promotion_mode`, and optional override metadata so
  automatic eligibility and exception-driven advancement remain visibly distinct.
- Promotion is blocked when the lane is still unstable (`scheduler.lock` exists), the
  candidate summary artifact is missing or mismatched, validation is not passed,
  reconciliation is blocked, or analyst review is still required. The unresolved
  analyst-review case is surfaced as `exception-required`, not silent success.
- When the latest successful shadow batch already matches `latest-promoted.json`, the
  evaluation returns `noop` and leaves the working-lane pointer untouched.
- Operators can intentionally advance an `exception-required` batch only by supplying
  `--promoted-by`, `--allow-exception-override`, `--override-rationale`, and
  `--override-scope`; that path writes a durable audit record under
  `promotion-overrides/` before the promotion pointer is committed.

### Reviewed Reconciliation Corrections

- `cd backend && uv run python -m scripts.propose_reconciliation_corrections ...` is
  the reviewed proposal surface. It produces candidate correction CSV rows and keeps
  configured review-only categories visible as manual/operator work.
- `cd backend && uv run python -m scripts.apply_reconciliation_corrections --csv ... --approved-by ...`
  is the reviewed apply surface. It remains dry-run by default and only persists rows
  whose CSV `approval_action` is exactly `apply` and whose `disposition` is
  `actionable`.
- Scheduled refresh and automatic promotion never invoke correction application.
  Reconciliation correction stays explicit and operator-approved.

### Severity Policy

- Severity 1: invoice total mismatch, tax mismatch, payment allocation mismatch, or other correctness blockers. These block cutover.
- Severity 2: non-blocking data quality or attribution issues such as unresolved variant mapping still routed to `UNKNOWN`.

### Story 15.5 Validation Handoff

- Story 15.5 owns batch-scoped import validation only: stage row reconciliation, unresolved mapping visibility, import-stage failures, replay metadata, and artifact emission.
- The `legacy-import validate-import` CLI emits machine-readable JSON and operator-readable Markdown under `_bmad-output/validation/legacy-import/`, uses schema-and-tenant-scoped artifact names, and accepts an optional `--attempt-number` for validating a specific retry.
- Those artifacts are the handoff contract into Epic 13. They provide batch counts, failure stages, `UNKNOWN` routing totals, replay scope keys, and lineage-backed inputs for later shadow-mode comparisons.
- Epic 13 still owns versioned comparison rules, longer-running discrepancy trending, and the broader 30-day shadow-mode correctness program.

## Rollback And Contingency

- If the import produces unresolved Severity 1 discrepancies, stop cutover and continue shadow-mode.
- If product-code mapping quality is insufficient, keep unresolved rows on `UNKNOWN` and prevent product-level analytics from being treated as authoritative.
- If staging counts do not reconcile with the planning baseline, freeze the migration pipeline and reconcile the `94 logical tables` versus `96 CSV files` discrepancy before production decisions.

## Stability Gate And Fallback Policy

### Default-Path Stability Gate

The repo considers the dump-era default retired only when the following evidence remains available and legible:

1. A reviewed live refresh can complete through `run_legacy_refresh` and emit a durable summary under `_bmad-output/operations/legacy-refresh/`.
2. Scheduled shadow refresh persists `latest-run.json` and `latest-success.json` for the lane and keeps blocked or failed runs from replacing the last trusted success record.
3. Promotion evaluation persists `latest-promoted.json` and append-only `promotion-results/` artifacts, while exception-driven advancement remains auditable through `promotion-overrides/`.
4. Shared `promotion_policy` classification and reason codes remain the operator and alerting contract across refresh, scheduler, and promotion surfaces.
5. Routine operator docs and command maps default to the live gated path. Dump-era file workflows are opt-in only and require an explicit archival directory rather than a repo-local default.

### Retained Archival And Break-Glass Surfaces

The following surfaces intentionally remain after retirement:

- `legacy-import extract` for preserved raw SQL dumps.
- `legacy-import stage --source-dir ...` for preserved CSV exports.
- `legacy-import currency-import --export-dir ...` for archival `tbscurrency.csv` replay.
- `legacy-migration-pipeline/` for historical research, schema notes, and git-preserved extraction evidence.
- `run_legacy_promotion --allow-exception-override ...` for reviewed `exception-required` promotions.
- `apply_reconciliation_corrections --csv ... --approved-by ...` for explicit operator-approved correction application.

These surfaces are not part of the routine refresh path and should not be presented as such in active operator instructions.

### Archival Storage Rule

New SQL dumps and extracted CSV batches must be archived outside the working repo. Operators should pass an explicit archive directory through `--output`, `--source-dir`, `--export-dir`, or `LEGACY_IMPORT_DATA_DIR` when invoking dump-era commands. Keeping new dump artifacts outside the repo preserves audit retention without reintroducing `legacy-migration-pipeline/extracted_data` as a default working location.

## Implementation Notes

- The relationship map in `RELATIONSHIPS.md` remains the best quick reference for table linkage.
- The orphan-code correction in `03-findings.md` is the current source of truth for sales-detail migration logic.
- The old `FK_VALIDATION.md` should be read with caution until its sales-detail section is updated or explicitly marked historical.
- The canonical landing zones for Story 15.4 are documented in `docs/legacy/canonical-import-target-matrix.md`.
- Purchase invoice history now lands in the new `supplier_invoices` and `supplier_invoice_lines` AP target; payment-adjacent legacy rows still remain in holding until payment-side AP semantics are defined.
- The AP target, read-only verification workspace, and current invoice-side deferrals are documented in `docs/legacy/purchase-invoice-canonical-target.md`.
- The deferred supplier payment and prepayment target design is documented in `docs/legacy/ap-payment-model.md`.