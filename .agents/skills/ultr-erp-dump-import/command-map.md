# Legacy Import Command Map

Run every legacy-import command from the backend directory so the repo uses the reviewed `uv` environment and import paths.

## Stable Invocation Path

```bash
cd backend && uv run python -m domains.legacy_import.cli --help
```

If the environment is fresh or the CLI reports missing legacy-import control tables,
bring the schema to the current Alembic head first:

```bash
cd backend && uv run alembic -c ../migrations/alembic.ini upgrade head
```

If Alembic reports multiple heads on the active branch, confirm with the operator
before using the fallback:

```bash
cd backend && uv run alembic -c ../migrations/alembic.ini upgrade heads
```

## Read-Only Discovery Commands

Use these before any write command when the operator needs syntax confirmation.

```bash
cd backend && uv run python -m domains.legacy_import.cli --help
cd backend && uv run python -m domains.legacy_import.cli extract --help
cd backend && uv run python -m domains.legacy_import.cli stage --help
cd backend && uv run python -m domains.legacy_import.cli normalize --help
cd backend && uv run python -m domains.legacy_import.cli map-products --help
cd backend && uv run python -m domains.legacy_import.cli export-product-review --help
cd backend && uv run python -m domains.legacy_import.cli import-product-review --help
cd backend && uv run python -m domains.legacy_import.cli canonical-import --help
cd backend && uv run python -m domains.legacy_import.cli validate-import --help
cd backend && uv run python -m domains.legacy_import.cli currency-import --help
cd backend && uv run python -m domains.legacy_import.cli ap-payment-import --help
```

## Phase-to-Command Mapping

### 0. Extract a raw SQL dump into CSV files (no DB required)

```bash
cd backend && uv run python -m domains.legacy_import.cli extract \
  --input </path/to/dump.sql> \
  --output <output-dir> \
  [--format csv|json|both] \
  [--encoding <force-encoding>]
```

This is the entry point when starting from a raw SQL dump. It has no database
dependency. Re-running overwrites the output directory. After extraction, use `stage`
(phase 1) to load the CSVs into the staging schema.

### 1. Stage extracted legacy CSVs into raw staging

```bash
cd backend && uv run python -m domains.legacy_import.cli stage \
  --batch-id <batch-id> \
  --source-dir <legacy-export-dir> \
  --schema raw_legacy \
  --tenant-id <tenant-uuid>
```

Optional repeatable scope limiter:

```bash
  --table <table-name>
```

### 2. Normalize staged master data into canonical prep tables

```bash
cd backend && uv run python -m domains.legacy_import.cli normalize \
  --batch-id <batch-id> \
  --schema raw_legacy \
  --tenant-id <tenant-uuid>
```

### 3. Seed auditable product-code mappings

```bash
cd backend && uv run python -m domains.legacy_import.cli map-products \
  --batch-id <batch-id> \
  --schema raw_legacy \
  --tenant-id <tenant-uuid>
```

### 4. Export unresolved product mappings for analyst review

```bash
cd backend && uv run python -m domains.legacy_import.cli export-product-review \
  --batch-id <batch-id> \
  --output <review-export.csv> \
  --schema raw_legacy \
  --tenant-id <tenant-uuid>
```

### 5. Import analyst-reviewed mapping decisions

```bash
cd backend && uv run python -m domains.legacy_import.cli import-product-review \
  --batch-id <batch-id> \
  --input <review-import.csv> \
  --approved-by <operator-id> \
  --schema raw_legacy \
  --tenant-id <tenant-uuid>
```

### 6. Import normalized legacy data into canonical tables

Prerequisites:

- the batch already has staged sales headers and details (`tbsslipx` and `tbsslipdtx`)
- required master-data normalization and mapping work for the batch is complete

```bash
cd backend && uv run python -m domains.legacy_import.cli canonical-import \
  --batch-id <batch-id> \
  --schema raw_legacy \
  --tenant-id <tenant-uuid>
```

### 7. Validate an imported batch and emit JSON plus Markdown artifacts

Prerequisite: the batch already has at least one completed `canonical-import` run.
If the CLI reports that no canonical import run exists, stop and ask for the
batch that actually reached canonical import.

```bash
cd backend && uv run python -m domains.legacy_import.cli validate-import \
  --batch-id <batch-id> \
  --schema raw_legacy \
  --tenant-id <tenant-uuid>
```

Optional attempt pinning:

```bash
  --attempt-number <canonical-attempt-number>
```

## Required Run Report Back to the Operator

After any command finishes, report:

- exact CLI command
- exit code
- batch id
- schema
- tenant id
- attempt number when validation or canonical import surfaces one
- output file paths for review exports or validation artifacts
