# Story 1.1: Developer Environment Setup

Status: completed

## Story

As a developer,
I want to set up my development environment in under 10 minutes,
So that I can start coding immediately without configuration headaches.

## Context

This story establishes the foundational tools needed for the entire project. Based on architecture decisions:
- **Frontend:** root Vite workspace managed with pnpm 10.5.2 via Corepack
- **Backend:** UV for Python dependencies under `backend/`
- **Database:** PostgreSQL 17 is the required local day-one dependency
- **Cache/Object Storage:** Redis 7 and MinIO are architecture components introduced in later integration stories; they are not blockers for Story 1.1
- **Storage/Backups:** Cloudflare R2 is the remote backup target

## Acceptance Criteria

**Given** a fresh clone of the repository
**When** I follow the README setup instructions
**Then** I have pnpm 10.5.2, UV, and PostgreSQL 17 installed locally
**And** `pnpm --version` reports 10.x
**And** `uv --version` returns success
**And** PostgreSQL 17 is running and accessible on port 5432
**And** `pg_isready -h localhost -p 5432` returns success

## Technical Requirements

### Prerequisites Installation

```bash
# Install pnpm (requires Node 20+)
corepack enable
corepack use pnpm@10.5.2

# Install UV for Python
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install PostgreSQL 17 (macOS)
brew install postgresql@17

# Start PostgreSQL
brew services start postgresql@17

# Create app role and database
createuser ultr_erp --pwprompt
createdb ultr_erp --owner ultr_erp
```

### Verification Commands

```bash
# Verify pnpm
pnpm --version  # should be 10.x

# Verify UV
uv --version

# Verify PostgreSQL
pg_isready -h localhost -p 5432

# Verify role and database
psql -d postgres -c "\du ultr_erp"
psql -d postgres -c "\l ultr_erp"
```

## Project Structure to Create

```
ultr-erp/
├── src/                          # Frontend source tree
├── backend/                      # Python/FastAPI workspace
├── migrations/                   # Alembic config and versions
├── scripts/
│   ├── backup/
│   └── restore/
├── .github/
│   └── workflows/
├── package.json                  # Root frontend package manifest
├── pnpm-workspace.yaml
├── tsconfig.json
├── vite.config.ts
├── backend/
│   ├── pyproject.toml
│   ├── .python-version
│   ├── app/
│   ├── common/
│   └── domains/
└── README.md
```

## Tasks

- [x] Task 1: Create README.md with setup instructions
  - [x] Subtask: Document all prerequisite installation commands
  - [x] Subtask: Document database setup commands
  - [x] Subtask: Document verification commands
- [x] Task 2: Document repository bootstrap order
  - [x] Subtask: Note that Story 1.2 creates the initial package manifests before dependency install validation
- [x] Task 3: Verify local prerequisites with test commands
  - [x] Subtask: Test pnpm binary availability
  - [x] Subtask: Test UV binary availability
  - [x] Subtask: Test PostgreSQL connection

## Dev Notes

### Critical Architecture Decisions

1. **pnpm workspaces** - This is the chosen package manager for frontend. Do NOT use npm or yarn.
2. **UV for Python** - Modern fast Python package manager. Do NOT use pip or Poetry.
3. **PostgreSQL 17** - Required locally from the first story.
4. **Redis/MinIO** - Architecture components, but not Story 1.1 prerequisites.
5. **Cloudflare R2** - Remote backup destination.

### Source References

- Architecture: Section 3 - Technology Stack
- PRD: Section on Technology decisions

## File List

- README.md
- .env.example

## Validation Evidence

- README bootstrap and verification commands were exercised during Epic 1 validation.
- Repository validation now passes `pnpm test`, `pnpm lint`, `pnpm build`, `cd backend && uv run pytest`, and `cd backend && uv run ruff check .`.

## Review Outcome

- pnpm was standardized to 10.5.2 across README, package metadata, and CI to match the validated local/Corepack toolchain.
- Setup commands were made idempotent for repeat local bootstrap runs.
