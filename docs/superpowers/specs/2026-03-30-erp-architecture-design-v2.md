# AI-Native ERP Architecture Design v2

**Date:** 2026-03-30
**Version:** 2.0.0
**Status:** Post-Research Sprint — Approved for Planning
**Supersedes:** `design-artifacts/A-Product-Brief/2026-03-30-erp-architecture-design.md`

---

## 1. Executive Summary

This document defines the architecture for an AI-native ERP system targeting Taiwan SMBs. The system pivots from building AI internally to integrating existing AI agents (Claude Code, OpenClaw, etc.) as first-class users. The ERP exposes one shared business capability layer: AI agents consume it through MCP, while GUI and CLI clients use the same domain logic through typed application APIs.

**Deployment:** Hybrid topology — one codebase, switchable between solo (local sidecar + PostgreSQL) and team (central server + shared PostgreSQL) via config change only.

**Build order:** Invoice-first (critical path due to MIG 4.1-ready invoice model, feature-flagged eGUI workflow, and FIA API long lead time) → Customers → Inventory → Orders → Payments

**Key corrections from research sprint:**

| Decision | v1 (Original) | v2 (Post-Sprint) | Evidence |
|----------|---------------|-------------------|----------|
| MCP transport | `stateless_http=True` | Session-mode HTTP (SSE/WS) | FastMCP bug #678 |
| FastMCP version | 2.0 | **2.14.6** | 3.x incompatible with MCP SDK 1.23+ |
| React version | "latest" | **React 19** | Tauri webview dropdown bug |
| Windows installer | NSIS | **WiX** | Bug #15134 |
| Legacy orphan rate | 99.7% (660 codes) | **0.09%** (190 codes, 523 rows) | Field confusion corrected |
| asyncpg + PgBouncer | not mentioned | **`statement_cache_size=0`** | Tech viability PoC |
| FIA API | assumed available | **no sandbox, long approval** | eGUI compliance survey |

---

## 2. Architecture Overview

### 2.1 Core Principle: Shared Capability Layer, MCP as Canonical Agent Surface

All business logic lives in one shared domain layer inside the FastAPI + FastMCP process. AI agents consume that layer through FastMCP 2.14.6 tools. Human GUI and CLI clients use typed application APIs backed by the same services. MCP is the canonical agent surface, not the only client surface.

```
┌─────────────────────────────────────────────────────────────────────┐
│  ACTORS                                                             │
│  ┌──────────────────────────┐    ┌─────────────────────────────────┐│
│  │  Humans                 │    │  AI Agents                      ││
│  │  ├── GUI (Tauri App)    │    │  ├── Claude Code               ││
│  │  └── CLI (power users)  │    │  ├── OpenClaw                  ││
│  │       │                  │    │  └── Custom agents             ││
│  └───────│──────────────────┘    └───────────│───────────────────┘│
│          │                                     │                      │
│          ▼                                     ▼                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  FastAPI + FastMCP 2.14.6 (single process)                    ││
│  │  ┌────────────────────────┐  ┌────────────────────────────┐   ││
│  │  │  REST API /api/v1/*  │  │  MCP endpoint /mcp        │   ││
│  │  │  (for GUI/CLI)       │  │  (for AI agents)          │   ││
│  │  └────────────────────────┘  └────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Hybrid Deployment Topology

The same codebase runs in two modes — switchable via `ERP_MODE` config:

**Solo Mode (Personal):**

```
┌──────────────────────────────────────────────────────────────────┐
│  Tauri Desktop App                                                 │
│  ┌──────────────────────────────┐  ┌──────────────────────────┐  │
│  │  Vite + React 19 WebView    │  │  Python Sidecar         │  │
│  │  (localhost:8000)            │◄─│  FastAPI + FastMCP      │  │
│  └──────────────────────────────┘  │  (spawned by Tauri)    │  │
│                                     └──────────┬───────────────┘  │
│                                                 │                  │
│                                                 ▼                  │
│                                     ┌───────────────────────┐   │
│                                     │  PostgreSQL 17        │   │
│                                     │  (local, single-tenant)│   │
│                                     └───────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

