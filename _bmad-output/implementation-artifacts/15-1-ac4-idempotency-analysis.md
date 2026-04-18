# AC4 Idempotency Gap Analysis — Receiving Audit Batch Rerun

**Story:** 15.1 Raw Legacy Staging Import
**Acceptance Criterion:** AC4 — "a stage rerun alone cannot create duplicate canonical records"
**Status:** Risk identified

---

## Current State

### What Is Protected

The receiving audit import ( `_import_legacy_receiving_audit`, canonical.py:1500) performs two distinct writes per line:

**1. `stock_adjustment` insert (line 1556)**

```python
stock_adjustment_id = _tenant_scoped_uuid(
    tenant_id,
    "legacy-receiving-adjustment",
    source_identifier,   # = f"{doc_number}:{line_number}"
)
await connection.execute("""
    INSERT INTO stock_adjustment (
        id, tenant_id, product_id, warehouse_id,
        quantity_change, reason_code, actor_id, notes, transfer_id, created_at
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
    ON CONFLICT (id) DO NOTHING
""", stock_adjustment_id, ...)
```

The `id` is a **deterministic UUID** derived from `tenant_id + "legacy-receiving-adjustment" + source_identifier`. Rerunning the same batch with the same `doc_number:line_number` rows will generate the same UUIDs. Because the upsert uses `ON CONFLICT (id) DO NOTHING`, a rerun is silently idempotent at the `stock_adjustment` layer — no duplicate canonical records are created.

**2. `canonical_record_lineage` insert (`_upsert_lineage`, line 544)**

```python
await connection.execute(f"""
    INSERT INTO {quoted_schema}.canonical_record_lineage (
        tenant_id, batch_id, canonical_table, canonical_id,
        source_table, source_identifier, source_row_number, import_run_id
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    ON CONFLICT (run_id, step_name, canonical_table, canonical_id) DO NOTHING
""", ...)
```

The `ON CONFLICT` here is on the **composite key** `(run_id, step_name, canonical_table, canonical_id)`.

---

## The Specific Risk

When a batch is rerun with a **new `run_id`** (which is a fresh `uuid.UUID` generated per import invocation):

| Layer | `run_id` | Effect on rerun of same batch |
|---|---|---|
| `stock_adjustment` | Same deterministic UUID (not run-scoped) | `ON CONFLICT (id) DO NOTHING` — silently skips, no duplicate |
| `canonical_record_lineage` | **New UUID per run** | `ON CONFLICT (run_id, step_name, canonical_table, canonical_id)` — unique constraint uses new `run_id`, so the conflict does **not** fire; a second lineage row is inserted for the **same canonical_id** |

The result is: a batch rerun creates **duplicate lineage rows** pointing to the same canonical `stock_adjustment` record, violating AC4's intent. More critically, if the `run_id`-scoped unique constraint is the only guard on the lineage table, there is no database-level enforcement preventing two distinct runs from creating lineage entries for the same canonical ID — it is a logical, not enforced, uniqueness.

---

## Affected Tables

| Table | Risk |
|---|---|
| `stock_adjustment` | Protected by deterministic `id` + `ON CONFLICT (id) DO NOTHING` |
| `canonical_record_lineage` | **Vulnerable** — distinct `run_id` values bypass the composite unique key; same `canonical_id` can appear multiple times across runs |

Other canonical tables in the import (e.g., `orders`, `invoices`, `customers`) use similar deterministic-UUID + `ON CONFLICT` patterns and are similarly protected at the record level, but the lineage table's `run_id`-scoped unique key means cross-run lineage deduplication is not enforced by the database.

---

## Recommended Approach

### Option A — Extend lineage unique constraint (preferred)

Remove `run_id` from the lineage unique key and rely on the natural key of `(canonical_table, source_table, source_identifier)` for deduplication within a batch context:

```sql
-- Migration
ALTER TABLE canonical_record_lineage
    DROP CONSTRAINT IF EXISTS canonical_record_lineage_run_id_step_name_canonical_table_canonical_id_key;

CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS
    canonical_record_lineage_source_scope_key
    ON canonical_record_lineage (canonical_table, source_table, source_identifier, tenant_id)
    WHERE batch_id = $1;  -- deduplicate within the same batch

-- Or simpler: include batch_id in the constraint to deduplicate within a batch run
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS
    canonical_record_lineage_batch_canonical_key
    ON canonical_record_lineage (batch_id, canonical_table, source_table, source_identifier, tenant_id);
```

Then change the `ON CONFLICT` target to the natural key so reruns of the same batch insert cleanly with `DO NOTHING`.

### Option B — `ON CONFLICT DO NOTHING` with the right key (minimal fix)

Change the lineage upsert to target `(canonical_table, source_table, source_identifier)` instead of the run-scoped composite key:

```python
await connection.execute(f"""
    INSERT INTO {quoted_schema}.canonical_record_lineage (...)
    VALUES (...)
    ON CONFLICT (canonical_table, source_table, source_identifier, tenant_id) DO NOTHING
""", ...)
```

**Caveat:** This would prevent a **different** batch (different `batch_id`) from inserting lineage for the same `source_identifier` — which may be undesirable if the same source data can legitimately appear in multiple batches. Option A with `batch_id` in the constraint is safer.

### Option C — Add `import_run_id` to canonical table unique constraints

For full cross-run safety, add `import_run_id` (or `run_id`) to the unique constraint on the canonical tables themselves (`stock_adjustment`, etc.), alongside the deterministic key. This makes the database enforce that a given row can only be inserted once per run, and the `ON CONFLICT (id) DO NOTHING` becomes truly idempotent at the canonical layer too.

```sql
-- On stock_adjustment
CREATE UNIQUE INDEX ON stock_adjustment (tenant_id, id, import_run_id);
-- Then use: ON CONFLICT (tenant_id, id, import_run_id) DO NOTHING
```

---

## Recommended Fix

Implement **Option A**: include `batch_id` in the lineage unique constraint and update `_upsert_lineage`'s `ON CONFLICT` target to `(batch_id, canonical_table, source_table, source_identifier, tenant_id)`. This is the minimal change that enforces AC4's guarantee: "a stage rerun alone cannot create duplicate canonical records" at the lineage layer while preserving the ability for distinct batches to have independent lineage entries.

The fix should be applied to `_upsert_lineage` (canonical.py:544) and the corresponding database migration.
