---
name: legacy-import
description: Guide the reviewed UltrERP legacy-import workflow through the stable backend CLI. Default to the live legacy DB path for routine refreshes; use dump extraction or file-based staging only when the operator explicitly starts from an archival SQL dump or preserved CSV export.
argument-hint: "[phase] --batch-id <batch-id> [--schema raw_legacy] [--tenant-id <uuid>]"
---

Use this skill when the operator wants to run or plan the reviewed legacy-import workflow. The routine operator path is the live legacy PostgreSQL source over Tailscale plus the reviewed refresh and promotion surfaces. Dump extraction and file-based staging are archival or break-glass paths only.

This skill is an orchestration wrapper around the backend CLI. Do not reimplement import business logic in Markdown, Python snippets, or ad hoc shell pipelines. Always route workflow execution through the reviewed CLI in [the command map](./command-map.md).

Use these operating rules:

1. Start by identifying the requested phase, batch id, schema, tenant id, and any file path arguments.
2. Use the stable backend invocation path from [the command map](./command-map.md): run commands from `backend/` with `uv run python -m domains.legacy_import.cli ...`.
3. On fresh environments or when the CLI reports missing legacy-import control tables, stop and ask the operator to bring the schema to the current Alembic target before retrying. Use the repo-documented `upgrade head` path first, and if Alembic reports multiple heads on the active branch, ask for confirmation before using the `upgrade heads` fallback documented in [the safety and validation guide](./safety-and-validation.md).
4. Keep shell approval conservative. This skill intentionally does not pre-approve `shell` or `bash`. Follow the confirmation policy in [the safety and validation guide](./safety-and-validation.md).
5. Treat `extract`, `stage`, `live-stage`, `normalize`, `map-products`, `export-product-review`, `import-product-review`, `canonical-import`, and `validate-import` as commands that write files or persistent state. Before running them, show the exact command, input path, output directory, batch scope, schema, tenant, and file paths, then wait for explicit operator confirmation.
6. Prefer explicit scope arguments over hidden defaults. If the operator does not provide a schema, tenant id, source directory, review CSV path, or approval identity that matters for the requested phase, ask for it instead of guessing.
7. After every CLI run, report the exact subcommand, exit status, batch id (where applicable), schema, tenant id (where applicable), and any attempt number that was used or returned.
8. For `validate-import`, do not rely on terminal prose alone. Capture the `json=` artifact path from CLI output, open that file, and summarize the machine-readable fields described in [the safety and validation guide](./safety-and-validation.md). A blocked validation can legitimately exit with status `1`, so treat the artifact as authoritative when it is present.
9. If the operator wants this workflow moved under `erp-skills/`, explain that `erp-skills/` is not a default project-skill discovery path. The supported locations are `.github/skills/`, `.claude/skills/`, and `.agents/skills/` unless `chat.skillsLocations` is configured explicitly.
10. If `validate-import` reports that no canonical import run exists for the batch, stop and explain that validation only works after a completed `canonical-import` attempt for that same batch.
11. `extract` is the only phase that reads a raw SQL dump and writes files. It is idempotent — re-running overwrites the output directory. It is also the only phase that has no database dependency.
12. `live-stage` requires the `LEGACY_DB_HOST`, `LEGACY_DB_PORT`, `LEGACY_DB_USER`, `LEGACY_DB_PASSWORD`, `LEGACY_DB_NAME`, and `LEGACY_DB_CLIENT_ENCODING` environment variables to be configured without echoing secret values back into chat or logs.
13. The guarded live refresh connector permits superuser credentials only through the reviewed pipeline path: it forces read-only transaction defaults, rejects non-`SHOW`/`SELECT` SQL on the legacy connection, and refuses non-read-only transactions.

Suggested execution flow:

1. Read the requested phase in [the command map](./command-map.md). Prefer the live-source and reviewed refresh surfaces for routine work. Use `extract` (phase 0) only when starting from a raw SQL dump, `stage` (phase 1) only when archival CSV files already exist, and `live-stage` when the operator wants to stage directly from the live legacy DB.
2. If the operator needs syntax or available flags, run the corresponding `--help` command first.
3. If the phase writes data or files, apply the confirmation checklist from [the safety and validation guide](./safety-and-validation.md).
4. Run the reviewed CLI command.
5. If validation was requested, open the JSON artifact and summarize blockers, replay metadata, and stage discrepancies from the artifact itself.

Use this skill for legacy-import workflow guidance only. Do not use it for unrelated ERP tasks, generic data migration advice, or non-CLI import implementations.
