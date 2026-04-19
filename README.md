# UltrERP

AI-native ERP for Taiwan SMBs, delivered as a hybrid desktop and API platform.

## Story 1.1 Developer Setup

### Prerequisites

- Node.js 24+ (or use `.nvmrc`)
- pnpm 10.33.x
- Python 3.12+
- uv
- PostgreSQL 18+

### macOS Setup

```bash
brew install node
corepack enable
corepack use pnpm@10.33.0

curl -LsSf https://astral.sh/uv/install.sh | sh

brew install postgresql@18
brew services start postgresql@18

createuser ultr_erp --pwprompt 2>/dev/null || true
createdb ultr_erp --owner ultr_erp 2>/dev/null || true
```

### Verification

```bash
pnpm --version
uv --version
pg_isready -h localhost -p 5432
psql -d postgres -c "\\du ultr_erp"
psql -d postgres -c "\\l ultr_erp"
```

### Environment File

Create the local environment file before running backend commands:

```bash
cp .env.example .env
```

Replace `JWT_SECRET` in `.env` with a local-only value before using the app outside disposable development setups. One simple option is:

```bash
openssl rand -hex 32
```

## Bootstrap Order

1. Install the prerequisites above.
2. Confirm the repository structure exists.
3. Copy `.env.example` to `.env` and set `JWT_SECRET`.
4. Install frontend dependencies with `pnpm install`.
5. Install backend dependencies with `cd backend && uv sync`.
6. Run backend and frontend development servers.

Story 1.2 creates the initial scaffold. Story 1.6 and Story 1.7 add the executable toolchain and migration commands.

The original Epic 1 notes referenced pnpm 9, but current official pnpm action examples and the local developer environment both use pnpm 10. This repository standardizes on pnpm 10 to avoid version drift between local development and CI.

## Repository Layout

```text
.
├── src/
├── backend/
├── migrations/
├── scripts/
└── .github/workflows/
```

## Frontend Commands

```bash
pnpm install
pnpm dev
pnpm dev:proxy:8001
pnpm test
pnpm build
```

## Backend Commands

```bash
cd backend
uv sync
uv run pytest
uv run uvicorn app.main:app --reload
uv run alembic -c ../migrations/alembic.ini upgrade head
```

Fresh local validation helpers from the repository root:

```bash
pnpm dev:backend:8000
pnpm dev:backend:8001
pnpm dev:proxy:8001
```

- `pnpm dev:backend:8000` runs the current backend worktree on the default Vite proxy port. Re-running it replaces an older UltrERP backend already listening on `:8000`.
- `pnpm dev:backend:8001` runs a fresh backend on `127.0.0.1:8001`. Re-running it replaces an older UltrERP backend already listening on `:8001` so you do not have to hunt stale PIDs by hand.
- `pnpm dev:proxy:8001` keeps the frontend on `127.0.0.1:5173` but proxies `/api` to the fresh backend on `:8001`.
- If the port is owned by some other process, `scripts/dev-backend.sh` refuses to kill it and tells you to stop it manually first.
- If browser QA still shows `/api` 500s while in-repo backend checks pass, verify which process owns `:8000` with `lsof -nP -iTCP:8000 -sTCP:LISTEN` before assuming the workspace code is still broken.

Additional Alembic commands:

```bash
cd backend
uv run alembic -c ../migrations/alembic.ini revision -m "describe-change"
uv run alembic -c ../migrations/alembic.ini downgrade -1
uv run alembic -c ../migrations/alembic.ini current
uv run alembic -c ../migrations/alembic.ini history
```

The backend defaults to `postgresql+asyncpg://ultr_erp@localhost:5432/ultr_erp`, which matches the Story 1.1 local role/database bootstrap. Settings are loaded from either the repository-root `.env` or `backend/.env`, plus the current shell environment, so copying `.env.example` to the repository root is part of the required local bootstrap.
Set `VITE_API_PROXY_TARGET` if the frontend should proxy `/api` requests to a non-default backend address, and set `CORS_ORIGINS` as a JSON array when local origins differ from the default desktop/browser pair.

## Agent MCP Setup

UltrERP exposes MCP from the backend at `/mcp/`. To add project-scoped MCP config for both Codex and Claude Code in one step:

```bash
ULTRERP_MCP_API_KEY=dev-readonly-key ./scripts/setup-mcp-clients.sh
```

The script writes `.codex/config.toml` for Codex and `.mcp.json` for Claude Code, both pointing at the backend MCP endpoint and both reading the API key from `ULTRERP_MCP_API_KEY`.

See [docs/mcp-client-setup.md](docs/mcp-client-setup.md) for the backend `MCP_API_KEYS` example, custom URLs, and verification steps.

