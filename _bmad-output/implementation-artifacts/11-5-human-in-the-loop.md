# Story 11.5: Human-in-the-Loop for Sensitive Writes

Status: completed

## Story

As a system,
I want to require explicit human confirmation for sensitive write actions via AI or automation,
so that we prevent unauthorized or accidental changes to critical data.

## Context

UltrERP has AI agents accessing the system via MCP (Epic 8) and LINE BOT order submission (Epic 9). FR54 and NFR12 require that sensitive write actions triggered through AI or automation must get explicit human confirmation before execution. This story creates an approval workflow with a pending state, human review, and execution upon approval.

### Sensitive Actions Requiring Approval (FR54)

Per PRD: `invoices.void`, `invoices.submit`, and `inventory.adjust` above a configurable threshold.

Currently in the codebase:
- **Invoice void**: Not yet implemented (Epic 2 Story 2.3 is ready-for-dev, not built)
- **Invoice submit**: Not yet implemented
- **Inventory adjust**: Implemented in `domains/inventory/services.py` — `adjust_stock()`

Since most write MCP tools don't exist yet, this story focuses on the **approval framework** and wires it to the one existing sensitive action (inventory adjustments above threshold when triggered by non-human actors).

### Architecture Decision

- New `approval_requests` table
- New `backend/domains/approval/` domain module
- Approval workflow: `create_approval() → pending → approve/reject → execute`
- Threshold configuration in Settings: `approval_threshold_inventory_adjust` (default 100 units)
- Actor type check: only `agent`, `line_bot`, or `automation` actor types trigger approval; `user` actors bypass (they are the human)
- Approval endpoint: `POST /api/v1/admin/approvals/{id}/resolve` with `{action: "approve"|"reject"}`
- Query endpoint: `GET /api/v1/admin/approvals` (list pending approvals)
- Expiry: approvals expire after 24 hours (configurable)
- Only owner/finance roles can resolve approvals

### Approval Request Model

```python
class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: UUID PK
    tenant_id: UUID (indexed)
    action: String(100)  # e.g. "inventory.adjust", "invoices.void"
    entity_type: String(100)  # e.g. "stock_adjustment"
    entity_id: String(100) | None  # entity affected, if known
    requested_by: String(100)  # actor_id who triggered
    requested_by_type: String(20)  # "agent", "line_bot", "automation"
    context: JSON  # full context for the action (params, etc.)
    status: String(20)  # "pending", "approved", "rejected", "expired"
    resolved_by: String(100) | None  # user_id who approved/rejected
    resolved_at: DateTime | None
    expires_at: DateTime
    created_at: DateTime (server_default=func.now())
```

## Acceptance Criteria

**AC1:** Approval request creation
**Given** an AI agent or automation triggers a sensitive write action
**When** the action matches a configured approval rule (e.g., inventory.adjust > threshold)
**Then** an approval request is created with status="pending"
**And** the original action is NOT executed
**And** the response indicates "approval required" with the approval request ID

**AC2:** List pending approvals
**Given** pending approval requests exist
**When** an admin requests `GET /api/v1/admin/approvals?status=pending`
**Then** the response includes all pending approvals with context details
**And** expired approvals are automatically marked as "expired"

**AC3:** Approve an action
**Given** a pending approval request exists
**When** an admin/finance user requests `POST /api/v1/admin/approvals/{id}/resolve` with `{"action": "approve"}`
**Then** the approval status changes to "approved"
**And** the original action is executed (e.g., stock adjustment is performed)
**And** an audit log entry is created with action="approval.approve"

**AC4:** Reject an action
**Given** a pending approval request exists
**When** an admin requests `POST /api/v1/admin/approvals/{id}/resolve` with `{"action": "reject"}`
**Then** the approval status changes to "rejected"
**And** the original action is NOT executed
**And** an audit log entry is created with action="approval.reject"

**AC5:** Expiry enforcement
**Given** a pending approval request older than 24 hours
**When** the approval is queried or resolved
**Then** it is automatically marked as "expired"
**And** the original action is NOT executed