**Team Mode (Shared Server):**

```
┌──────────────────────────────────────────────────────────────────┐
│  Tauri Desktop App (same binary)                                 │
│  ┌──────────────────────────────┐                                │
│  │  Vite + React 19 WebView    │                                │
│  │  (erp.company.com:8000)     │                                │
│  └──────────────────────────────┘                                │
└──────────────────────────┬────────────────────────────────────────┘
                           │ LAN / VPN / Internet
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  Central Server (NAS / VPS)                                       │
│  ┌──────────────────────────────┐                                │
│  │  FastAPI + FastMCP 2.14.6   │                                │
│  │  /api/v1/*  +  /mcp        │                                │
│  └──────────┬───────────────────┘                                │
│              │                                                      │
│              ├──────────────────────┬──────────────────────┐      │
│              ▼                      ▼                      ▼      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐  │
│  │  PostgreSQL 17  │  │  Redis 7         │  │  MinIO     │  │
│  │  + pgvector     │  │  Sessions/Cache  │  │  S3 Storage│  │
│  │  Multi-tenant   │  │  Task broker     │  │            │  │
│  └─────────────────┘  └─────────────────┘  └────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

**Topology switching:**

```python
# src/app/config.py
from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    mode: Literal["solo", "team"] = "solo"
    server_url: str = "http://localhost:8000"

    @property
    def database_url(self) -> str:
        if self.mode == "solo":
            return os.environ.get("DATABASE_URL", "postgresql://localhost:5432/ultr_erp")
        return os.environ["DATABASE_URL"]

    @property
    def mcp_url(self) -> str:
        if self.mode == "solo":
            return "http://localhost:8000/mcp"
        return f"{self.server_url}/mcp"
```

---

## 3. Technology Stack

### 3.1 Core Technologies (v2)

| Layer | Technology | Version | Evidence |
|-------|-----------|--------|---------|
| Desktop Shell | Tauri | 2.x | 8MB vs 120MB Electron; Cursor uses it |
| Frontend | Vite + React | **19** | Webview dropdown bug fix |
| Backend Framework | FastAPI | 0.115+ | Massive ecosystem |
| MCP Server | **FastMCP 2.14.6** | 2.14.6 | 3.x incompatible with SDK 1.23+ |
| MCP Transport | Session-mode HTTP | SSE/WS | `stateless_http=True` hangs |
| Database | PostgreSQL | 17+ | Industry standard |
| ORM | SQLAlchemy | 2.0+ | Full async support |
| DB Pool | asyncpg | latest | with `statement_cache_size=0` |
| Cache | Redis | 7+ | Sessions, cache, task broker |
| Object Storage | MinIO | Latest | S3-compatible |
| AI | Claude API | Latest | Cloud subscription |

### 3.2 Key Configuration Requirements

**asyncpg connection (PgBouncer-safe):**
```python
engine = create_async_engine(
    database_url,
    connect_args={"statement_cache_size": 0},  # CRITICAL for PgBouncer
)
```

**FastMCP server:**
```python
mcp = FastMCP(
    "UltrERP",
    transport="streamable-http",  # NOT stateless_http=True
    port=8000,
)
```

---

## 4. Architecture Patterns

### 4.1 Tauri + Python Sidecar (Solo Mode)

**Pattern:** Tauri spawns Python sidecar via `std::process::Command`. Sidecar path resolved via `CARGO_MANIFEST_DIR` environment variable (not `current_exe()` path walking, which is fragile for GUI apps).

```rust
// src-tauri/src/lib.rs
use std::process::Command;

