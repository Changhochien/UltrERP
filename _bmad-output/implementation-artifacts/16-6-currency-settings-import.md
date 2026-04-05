# Story 16.6: Currency Settings Import

Status: draft

## Story

As a migration operator,
I want currency settings from the legacy system available in UltrERP,
So that the canonical app_settings reflects the currencies used in historical transactions.

## Acceptance Criteria

**AC1:** Currency rows upserted into app_settings
**Given** tbscurrency contains currency configuration (6 rows)
**When** the currency import step runs
**Then** each currency row is upserted into app_settings with keys like `currency.{code}.symbol`, `currency.{code}.decimal_places`

**AC2:** Default currency marked
**When** the import runs
**Then** the default currency is marked in app_settings as `currency.default`

**AC3:** Existing keys preserved on re-import
**Given** existing app_settings.currency.* keys are present
**When** the same currency code is re-imported
**Then** only that currency's keys are replaced; unrelated currency keys are preserved

**AC4:** Idempotent — no duplicates
**When** the import is re-run
**Then** no duplicate currency settings are created

## Tasks / Subtasks

- [ ] **Task 1: Survey tbscurrency shape**
  - [ ] Confirm column names, row count, and sample values from the extracted CSV or staging view
  - [ ] Identify which row represents the default currency

- [ ] **Task 2: Add currency-import CLI subcommand**
  - [ ] Add `currency-import` subcommand to `domains.legacy_import.cli`
  - [ ] Command: `uv run python -m domains.legacy_import.cli currency-import --export-dir <path>`
  - [ ] Read CSV directly (no raw_legacy staging needed — small, static reference table)
  - [ ] Upsert into app_settings per AC1/AC2/AC3/AC4

- [ ] **Task 3: Idempotent upsert logic**
  - [ ] Query existing `currency.*` keys from app_settings before writing
  - [ ] Use ON CONFLICT (key) DO UPDATE for PostgreSQL upsert
  - [ ] Track import in `legacy_import_table_runs` with batch_id semantics

## Dev Notes

### Table Structure (tbscurrency)

The tbscurrency table holds currency configuration. Expected columns:

| Column | Type | Description |
|--------|------|-------------|
| currency_id | int | Primary key |
| currency_code | varchar | ISO code e.g. USD, TWD |
| currency_name | varchar | Full name e.g. US Dollar |
| symbol | varchar | e.g. $, NT$ |
| decimal_places | int | Number of decimal places (typically 2) |
| is_default | bool | True for the system default currency |

Typical row count: **6 rows**.

### app_settings Key Pattern

Each currency writes two keys:

```
currency.{code}.symbol        → e.g. "NT$"
currency.{code}.decimal_places → e.g. "2"
```

Default currency marker:

```
currency.default              → e.g. "USD"
```

Values are stored as plain strings in `app_settings.value`.

### Idempotent Upsert

```python
# Pseudocode — run inside transaction
for row in currency_rows:
    key_symbol = f"currency.{row.currency_code}.symbol"
    key_decimal = f"currency.{row.currency_code}.decimal_places"

    # Upsert symbol
    stmt = insert(AppSetting).values(key=key_symbol, value=row.symbol)
    stmt = stmt.on_conflict_do_update(
        index_elements=["key"],
        set_={"value": row.symbol}
    )
    await db.execute(stmt)

    # Upsert decimal_places
    stmt = insert(AppSetting).values(key=key_decimal, value=str(row.decimal_places))
    stmt = stmt.on_conflict_do_update(
        index_elements=["key"],
        set_={"value": str(row.decimal_places)}
    )
    await db.execute(stmt)

# Upsert default marker
if row.is_default:
    stmt = insert(AppSetting).values(key="currency.default", value=row.currency_code)
    stmt = stmt.on_conflict_do_update(
        index_elements=["key"],
        set_={"value": row.currency_code}
    )
    await db.execute(stmt)
```

### Why No raw_legacy Staging

tbscurrency is a small, static reference table (6 rows). Unlike transaction tables (tbspurh, tbspodetail) it does not require:
- Lineage tracking across batches
- Versioned same-batch reruns
- Large-table COPY optimization

It is read directly from the extracted CSV and written straight into app_settings.

### CLI Integration

The `currency-import` subcommand can be run standalone or as part of a wider import pipeline:

```bash
# Standalone
uv run python -m domains.legacy_import.cli currency-import --export-dir /path/to/extracted

# As part of full import sequence
uv run python -m domains.legacy_import.cli stage --table tbscurrency
uv run python -m domains.legacy_import.cli currency-import --export-dir /path/to/extracted
```

Note: The `stage` step for tbscurrency is optional since this command reads the CSV directly and does not use raw_legacy staging.

### Validation

- Confirm 6 rows in tbscurrency after import
- Confirm `currency.default` key exists and matches the row with `is_default = True`
- Rerun the command and confirm row count stays at 6 (no duplicates)
- Check app_settings for `currency.*` keys after rerun — values should be updated, not appended

## File List

- `backend/domains/legacy_import/cli.py` — add `currency-import` subcommand
- `backend/domains/legacy_import/currency.py` — currency import logic
- `backend/tests/domains/legacy_import/test_currency.py` — idempotency and correctness tests

## References

- `_bmad-output/planning-artifacts/epics.md` — Epic 16 / Story 16.6
- `backend/domains/settings/seed.py` — app_settings upsert pattern
- `backend/domains/settings/models.py` — AppSetting model
- `legacy-migration-pipeline/extracted_data/` — tbscurrency CSV source