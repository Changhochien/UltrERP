# Story 11.6: Audit Log Service & Query API

Status: completed

## Story

As a system,
I want to record all invoice state changes, inventory adjustments, and user actions in a queryable audit trail,
so that we have a complete, immutable record of everything that happened in the system.

## Context

UltrERP already has an `AuditLog` model (`common/models/audit_log.py`) and **inline audit logging** scattered across domains: `orders/services.py` (4 callsites), `payments/services.py` (3 callsites), `inventory/services.py` (5 callsites). The pattern is repeated code — each service creates `AuditLog(...)` directly, duplicating tenant_id resolution and field population.

This story centralizes that pattern into a reusable service, adds a query API for admins, and ensures immutability at the database level. It does NOT add new audit points yet — that happens in subsequent stories as new write operations are created.

### Existing AuditLog Model (common/models/audit_log.py)

```python
class AuditLog(Base):
    __tablename__ = "audit_log"
    id: UUID PK
    tenant_id: UUID (indexed)
    actor_id: String(100) — who did it
    actor_type: String(20) — "user", "system", "agent", "line_bot"
    action: String(100) — "order.create", "payment.record", etc.
    entity_type: String(100) — "order", "payment", "invoice"
    entity_id: String(100) — the affected entity's ID
    before_state: JSON | None
    after_state: JSON | None
    correlation_id: String(100) | None
    notes: Text | None
    created_at: DateTime (server_default=func.now())
```

No `updated_at` column — audit entries are append-only by design (NFR13, AR10).

### Coverage Gaps

Current audit logging covers: order creation, order status changes, order→invoice generation, payment recording, payment reconciliation, stock adjustments, stock transfers, reorder alert acknowledgement. **NOT covered yet:** invoice void, customer create/update, user CRUD (future stories), RBAC changes (future stories).

### Architecture Decision

- New `backend/domains/audit/` domain module with service and routes
- `write_audit()` helper: centralizes AuditLog creation with tenant_id
- Query endpoint: `GET /api/v1/admin/audit-logs` with pagination and filtering
- Alembic migration: add PostgreSQL rule to prevent UPDATE/DELETE on audit_log
- **Do NOT refactor existing inline AuditLog usage** — that would touch too many files and risk regressions. New code uses the centralized service; old code stays until those stories are revisited.

## Acceptance Criteria

**AC1:** Centralized audit write helper
**Given** a domain service needs to record an audit entry
**When** it calls `write_audit(session, actor_id, actor_type, action, entity_type, entity_id, before_state, after_state, correlation_id, notes)`
**Then** an AuditLog row is created with `tenant_id=DEFAULT_TENANT_ID`
**And** `created_at` is set by the database

**AC2:** Query audit logs with pagination
**Given** audit log entries exist
**When** I request `GET /api/v1/admin/audit-logs?page=1&page_size=50`
**Then** the response includes `items` (list of audit entries), `total`, `page`, `page_size`
**And** entries are ordered by `created_at DESC` (newest first)
**And** each entry includes all fields (id, tenant_id, actor_id, actor_type, action, entity_type, entity_id, before_state, after_state, correlation_id, notes, created_at)

**AC3:** Filter audit logs
**Given** audit log entries exist for multiple entity types
**When** I request `GET /api/v1/admin/audit-logs?entity_type=order`
**Then** only entries with entity_type="order" are returned
**And** filtering also works for: `action`, `actor_id`, `actor_type`, `entity_id`
**And** date range filtering: `created_after` and `created_before` (ISO 8601)

**AC4:** Immutability enforcement
**Given** audit_log rows exist
**When** an UPDATE or DELETE is attempted on the audit_log table
**Then** the database rejects the operation with a rule/trigger error
**And** this is enforced at the PostgreSQL level, not just application code

**AC5:** All existing tests pass
**Given** all 482 existing tests
**When** I run `cd backend && python -m pytest tests/ -v --tb=short`
**Then** all 482 tests continue to pass
**And** new audit service tests are added (≥ 10 tests)

## Tasks / Subtasks

- [x] **Task 1: Create audit domain module** (AC1)
  - [x] Create `backend/domains/audit/__init__.py`
  - [x] Create `backend/domains/audit/service.py`:
    ```python
    """Centralized audit log service."""
    from __future__ import annotations
    from typing import Any
    from sqlalchemy.ext.asyncio import AsyncSession
    from common.models.audit_log import AuditLog
    from common.tenant import DEFAULT_TENANT_ID

    async def write_audit(
        session: AsyncSession,
        *,
        actor_id: str,
        actor_type: str = "user",
        action: str,
        entity_type: str,
        entity_id: str,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        notes: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            tenant_id=DEFAULT_TENANT_ID,
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
            correlation_id=correlation_id,
            notes=notes,
        )
        session.add(entry)
        return entry
    ```

- [x] **Task 2: Create audit query service** (AC2, AC3)
  - [x] Create `backend/domains/audit/queries.py`:
    - `list_audit_logs(session, *, page, page_size, entity_type, action, actor_id, actor_type, entity_id, created_after, created_before)` → `{items, total, page, page_size}`
    - Uses SQLAlchemy `select(AuditLog)` with dynamic `where()` clauses
    - Order by `created_at DESC`
    - Offset-based pagination: `offset = (page - 1) * page_size`
    - Always filters by `tenant_id = DEFAULT_TENANT_ID`