fn spawn_sidecar() -> Option<Child> {
    // CARGO_MANIFEST_DIR is set at compile time — always correct
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let sidecar_path = PathBuf::from(manifest_dir)
        .join("sidecar")
        .join("main.py");

    Command::new("python3")
        .args(&["-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"])
        .current_dir(sidecar_path.parent()?)
        .spawn()
        .ok()
}
```

**Evidence:** Tech viability PoC confirmed this works on macOS. Windows requires WiX installer (not NSIS) due to bug #15134.

### 4.2 FastAPI Modular Monolith

**Pattern:** FastAPI sub-applications mounted at `/api/v1/{domain}`. Services call each other directly (not via HTTP) for intra-process communication.

```
src/
├── app/
│   ├── main.py               # create_app() — mounts all sub-apps
│   └── deps.py               # Shared dependencies (db session, tenant)
├── common/
│   ├── database.py           # Async session factory, statement_cache_size=0
│   ├── cache.py              # Redis client
│   ├── auth.py               # Audience-validated tokens + scoped API keys
│   ├── errors.py             # Structured error types
│   └── events.py             # Domain event bus
└── domains/
    ├── customers/
    │   ├── models.py          # SQLAlchemy models
    │   ├── schemas.py         # Pydantic request/response
    │   ├── service.py         # Business logic
    │   ├── routes.py          # /api/v1/customers endpoints
    │   └── mcp.py             # FastMCP tool definitions
    ├── invoices/              # Invoice lifecycle + eGUI
    ├── inventory/             # Stock management
    ├── orders/                # Order processing
    └── payments/              # Payment handling
```

**Sub-app mounting:**
```python
app.mount("/api/v1/customers", create_customers_app())
app.mount("/api/v1/invoices", create_invoices_app())
app.mount("/api/v1/inventory", create_inventory_app())
app.mount("/api/v1/orders", create_orders_app())
app.mount("/api/v1/payments", create_payments_app())
app.mount("/mcp", create_mcp_server())
```

### 4.3 MCP Server (FastMCP 2.14.6)

**Tool naming:** `{domain}.{action}.{entity}` — single responsibility per tool.

```python
# domains/invoices/mcp.py
@mcp.tool()
async def invoices_create(
    ctx: Context,
    customer_id: str,
    items: list[dict],
    tax_included: bool = True,
) -> dict:
    """Create MIG 4.1-ready invoice.

    Validates tax ID format, calculates tax, generates MIG 4.1 XML,
    and, when eGUI is enabled for the tenant, schedules FIA submission.
    """
    invoice = await InvoiceService(session).create_invoice(
        customer_id=customer_id,
        items=items,
        tax_included=tax_included,
    )
    return {"invoice_id": str(invoice.id), "status": invoice.status}
```

### 4.4 Durable Workflows (Transactional Outbox)

**Outbox table:**
```sql
CREATE TABLE outbox_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type        VARCHAR(255) NOT NULL,
    payload     JSONB NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'NEW',
    -- Status: NEW, PROCESSING, SENT, FAILED, RETRYING, DEAD_LETTER
    retry_count INT NOT NULL DEFAULT 0,
    max_retries INT NOT NULL DEFAULT 5,
    next_retry_utc TIMESTAMPTZ,
    error       TEXT,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_utc TIMESTAMPTZ,
    correlation_id UUID
);

CREATE INDEX idx_outbox_pending
    ON outbox_events (status, next_retry_utc)
    WHERE status IN ('NEW', 'RETRYING');
```

**Inbox table:**
```sql
CREATE TABLE inbox_events (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source        VARCHAR(255) NOT NULL,  -- e.g., "FIA"
    message_type  VARCHAR(255) NOT NULL,  -- e.g., "EguiAck"
    payload       JSONB NOT NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'NEW',
    -- Status: NEW, PROCESSING, APPLIED, DUPLICATE, ERROR, DEAD_LETTER
    idempotency_key VARCHAR(255) UNIQUE,
    error         TEXT,
    created_utc   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_utc TIMESTAMPTZ
);
```

**Domain events and their side effects:**

| Event | External Side Effect |
|-------|---------------------|
| `InvoiceIssued` | Persist MIG 4.1 XML; submit to FIA via outbox if eGUI is enabled |
| `InvoiceVoided` | Submit void to FIA via outbox if eGUI is enabled |
| `OrderShipped` | Send notification email |
| `PaymentReceived` | Reconcile invoice |

### 4.5 Shadow-Mode Reconciliation

**Pattern:** A versioned reconciliation specification compares old and new system outputs during parallel run. Cutover is blocked by unresolved severity-1 discrepancies.

```yaml
version: 1
domains:
    invoices:
        compare:
            - invoice_total
            - tax_total
            - line_count
    inventory:
        compare:
            - qty_on_hand
            - warehouse
    payments:
        compare:
            - amount
            - invoice_allocation