**AC6:** User-initiated actions bypass approval
**Given** a human user (actor_type="user") triggers a sensitive write
**When** the action is performed
**Then** it executes immediately without an approval request
**And** only AI/automation actor types trigger the approval workflow

**AC7:** Threshold-based rules
**Given** `approval_threshold_inventory_adjust` is set to 100
**When** an agent requests a stock adjustment of 50 units
**Then** the action executes immediately (below threshold)
**When** an agent requests a stock adjustment of 150 units
**Then** an approval request is created (above threshold)

**AC8:** All existing tests pass
**Given** all existing tests
**When** I run `cd backend && python -m pytest tests/ -v --tb=short`
**Then** all existing tests continue to pass
**And** new approval workflow tests are added (≥ 12 tests)

## Tasks / Subtasks

- [x] **Task 1: Config + model foundation**
  - [x] Added approval threshold and expiry settings plus the `ApprovalRequest` ORM model and registration.

- [x] **Task 2: Persistence + routing**
  - [x] Added the approval migration, domain package, schemas, service, routes, and executor.

- [x] **Task 3: Sensitive write gating**
  - [x] Wired `inventory.adjust` so non-human actors above the configured threshold return an approval-required response instead of executing immediately.

- [x] **Task 4: Approval lifecycle**
  - [x] Pending approvals can be listed, auto-expired, approved, rejected, and replayed through the executor on approval.

- [x] **Task 5: Focused validation**
  - [x] Approval tests pass and the existing stock-adjustment regression slice continues to pass.

## File Changes

### New Files
| File | Purpose |
|------|---------|
| `backend/common/models/approval_request.py` | ApprovalRequest ORM model |
| `backend/domains/approval/__init__.py` | Module init |
| `backend/domains/approval/service.py` | Approval CRUD + resolve |
| `backend/domains/approval/checks.py` | `needs_approval()` utility |
| `backend/domains/approval/routes.py` | Admin approval endpoints |
| `backend/domains/approval/schemas.py` | Request/response models |
| `backend/tests/test_approval.py` | Tests |
| `migrations/versions/pp666rr66s98_create_approval_requests.py` | Migration |

### Modified Files
| File | Change |
|------|--------|
| `backend/common/config.py` | Add threshold and expiry settings |
| `backend/common/models/__init__.py` | Register ApprovalRequest |
| `backend/app/main.py` | Mount approval router |
| `backend/domains/inventory/routes.py` | Gate sensitive non-human stock adjustments behind approvals |

## Dev Agent Record

- **Implemented by:** Copilot Agent
- **Date:** 2026-04-03
- **Validation:** `tests/test_approval.py` passed with 14 focused tests; `tests/domains/inventory/test_stock_adjustment.py` passed with 11 regression tests.
- **Implementation notes:**
  - This story now goes beyond framework scaffolding by intercepting high-risk `inventory.adjust` requests from non-human actors before the write occurs.
  - Approval resolution avoids a redirect edge case on the list route and replays approved actions through a dedicated executor.
  - 2026-04-04 follow-up: expired approvals now keep `resolved_by=None` so timeout expiry stays distinct from human resolution attempts in the audit trail.

## Dev Notes

- **This story now includes the first real integration point.** `inventory.adjust` is approval-gated for non-human actors when the configured threshold is exceeded.
- **`needs_approval()` is a pure function** — it doesn't touch the database. It's called by the service layer before executing a write action. Services decide whether to call `create_approval()` or proceed directly.
- **Invoice void/submit approval** — these actions don't exist yet in the codebase (Epic 2 stories 2.3+ are ready-for-dev). The `needs_approval()` function registers the rules now so they're ready when those stories are implemented.
- **Executing approved actions** — `inventory.adjust` is replayed automatically through `domains/approval/executor.py` when an approval is accepted. Future approval-gated actions such as `invoices.void` and `invoices.submit` still need their own executors when those stories are implemented.
- TAB indentation. Ruff py312 rules E/F/I.
