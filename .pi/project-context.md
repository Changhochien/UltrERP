# UltrERP - Project Context

## Overview
UltrERP is a full-stack ERP (Enterprise Resource Planning) system with:
- **Backend**: Python/FastAPI with SQLAlchemy ORM, Alembic migrations, PostgreSQL
- **Frontend**: React/TypeScript with Tailwind CSS (see `.agents/skills/design-taste-frontend/SKILL.md`)
- **Architecture**: Multi-tenant SaaS with domain-driven design

## Project Structure
```
backend/           # FastAPI application
  ├── domains/     # Domain modules (inventory, orders, CRM, etc.)
  ├── alembic/     # Database migrations
  └── pyproject.toml

frontend/          # React application
  ├── src/
  └── package.json

.agents/skills/    # BMAD project skills
.omc/              # OMC state and plans
```

## Key Conventions

### Backend
- Use `uv` for Python package management
- Run migrations with `uv run alembic upgrade head`
- Backend CLI: `uv run python -m domains.<module>.cli`

### Frontend
- Check `package.json` before importing dependencies
- Use `@phosphor-icons/react` for icons
- Use Tailwind CSS v3/v4 syntax appropriately
- Follow design rules in `.agents/skills/design-taste-frontend/SKILL.md`

### Skills Available
- `/bmad-dev-story` - Implement user stories
- `/bmad-create-prd` - Create product requirements
- `/ultr-erp-ops` - ERP operations (health checks, users)
- `/ultr-erp-migrate` - Migration management
- `/legacy-import` - Legacy data import workflow

### Model Selection
- Quick tasks: `haiku`
- Standard tasks: `sonnet`
- Complex/architecture: `opus`
