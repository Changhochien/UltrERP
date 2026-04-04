# Story 1.5: FastAPI Backend Foundation

Status: completed

## Story

As a developer,
I want a working FastAPI backend with health check,
So that I can verify the API surface works before adding domain logic.

## Context

Based on architecture:
- **Framework:** FastAPI 0.115+
- **Server:** uvicorn with reload
- **Transport:** Session-mode HTTP for MCP (NOT stateless_http)
- **ORM:** SQLAlchemy 2.0+ with asyncpg
- **Config:** pydantic-settings (NOT dataclasses)

## Acceptance Criteria

**Given** the backend is set up
**When** I run `cd backend && uv run uvicorn app.main:app --reload`
**Then** the server starts on port 8000
**And** `curl localhost:8000/api/v1/health` returns `{"status": "ok"}`
**And** CORS is configured to allow localhost:5173

## Technical Requirements

### pyproject.toml

```toml
[project]
name = "ultr-erp-backend"
version = "0.1.0"
description = "UltrERP FastAPI backend"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.13.0",
    "asyncpg>=0.29.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "redis>=5.0.0",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
    "ruff>=0.8.0",
]

[tool.ruff]
target-version = "py312"
line-length = 100
```

### config.py (pydantic-settings)

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://ultr_erp@localhost:5432/ultr_erp"
    redis_url: str | None = None
    app_env: str = "development"
    log_level: str = "INFO"


settings = Settings()
```

### main.py (FastAPI app)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter

from domains.health.routes import router as health_router

app = FastAPI(title="UltrERP API", version="0.1.0")
api_v1 = APIRouter(prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_v1.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(api_v1)


@app.get("/")
def root():
    return {"message": "UltrERP API", "version": "0.1.0"}
```

### api/routes/health.py

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("")
def health_check():
    return {"status": "ok"}
```

### common/database.py (asyncpg with PgBouncer-safe config)

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

## Tasks

- [x] Task 1: Create backend core files
        - [x] Subtask: Create common/config.py with pydantic-settings
    - [x] Subtask: Create app/main.py with FastAPI setup
    - [x] Subtask: Configure CORS for localhost:5173
- [x] Task 2: Create health endpoint
        - [x] Subtask: Create domains/health/routes.py
        - [x] Subtask: Test /api/v1/health returns {"status": "ok"}
- [x] Task 3: Create database session module
        - [x] Subtask: Create common/database.py with asyncpg
    - [x] Subtask: Ensure statement_cache_size=0
        - [x] Subtask: Create shared metadata placeholder if needed by migrations
- [x] Task 4: Verify server starts
    - [x] Subtask: Run `uv run uvicorn app.main:app --reload`
    - [x] Subtask: Test health endpoint
    - [x] Subtask: Test CORS headers

## Dev Notes

### Critical Implementation Details

1. **pydantic-settings** - Use for configuration (not BaseModel)
2. **asyncpg + statement_cache_size=0** - Required for PgBouncer compatibility
3. **CORS origins** - Include "tauri://localhost" for desktop app
4. **FastAPI 0.115+** - Required for latest features
5. **uvicorn[standard]** - Includes reload functionality
6. **Versioned API root** - Health and domain routes must mount under `/api/v1`

### Architecture References

- Section 3.2: asyncpg with statement_cache_size=0
- Section 4.2: FastAPI Modular Monolith
- Section 7: Security - CORS configuration

### Source References

- Architecture: Section 3.1 - Technology Stack Table
- PRD: Technical Constraints
- Best practices: FastAPI + asyncpg + PgBouncer

## File List

- backend/common/config.py
- backend/app/main.py
- backend/domains/health/routes.py
- backend/common/database.py

## Validation Evidence

- Backend validation passes with `cd backend && uv run pytest` and `cd backend && uv run ruff check .`.
- Runtime validation confirmed `uv run uvicorn app.main:app --reload`, `curl localhost:8000/api/v1/health`, and the localhost CORS preflight flow.

## Review Outcome

- CORS origins are now configurable through settings while preserving the default browser and Tauri origins.
- Database connection configuration retains PgBouncer-safe `statement_cache_size=0` and adds explicit asyncpg timeouts.
- 2026-04-04 follow-up: `backend/common/config.py` now normalizes both JSON-array and bracketed comma-separated `CORS_ORIGINS` values so `Settings()` still loads when a shell-exported value overrides the repo `.env` entry.
