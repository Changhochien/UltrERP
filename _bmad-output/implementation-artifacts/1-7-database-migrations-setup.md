# Story 1.7: Database Migrations Setup

Status: completed

## Story

As a developer,
I want Alembic configured for database migrations,
So that I can evolve the schema over time.

## Context

Based on architecture:
- **ORM:** SQLAlchemy 2.0+
- **Migrations:** Alembic 1.13+
- **Database:** PostgreSQL 17
- **Important:** asyncpg with `statement_cache_size=0` for PgBouncer compatibility

## Acceptance Criteria

**Given** migrations are configured
**When** I run `cd backend && uv run alembic -c ../migrations/alembic.ini upgrade head`
**Then** it connects to PostgreSQL and runs any pending migrations
**And** the database schema is created according to migration files

## Technical Requirements

### alembic.ini

```ini
[alembic]
script_location = ../migrations
prepend_sys_path = ../backend
version_path_separator = os

sqlalchemy.url = postgresql+asyncpg://ultr_erp@localhost:5432/ultr_erp

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### migrations/env.py

```python
from logging.config import fileConfig

import asyncio
from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from sqlalchemy import MetaData

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = MetaData()


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.AsyncAdaptedNullPool,
    )

    async with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### common/database.py (with asyncpg PgBouncer-safe config)

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from common.config import settings

# CRITICAL: statement_cache_size=0 for PgBouncer compatibility
engine = create_async_engine(
    settings.database_url,
    connect_args={"statement_cache_size": 0},
    pool_pre_ping=True,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent DetachedInstanceError after commit
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

### Alembic Commands

```bash
# Create a new migration
cd backend
uv run alembic -c ../migrations/alembic.ini revision --autogenerate -m "create customers table"

# Run migrations
uv run alembic -c ../migrations/alembic.ini upgrade head

# Rollback last migration
uv run alembic -c ../migrations/alembic.ini downgrade -1

# Show current revision
uv run alembic -c ../migrations/alembic.ini current

# Show migration history
uv run alembic -c ../migrations/alembic.ini history
```

### Initial Migration Template

First migration should be a version marker (empty) to establish baseline:

```bash
uv run alembic -c ../migrations/alembic.ini revision -m "initial"
```

Then manually create tables as needed in subsequent migrations.

## Tasks

- [x] Task 1: Create Alembic configuration
    - [x] Subtask: Create migrations/alembic.ini
    - [x] Subtask: Create migrations/env.py
    - [x] Subtask: Create migrations/script.py.mako (template)
- [x] Task 2: Create initial migration
        - [x] Subtask: Run `uv run alembic -c ../migrations/alembic.ini revision -m "initial"`
    - [x] Subtask: Verify migration runs
- [x] Task 3: Verify database connection
        - [x] Subtask: Test `uv run alembic -c ../migrations/alembic.ini upgrade head`
    - [x] Subtask: Verify tables created
- [x] Task 4: Document Alembic commands
    - [x] Subtask: Add commands to README

## Dev Notes

### Critical Implementation Details

1. **statement_cache_size=0** - Required for PgBouncer compatibility (per architecture)
2. **asyncpg** - Async PostgreSQL driver
3. **Alembic 1.13+** - Latest version with SQLAlchemy 2.0 support
4. **Explicit Alembic config path** - Backend commands must point to `../migrations/alembic.ini`

### Architecture References

- Section 3.1: asyncpg requirement
- Section 3.2: statement_cache_size=0 note
- Section 8.1: PostgreSQL 17 + pgvector

### Source References

- Architecture: Section 3.1 - Technology Stack Table
- PRD: Technical Constraints

## File List

- migrations/alembic.ini
- migrations/env.py
- migrations/script.py.mako
- migrations/versions/aa111dd11c43_initial.py

## Validation Evidence

- `cd backend && uv run alembic -c ../migrations/alembic.ini upgrade head` succeeds against the local PostgreSQL database.
- The Alembic version table was confirmed at revision `aa111dd11c43` after upgrade.

## Review Outcome

- The migration environment now uses the async transaction flow required by the validated SQLAlchemy/Alembic stack.
- README documents the explicit `../migrations/alembic.ini` command path used by the implementation.
