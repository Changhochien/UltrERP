# Story 16.2: Normalize Purchase Master Data

Status: implemented

## Story

As a migration operator,
I want purchase master data normalized before canonical import,
So that suppliers, products, and warehouses are consistent with the canonical schema and the same product mapping used in Epic 15.

## Acceptance Criteria

**AC1:** Supplier parties are derived from tbscust type='1' rows
**Given** raw_legacy.tbscust is staged with supplier rows (type='1')
**When** the normalize CLI step runs for the purchase batch
**Then** supplier records are written to the canonical customers table with role='supplier'
**And** deterministic legacy-to-canonical keys are generated so re-runs produce identical keys

**AC2:** ROC-encoded dates are converted to AD dates
**Given** raw_legacy.tbsslipj and tbsslipdtj contain ROC-encoded dates
**When** normalization runs
**Then** ROC dates are converted to AD using the same rules established in Epic 15 Story 15.2
**And** empty-date sentinels are converted to None rather than flowing into canonical date fields
**And** unsupported legacy date formats fail with explicit errors

**AC3:** Product and warehouse mappings are reused from Epic 15
**Given** normalized product codes and warehouse codes are already mapped in the Epic 15 batch
**When** purchase normalization runs
**Then** tbsslipdtj.product_code is resolved through the product_code_mapping table from Epic 15
**And** tbsslipj.warehouse_code is resolved through the warehouse mapping from Epic 15
**And** unmapped product or warehouse codes are surfaced as normalization warnings, not silent failures

**AC4:** Normalization is batch-scoped and idempotent
**Given** a normalization batch has already run
**When** the normalize step is re-run for the same batch and tenant
**Then** the same canonical keys are produced for the same source rows
**And** the operation is safe to re-run without creating duplicate supplier or mapping records

## Tasks / Subtasks

- [x] **Task 1: Normalize supplier parties from tbscust type='1'** (AC1)
  - [x] Read tbscust rows where type='1' from the staged raw_legacy source
  - [x] Write canonical customer records with role='supplier' to the normalized parties table
  - [x] Generate deterministic UUIDs using the same namespace as Epic 15 normalization
  - [x] Preserve batch_id and tenant_id scoping

- [x] **Task 2: Apply ROC→AD date conversion to purchase transaction fields** (AC2)
  - [x] Reuse the normalize_legacy_date helper from the Epic 15 normalization module
  - [x] Handle ROC 10-digit (yyyymmdd-roc), 8-digit (yymmdd-roc), and AD ISO formats
  - [x] Fail explicitly on unrecognized legacy date encodings

- [x] **Task 3: Reuse Epic 15 product_code_mapping for purchase line items** (AC3)
  - [x] Join tbsslipdtj.product_code against the product_code_mapping table created in Epic 15
  - [x] Emit warnings for product codes that have no Epic 15 mapping entry
  - [x] Write normalized product references into the purchase-normalized prep layer

- [x] **Task 4: Reuse Epic 15 warehouse mapping for purchase invoice headers** (AC3)
  - [x] Resolve tbsslipj.warehouse_code against the warehouse mapping created during Epic 15 tbsstkhouse staging
  - [x] Emit warnings for warehouse codes not found in the Epic 15 mapping
  - [x] Write resolved warehouse references into the purchase-normalized prep layer

- [x] **Task 5: Add idempotency and deterministic key coverage** (AC4)
  - [x] Verify deterministic UUID generation uses the same _NAMESPACE as Epic 15
  - [x] Confirm re-running the normalize step for the same batch_id + tenant_id produces identical keys
  - [x] Add regression tests for supplier-key determinism and batch-scoped rerun safety

## Dev Notes

### Repo Reality

- The normalization module at `backend/domains/legacy_import/normalization.py` already contains `normalize_legacy_date` and `deterministic_legacy_uuid` with the correct _NAMESPACE.
- The `normalize_party_record` function already handles role='supplier' via the legacy_type mapping `{'1': 'supplier', '2': 'customer'}`.
- Product and warehouse mappings from Epic 15 are stored in the `raw_legacy` schema and can be joined during purchase normalization.

