# UltrERP-ops Command Map

Run every backend command from the `backend/` directory so the repo's `uv` environment and import paths are correct.

## Stable Invocation Path

```bash
cd backend && uv run python -c "import common.config; print(common.config.settings.database_url)"
```

If the above prints a URL, the environment is configured. If it throws `ModuleNotFoundError`, run from the `backend/` directory.

## Database Connectivity Check (read-only)

```bash
cd backend && uv run python -c "
import asyncio
from common.database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as s:
        result = await s.execute(text('SELECT 1'))
        rows = result.fetchall()
        print('DB reachable, returned:', rows)

asyncio.run(check())
"
```

### List schemas (read-only)

```bash
cd backend && uv run python -c "
import asyncio
from common.database import AsyncSessionLocal
from sqlalchemy import text

async def list_schemas():
    async with AsyncSessionLocal() as s:
        result = await s.execute(text(\"SELECT schema_name FROM information_schema.schemata ORDER BY schema_name\"))
        rows = result.fetchall()
        for r in rows:
            print(r[0])

asyncio.run(list_schemas())
"
```

## Table Existence Check (read-only)

```bash
cd backend && uv run python -c "
import asyncio
from common.database import AsyncSessionLocal
from sqlalchemy import text

async def check_tables():
    async with AsyncSessionLocal() as s:
        result = await s.execute(text(\"\"\"
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name
        \"\"\"))
        rows = result.fetchall()
        by_schema = {}
        for r in rows:
            by_schema.setdefault(r[0], []).append(r[0])
        for schema, tables in by_schema.items():
            print(f'{schema}: {tables}')

asyncio.run(check_tables())
"
```

## Check if App Settings are Seeded (read-only)

```bash
cd backend && uv run python -c "
import asyncio
from common.database import AsyncSessionLocal
from sqlalchemy import select, func, text
from common.models.settings import AppSetting

async def check():
    async with AsyncSessionLocal() as s:
        result = await s.execute(select(func.count()).select_from(AppSetting))
        count = result.scalar()
        print(f'app_settings rows: {count}')
        if count == 0:
            print('NOT SEEDED — run seed-settings')
        else:
            print('SEEDED')

asyncio.run(check())
"
```

## Seed App Settings (WRITE — requires confirmation)

```bash
cd backend && uv run python -c "
import asyncio
from common.database import AsyncSessionLocal
from domains.settings.seed import seed_settings_if_empty

async def seed():
    async with AsyncSessionLocal() as s:
        await seed_settings_if_empty(s)
        print('Seeding complete')

asyncio.run(seed())
"
```

## Check User Count (read-only)

```bash
cd backend && uv run python -c "
import asyncio
from common.database import AsyncSessionLocal
from sqlalchemy import select, func
from common.models.users import User

async def check():
    async with AsyncSessionLocal() as s:
        result = await s.execute(select(func.count()).select_from(User))
        count = result.scalar()
        print(f'User count: {count}')
        if count == 0:
            print('NO USERS — run create-admin')
        else:
            result2 = await s.execute(select(User.email, User.role, User.status))
            users = result2.fetchall()
            for u in users:
                print(f'  {u[0]} | role={u[1]} | status={u[2]}')

asyncio.run(check())
"
```

## Create Admin User (WRITE — requires confirmation)

**First**, prompt the operator for: `email`, `display_name`, `password`.

```bash
cd backend && uv run python -c "
import asyncio
from common.database import AsyncSessionLocal
from domains.users.service import create_user
from common.auth import hash_password

async def create_admin(email: str, display_name: str, password: str):
    async with AsyncSessionLocal() as s:
        user = await create_user(
            s,
            email=email,
            password=password,
            display_name=display_name,
            role='admin',
        )
        await s.commit()
        print(f'Admin user created: {user.email} (id={user.id})')

# Replace with actual values from operator input
asyncio.run(create_admin('admin@example.com', 'System Admin', '...'))
"
```

## Check Legacy Import Batches (read-only)

```bash
cd backend && uv run python -c "
import asyncio
from common.database import AsyncSessionLocal
from sqlalchemy import select, func, text

async def check():
    async with AsyncSessionLocal() as s:
        # Try to query the legacy_import_control table if it exists
        try:
            result = await s.execute(text(\"\"\"
                SELECT COUNT(*) FROM legacy_import_control
            \"\"\"))
            count = result.scalar()
            print(f'Legacy import batches: {count}')
        except Exception as e:
            print(f'legacy_import_control table not found: {e}')

asyncio.run(check())
"
```

## Full Health Check Summary (read-only)

```bash
cd backend && uv run python -c "
import asyncio
from common.database import AsyncSessionLocal
from sqlalchemy import text, select, func

async def health():
    async with AsyncSessionLocal() as s:
        # DB connectivity
        try:
            await s.execute(text('SELECT 1'))
            print('DB: OK')
        except Exception as e:
            print(f'DB: FAILED — {e}')
            return

        # Tables
        try:
            result = await s.execute(text(\"\"\"
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            \"\"\"))
            table_count = result.scalar()
            print(f'Tables: {table_count}')
        except Exception as e:
            print(f'Tables: ERROR — {e}')

        # App settings
        try:
            result = await s.execute(text('SELECT COUNT(*) FROM app_settings'))
            settings_count = result.scalar()
            print(f'App settings rows: {settings_count}')
        except Exception as e:
            print(f'App settings: ERROR — {e}')

        # Users
        try:
            result = await s.execute(text('SELECT COUNT(*) FROM users'))
            user_count = result.scalar()
            print(f'Users: {user_count}')
        except Exception as e:
            print(f'Users: ERROR — {e}')

        # Legacy import batches
        try:
            result = await s.execute(text('SELECT COUNT(*) FROM legacy_import_control'))
            legacy_count = result.scalar()
            print(f'Legacy import batches: {legacy_count}')
        except Exception as e:
            print(f'Legacy import batches: not present ({e})')

asyncio.run(health())
"
```

## Required Run Report Back to the Operator

After any command finishes, report:
- exact command that was run
- exit code (0 = success, non-zero = failure)
- what was detected or changed
- what to do next
