# Canonical Import Target Matrix

This document defines where Story 15.4 lands historical legacy data during the `legacy-import canonical-import` phase.

## Principles

- Only write into live UltrERP tables when the target domain already exists and the field mapping is verified.
- Preserve unsupported or only partially mapped history in a migration-owned holding area instead of forcing it into operational tables.
- Keep tenant scope, import batch, and source lineage visible for every canonical write.

## Target Matrix

| Legacy source | Scope | Target | Notes |
| --- | --- | --- | --- |
| `raw_legacy.normalized_parties` where `role = customer` | Supported live master data | `customers` | `normalized_business_number` uses the verified tax ID when present, otherwise a deterministic synthetic fallback derived from the legacy key. |
| `raw_legacy.normalized_parties` where `role = supplier` | Supported live master data | `supplier` | Supplier master rows are imported before purchase invoice history so AP documents can bind to stable supplier IDs. |
| `raw_legacy.normalized_products` | Supported live master data | `product` | Uses deterministic tenant-scoped product UUIDs derived from normalized legacy codes so reruns remain idempotent without cross-tenant collisions. |
| `raw_legacy.normalized_warehouses` | Supported live master data | `warehouse` | Uses the normalized synthetic default warehouse when the legacy dataset does not expose a first-class warehouse master. |
| `raw_legacy.normalized_inventory_prep` | Supported live stock state | `inventory_stock` | Imports only after product and warehouse rows are present. |
| `raw_legacy.tbsslipx` | Supported live transaction header | `orders`, `invoices` | Historical sales headers are imported through the legacy import layer, not via operational order or invoice routes. |
| `raw_legacy.tbsslipdtx` | Supported live transaction detail | `order_lines`, `invoice_lines` | Product resolution uses `raw_legacy.product_code_mapping`; unresolved codes fall back to `UNKNOWN`. |
| `raw_legacy.tbsslipj` | Supported live AP header | `supplier_invoices` | Imported as first-class supplier invoice history with deterministic IDs and lineage back to the legacy purchase document. |
| `raw_legacy.tbsslipdtj` | Supported live AP detail | `supplier_invoice_lines` | Product resolution uses `raw_legacy.product_code_mapping`; unresolved codes fall back to `UNKNOWN`. |
| `raw_legacy.tbsprepay`, `raw_legacy.tbsspay` when staged | Unsupported payment-adjacent history | `raw_legacy.unsupported_history_holding` | Stored with `domain_name = payment_history` and the full raw payload until the verification gates in `docs/legacy/ap-payment-model.md` are satisfied. |

## Lineage And Replay Tables

| Table | Purpose |
| --- | --- |
| `raw_legacy.canonical_import_runs` | Batch-level canonical import run metadata with replay attempts and final status. |
| `raw_legacy.canonical_import_step_runs` | Step-level observability for dependency-ordered canonical import execution. |
| `raw_legacy.canonical_record_lineage` | Deterministic mapping from a live canonical row back to source table, source identifier, source row, tenant, and batch. |
| `raw_legacy.unsupported_history_holding` | Explicit holding area for unsupported payment-adjacent history and any future unmapped legacy domains. |

## Replay Safety Rules

- Live canonical writes use deterministic tenant-scoped UUIDs and `ON CONFLICT` upserts.
- Lineage rows upsert on tenant, batch, canonical table, canonical record, and source identifier.
- Unsupported holding rows upsert on tenant, batch, source table, source identifier, and source row number.
- Replaying the same tenant and batch updates the same canonical and lineage rows rather than creating duplicates.