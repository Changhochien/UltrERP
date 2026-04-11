---
title: 'Preserve Legacy Header Snapshots On Imported Documents'
type: 'feature'
created: '2026-04-10'
baseline_commit: '187c66ead0e44c8103075086a00430272a972a94'
status: 'completed'
context:
  - 'docs/legacy/canonical-import-target-matrix.md'
  - 'docs/legacy/migration-plan.md'
  - 'docs/legacy/purchase-invoice-canonical-target.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The legacy import pipeline currently preserves document totals and lineage, but it drops critical sales and purchase header state on supported rows. Imported orders, invoices, and supplier invoices lose source-era header context such as exchange rate, period, raw status codes, denormalized party snapshots, and other legacy fields that operators need to audit overdue behavior and reconcile historical documents.

**Approach:** Preserve verified legacy sales and purchase header state as explicit snapshot data on imported documents, expose that snapshot through read APIs, and extend import validation so snapshot coverage is visible. Keep current operational status logic intact unless the source-to-target semantic mapping is already proven.

## Boundaries & Constraints

**Always:** Keep canonical import replay-safe and idempotent; preserve tenant, batch, and lineage behavior; support both sales headers and purchase headers in the same slice; treat legacy source values as evidence snapshots rather than authoritative modern workflow state unless the mapping is already verified; keep unsupported payment history on its current gated path.

**Ask First:** Any change that would reinterpret live operational status enums, replace current invoice payment-status computation, or alter external API contracts in a breaking way.

**Never:** Do not implement AP allocation logic, line-level snapshot preservation, or broad master-data preservation in this slice; do not guess due dates or payment states from ambiguous legacy fields; do not remove raw staging or holding paths; do not overwrite current live workflow fields with unverified legacy codes.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Sales header import | A staged tbsslipx row with extra header state such as exchange rate, tax metadata, period code, source status, and denormalized party snapshots | Canonical import writes the order and invoice as today and also stores a legacy header snapshot on both records | N/A |
| Purchase header import | A staged tbsslipj row with supplier-facing invoice metadata and extra header state | Canonical import writes the supplier invoice as today and also stores a legacy header snapshot on the supplier invoice | N/A |
| Missing optional state | A staged legacy header lacks one or more optional header fields | Import succeeds, snapshot omits or nulls only the missing keys, and operational fields remain valid | Do not synthesize fake state |
| Replay | The same batch is canonical-imported again | Snapshot fields upsert deterministically without duplicates or divergent payloads | N/A |
| API read | An imported order, invoice, or supplier invoice is returned from a read endpoint | Response includes the stored legacy header snapshot so the app can inspect historical state | N/A |

</frozen-after-approval>

## Code Map

- `backend/common/models/order.py` -- Sales-order persistence model that needs a legacy header snapshot field.
- `backend/domains/invoices/models.py` -- Invoice persistence model that needs a legacy header snapshot field.
- `backend/common/models/supplier_invoice.py` -- Purchase-side persistence model that needs a legacy header snapshot field.
- `backend/domains/legacy_import/canonical.py` -- Fetches staged sales and purchase headers and writes canonical records; primary import logic change lives here.
- `backend/domains/legacy_import/validation.py` -- Batch validation reporting surface for making snapshot coverage visible.
- `backend/domains/orders/schemas.py` -- Order read schema that should expose legacy header snapshot data.
- `backend/domains/invoices/schemas.py` -- Invoice read schema that should expose legacy header snapshot data.
- `backend/domains/purchases/schemas.py` -- Supplier invoice read schema that should expose legacy header snapshot data.
- `backend/tests/domains/legacy_import/test_canonical.py` -- Canonical import regression coverage for preserved header snapshots.
- `backend/tests/domains/purchases/test_supplier_invoices_api.py` -- Purchase read API coverage for exposing snapshot fields.

## Tasks & Acceptance

