# Tech Viability Context

Source: /Volumes/2T_SSD_App/Projects/UltrERP/design-artifacts/A-Product-Brief/2026-03-30-erp-architecture-design.md

Architecture decisions to validate:
- Tauri 2.x desktop shell + Python FastAPI sidecar (localhost IPC)
- FastMCP 2.0 with stateless HTTP mode (stateless_http=True)
- FastAPI sub-apps (mounts) for modular monolith service isolation
- SQLAlchemy 2.0 async with PostgreSQL 17+ + pgvector
- Redis 7+ for sessions/cache, MinIO for S3-compatible storage

Reference repos to validate:
- github.com/dieharders/example-tauri-v2-python-server-sidecar — Tauri + Python sidecar pattern
- github.com/YoraiLevi/modular-monolith-fastapi — FastAPI sub-apps/mounts pattern
- github.com/prefecthq/fastmcp — FastMCP 2.0 official SDK

Key validation questions:
- Does Tauri 2.x still support external binary sidecar on macOS/Windows?
- Does FastMCP 2.0 stateless HTTP mode work as documented?
- Does FastAPI mount pattern still work in FastAPI 0.115+?
- Does SQLAlchemy 2.0 async work with PgBouncer transaction pooling mode?