- [x] **Task 3: Create audit routes** (AC2, AC3)
  - [x] Create `backend/domains/audit/routes.py`:
    - Router with `GET /` endpoint (mounted at `/api/v1/admin/audit-logs`)
    - Query params: `page` (default 1), `page_size` (default 50, max 200), `entity_type`, `action`, `actor_id`, `actor_type`, `entity_id`, `created_after` (datetime), `created_before` (datetime)
    - Response schema: `AuditLogListResponse` with items list and pagination metadata
  - [x] Create `backend/domains/audit/schemas.py`:
    - `AuditLogResponse` — Pydantic model matching AuditLog fields, with `model_config = ConfigDict(from_attributes=True)`
    - `AuditLogListResponse` — `items: list[AuditLogResponse]`, `total: int`, `page: int`, `page_size: int`

- [x] **Task 4: Mount audit router** (AC2)
  - [x] In `backend/app/main.py`, import and mount:
    ```python
    from domains.audit.routes import router as audit_router
    # ...
    api_v1.include_router(audit_router, prefix="/admin/audit-logs", tags=["audit"])
    ```

- [x] **Task 5: Alembic migration for immutability** (AC4)
  - [x] Initial migration: `nn444pp44q76_audit_log_immutability.py`
  - [x] Follow-up correction: `qq777ss77t09_fix_audit_log_immutability.py`
  - [x] Upgrade path now drops the silent rules and installs a PostgreSQL trigger via `audit_log_reject_mutation()` so UPDATE/DELETE attempts fail explicitly.
  - [x] Downgrade drops the trigger/function and restores the legacy rules only for rollback compatibility.

- [x] **Task 6: Tests** (AC5)
  - [x] Create `backend/tests/test_audit_service.py`:
    - `test_write_audit_creates_entry` — verify all fields are set correctly ✅
    - `test_write_audit_defaults` — verify actor_type defaults to "user" ✅
    - `test_write_audit_optional_fields_none` — before_state, after_state, correlation_id, notes can all be None ✅
    - `test_list_audit_logs_pagination` — verify page/page_size/total ✅
    - `test_list_audit_logs_filter_entity_type` — filter by entity_type ✅
    - `test_list_audit_logs_filter_action` — filter by action ✅
    - `test_list_audit_logs_filter_actor_id` — filter by actor_id ✅
    - `test_list_audit_logs_filter_date_range` — created_after/before ✅
    - `test_list_audit_logs_ordered_newest_first` — verify DESC ordering ✅
    - `test_audit_api_returns_paginated_list` — API endpoint integration test ✅
    - `test_audit_api_filters` — API endpoint with query params ✅
    - `test_audit_api_empty_result` — no matching entries ✅
    - `test_audit_api_page_size_max` — page_size > 200 rejected ✅ (bonus)

## File Changes

### New Files
| File | Purpose |
|------|---------|
| `backend/domains/audit/__init__.py` | Module init |
| `backend/domains/audit/service.py` | `write_audit()` centralized helper |
| `backend/domains/audit/queries.py` | `list_audit_logs()` query with filtering |
| `backend/domains/audit/routes.py` | `GET /` endpoint |
| `backend/domains/audit/schemas.py` | Response models |
| `backend/tests/test_audit_service.py` | Tests |
| `migrations/versions/nn444pp44q76_audit_log_immutability.py` | Immutability rules |
| `migrations/versions/qq777ss77t09_fix_audit_log_immutability.py` | Replace silent rules with trigger-based rejection |

### Modified Files
| File | Change |
|------|--------|
| `backend/app/main.py` | Mount audit router at `/api/v1/admin/audit-logs` |

## Dev Notes

- **DO NOT refactor existing inline AuditLog usage.** Those services work fine. The centralized helper is for NEW code going forward.
- The AuditLog table was created in migration `aa111dd11c43_initial.py`. The immutability rules are added in a separate migration.
- `page_size` max 200 prevents full-table dumps. Default 50 is reasonable for UI pagination.
- All queries MUST filter by `tenant_id = DEFAULT_TENANT_ID` for data isolation.
- Test with `FakeAsyncSession` pattern (queue_scalar/queue_rows) for service-level tests and httpx AsyncClient for API tests.
- TAB indentation throughout. Ruff py312 rules E/F/I.

## Dev Agent Record

- **Implemented by:** Copilot Agent
- **Date:** 2025-07-08
- **All tasks completed:** Yes (6/6)
- **Tests:** 14 tests (12 planned + 1 bonus `test_audit_api_page_size_max` + 1 `test_list_audit_logs_empty_result`)
- **All 496 tests pass** (14 new + 482 existing, 0 regressions)
- **Implementation notes:**
  - Used `FakeAuditLog` plain class instead of `AuditLog.__new__()` because SQLAlchemy 2.0 ORM models require `_sa_instance_state`
  - Shared test helpers imported from `tests/domains/orders/_helpers.py` (`FakeAsyncSession`, `setup_session`, `teardown_session`, `http_get`)
  - Query service uses dual queries (COUNT + SELECT) for accurate pagination totals
  - Route mounted at `/api/v1/admin/audit-logs` with alphabetical ordering in main.py
  - 2026-04-03 follow-up review replaced the original `DO INSTEAD NOTHING` rules with trigger-based rejection so immutability violations now fail loudly instead of being silently discarded
  - Focused migration validation added in `backend/tests/test_audit_log_migration.py` (2 tests passing)
  - 2026-04-04 follow-up review keeps the audit query route explicitly owner-only and adds focused regression coverage for non-owner rejection