**Execution:**
- [ ] `migrations/versions/*.py` -- Add nullable legacy header snapshot columns to `orders`, `invoices`, and `supplier_invoices` -- Preserve source-era document state without overloading operational columns.
- [ ] `backend/common/models/order.py`, `backend/domains/invoices/models.py`, `backend/common/models/supplier_invoice.py` -- Add mapped snapshot fields -- Make the new columns available to import and read layers.
- [ ] `backend/domains/legacy_import/canonical.py` -- Capture extra staged sales and purchase header fields into deterministic snapshot payloads and upsert them during canonical import -- Fix the current header-state data-loss root cause.
- [ ] `backend/domains/orders/schemas.py`, `backend/domains/invoices/schemas.py`, `backend/domains/purchases/schemas.py` -- Expose legacy header snapshots in read responses -- Let the app inspect preserved legacy state.
- [ ] `backend/domains/legacy_import/validation.py` -- Add snapshot-coverage counts or issues to validation output -- Make future silent defaulting visible in batch artifacts.
- [ ] `backend/tests/domains/legacy_import/test_canonical.py`, `backend/tests/domains/purchases/test_supplier_invoices_api.py` -- Add focused regression tests for snapshot persistence and API exposure -- Prove replay-safe preservation and read-surface support.
- [x] `migrations/versions/*.py` -- Add nullable legacy header snapshot columns to `orders`, `invoices`, and `supplier_invoices` -- Preserve source-era document state without overloading operational columns.
- [x] `backend/common/models/order.py`, `backend/domains/invoices/models.py`, `backend/common/models/supplier_invoice.py` -- Add mapped snapshot fields -- Make the new columns available to import and read layers.
- [x] `backend/domains/legacy_import/canonical.py` -- Capture extra staged sales and purchase header fields into deterministic snapshot payloads and upsert them during canonical import -- Fix the current header-state data-loss root cause.
- [x] `backend/domains/orders/schemas.py`, `backend/domains/invoices/schemas.py`, `backend/domains/purchases/schemas.py` -- Expose legacy header snapshots in read responses -- Let the app inspect preserved legacy state.
- [x] `backend/domains/legacy_import/validation.py` -- Add snapshot-coverage counts or issues to validation output -- Make future silent defaulting visible in batch artifacts.
- [x] `backend/tests/domains/legacy_import/test_canonical.py`, `backend/tests/domains/purchases/test_supplier_invoices_api.py` -- Add focused regression tests for snapshot persistence and API exposure -- Prove replay-safe preservation and read-surface support.

**Acceptance Criteria:**
- Given a staged sales header with legacy-only state fields, when canonical import runs, then the resulting order and invoice retain that state in a persisted legacy header snapshot.
- Given a staged purchase header with legacy-only state fields, when canonical import runs, then the resulting supplier invoice retains that state in a persisted legacy header snapshot.
- Given an imported document returned by order, invoice, or purchase read APIs, when the response is serialized, then the legacy header snapshot is included without changing existing operational status fields.
- Given a replay of the same batch, when canonical import reruns, then the snapshot payload is updated deterministically on the same canonical records.
- Given a validation run for a batch using the new snapshot preservation path, when validation artifacts are emitted, then they surface whether header snapshots were preserved for the imported documents.

## Spec Change Log

- 2026-04-10: Completed the legacy header snapshot slice, including persistence, read-surface exposure, validation artifact coverage, and focused regression coverage.

## Design Notes

Preserve header state as snapshot data, not as a premature status remapping.

This slice is intentionally narrower than “fix every audited gap.” It addresses the most visible loss first: imported document headers. That keeps the initial schema and import changes bounded while creating the architectural pattern that later slices can reuse for line-level and master-data preservation.

The snapshot payload should contain verified raw header evidence that the importer already reads or can read cheaply from the staged header rows. Good candidates include source status code, period code, exchange rate, denormalized party name and address, source tax metadata, and any import-time fallback decisions such as which purchase invoice number/date source won.

## Verification

**Commands:**
- `cd backend && uv run pytest -q tests/domains/legacy_import/test_canonical.py` -- expected: legacy canonical import tests pass with snapshot assertions.
- `cd backend && uv run pytest -q tests/domains/purchases/test_supplier_invoices_api.py` -- expected: purchase API serialization passes with snapshot fields exposed.
- `cd backend && uv run python -m domains.legacy_import.cli --help` -- expected: CLI remains wired after the schema and import changes.

**Completed:**
- `cd backend && uv run pytest -q tests/domains/legacy_import/test_validation.py tests/domains/legacy_import/test_canonical.py tests/domains/purchases/test_supplier_invoices_api.py`
- `cd backend && uv run python -m domains.legacy_import.cli --help`