severity_1:
    - invoice_total_mismatch
    - tax_total_mismatch
    - payment_allocation_mismatch
```

**Outputs:** discrepancy alerts, daily summary report, cutover gate status.

### 4.6 Claude Skills

```
erp-skills/
├── SKILL.md
├── taiwan-egui/
│   ├── SKILL.md
│   └── reference/
│       ├── tax-rates.md
│       ├── mig41.md
│       ├── submission.md
│       └── states.md
├── sales-workflow/
│   ├── SKILL.md
│   └── reference/
│       ├── credit.md
│       └── pricing.md
└── inventory/
    ├── SKILL.md
    └── reference/
        ├── reorder.md
        └── suppliers.md
```

---

## 5. Domain Model

### 5.1 Core Entities

| Entity | Description | Key Fields |
|--------|-------------|------------|
| Customer | Business customer with tax ID | name, tax_id (current Taiwan checksum guidance), credit_limit |
| Invoice | Invoice lifecycle | customer, line_items, tax, status, egui_submission |
| InvoiceLine | Line items on invoice | product_code, qty, unit_price, tax_rate, tax_amount |
| EguiSubmission | eGUI submission record | invoice_id, status, FIA_reference |
| Product | Inventory item | code, name, category, sale_price, avg_cost |
| Stock | Current inventory levels | product_id, warehouse_id, qty_on_hand, reorder_point |
| Order | Sales order | customer, lines, status |
| Payment | Payment against invoice | amount, method, reconcile_invoice_id |
| Approval | Pending approval for high-risk action | actor, action, status |

### 5.2 eGUI State Machine

```
PENDING → QUEUED → SENT → ACKED
                  ↓
               FAILED → RETRYING → SENT
                  ↓
            DEAD_LETTER (after max retries)
```

| State | Meaning |
|-------|---------|
| `PENDING` | Invoice issued; awaiting eGUI processing |
| `QUEUED` | Submitted to outbox; worker will dispatch |
| `SENT` | Transmitted to FIA; awaiting ack |
| `ACKED` | FIA confirmed receipt |
| `FAILED` | FIA rejected or timeout |
| `RETRYING` | Scheduled for retry with backoff |
| `DEAD_LETTER` | All retries exhausted; requires manual intervention |

This state machine is active when live FIA/eGUI submission is enabled. When submission is feature-flagged off, invoices still generate MIG 4.1-ready artifacts but no FIA transition is enqueued.

### 5.3 MIG 4.1 Requirements

**Effective:** January 1, 2026

| Field | Format | Notes |
|-------|--------|-------|
| InvoiceNumber | `[A-Z]{2}\d{8}` | e.g., `AZ12345678` |
| InvoiceDate | `YYYY-MM-DD` | ISO 8601 |
| BuyerId | 8 digits validated by current Taiwan business-number checksum guidance | Taiwan tax ID |
| TaxType | 1/2/3/4 | 1=課稅, 2=零稅率, 3=免稅, 4=特種 |
| TaxType (ProductItem) | **Required at line level** | New in MIG 4.1 |
| TaxAmount | `decimal(20,0)` integer amount | No fractional cents allowed in MIG 4.1 payloads |
| Amount | `decimal(20,0)` integer amount | No fractional cents allowed in MIG 4.1 payloads |

**Evidence:** eGUI compliance PoC (`research/egui-compliance/02-poc/`) produces valid MIG 4.1 XML.

### 5.3.1 Invoice Output and Number Allocation

- Invoice numbers matching `[A-Z]{2}\d{8}` are allocated from configured government-issued ranges; application persistence tracks the next available number and prevents reuse.
- Physical printing uses one shared invoice HTML/CSS renderer plus the platform print dialog from the Tauri/webview shell.
- PDF export uses backend-assisted headless browser rendering from that same renderer; do not depend on Tauri-native print-to-PDF APIs.
- Both print and PDF flows require a source-controlled stationery contract and approved reference asset under `docs/invoices/`.

### 5.4 Multi-Tenancy

All tenant-owned tables include `tenant_id`. Tenant context set per session via `SET LOCAL app.tenant_id`:

```sql
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON invoices
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

