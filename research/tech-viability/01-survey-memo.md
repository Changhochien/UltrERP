# Technology Viability Survey

## Known Facts

### Tauri 2.x + Sidecar
- Current stable: **v2.10.1** (released 2026-03-04). The `externalBin` sidecar pattern is documented and supported on macOS and Windows.
- Cross-platform binaries require `-$TARGET_TRIPLE` suffixes (e.g., `my-sidecar-aarch64-apple-darwin`).
- The `example-tauri-v2-python-server-sidecar` repo (v0.1.3, Jan 2025, 114 stars) demonstrates the pattern with PyInstaller-compiled Python, Rust-side spawning via Tauri's API, localhost HTTP IPC, and graceful shutdown. It is functional and the most concrete reference available.
- **Open NSIS installer bug (issue #15134, 2026-03-20):** The NSIS installer does not replace the sidecar binary on reinstalls or upgrades. This is a production packaging risk for Windows auto-update flows.
- **Related open issues:** sidecar not stopped on NSIS upgrade (#9950); "Access is denied" binary patching errors on Windows (#14622).

### FastMCP 3.0 (formerly 2.x)
- **FastMCP 3.1.1** is current as of 2026-03-14. Version 2.x is in maintenance-only mode (last patch 2.14.6 on 2026-03-27). The architecture has been redesigned (provider/transform system, session state by default, component versioning, auth middleware, CLI tools).
- The `stateless_http` parameter **exists in v3** but its location moved from the `FastMCP()` constructor to the `run()` / `run_http_async()` / `http_app()` call site.
- **Known bug (issue #678, open):** `stateless_http=True` causes sampling calls to **hang indefinitely**. Elicitation and sampling (bidirectional context) are fundamentally incompatible with stateless HTTP in the current MCP spec. The MCP spec itself does not yet define stateless HTTP; the implementation is "a bit of a wild west." No fix is imminent pending spec changes (SEP-1442, SEP-1359).
- The `dieharders/example-tauri-v2-python-server-sidecar` repo predates FastMCP 3.0 and would need migration.

### FastAPI Sub-apps / Mounts
- Current stable: **FastAPI 0.135.x** (March 2026). Python 3.10+ required.
- The mount/sub-app pattern is **fully documented and unchanged** in 0.115+. The `app.mount()` API continues to work exactly as documented at `fastapi.tiangolo.com/advanced/sub-applications/`.
- The `YoraiLevi/modular-monolith-fastapi` repo demonstrates the pattern with isolated services at `/user` and `/pet`, independent SQLModel setups, and aggregated OpenAPI specs. This repo is a valid reference.

### SQLAlchemy 2.0 Async + PgBouncer
- SQLAlchemy 2.0.48 is current (2026-03-02). The asyncpg driver uses named prepared statements, which **PgBouncer in transaction mode does not support**.
- **The `statement_cache_size=0` workaround** (passed to `asyncpg.connect()` / `create_pool()`) disables prepared statements and resolves the conflict. This is the recommended production fix for transaction-mode PgBouncer.
- **Alternative:** Switch PgBouncer to `pool_mode = session` (eliminates the issue but sacrifices transaction-mode connection efficiency benefits).
- SQLAlchemy's own `dbapi_autocommit` is a supplemental mitigation but the primary fix is the asyncpg cache setting.
- **DbAPI compliance note:** SQLAlchemy 2.1 (upcoming) is tightening async session/connection lifecycle requirements that will catch improper connection management earlier.

### PostgreSQL 17 + pgvector; Redis 7+; MinIO
- PostgreSQL 17 is current. pgvector is maintained and works with PG 17. No known breaking changes.
- Redis 7+ sessions/cache: no issues. Straightforward.
- MinIO: SDK is stable; no known compatibility issues with the S3-compatible API.

---

## Unknowns / Open Questions

1. **Tauri sidecar NSIS bug (#15134):** Is there a confirmed workaround or patch in flight? The issue is 10 days old (as of 2026-03-30). Windows auto-update would be broken for sidecar users until fixed.
2. **FastMCP stateless HTTP elicitation/sampling:** The hang bug blocks any MCP tool that uses sampling or elicitation in stateless HTTP mode. For a desktop-first ERP, these features may not be near-term requirements, but they limit the AI agent interaction model. Is this an acceptable constraint for the PoC?
3. **FastMCP 3.0 migration effort:** The reference `example-tauri-v2-python-server-sidecar` predates FastMCP 3.0. Migration from FastMCP 2.x to 3.x has a published guide but introduces breaking changes to constructor patterns and state serialization (ctx.set_state values must now be JSON-serializable per issue #3156).
4. **SQLAlchemy 2.1 incoming:** A 2.1 release with stricter async session lifecycle requirements is approaching. This may require adjustment to connection management patterns in the PoC.
5. **PgBouncer deployment mode:** Not yet determined whether the team will run PgBouncer themselves or rely on a cloud provider's pooled endpoints (e.g., Supabase). The `statement_cache_size=0` workaround is required in both cases for transaction-mode pooling.

---

## Top 3 Risks

### 1. FastMCP Stateless HTTP Is Broken for Bidirectional AI Features (HIGH)
The `stateless_http=True` mode needed for multi-instance horizontal scaling **hangs on sampling calls**. This is a known unresolved bug in the MCP Python SDK. If the ERP AI agent needs sampling/elicitation (which is the primary value-add for AI-native ERP), stateless HTTP cannot be used as the scaling mechanism. This fundamentally conflicts with the stated architecture requirement of `stateless_http=True`.

### 2. Tauri 2.x NSIS Sidecar Binary Not Replaced on Upgrade (MEDIUM)
As of March 2026, open issue #15134 shows that the NSIS installer on Windows does not replace the sidecar binary during reinstalls or upgrades. Production Windows deployments using auto-update would ship an outdated Python sidecar after the first upgrade. This requires a confirmed fix or a packaging workaround before Windows production deployment.

### 3. SQLAlchemy 2.0 + PgBouncer Transaction Mode Requires asyncpg Cache Disable (MEDIUM)
Using SQLAlchemy 2.0 async with asyncpg behind PgBouncer in transaction mode will produce intermittent "prepared statement does not exist" errors unless `statement_cache_size=0` is passed to the asyncpg pool. This is a well-documented issue but must not be forgotten in the connection string configuration. The risk is silent failure until runtime under load.

---

## 3-Point Recommendation

### 1. PoC Scope: Use FastMCP 3.x with SSE/websocket (NOT stateless HTTP) for the AI Layer
For the PoC, do not use `stateless_http=True`. Instead, deploy FastMCP 3.x with its default session-mode HTTP transport (SSE or websockets). This avoids the sampling/elicitation hang bug entirely. The stateless HTTP question can be revisited only after (a) the MCP spec formally defines stateless HTTP and (b) the Python SDK fixes the hang bug. If horizontal scaling is needed before then, run multiple session-mode instances behind a load balancer with sticky sessions.

### 2. PoC Scope: Validate Tauri Sidecar on Windows NSIS Packaging Early
The NSIS sidecar binary replacement bug (#15134) should be tested in the PoC's first Windows build. If unresolved, use the WiX installer instead of NSIS, or implement a post-install script that explicitly replaces the sidecar binary. Do not assume NSIS auto-update works with sidecar.

### 3. PoC Scope: Configure asyncpg Pool with `statement_cache_size=0` from Day 1
Set `statement_cache_size=0` in the asyncpg connection pool configuration immediately in the PoC, before any database load testing. This eliminates the PgBouncer prepared-statement conflict proactively. Also verify the exact SQLAlchemy 2.0.48 + asyncpg version combination being used matches the PoC environment, and run a load test with PgBouncer in transaction mode to confirm no "idle in transaction" or connection-leak issues appear under concurrent requests.

---

## 3 Most Important Things Learned for PoC Phase

1. **FastMCP 3.0 is now the active release line; FastMCP 2.x is legacy.** The `stateless_http` parameter moved from the constructor to `run()`, and `ctx.set_state()` values must now be JSON-serializable. The sampling hang bug makes stateless HTTP currently unusable for any AI agent needing bidirectional context. Plan to use session-mode HTTP transport in PoC and treat stateless HTTP scaling as a post-PoC risk.

2. **The Tauri sidecar + NSIS Windows installer has a live bug (March 2026) where the sidecar binary is not replaced on upgrade.** This must be tested and worked around in the PoC's Windows packaging step — it will silently break auto-update for Windows desktop users if not caught.

3. **SQLAlchemy 2.0 async + asyncpg + PgBouncer transaction mode requires `statement_cache_size=0`** to avoid prepared-statement errors. This is a one-line fix but is easy to miss. The PoC should set this on day one and include a PgBouncer transaction-mode load test to confirm connection lifecycle hygiene under concurrency.
