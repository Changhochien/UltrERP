# Safety and Validation Guide

## Why This Skill Does Not Pre-Approve Shell

This skill intentionally omits `allowed-tools`.

The VS Code and Copilot CLI docs warn that pre-approving `shell` or `bash` removes the confirmation step for terminal commands. The legacy-import workflow can write staging data, mapping decisions, canonical records, and validation summaries, so broad shell pre-approval is unsafe.

## Confirmation Policy

Require explicit operator confirmation before running any command that writes data or files:

- `stage`
- `live-stage`
- `normalize`
- `map-products`
- `export-product-review`
- `import-product-review`
- `canonical-import`
- `validate-import`
- `currency-import`
- `ap-payment-import`

Before asking for confirmation, summarize:

- subcommand name
- batch id
- schema
- tenant id
- source directory, export path, or import path when applicable
- source schema when `live-stage` is used
- which `LEGACY_DB_*` variables must be configured, without echoing secret values
- approved-by identity for review imports
- why the command is being run now

If any of those inputs are missing, stop and ask rather than guessing.

## Machine-Readable Validation Rule

When the operator requests `validate-import`:

0. If the command fails because legacy-import control tables are missing, stop and
   ask the operator to run `cd backend && uv run alembic -c ../migrations/alembic.ini upgrade head`
   before retrying.
   If Alembic reports multiple heads on the active branch, ask for confirmation
   before falling back to:

```bash
cd backend && uv run alembic -c ../migrations/alembic.ini upgrade heads
```

0a. If `validate-import` reports that no canonical import run exists for the
    batch, stop and explain that the selected batch has not reached validation
    stage yet. Ask for a batch with a completed `canonical-import` attempt or
    ask for approval to run canonical import on a valid staged batch first.

1. Run the documented CLI command from [the command map](./command-map.md).
2. If the command exits with status `1` but still prints `json=` and `markdown=`, treat that as a blocked validation outcome, not a transport failure.
3. Capture the CLI summary line and extract the `json=` path.
4. Open the JSON artifact at that path.
5. Summarize the validation result from the JSON artifact itself, not from prose alone.

At minimum, report these JSON-backed fields:

- `status`
- `blocking_issue_count`
- `batch_id`
- `attempt_number`
- `schema_name`
- `tenant_id`
- `replay.scope_key`
- `issues`
- `stage_reconciliation`

## Manual Validation Checklist For This Skill

Use this checklist to prove the skill documentation matches the reviewed CLI surface:

1. Confirm discovery packaging:
   - Skill path is `.agents/skills/legacy-import/`
   - Directory name matches frontmatter `name: legacy-import`
2. Confirm CLI help path works:

```bash
cd backend && uv run python -m domains.legacy_import.cli --help
cd backend && uv run python -m domains.legacy_import.cli live-stage --help
cd backend && uv run python -m domains.legacy_import.cli validate-import --help
```

3. If the environment is fresh or legacy-import tables are missing, run:

```bash
cd backend && uv run alembic -c ../migrations/alembic.ini upgrade head
```

If the command reports multiple heads on the active branch, confirm and use:

```bash
cd backend && uv run alembic -c ../migrations/alembic.ini upgrade heads
```

4. If the operator provides a known imported batch, run:

```bash
cd backend && uv run python -m domains.legacy_import.cli validate-import \
  --batch-id <batch-id> \
  --schema raw_legacy \
  --tenant-id <tenant-uuid>
```

5. Confirm the result exposes `json=` and `markdown=` artifact paths.
6. Open the JSON artifact and confirm the reported status/blockers match the artifact contents.

## Discovery Caveat For `erp-skills/`

`erp-skills/` is useful as repository domain knowledge, but it is not a default project-skill discovery location for VS Code or Copilot CLI. If the team wants to host this skill there instead, they must configure `chat.skillsLocations` explicitly and keep the directory name aligned with the frontmatter `name`.