**Deployment modes:**

| Mode | RLS | Use Case |
|------|-----|---------|
| Solo | Off | Single user |
| Team | Off | Small team, trust-based |
| Business | On | Customer-facing SaaS |

---

## 6. MCP Tool Reference

### 6.1 Customers

| Tool | Description | Scopes |
|------|-------------|--------|
| `customers.list` | List customers with filters | customers:read |
| `customers.get` | Get customer by ID or tax_id | customers:read |
| `customers.create` | Create customer with current Taiwan business-number checksum validation | customers:write |
| `customers.update` | Update customer | customers:write |

### 6.2 Invoices

| Tool | Description | Scopes |
|------|-------------|--------|
| `invoices.list` | List invoices with filters | invoices:read |
| `invoices.get` | Get invoice with line items | invoices:read |
| `invoices.create` | Create invoice + MIG 4.1 XML | invoices:write |
| `invoices.void` | Void invoice (same-month) | invoices:write |
| `invoices.submit` | Trigger eGUI submission when enabled | invoices:write |

### 6.3 Inventory

| Tool | Description | Scopes |
|------|-------------|--------|
| `inventory.check` | Check stock levels | inventory:read |
| `inventory.adjust` | Adjust stock (idempotent delta) | inventory:write |
| `inventory.reorder_report` | Products below reorder point | inventory:read |

### 6.4 Orders

| Tool | Description | Scopes |
|------|-------------|--------|
| `orders.list` | List orders with filters | orders:read |
| `orders.get` | Get order with line items | orders:read |
| `orders.create` | Create order | orders:write |
| `orders.update_status` | Update order status | orders:write |

### 6.5 Payments

| Tool | Description | Scopes |
|------|-------------|--------|
| `payments.list` | List payments | payments:read |
| `payments.get` | Get single payment | payments:read |
| `payments.create` | Record payment | payments:write |
| `payments.reconcile` | Auto-match payments to invoices | payments:write |

---

## 7. Security

### 7.1 Authentication Matrix

| User Type | Method |
|-----------|--------|
| Human (GUI) | Interactive login → audience-validated token/session |
| Human (CLI) | Interactive login/device flow → audience-validated token |
| AI Agent (interactive) | Audience-validated bearer token with scopes |
| Automation | API key with scopes |

### 7.2 RBAC

| Role | customers | invoices | inventory | orders | payments | admin |
|------|-----------|----------|-----------|--------|----------|-------|
| admin | CRUD | CRUD | CRUD | CRUD | CRUD | Full |
| finance | R | CRUD+void | — | R | CRUD | — |
| warehouse | R | — | CRUD | R | — | — |
| sales | CRUD | Create | R | CRUD | — | — |
| agent | R | R+C | R | R | — | — |

### 7.3 Automation API Key Scopes

Scoped API keys are limited to controlled, non-interactive automation contexts. Interactive use should rely on audience-validated tokens.

```python
API_KEY_SCOPES = {
    "erp_key_admin_*": ["admin"],
    "erp_key_finance_*": [
        "customers:read", "invoices:read", "invoices:write",
        "payments:read", "payments:write",
    ],
    "erp_key_sales_*": [
        "customers:read", "customers:write",
        "invoices:read", "invoices:create",
        "orders:read", "orders:write",
    ],
    "erp_key_agent_*": [
        "customers:read", "invoices:read", "invoices:create",
        "inventory:read", "orders:read",
    ],
}
```

### 7.4 Human-in-the-Loop Approvals

High-risk write actions create an approval record and require explicit human confirmation before execution when initiated through AI or automation.

Examples:
- `invoices.void`
- `invoices.submit` when eGUI is enabled
- `inventory.adjust` above configured threshold

### 7.5 Audit Log