## CI Requirements

GitHub Actions runs two required checks:

- `frontend`: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm test`, `pnpm build`
- `backend`: `uv sync`, `uv run ruff check .`, `uv run alembic -c ../migrations/alembic.ini upgrade head`, `uv run pytest`

Recommended branch protection for `main`:

1. Require pull requests before merging.
2. Require status checks to pass before merging.
3. Select `frontend` and `backend` as required checks.
4. Require branches to be up to date before merging.

These rules are enforced in GitHub repository settings rather than the source tree, so repo administrators still need to apply them after cloning or mirroring the repository.

## Backup And Restore

### Environment

Use shell environment variables or secure CI/launchd secrets, not committed `.env` files, for backup credentials.

```bash
export BACKUP_GPG_RECIPIENT="backup@ultr-erp.local"
export RCLONE_REMOTE="ultr-erp-backups"
export R2_BUCKET="ultr-erp-backups"
```

Generate the local encryption key once:

```bash
gpg --quick-generate-key "backup@ultr-erp.local" default default never
```

Export and store the private key in an offline vault before relying on automated backups:

```bash
gpg --armor --export-secret-keys "backup@ultr-erp.local" > ultrerp-backup-private-key.asc
```

### rclone Configuration

Configure the Cloudflare R2 remote once:

```bash
rclone config
```

Use these values during setup:

- Storage: `s3`
- Provider: `Cloudflare`
- Remote name: `ultr-erp-backups`
- Endpoint: `https://<account-id>.r2.cloudflarestorage.com`
- Bucket: `ultr-erp-backups`

Keep the access key and secret outside the repository, preferably in the shell profile or launchd environment for the backup agent.

### Remote Retention

Configure the R2 bucket to preserve long-term archives independently of local cleanup:

1. Enable bucket versioning for `ultr-erp-backups`.
2. Add a lifecycle policy that retains `postgres/` backup objects for at least 10 years.
3. Do not mirror local deletions to the remote archive.

### Backup

```bash
scripts/backup/pg-dump.sh
scripts/backup/rclone-sync.sh
```

The local backup directory is `~/Library/Application Support/UltrERP/backups/`. Unencrypted `.dump` files and `.sha256` checksum files older than 7 days are pruned locally. Encrypted archives remain append-only in Cloudflare R2.

### Restore

```bash
scripts/restore/pg-restore.sh ultr_erp_YYYYMMDD_HHMMSS.dump.gpg
```

Restore uses the same target-selection semantics as backup: `DATABASE_URL` when set, otherwise `ULTR_ERP_DB_NAME`, with SQLAlchemy-style URLs normalized automatically for PostgreSQL CLI tools. Set `PG_MAINTENANCE_DB` if your admin database is not `postgres`.

### Development Reset

```bash
scripts/restore/reset-dev-db.sh --yes
```

This is the reviewed clean-rebuild path for local development and development
pipelines when you need an empty app DB with the latest schema. It drops and
recreates the configured target DB, runs `alembic upgrade head`, then seeds
non-sensitive app settings plus the default dev users. Use `--skip-bootstrap`
if the pipeline should stop after migrations. This command does not import live
legacy data; run the reviewed legacy refresh after the reset if you need a fresh
live-data load.

### launchd Example

Save this as `~/Library/LaunchAgents/com.ultrerp.backup.plist` and load it with `launchctl load ~/Library/LaunchAgents/com.ultrerp.backup.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
	<dict>
		<key>Label</key>
		<string>com.ultrerp.backup</string>
		<key>ProgramArguments</key>
		<array>
			<string>/bin/zsh</string>
			<string>-lc</string>
			<string>cd /Volumes/2T_SSD_App/Projects/UltrERP && scripts/backup/pg-dump.sh && scripts/backup/rclone-sync.sh</string>
		</array>
		<key>StartCalendarInterval</key>
		<dict>
			<key>Hour</key>
			<integer>2</integer>
			<key>Minute</key>
			<integer>0</integer>
		</dict>
		<key>RunAtLoad</key>
		<false/>
	</dict>
</plist>
```

### Verification

```bash
bash -n scripts/backup/pg-dump.sh
bash -n scripts/backup/rclone-sync.sh
bash -n scripts/restore/pg-restore.sh
```

For operational monitoring, make the launchd job write to explicit log files and alert on non-zero exits. A minimal pattern is to wrap the backup commands in a small shell script that appends to `~/Library/Logs/UltrERP/backup.log` and triggers your preferred notifier when a command fails.


## Planned Operations Docs

- Backup and restore procedures are documented as part of Story 1.4.
- Migration analysis consolidation is documented as part of Story 1.8.
