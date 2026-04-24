# Legacy Import Command Map

This command map now treats dump extraction and file-based staging as archival or break-glass workflows. The routine operator path is the live legacy DB flow in sections 8-10: `run_legacy_refresh`, scheduled shadow refresh, and promotion evaluation.

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
cd backend && uv run python -m domains.legacy_import.cli live-stage --help
cd backend && uv run python -m domains.legacy_import.cli normalize --help
cd backend && uv run python -m domains.legacy_import.cli map-products --help
cd backend && uv run python -m domains.legacy_import.cli export-product-review --help
cd backend && uv run python -m domains.legacy_import.cli import-product-review --help
cd backend && uv run python -m domains.legacy_import.cli canonical-import --help
cd backend && uv run python -m domains.legacy_import.cli validate-import --help
cd backend && uv run python -m domains.legacy_import.cli currency-import --help
cd backend && uv run python -m domains.legacy_import.cli ap-payment-import --help
cd backend && uv run python -m scripts.run_legacy_refresh --help
cd backend && uv run python -m scripts.run_scheduled_legacy_shadow_refresh --help
cd backend && uv run python -m scripts.run_legacy_promotion --help
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
dependency. Re-running overwrites the output directory. Use an explicit archival output
directory; do not treat `legacy-migration-pipeline/extracted_data` as the default
working location. After extraction, use `stage`
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

Pass `--source-dir` explicitly unless `LEGACY_IMPORT_DATA_DIR` is intentionally set to
an archival dump directory.

### 1A. Stage directly from the live legacy DB over Tailscale

Required environment variables: `LEGACY_DB_HOST`, `LEGACY_DB_PORT`, `LEGACY_DB_USER`,
`LEGACY_DB_PASSWORD`, `LEGACY_DB_NAME`, and `LEGACY_DB_CLIENT_ENCODING`.
Do not echo secret values into chat or commit them to the repo. The reviewed live
refresh connector forces read-only transaction defaults, rejects non-`SHOW`/`SELECT`
SQL against the legacy source, and refuses non-read-only transactions even when the
configured legacy role is privileged.

```bash
cd backend && uv run python -m domains.legacy_import.cli live-stage \
  --batch-id <batch-id> \
  --schema raw_legacy \
  --tenant-id <tenant-uuid> \
  [--source-schema public]
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

## 8. Run the reviewed end-to-end live refresh orchestrator

Use this command when the operator wants one reviewed entry point that stages from
the live legacy DB, normalizes, seeds product mappings, optionally exports or imports
product review CSVs, runs canonical import, validates the batch, backfills stock
history, and verifies reconciliation in one batch-scoped flow.

```bash
cd backend && uv run python -m scripts.run_legacy_refresh \
  --batch-id <batch-id> \
  --tenant-id <tenant-uuid> \
  --schema raw_legacy \
  [--source-schema public] \
  [--lookback-days 10000] \
  [--reconciliation-threshold 0] \
  [--review-input <approved-review.csv> --approved-by <operator-id>]
```

Operator notes:

- If `map-products` still has unresolved codes and no approved review CSV is supplied,
  the orchestrator exports a deterministic review CSV under
  `_bmad-output/operations/legacy-refresh/product-review/`, continues with the existing
  `UNKNOWN` fallback behavior, and records the batch as not promotion-ready.
- The orchestrator writes one machine-readable summary JSON per run under
  `_bmad-output/operations/legacy-refresh/`. Same-batch reruns create a new summary file
  instead of overwriting the prior run evidence.
- Each summary includes a shared `promotion_policy` object with `classification`,
  `reason_codes`, and machine-readable gate details so scheduler state and promotion
  reuse the same reviewed policy contract.
- This command stops at refresh plus evidence generation. It does not schedule recurring
  runs, promote the batch into the working lane, or auto-apply reconciliation corrections.

## 9. Run the scheduled shadow refresh wrapper

Use this command when the operator wants a cron-safe shadow refresh entry point that
generates its own immutable batch id, reuses the reviewed refresh orchestrator, and
persists stable `latest-run` and `latest-success` state for one shadow lane.

```bash
cd backend && uv run python -m scripts.run_scheduled_legacy_shadow_refresh \
  --tenant-id <tenant-uuid> \
  --schema raw_legacy \
  [--source-schema public] \
  [--batch-prefix legacy-shadow] \
  [--lookback-days 10000] \
  [--reconciliation-threshold 0]
