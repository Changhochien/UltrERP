# Purchase Invoice Canonical Target

This note documents the first-class AP landing zone introduced for legacy purchase invoice history.

## Scope

- `raw_legacy.tbsslipj` now imports into `supplier_invoices`.
- `raw_legacy.tbsslipdtj` now imports into `supplier_invoice_lines`.
- `raw_legacy.normalized_parties` where `role = supplier` now imports into `supplier` before purchase history runs.
- `raw_legacy.tbsprepay` and `raw_legacy.tbsspay` still remain in `raw_legacy.unsupported_history_holding` until a verified payment-side AP model exists.
- The read API for imported AP history now lives at `/api/v1/purchases/supplier-invoices` and `/api/v1/purchases/supplier-invoices/{invoice_id}`.
- The frontend shell now exposes that read model through the read-only `/purchases` workspace.

## Design Rules

- Supplier invoices use deterministic tenant-scoped UUIDs derived from the legacy purchase document number.
- Supplier invoice lines use deterministic tenant-scoped UUIDs derived from legacy document number plus line number.
- Purchase lines reuse `raw_legacy.product_code_mapping`; unresolved codes still fall back to `UNKNOWN` so reruns stay lossless.
- Header tax is allocated across imported purchase lines so line totals reconcile to the imported supplier invoice header.
- Canonical lineage records are written for `supplier`, `supplier_invoices`, and `supplier_invoice_lines` the same way they are for sales-side history.

## Deferred Work

- AP payment and prepayment implementation is still deferred, but the target design now lives in `docs/legacy/ap-payment-model.md`.
- Purchase-order to supplier-invoice matching is still deferred.
- Write-side AP workflow and payment-specific screens are still deferred; the shipped `/purchases` workspace is read-only.

This keeps the migration lossless and auditable without forcing purchase invoice history into the sales AR tables or the payment holding path.