```sql
CREATE TABLE audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    occurred_utc    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_type      VARCHAR(20) NOT NULL,  -- 'human' or 'agent'
    actor_id        VARCHAR(255) NOT NULL,
    tenant_id       UUID NOT NULL,
    action          VARCHAR(255) NOT NULL,
    target_entity   VARCHAR(255) NOT NULL,
    target_id       UUID,
    before_state    JSONB,
    after_state     JSONB,
    correlation_id  UUID,
    mcp_call_id     VARCHAR(255),
    ip_address      INET,
    metadata        JSONB
);

-- Append-only enforced by trigger
CREATE TRIGGER prevent_audit_modification
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION prevent_modification();
```

---

## 8. Infrastructure Components

### 8.1 PostgreSQL 17 + pgvector

- Single deployment unit for both solo and team modes
- `statement_cache_size=0` required for PgBouncer compatibility
- pgvector enabled for semantic search (optional in solo)

### 8.2 Redis 7+

| Use Case | TTL |
|----------|-----|
| MCP tool result cache | 60s |
| Rate limit counters | Sliding window |
| Session tokens | 24h |
| Job locks | 30s |

### 8.3 MinIO

- Invoice XML archives: `{tenant_id}/mig41/{invoice_id}.xml`
- Issuer-side archive of record for invoice artifacts; do not rely on MOF platform retention windows as primary archive
- File attachments
- S3-compatible for portable backups

### 8.4 Retention Policy Baseline

- eGUI consent/supporting records: at least 5 years
- Core financial records and books: at least 10 years
- Optional company-policy override may retain artifacts longer
- Retention rules are applied by record class, not by one global hardcoded period

---

## 9. Build Order

Invoice-first due to MIG 4.1-ready invoice modeling requirements and FIA API long approval lead. Live FIA/eGUI activation remains gated by credentials, filing obligation, and operator readiness.

| Phase | Domain | Duration | Key Deliverables |
|-------|--------|----------|-------------------|
| 0 | Prerequisites | Parallel | FIA registration; React 19 hardware test |
| 1 | Invoice + eGUI-ready flow | 4-6 weeks | MIG 4.1 XML gen; FIA mock; feature-flagged eGUI state machine |
| 2 | Customers + Inventory | 3-4 weeks | Taiwan business-number checksum validation; stock levels; reorder alerts |
| 3 | Orders + Payments | 3-4 weeks | Order lifecycle; payment reconciliation |
| 4 | Desktop Shell + MCP | 4-6 weeks | Tauri app; FastMCP integration |
| 5 | Polish | 2-3 weeks | Security hardening; live FIA activation checklist; documentation; skills |

**Total: 16-23 weeks**

---

## 10. Evidence Index

| Category | Source | Location |
|----------|--------|----------|
| FastMCP bug (stateless HTTP) | Tech viability survey | `research/tech-viability/01-survey-memo.md` |
| FastMCP 3.x SDK incompatibility | Multi-agent survey | `research/multi-agent-patterns/01-survey-memo.md` |
| React 19 requirement | UI/UX survey | `research/ui-ux/01-survey-memo.md` |
| Tauri NSIS bug #15134 | Tech viability survey | `research/tech-viability/01-survey-memo.md` |
| asyncpg + PgBouncer fix | Tech viability survey | `research/tech-viability/01-survey-memo.md` |
| MIG 4.1 XML generator | eGUI PoC | `research/egui-compliance/02-poc/mig41_generator.py` |
| FIA mock server | eGUI PoC | `research/egui-compliance/02-poc/fia_mock_server.py` |
| FastMCP 2.14.6 server | Multi-agent PoC | `research/multi-agent-patterns/02-poc/` |
| Tauri + FastAPI sidecar | Tech viability PoC | `research/tech-viability/02-poc/tauri-fastapi-poc/` |
| Legacy orphan correction | Legacy data PoC | `research/legacy-data/02-poc/03-findings.md` |
| Modular monolith pattern | modular-monolith-fastapi | github.com/YoraiLevi/modular-monolith-fastapi |
| Tauri sidecar reference | example-tauri-v2-python-server-sidecar | github.com/dieharders/example-tauri-v2-python-server-sidecar |

---

**Status:** ✅ Post-research sprint architecture — ready for implementation planning
