# Story 16.6: Currency Settings Import

Status: done

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

- [x] **Task 1: Survey tbscurrency shape**
  - [x] Confirm column names, row count, and sample values from the extracted CSV and raw SQL DDL
  - [x] Identify the default currency from `scurlocal = '1'`

- [x] **Task 2: Add currency-import CLI subcommand**
  - [x] Add `currency-import` subcommand to `domains.legacy_import.cli`
  - [x] Command: `uv run python -m domains.legacy_import.cli currency-import --export-dir <path>`
  - [x] Read CSV directly (no raw_legacy staging needed — small, static reference table)
  - [x] Upsert into app_settings per AC1/AC2/AC3/AC4

- [x] **Task 3: Idempotent upsert logic**
  - [x] Replace same-key values via PostgreSQL `ON CONFLICT (key) DO UPDATE`
  - [x] Preserve unrelated `currency.*` keys because only touched keys are upserted
  - [x] Track the import in `legacy_import_runs` and `legacy_import_table_runs`

## Dev Notes

### Table Structure (tbscurrency)

The raw SQL DDL in the legacy dump shows these relevant columns:

| Column | Description | Used for import |
|--------|-------------|-----------------|
| `scurno` | legacy currency identifier | no |
| `scurengname` | currency code (`NTD`, `USD`, `HKD`, etc.) | yes |
| `scurlocal` | default/local currency flag | yes |
| `ioutamtdot`, `iinamtdot`, `iapayamtdot`, `iapaytotaldot`, `iapaytaxdot` | legacy precision fields | yes, importer takes the maximum |

Typical row count: **6 rows**.

The source data does **not** expose a dedicated symbol column. The importer therefore uses a trusted fallback map for well-known codes (`TWD`, `USD`, `JPY`, `HKD`, `EUR`) and otherwise falls back to the currency code itself.

### app_settings Key Pattern

Each currency writes two keys:

```
currency.{code}.symbol        → e.g. "NT$"
currency.{code}.decimal_places → e.g. "2"
```

Default currency marker:

```
currency.default              → e.g. "TWD"
```

Values are stored as plain strings in `app_settings.value`.

### Implementation Notes

- `backend/domains/legacy_import/currency.py` loads `tbscurrency.csv` directly through the existing legacy-row parser.
- `NTD` is normalized to `TWD` so the resulting app settings align with the canonical currency handling already used elsewhere in Epic 16.
- Decimal places are derived from the maximum legacy precision across the amount-dot columns so currencies like `HKD` retain their higher configured precision.
- Upserts touch only the target keys for the current currency code plus `currency.default`, which keeps unrelated `currency.*` settings intact.

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

- `cd backend && uv run pytest tests/domains/legacy_import/test_currency.py tests/domains/legacy_import/test_cli.py -q`
- `cd backend && uv run ruff check domains/legacy_import/currency.py domains/legacy_import/cli.py tests/domains/legacy_import/test_currency.py tests/domains/legacy_import/test_cli.py`
- Result: `10 passed`, Ruff clean

## File List

- `backend/domains/legacy_import/cli.py` — add `currency-import` subcommand
- `backend/domains/legacy_import/currency.py` — currency import logic
- `backend/tests/domains/legacy_import/test_currency.py` — idempotency and correctness tests
- `backend/tests/domains/legacy_import/test_cli.py` — CLI wiring coverage

## References

- `_bmad-output/planning-artifacts/epics.md` — Epic 16 / Story 16.6
- `backend/domains/settings/seed.py` — app_settings upsert pattern
- `backend/domains/settings/models.py` — AppSetting model
- `legacy-migration-pipeline/extracted_data/` — tbscurrency CSV source