# AP Payment Model

This note defines the canonical target design for supplier-side payment history from `raw_legacy.tbsprepay` and `raw_legacy.tbsspay`.

It does not implement canonical import yet. Its purpose is to replace the vague "payment-side AP model exists later" gap with an explicit design that can be verified before code lands.

## Current State

- The canonical AP payment schema foundation now exists in code as `supplier_payments` and `supplier_payment_allocations`.
- The schema foundation is intentionally ahead of import logic: `tbsprepay` and `tbsspay` still stay in holding until the verification checklist below is satisfied.
- This means the repo now has a stable AP target without pretending the legacy allocation semantics are already proven.

## Why The Existing `payments` Table Is Not The Right Target

- The current `payments` model is AR-oriented: it requires `customer_id` and centers reconciliation around customer invoices.
- It only exposes one direct `invoice_id` pointer, which is fine for customer payment matching but not for supplier settlements that may span multiple invoices.
- Its `match_status`, `match_type`, and `suggested_invoice_id` fields assume customer receivable workflows, not supplier payable workflows.
- Reusing it for AP would either force supplier cash events into customer semantics or drop core AP behavior such as unapplied balances and many-to-many allocations.

## Design Goals

- Keep AP settlement history separate from AR payment history.
- Model one supplier cash event once, then allocate it across zero or more supplier invoices.
- Treat prepayments as a first-class payment kind, not as a special-case table outside the settlement model.
- Preserve deterministic IDs, tenant scope, and canonical lineage so replay remains lossless.
- Allow import to stop at an unapplied payment state when invoice linkage is not yet verified.

## Canonical Target

### `supplier_payments`

One row per supplier cash event or legacy payment document.

Recommended fields:

- `id`: deterministic tenant-scoped UUID derived from legacy source identity.
- `tenant_id`
- `supplier_id`: foreign key to `supplier`.
- `payment_number`: business-facing identifier from the legacy payment/prepayment record.
- `payment_kind`: `prepayment`, `special_payment`, `adjustment`, or another verified AP-specific enum value.
- `status`: `unapplied`, `partially_applied`, `applied`, `voided`.
- `currency_code`
- `payment_date`
- `gross_amount`
- `payment_method`: initially permissive string or lightly bounded enum until legacy semantics are verified.
- `reference_number`: bank slip, transfer reference, or legacy document cross-reference when present.
- `notes`
- `created_at`, `updated_at`

Design rules:

- Do not create a separate `supplier_prepayments` table. Prepayments are `supplier_payments` with `payment_kind = prepayment`.
- Canonical truth is the supplier payment plus its allocations. Applied and unapplied balances should be derived from allocation totals even if materialized later for performance.
- Keep raw source payload in lineage or holding tables, not duplicated inside the operational AP tables.

### `supplier_payment_allocations`

Many-to-many settlement bridge between supplier payments and supplier invoices.

Recommended fields:

- `id`: deterministic tenant-scoped UUID derived from payment, invoice, and source allocation identity.
- `tenant_id`
- `supplier_payment_id`: foreign key to `supplier_payments`.
- `supplier_invoice_id`: foreign key to `supplier_invoices`.
- `allocation_date`
- `applied_amount`
- `allocation_kind`: `invoice_settlement`, `prepayment_application`, `reversal`.
- `notes`
- `created_at`, `updated_at`

Design rules:

- One supplier payment may allocate across many supplier invoices.
- One supplier invoice may be settled by many supplier payments.
- Allocation rows should only be created when invoice linkage is verified from legacy columns or from a separately approved mapping rule.

## Import Rules By Legacy Source

| Legacy source | Canonical target | Import rule |
| --- | --- | --- |
| `raw_legacy.tbsprepay` | `supplier_payments` | Import one supplier payment per legacy prepayment row with `payment_kind = prepayment`. Default to `unapplied` or `partially_applied` until linked supplier invoices are verified. |
| `raw_legacy.tbsspay` | `supplier_payments` | Import one supplier payment per legacy special-payment row with an AP-specific `payment_kind`. Only create allocations when invoice linkage is verified. |
| Verified invoice-link columns from either source | `supplier_payment_allocations` | Create allocation rows only when supplier, invoice, amount, and sign semantics are proven. |

## Implementation Boundary

Until the remaining legacy column semantics are verified, `tbsprepay` and `tbsspay` should stay in `raw_legacy.unsupported_history_holding` during canonical import.

The move out of holding should happen in two stages:

1. Create canonical AP payment rows as unapplied supplier payments once supplier identity, dates, signs, and amount columns are verified.
2. Create allocation rows only after invoice-link fields are proven on real sample data.

That boundary keeps the migration lossless without faking allocation certainty.

## Verification Checklist Before Implementation

Implementation should not start until these checks are complete for both `tbsprepay` and `tbsspay`:

- Identify the supplier-reference column and prove it maps to the normalized supplier-party flow from Story 16.2.
- Identify the legacy document number used as the stable business key for deterministic IDs.
- Verify payment amount columns and sign conventions for normal, partial, and reversed rows.
- Verify ROC date fields and empty-date defaults.
- Verify whether either table contains trustworthy supplier-invoice references.
- Verify whether the source distinguishes full settlement, partial settlement, prepayment carry-forward, and void/reversal rows.
- Reconcile at least one sample supplier across supplier invoices, payment rows, and expected open balances.

## Future Product Surface

- The shipped `/purchases` workspace remains read-only and invoice-centric for now.
- Once `supplier_payments` exists, the next read-side surface should show supplier payment history, unapplied balances, and invoice allocations alongside the existing supplier invoice detail view.
- Write-side AP settlement workflow remains a later step after canonical import and read models are stable.