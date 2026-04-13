## Epic 1: Project Foundation

### Epic Goal

Establish a production-ready project foundation aligned to the approved hybrid architecture: root Vite/React frontend, modular FastAPI backend under `backend/`, versioned APIs, CI/CD, migrations, and durable backups.

### Stories

### Story 1.1: Developer Environment Setup

As a developer,
I want to set up my development environment in under 10 minutes,
So that I can start coding immediately without configuration headaches.

**Acceptance Criteria:**

**Given** a fresh clone of the repository
**When** I follow the README setup instructions
**Then** I have pnpm 9, UV, and PostgreSQL 17 installed locally
**And** `pnpm --version` reports 9.x
**And** `uv --version` returns success
**And** PostgreSQL 17 is running and accessible on port 5432
**And** `pg_isready -h localhost -p 5432` returns success

### Story 1.2: Project Structure

As a developer,
I want a clear, consistent project structure,
So that I know where to put code and can navigate easily.

**Acceptance Criteria:**

**Given** the project structure is established
**When** I look at the codebase
**Then** frontend code is in `src/` with components/, pages/, domain/, hooks/, lib/ subdirectories
**And** backend code is in `backend/` with `app/`, `common/`, and `domains/` subdirectories
**And** migrations are in `migrations/`
**And** scripts are in `scripts/backup/` and `scripts/restore/`
**And** GitHub Actions workflows are in `.github/workflows/`
**And** empty directories have placeholder files where needed

### Story 1.3: CI/CD Pipeline

As a developer,
I want automated quality gates on every PR,
So that no broken code gets merged.

**Acceptance Criteria:**

**Given** a PR is opened
**When** CI pipeline runs
**Then** frontend job runs: lint → test → build
**And** backend job runs: ruff check → pytest
**And** both jobs must pass for merge
**And** failing checks block merge

### Story 1.4: Cloud Backup Strategy

As a developer/owner,
I want automated daily backups to cloud storage,
So that data is safe and recoverable for 10+ years.

**Acceptance Criteria:**

**Given** the backup scripts are in place
**When** `scripts/backup/pg-dump.sh` runs
**Then** it creates a compressed pg_dump file in `~/Library/Application Support/UltrERP/backups/`
**And** local temporary unencrypted backup artifacts older than 7 days are automatically removed
**And** encrypted archives are copied to Cloudflare R2 without deleting prior remote backups
**And** `scripts/restore/pg-restore.sh` can recover from a local or downloaded backup archive

### Story 1.5: FastAPI Backend Foundation

As a developer,
I want a working FastAPI backend with health check,
So that I can verify the API surface works before adding domain logic.

**Acceptance Criteria:**

**Given** the backend is set up
**When** I run `cd backend && uv run uvicorn app.main:app --reload`
**Then** the server starts on port 8000
**And** `curl localhost:8000/api/v1/health` returns `{"status": "ok"}`
**And** CORS is configured to allow localhost:5173

### Story 1.6: React Frontend Foundation

As a developer,
I want a working React frontend with Vite dev server,
So that I can see the UI and verify the frontend infrastructure.

**Acceptance Criteria:**

**Given** the frontend is set up
**When** I run `pnpm install` and then `pnpm dev`
**Then** Vite starts on port 5173
**And** loading localhost:5173 shows the app
**And** the app can make API calls to localhost:8000 through the proxy

### Story 1.7: Database Migrations Setup

As a developer,
I want Alembic configured for database migrations,
So that I can evolve the schema over time.

**Acceptance Criteria:**

**Given** migrations are configured
**When** I run `cd backend && uv run alembic -c ../migrations/alembic.ini upgrade head`
**Then** it connects to PostgreSQL and runs any pending migrations
**And** the database schema is created according to migration files

### Story 1.8: Legacy Data Analysis

As a developer,
I want to understand the legacy database structure,
So that I can plan the migration strategy.

**Acceptance Criteria:**

**Given** the legacy analysis artifacts are consolidated and reviewed
**When** I review the findings
**Then** I know the 94 tables and 1.1M rows structure
**And** I know the corrected orphan profile: 190 orphan codes affecting 523 rows (0.09%)
**And** I have a documented migration plan for shadow-mode validation

---