### Critical Warnings

- Do not generate new supplier keys outside the Epic 15 _NAMESPACE;下游 transaction import expects deterministic keys that match across batches.
- Do not allow ROC date conversion failures to silently fall through; unsupported formats must raise so the operator can correct the source data before import.
- Do not skip the product/warehouse mapping join; unmapped purchase lines need explicit warnings, not silent NULL references in the canonical layer.

### Implementation Direction

- Purchase normalization runs after Epic 15 staging is complete so the product_code_mapping and warehouse_mapping tables are available to join against.
- The CLI entry point extends the existing `normalize` subcommand with `--schema raw_legacy --tenant-id <id> --batch-id <id>` flags already used in Epic 15.
- Normalized outputs are written to batch-scoped tables inside `raw_legacy` (e.g., `normalized_purchase_parties`, `normalized_purchase_invoice_prep`) to keep purchase and sales normalization traces separate.
- Deterministic keys ensure downstream Stories 16.3 and 16.4 can reference the same canonical supplier and product keys without re-mapping.

### Validation Follow-up

- Verify that re-running normalize for the same batch_id + tenant_id produces byte-identical UUIDs for the same supplier codes.
- Confirm that tbscust type='1' suppliers normalized in Story 16.2 have the same canonical UUIDs as if they had been normalized as suppliers in Epic 15 (same legacy_code + same namespace).

### References

- `_bmad-output/planning-artifacts/epics.md` - Epic 16 / Story 16.2 / FR64
- `_bmad-output/implementation-artifacts/15-2-canonical-master-data-normalization.md` - Epic 15 normalization pattern and ROC date rules
- `_bmad-output/implementation-artifacts/16-1-raw-purchase-invoice-staging.md` - purchase invoice staging (Story 16.1)
- `backend/domains/legacy_import/normalization.py` - normalize_legacy_date and deterministic_legacy_uuid helpers
- `backend/domains/legacy_import/staging.py` - raw_legacy connection helpers and CSV COPY staging
- `backend/common/models/inventory_stock.py` - current inventory anchor
- `backend/tests/domains/legacy_import/test_normalization.py` - existing normalization regression coverage

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Completion Notes List

- Story 16.2 normalizes purchase master data by deriving suppliers from tbscust type='1', reusing the Epic 15 ROC→AD date conversion, and joining against the Epic 15 product_code_mapping and warehouse_mapping tables.
- Deterministic UUIDs are generated using the same _NAMESPACE as Epic 15 normalization, ensuring supplier keys are stable across Epic 15 and Epic 16 batches.
- CLI command: `uv run python -m domains.legacy_import.cli normalize --batch-id <id> --schema raw_legacy --tenant-id <id>`
- Normalized outputs are written to batch-scoped tables: `normalized_purchase_parties` and `normalized_purchase_invoice_prep`.
- Idempotency is guaranteed by the deterministic key generation and batch-scoped table design; re-running the normalize step for the same batch_id + tenant_id produces identical canonical keys.
- Focused regression tests added for supplier-key determinism across batches and batch-scoped rerun safety.

### File List

- backend/domains/legacy_import/normalization.py (shared helpers: normalize_legacy_date, deterministic_legacy_uuid, normalize_party_record)
- backend/domains/legacy_import/cli.py (normalize subcommand extended with purchase normalization paths)
- backend/domains/legacy_import/staging.py (raw_legacy connection and COPY helpers)
- backend/tests/domains/legacy_import/test_normalization.py (regression tests for AC1–AC4)

### Change Log

- 2026-04-05: Implemented Story 16.2 purchase master data normalization with supplier derivation from tbscust type='1', ROC→AD date reuse, Epic 15 product/warehouse mapping joins, and deterministic key guarantees.
- 2026-04-05: Added regression tests for supplier-key determinism and batch-scoped idempotency; verified CLI command matches Epic 15 interface.
