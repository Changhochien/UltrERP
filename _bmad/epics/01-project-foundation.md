# Epic: Project Foundation

**ID:** epic-01
**Status:** Draft

## Epic Overview

Establish a complete, production-ready project foundation that enables parallel frontend (React/Tauri) and backend (FastAPI) development with automated quality gates and cloud backup.

## Motivation

Without proper project structure, environment configuration, and CI/CD pipeline, no domain code can be reliably built, tested, or deployed. This is the prerequisite for all subsequent development work.

## Scope

- Project directory structure (src/, backend/, migrations/, scripts/)
- Development environment (pnpm, UV, PostgreSQL 17)
- CI/CD pipeline (GitHub Actions)
- Cloud backup strategy (pg_dump + rclone to R2)

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| Fresh clone → dev server | < 10 minutes |
| CI pipeline runtime | < 5 minutes |
| Test coverage on new code | > 80% |
| Frontend build | Zero errors |
| Backend import | No circular deps |
| PostgreSQL local | pg_isready confirms running |
| Backup configured | rclone remote set up |

## Out of Scope

- Actual domain code (Invoice, Inventory, etc.)
- Tauri desktop build configuration
- Production deployment infrastructure
- Legacy data migration

---

**Status: [DRAFT] — Awaiting approval to create user stories**
