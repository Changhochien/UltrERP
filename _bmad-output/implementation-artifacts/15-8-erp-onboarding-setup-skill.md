# Story 15.8: Interactive ERP Onboarding Setup Skill

Status: todo

## Story

As a new operator setting up UltrERP for the first time,
I want the AI agent to guide me through an interactive onboarding workflow that checks, sets up, and validates the environment,
So that I can get a working ERP system without knowing the internal setup steps in advance.

## Story Summary

UltrERP currently requires manual knowledge to set up: running Alembic migrations, seeding app settings, creating the first admin user, and optionally running the legacy import pipeline. This story adds an interactive `/setup` skill that detects the current state and walks the operator through each step with confirmation.

## Acceptance Criteria

**AC1:** Setup skill is discoverable via slash command
**Given** a new Claude Code session starts with no prior context
**When** the operator types `/setup`
**Then** the skill loads and offers to run the ERP onboarding workflow

**AC2:** Skill detects current environment state
**Given** the skill is loaded
**When** it runs its detection phase
**Then** it reports: database connectivity, current Alembic head, whether app tables exist, whether app settings are seeded, whether at least one user exists, and whether legacy staging data exists
**And** it presents a checklist of what is missing vs. present

**AC3:** Skill is interactive and confirmation-gated
**Given** the skill identifies missing setup steps
**When** it proposes to run a step (e.g., run migrations, create admin user)
**Then** it shows the exact command it will run and waits for explicit operator confirmation before proceeding
**And** it reports the result (success/failure) after each step

**AC4:** Skill covers the full first-time setup sequence
**Given** a completely empty database (no schemas, no users)
**When** the operator confirms all proposed steps
**Then** the skill runs: Alembic upgrade head → seed app settings → create default admin user → optionally stage legacy data
**And** at the end, reports a health summary of the running system

**AC5:** Skill handles partial state gracefully
**Given** the environment is partially set up (some migrations applied, no users)
**When** the skill runs detection
**Then** it skips already-completed steps and only proposes the missing ones
**And** it clearly labels each step as "already done" or "will run now"

**AC6:** Skill is reusable — not only for first-time setup
**Given** an existing environment
**When** the operator loads the skill
**Then** they can ask for a health check or specific sub-commands (e.g., "check if DB is connected", "verify alembic head", "show current user count")

## Tasks / Subtasks

- [ ] **Task 1: Design the interactive setup workflow**
  - [ ] Define the detection checks (DB connectivity, alembic head, table existence, user count)
  - [ ] Define the setup steps in order (migrate → seed → create admin → optionally import legacy)
  - [ ] Define what confirmation prompts look like
  - [ ] Decide how to handle failures mid-workflow

- [ ] **Task 2: Create the setup skill directory and SKILL.md**
  - [ ] Create `.claude/skills/setup/` with `SKILL.md`
  - [ ] Frontmatter `name: setup`, `description: "Use when setting up UltrERP for the first time, checking DB connectivity, running migrations, seeding initial data, or verifying the system is ready."`
  - [ ] Add `command-map.md` for individual sub-commands (check-db, check-alembic, run-migrations, seed-settings, create-admin, check-health)

- [ ] **Task 3: Implement detection logic**
  - [ ] `check-db` — test database connectivity and report schema list
  - [ ] `check-alembic` — report current Alembic revision
  - [ ] `check-tables` — report which app tables exist
  - [ ] `check-users` — report user count and roles
  - [ ] `check-legacy` — report whether staging data exists

- [ ] **Task 4: Implement setup actions**
  - [ ] `run-migrations` — run `alembic upgrade head` with confirmation
  - [ ] `seed-settings` — trigger app settings seed via `seed_settings_if_empty`
  - [ ] `create-admin` — prompt for admin email/password, hash password, insert user
  - [ ] `check-health` — run all detection checks and summarize

- [ ] **Task 5: Validate end-to-end**
  - [ ] Skill loads via `/setup` slash command
  - [ ] Detection runs and reports correct state on current DB
  - [ ] Each setup step can be confirmed and runs successfully
  - [ ] Health check correctly identifies missing vs. present components

## Dev Notes

### Prerequisites

- Alembic migration directory at `backend/migrations/` must exist (may be created in this story if absent)
- `domains/settings/seed.py` has `seed_settings_if_empty` function to call
- `domains/users/service.py` has user creation logic to call
- The backend `pyproject.toml` must have a working database URL

### Confirmation Policy

Each write action (migrations, seed, user creation) requires explicit operator confirmation showing:
- What will be done
- What the command is
- What the expected outcome is

### Error Handling

If a step fails (e.g., migration conflict, duplicate user), the skill should:
1. Report the error message
2. Suggest a remediation
3. Offer to retry or skip

### Relationship to Legacy Import

The setup skill should offer to run the legacy import pipeline as an optional final step after the ERP is bootstrapped. It should use the `/legacy-import` skill for that phase rather than reimplementing it.

## References

- `domains/settings/seed.py` — app settings seeder
- `domains/users/service.py` — user CRUD
- `backend/domains/legacy_import/cli.py` — legacy import CLI
- `.claude/skills/legacy-import/SKILL.md` — existing skill pattern to follow
- `backend/common/config.py` — database URL configuration
