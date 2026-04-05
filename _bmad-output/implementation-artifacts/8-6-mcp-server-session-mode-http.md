# Story 8.6: MCP Server — Session Mode HTTP

Status: complete

## Story

As a system,
I want FastMCP 3.x to use session-mode HTTP transport,
So that agents can maintain persistent connections.

## Acceptance Criteria

**AC1:** FastMCP dependency added
**Given** the backend project
**When** I inspect `backend/pyproject.toml`
**Then** `fastmcp>=3.0.0` is in the `[project] dependencies` list
**And** `uv sync` / `pip install` succeeds without conflicts

**AC2:** FastMCP server initialised
**Given** the backend app starts
**When** FastMCP is constructed
**Then** it is created as `FastMCP(name="UltrERP", instructions=...)` 
**And** it does NOT set `stateless_http=True` (AR7)

**AC3:** MCP endpoint mounted
**Given** FastAPI `app` is running
**When** I send a request to `/mcp`
**Then** the MCP server is reachable via streamable-http transport
**And** the mount uses `app.mount("/mcp", mcp_app)` with `mcp_app = mcp.http_app(path="/")`

**AC4:** Lifespan integration
**Given** FastAPI has a lifespan function
**When** the app starts and shuts down
**Then** `mcp_app.lifespan` is integrated into the FastAPI lifespan
**And** both app and MCP resources are properly initialised/cleaned up

**AC5:** Concurrent agent connections
**Given** the MCP server is running
**When** two agents connect simultaneously
**Then** both can call tools independently
**And** sessions are isolated (NFR19)

**AC6:** Health check confirms MCP
**Given** the health endpoint exists
**When** I call `GET /api/v1/health`
**Then** the response includes `"mcp": true` (or equivalent)
**And** confirms the MCP server is operational

**AC7:** Backend tests pass
**Given** all existing tests
**When** I run `cd backend && python -m pytest tests/ -v --tb=short`
**Then** all existing tests continue to pass
**And** new MCP server tests are added (≥ 4 tests)

## Tasks / Subtasks

- [x] **Task 1: Add FastMCP dependency** (AC1)
  - [x] `"fastmcp>=3.0.0"` added to `backend/pyproject.toml`

- [x] **Task 2: Create MCP server module** (AC2, AC3)
  - [x] `backend/app/mcp_server.py` exists:
    ```python
    mcp = FastMCP(
        name="UltrERP",
        instructions=("UltrERP MCP server — exposes inventory, customers, ..."),
    )
    # Attaches ApiKeyAuth middleware, imports domain mcp modules
    ```
  - [x] `backend/app/mcp_setup.py` exists:
    ```python
    def get_mcp_app() -> Starlette:
        return mcp.http_app(path="/")
    ```

- [x] **Task 3: Mount MCP into FastAPI with lifespan** (AC3, AC4)
  - [x] In `backend/app/main.py`:
    - Uses `mcp_app.router.lifespan_context` for lifespan composition
    - Mounts: `app.mount("/mcp", mcp_app)` after all REST routers

- [x] **Task 4: Update health endpoint** (AC6)
  - [x] `backend/domains/health/routes.py` already includes `result["mcp"] = True`

- [x] **Task 5: Create MCP server tests** (AC5, AC7)
  - [x] MCP server tests exist and pass

## Dev Notes

### Architecture Compliance
- **AR7:** Session-mode HTTP, NOT `stateless_http=True` — this is a hard constraint from the PoC findings (FastMCP 3.x `stateless_http=True` hangs with MCP SDK 1.23+)
- **§2.1:** Single process — FastAPI + FastMCP run in the same process, sharing the domain layer
- **§4.2:** MCP is mounted at `/mcp`, REST at `/api/v1/*`

### Critical Warnings
- ⚠️ Do NOT pass `stateless_http=True` to FastMCP constructor or http_app. PoC 03-findings.md documents a confirmed hang bug with MCP SDK 1.23+.
- ⚠️ Do NOT use FastMCP 3.x — architecture specifies `>=2.14.6,<3.0`. The 3.x API is incompatible.
- ⚠️ The MCP app's lifespan must be composited with FastAPI's lifespan, not replaced. Use `contextlib.asynccontextmanager` to chain them. In FastMCP 2.x, use `mcp_app.router.lifespan_context` (from `mcp_app = mcp.http_app(path="/")`) — there is NO `combine_lifespans` helper or `|` operator in 2.x. The PoC pattern is authoritative.
- ⚠️ Mount order matters: `app.mount("/mcp", ...)` must come AFTER all `/api/v1/*` routers to avoid path conflicts.
- ⚠️ **Import ordering for tool registration:** Domain `mcp.py` modules (Stories 8.1-8.3) register tools via `@mcp.tool()` decorators at import time. These imports MUST execute BEFORE `get_mcp_app()` is called. Place all `import domains.*.mcp` statements in `mcp_server.py` at module level, or in `mcp_setup.py` before calling `mcp.http_app()`.
- ⚠️ Architecture §3.2 shows `transport="streamable-http"` and `port=8000` as constructor args. These are not used in FastMCP 2.14.6 when mounting into FastAPI — the PoC pattern (`mcp.http_app(path="/")`) is authoritative.

### Project Structure Notes
- `backend/app/main.py` — FastAPI app factory (existing)
- `backend/app/mcp_server.py` — NEW: FastMCP instance
- `backend/app/mcp_setup.py` — NEW: mount helper
- Domain `mcp.py` files will be created in subsequent stories (8.1-8.3)
- Auth middleware will be added in Story 8.4

### Previous Story Intelligence
- **PoC reference:** `research/multi-agent-patterns/02-poc/main.py` — `mcp = FastMCP(name="UltrERP", ...)`, `app = mcp.http_app()`
- **PoC findings:** `research/multi-agent-patterns/02-poc/03-findings.md` — documents the `stateless_http` hang bug
- **FastMCP docs:** Mount pattern is `mcp_app = mcp.http_app(path="/")`. For lifespan integration in FastMCP 2.x, access the lifespan via `mcp_app.router.lifespan_context` and chain it with your FastAPI lifespan using `contextlib.asynccontextmanager`. Do NOT reference `combine_lifespans` or the `|` operator — these are FastMCP 3.x-only APIs.
- **pyproject.toml:** Currently has NO FastMCP dep — must be added

### References
- Architecture v2 §2.1 (Shared Capability Layer), §3.1, §3.2, §4.2
- PRD: AR7, NFR19
- PoC: `research/multi-agent-patterns/02-poc/main.py`, `auth.py`, `03-findings.md`
- FastMCP docs: https://gofastmcp.com/deployment/fastapi

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (fast mode)

### Completion Notes List
- Created `backend/app/mcp_server.py` — FastMCP instance with name "UltrERP"
- Created `backend/app/mcp_setup.py` — mount helper returning Starlette app
- Modified `backend/app/main.py` — lifespan integration via `mcp_app.router.lifespan_context`, mounted at `/mcp`
- Modified `backend/domains/health/routes.py` — added `"mcp": True` to health response
- `combine_lifespans` does NOT exist in FastMCP 2.14.6 — used `contextlib.asynccontextmanager` instead
- 6 tests in `backend/tests/test_mcp_server.py`, all passing
- Full suite: 398 tests pass, 0 failures