```

Cron-safe example:

```bash
0 2 * * * cd /path/to/UltrERP/backend && uv run python -m scripts.run_scheduled_legacy_shadow_refresh --tenant-id <tenant-uuid> --schema raw_legacy --source-schema public --batch-prefix legacy-shadow --lookback-days 10000 --reconciliation-threshold 0
```

Operator notes:

- The wrapper generates a fresh UTC batch id such as `legacy-shadow-20260418T020304Z`
  for each scheduled invocation instead of accepting a caller-supplied `--batch-id`.
- Per-lane scheduler state lives under
  `_bmad-output/operations/legacy-refresh/state/<schema>-<tenant>-<source-schema>/`
  with `latest-run.json`, `latest-success.json`, and a transient `scheduler.lock`.
- `latest-success.json` advances only for `completed` and
  `completed-review-required`. A blocked, failed, or overlap-blocked run updates only
  `latest-run.json`.
- `latest-run.json` and `latest-success.json` copy the summary `promotion_policy`
  outcome so downstream alerts and operator tooling do not need to re-interpret the
  gate thresholds themselves.
- If `scheduler.lock` already exists, the wrapper exits with an explicit overlap outcome
  and does not start a second refresh for that same lane. Treat a stale lock as an
  operator investigation item; remove it only after confirming no refresh is still
  active.
- This command still stays inside the shadow lane. It does not write promotion
  pointers, approval requests, or working-lane cutover state.

## 10. Promote the latest eligible shadow batch into the working lane

Use this command when the operator wants the reviewed promotion entry point to
evaluate the current lane candidate and advance the working-lane pointer only if
all promotion gates pass.

```bash
cd backend && uv run python -m scripts.run_legacy_promotion \
  --tenant-id <tenant-uuid> \
  --schema raw_legacy \
  [--source-schema public] \
  [--promoted-by <operator-id> --allow-exception-override --override-rationale <text> --override-scope <text>]
```

Operator notes:

- The promotion step consumes the existing lane state under
  `_bmad-output/operations/legacy-refresh/state/<schema>-<tenant>-<source-schema>/`
  and reads `latest-success.json` plus the referenced refresh summary JSON.
- Successful promotion writes `latest-promoted.json`, which becomes the reviewed
  working-lane pointer for that lane.
- Every promotion evaluation also writes one machine-readable result artifact under
  `promotion-results/` in the same lane state root.
- Promotion artifacts expose `promotion_policy_classification`,
  `promotion_policy_reason_codes`, `promotion_mode`, and optional
  `override_record_path` metadata.
- If the lane still has an active `scheduler.lock`, the candidate summary is missing,
  validation is not passed, reconciliation is blocked, or analyst review is still
  required, the automatic path stays blocked and the previous `latest-promoted.json`
  pointer stays unchanged. Analyst-review cases are surfaced as `exception-required` so
  operators can distinguish them from hard blocks.
- If the latest successful shadow batch is already the promoted batch, the result is
  `noop` and the pointer is not rewritten.
- Exception overrides are explicit and audited. They require operator identity, a
  rationale, and a scope, and they write a durable record under `promotion-overrides/`
  before the pointer is updated.

## 11. Propose reconciliation corrections for operator review

Use this command when the operator wants a CSV of candidate inventory corrections
without applying anything automatically.

```bash
cd backend && uv run python -m scripts.propose_reconciliation_corrections \
  [--tenant-id <tenant-uuid>] \
  [--min-abs-gap 1] \
  [--limit 25] \
  [--csv <proposal.csv>] \
  [--as-of-day YYYY-MM-DD]
```

Operator notes:

- The proposal output marks rows as `actionable` or `review_only`; review-only rows stay
  manual by design.
- This command does not write stock adjustments or advance promotion state.

## 12. Apply an explicitly approved subset of correction proposals

Use this command only after an operator has reviewed the proposal CSV and marked the
approved actionable rows with `approval_action=apply`.

```bash
cd backend && uv run python -m scripts.apply_reconciliation_corrections \
  --csv <proposal.csv> \
  --approved-by <operator-id> \
  [--tenant-id <tenant-uuid>] \
  [--live]
```

Operator notes:

- Dry-run is the default. `--live` is required to persist approved corrections.
- The apply step rejects rows that are not `actionable` or whose `approval_action` is
  anything other than `apply`.
- Scheduled refresh and automatic promotion never invoke this command automatically.
