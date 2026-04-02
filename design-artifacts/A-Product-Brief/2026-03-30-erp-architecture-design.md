# AI-Native ERP Architecture Design

**Date:** 2026-03-30
**Version:** 2.1.0
**Status:** Validated with Evidence — Enhanced (multi-tenancy, durable workflows, eGUI bounded context, security, AI scope)

---

## 1. Executive Summary

This document defines the architecture for an AI-native ERP system targeting Taiwan SMBs. The system pivots from building AI internally to integrating existing AI agents (Claude Code, OpenClaw, etc.) as first-class users.

**Key Decisions:**

| Decision | Technology | Evidence |
|----------|------------|----------|
| Desktop Shell | Tauri 2.x | 8MB vs 120MB Electron; production-viable; Cursor uses it |
| Backend Framework | FastAPI + FastMCP | Official MCP SDK incorporates FastMCP; massive ecosystem |
| Desktop+Backend Pattern | Tauri Sidecar | `example-tauri-v2-python-server-sidecar` exists as reference |
| Modular Monolith | FastAPI Sub-apps | `modular-monolith-fastapi` uses mounts for service isolation |
| Agent Interface | MCP Server | FastMCP 2.0 is the standard; 1000+ RPS capable |
| Domain Expertise | Claude Skills | Well-established; evaluation-driven development |
| Database | PostgreSQL + pgvector | Industry standard for ERP; 74% plan integrated vectors |
| AI | Claude API (cloud) | Subscription model; cost-controlled |

**Architecture Validation:** ✅ All technologies validated against authoritative sources.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           USERS                                      │
│  ┌─────────────────────────┐    ┌─────────────────────────────────┐│
│  │  Humans                 │    │  AI Agents                      ││
│  │  ├── CLI (power users)  │    │  ├── Claude Code               ││
│  │  └── GUI (casual users) │    │  ├── OpenClaw                  ││
│  │       └── Tauri App     │    │  └── Custom agents              ││
│  └─────────────────────────┘    └─────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    TAURI DESKTOP APP (Shell)                        │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Vite + React WebView                                         │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │  Tauri IPC ──► HTTP Client ──► FastAPI Backend        │ │  │
│  │  │  (Rust)        (localhost)    (Python Sidecar)          │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (or direct MCP/REST for headless)
┌─────────────────────────────────────────────────────────────────────┐
│                      API LAYER (FastAPI)                            │
│  ┌──────────────────┐    ┌──────────────────────────────────────┐ │
│  │  REST API        │    │  MCP Server (FastMCP 2.0)           │ │
│  │  (for GUI)       │    │  - Tools: customers, invoices, etc. │ │
│  │                   │    │  - Resources: invoices://{id}       │ │
│  │                   │    │  - Stateless HTTP for scaling        │ │
│  └──────────────────┘    └──────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DOMAIN LAYER (Python)                          │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  FastAPI Sub-Applications (Mounts) per Domain               │  │
│  │                                                               │  │
│  │  ├── customers/    # Customer domain                         │  │
│  │  │   ├── models.py    # SQLAlchemy models                    │  │
│  │  │   ├── schemas.py   # Pydantic request/response            │  │
│  │  │   ├── service.py   # Business logic                      │  │
│  │  │   └── routes.py    # API endpoints                       │  │
│  │  │                                                             │  │
│  │  ├── invoices/    # Invoice lifecycle (create, void, reconcile)│  │
│  │  ├── egui/       # Taiwan eGUI submissions & state machine  │  │
│  │  │   ├── models.py   # EguiSubmission, EguiAck, EguiError    │  │
│  │  │   ├── service.py  # FIA submission, MIG 4.1 XML build     │  │
│  │  │   └── states.py   # PENDING→QUEUED→SENT→ACKED│FAILED   │  │
│  │  ├── inventory/   # Stock management                         │  │
│  │  ├── orders/       # Order processing                         │  │
│  │  └── payments/     # Payment handling                         │  │
│  │                                                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Shared Infrastructure                                       │  │
│  │  ├── database.py     # Async session, connection pool       │  │
│  │  ├── auth.py         # JWT, API keys                         │  │
│  │  ├── cache.py        # Redis integration                     │  │
│  │  └── events.py      # Domain events                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    SKILLS (Domain Expertise)                        │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  erp-skills/                                                │  │
│  │  ├── SKILL.md              # Main entry point               │  │
│  │  ├── taiwan-egui/                                          │  │
│  │  │   ├── SKILL.md         # eGUI state machine & workflow  │  │
│  │  │   └── reference/                                        │  │
│  │  │       ├── tax-rates.md   # 5%, 10%, 0%                │  │
│  │  │       ├── mig41.md       # MIG 4.1 XML format           │  │
│  │  │       ├── submission.md  # FIA API, 48-hour rule        │  │
│  │  │       └── states.md      # State transitions & dead letter│  │
│  │  ├── sales-workflow/                                        │  │
│  │  │   ├── SKILL.md         # Sales process                  │  │
│  │  │   └── reference/                                        │  │
│  │  │       ├── credit.md     # Credit management             │  │
│  │  │       └── pricing.md    # Pricing rules                 │  │
│  │  └── inventory/                                             │  │
│  │      ├── SKILL.md                                           │  │
│  │      └── reference/                                         │  │
│  │          ├── reorder.md    # Reorder points                 │  │
│  │          └── suppliers.md  # Supplier info                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE (Self-Hosted)                    │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐│
│  │  PostgreSQL  │  │    Redis     │  │       MinIO             ││
│  │  17+         │  │  7+          │  │  (S3-compatible)       ││
│  │  + pgvector  │  │  Sessions    │  │  File storage           ││
│  │               │  │  Cache       │  │                        ││
│  └──────────────┘  └──────────────┘  └──────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

### 3.1 Core Technologies

| Layer                  | Technology         | Version    | Evidence |
| ---------------------- | ------------------ | ---------- | -------- |
| **Desktop Shell**       | Tauri             | 2.x        | 8MB vs 120MB Electron; Cursor, Affine, AppFlowy in production |
| **Frontend**            | Vite + React      | Latest     | Standard React ecosystem; 50-80KB bundle |
| **CLI Framework**       | Typer             | Latest     | Auto-generates CLI from type hints |
| **Backend Framework**    | FastAPI           | 0.115+     | Massive ecosystem; SQLAlchemy/Pydantic native |
| **MCP Server**          | FastMCP 2.0       | 2.0        | Official SDK incorporates FastMCP v1; 1000+ RPS |
| **Database**            | PostgreSQL        | 17+        | Industry standard; pgvector (optional, cloud-only) |
| **ORM**                | SQLAlchemy        | 2.0+       | Full async support; SQLModel on top |
| **Cache**              | Redis             | 7+         | Sessions, cache, task broker |
| **Object Storage**      | MinIO             | Latest     | S3-compatible; self-hosted |
| **AI Inference**        | Claude API        | Latest     | Cloud subscription; Claude Code native |

### 3.2 Development Tools

| Category               | Tool                   | Evidence |
| ---------------------- | ---------------------- | -------- |
| **CLI**                | Typer                  | By FastAPI authors; auto help generation |
| **MCP**                | FastMCP 2.0            | PrefectHQ; incorporated into official SDK |
| **API Docs**           | OpenAPI/Swagger        | FastAPI native |
| **Migrations**         | Alembic                | Standard for SQLAlchemy |
| **Testing**            | pytest + httpx          | FastAPI best practice |
| **CSS**                | Tailwind CSS           | Standard |
| **UI Components**      | shadcn/ui + Radix      | Accessible component library |
| **Linting**            | ruff                   | 10-100x faster than flake8 |
| **Type Checking**      | pyright                | FastAPI recommended |

### 3.3 Reference Projects (Proven Patterns)

| Reference | URL | What It Gives You |
|-----------|-----|-------------------|
| **modular-monolith-fastapi** | github.com/YoraiLevi/modular-monolith-fastapi | FastAPI sub-apps/mounts pattern; SQLModel; uv+ruff+pyright |
| **example-tauri-v2-python-server-sidecar** | github.com/dieharders/example-tauri-v2-python-server-sidecar | Exact Tauri+Python sidecar pattern |
| **FastAPI Best Practices** | github.com/zhanymkanov/fastapi-best-practices | Opinionated conventions from production experience |
| **ERPNext** | github.com/frappe/erpnext | Domain modeling reference; metadata-driven architecture |
| **MCP Servers** | github.com/modelcontextprotocol/servers | Official reference implementations |

---

## 4. Architecture Patterns (Validated)

### 4.1 Tauri + Python Sidecar Pattern

**Evidence:** `example-tauri-v2-python-server-sidecar` (GitHub) provides the exact reference implementation.

```
┌─────────────────────────────────────────────────────────────┐
│  Tauri App                                                  │
│                                                              │
│  src-tauri/                                                 │
│  ├── tauri.conf.json    # externalBin: ["./bin/api"]       │
│  ├── main.rs            # Spawns sidecar, manages lifecycle│
│  └── Cargo.toml                                             │
│                                                              │
│  Sidecar Process (Python):                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  main.exe  ──►  FastAPI Server on localhost:8008   │   │
│  │  (PyInstaller)                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  Frontend (JS):                                             │
│  fetch('http://localhost:8008/api/invoices')               │
└─────────────────────────────────────────────────────────────┘
```

**Key Configuration:**

```json
// tauri.conf.json
{
  "bundle": {
    "externalBin": [
      "./src-tauri/bin/api-windows.exe",
      "./src-tauri/bin/api-macos",
      "./src-tauri/bin/api-linux"
    ]
  }
}
```

**IPC Communication:**
- HTTP from frontend to Python FastAPI (localhost)
- Tauri spawns sidecar, frontend controls via HTTP
- FastAPI serves both REST (GUI) and MCP (agents)

### 4.2 FastAPI Modular Monolith Pattern

**Evidence:** `modular-monolith-fastapi` uses **FastAPI sub-applications (mounts)** for service isolation.

> **Important — Internal Communication:** Intra-process calls between sub-apps go through application service layers, not HTTP. Self-RPC via HTTP is used only for horizontal scaling across processes or containers. In single-process deployments, services call each other directly.

```
src/
├── app/
│   └── main.py              # Root FastAPI app
├── common/
│   ├── logging/             # Context-aware middleware
│   └── database.py          # Async session factory
└── services/
    ├── customers/           # Mounted as /customers
    │   ├── __init__.py     # Creates FastAPI sub-app
    │   ├── models.py
    │   ├── schemas.py
    │   ├── service.py
    │   └── routes.py
    ├── invoices/            # Mounted as /invoices
    └── inventory/           # Mounted as /inventory
```

**Service Isolation Pattern:**

```python
# services/customers/__init__.py
from fastapi import FastAPI

def create_customers_app() -> FastAPI:
    app = FastAPI(title="Customers Service")

    @app.get("/customers")
    async def list_customers():
        ...

    return app

# app/main.py
from fastapi import FastAPI
from services.customers import create_customers_app

app = FastAPI()
app.mount("/customers", create_customers_app())
app.mount("/invoices", create_invoices_app())
```

**Internal Communication:** Services communicate via their public REST API endpoints (self-RPC pattern).

### 4.3 MCP Server Pattern

**Evidence:** FastMCP 2.0 / official MCP Python SDK

```python
# mcp/server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "ERP Service",
    stateless_http=True,  # Required for horizontal scaling
    json_response=True    # Structured JSON
)

@mcp.tool()
async def create_invoice(
    customer_id: str,
    items: list[dict],
    tax_included: bool = True
) -> dict:
    """Create Taiwan eGUI-compliant invoice.

    Validates tax ID format, calculates tax, and schedules
    submission to eGUI within 48-hour window.
    """
    # Business logic
    return {"invoice_id": "INV-2026-001", "status": "draft"}

@mcp.resource("invoices://{customer_id}")
async def customer_invoices(customer_id: str) -> list[dict]:
    """List all invoices for a customer."""
    return await invoice_service.list_by_customer(customer_id)
```

### 4.5 Durable Workflows (Transactional Outbox & Inbox)

**Problem:** Domain events that trigger external side effects (eGUI submissions, emails, 3rd-party API calls) must not be lost or double-executed if the process crashes.

**Solution:** Transactional Outbox + Inbox pattern. All authoritative workflow state lives in Postgres tables — Redis is for performance/caching only.

#### Outbox Table

```sql
CREATE TABLE outbox_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type        VARCHAR(255) NOT NULL,   -- e.g., "InvoiceIssued", "PaymentReceived"
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

-- Index for polling unprocessed events
CREATE INDEX idx_outbox_pending
    ON outbox_events (status, next_retry_utc)
    WHERE status IN ('NEW', 'RETRYING');
```

#### Inbox Table

```sql
CREATE TABLE inbox_events (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source        VARCHAR(255) NOT NULL,  -- e.g., "FIA", "PaymentProvider"
    message_type  VARCHAR(255) NOT NULL,  -- e.g., "EguiAck", "PaymentWebhook"
    payload       JSONB NOT NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'NEW',
    -- Status: NEW, PROCESSING, APPLIED, DUPLICATE, ERROR, DEAD_LETTER
    idempotency_key VARCHAR(255) UNIQUE,  -- Prevent duplicate processing
    error         TEXT,
    created_utc   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_utc TIMESTAMPTZ
);

CREATE INDEX idx_inbox_pending
    ON inbox_events (status)
    WHERE status = 'NEW';
```

#### Workflow Semantics

| Property | Requirement |
|----------|-------------|
| Atomicity | Domain change + outbox insert happen in the **same DB transaction** |
| Delivery | At-least-once; consumers must be **idempotent** |
| Ordering | Not guaranteed; use `correlation_id` to match request/response |
| Dead letter | After `max_retries`, move to `DEAD_LETTER` for manual inspection |
| Retry backoff | Exponential, configurable (e.g., 1min, 5min, 30min, 2hr) |
| Redis role | Only for high-frequency job scheduling and distributed locks — never as source of truth |

#### Worker Pattern

```python
# workers/outbox_worker.py
async def process_outbox(batch_size: int = 100):
    rows = await db.fetch("""
        SELECT * FROM outbox_events
        WHERE status IN ('NEW', 'RETRYING')
          AND (next_retry_utc IS NULL OR next_retry_utc <= NOW())
        ORDER BY created_utc
        LIMIT $1
        FOR UPDATE SKIP LOCKED
    """, batch_size)

    for row in rows:
        try:
            await dispatch_event(row['type'], row['payload'])
            await db.execute(
                "UPDATE outbox_events SET status='SENT', processed_utc=NOW() WHERE id=$1",
                row['id']
            )
        except Exception as exc:
            await db.execute("""
                UPDATE outbox_events
                SET status='RETRYING',
                    retry_count = retry_count + 1,
                    next_retry_utc = NOW() + (2 ^ retry_count) * INTERVAL '1 minute',
                    error = $2
                WHERE id = $1
            """, row['id'], str(exc))
```

#### Where This Applies

| Domain Event | External Side Effect |
|-------------|---------------------|
| `InvoiceIssued` | Submit MIG 4.1 XML to FIA (eGUI) |
| `InvoiceVoided` | Submit void to FIA |
| `OrderShipped` | Send notification email |
| `PaymentReceived` | Notify accounting, reconcile invoice |

---

**Tool Design Principles (from MCP best practices):**

| Principle | Implementation |
|----------|---------------|
| Single responsibility | One tool per business operation, not per CRUD |
| Descriptive names | `create_invoice`, not `add` or `new_invoice` |
| Comprehensive descriptions | Explain when to use, not just what it does |
| Typed parameters | JSON Schema with descriptions on every field |
| Limit returns | Max ~25 items; paginate with cursor |
| Fail gracefully | Structured errors with retry guidance |

### 4.4 Claude Skills Pattern

**Evidence:** Anthropic's skill authoring guide; `anthropics/skills` (106k stars)

```yaml
# erp-skills/taiwan-egui/SKILL.md
---
name: taiwan-egui-compliance
description: "Handles Taiwan eGUI electronic invoice compliance.
              Use when creating invoices, validating tax calculations,
              or submitting to Taiwan IRS systems."
---

# Taiwan eGUI Invoice Workflow

## Invoice Requirements
- MIG 4.1 XML format (effective January 1, 2026)
- All invoices include: 統一編號 (tax ID), 發票日期, 品項, 稅額
- Must submit to FIA within 48 hours of issuance

## Tax Rates
- **5%**: Standard rate
- **10%**: Transport, insurance, machinery
- **0%**: Exempt exports, specific healthcare

## Validation Checklist
- [ ] Tax ID format (8 digits + check digit)
- [ ] Tax rate matches product category
- [ ] 金額合計 matches sum of 課稅別
- [ ] Submission timestamp within 48hr window

## Reference
See [mig41.md](reference/mig41.md) for XML schema details.
See [tax-rates.md](reference/tax-rates.md) for rate tables.
```

**Progressive Disclosure:**
- `SKILL.md` — Overview + workflow (always loaded when triggered)
- `reference/*.md` — Detailed reference (loaded as needed)
- `scripts/*.py` — Executable validation scripts (run, not loaded)

---

## 5. Domain Model

### 5.1 Core Entities

| Entity       | Description                      | Evidence |
| ------------ | ------------------------------- | -------- |
| Customer     | Business customer with tax ID    | ERPNext metadata-driven DocType |
| Invoice      | Invoice lifecycle (create, void, reconcile) | MIG 4.1 format |
| InvoiceItem  | Line items on invoice           | Tax calculation per line |
| EguiSubmission | Taiwan eGUI submission record | FIA API; MIG 4.1 XML |
| EguiAck      | FIA acknowledgment response     | State tracking |
| EguiError    | FIA error or rejection          | Retry logic |
| Product      | Inventory item                  | SKU, pricing, reorder |
| Stock        | Current inventory levels        | Threshold alerts |
| Order        | Sales order                    | Status workflow |
| Payment      | Payment against invoice         | Reconciliation |
| Approval     | Pending approval for high-risk action | RBAC workflow |

### 5.2 eGUI State Machine

Each `EguiSubmission` transitions through the following states:

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

### 5.3 Taiwan eGUI Compliance

**Evidence:** MIG 4.1 standard (effective January 1, 2026)

| Requirement | Detail |
|-------------|--------|
| **Standard** | MIG 4.1 (updated from 4.0) |
| **Format** | XML via FIA API |
| **Authorization** | App ID + API Key from FIA |
| **Submission** | Within 48 hours of invoice creation |
| **Tax Rates** | 5%, 10%, 0% based on product type |
| **Void/Reissue** | Same month only |
| **MIG Version** | 4.1 mandatory from Jan 1, 2026 |

**API Integration:**
- Direct FIA API access requires application and approval
- Turnkey-style exchange workflows also supported
- Provider-mediated connectivity available

### 5.4 Multi-Tenancy and Tenants

All tenant-owned tables include a `tenant_id` column. The current tenant context is derived from auth (JWT or session) and set per database session via `SET LOCAL app.tenant_id`.

#### Deployment Modes

| Mode | Description | RLS |
|------|-------------|-----|
| **Solo / Team** | Logically single-tenant; `tenant_id` fixed to one value; RLS policies can be relaxed | Off by default |
| **Business / Cloud** | Multi-tenant with RLS enforced; partitioned tables for scale | Always on |
| **On-Premises** | Single-tenant; `tenant_id` still present for future cloud migration | Per deployment |

#### RLS Setup

```sql
-- Enable RLS on all tenant-owned tables
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices FORCE ROW LEVEL SECURITY;  -- Critical: owner connections are also filtered

CREATE POLICY tenant_isolation ON invoices
    USING (tenant_id = current_setting('app.tenant_id')::uuid);

-- Set tenant context at start of each transaction
BEGIN;
SET LOCAL app.tenant_id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11';
-- All queries in this transaction now see only this tenant's rows
COMMIT;
```

#### Indexing Strategy

Always lead indexes with `tenant_id` to enable partition pruning:

```sql
CREATE INDEX ON invoices (tenant_id, created_at DESC);
CREATE INDEX ON invoices (tenant_id, status, created_at DESC);
```

#### Partitioning (Large Tenants)

For Business/Cloud deployments, hash-partition by `tenant_id`:

```sql
CREATE TABLE invoices PARTITION BY HASH (tenant_id);
CREATE TABLE invoices_p0 PARTITION OF invoices FOR VALUES WITH (MODULUS 32, REMAINDER 0);
-- ... 32 partitions total
```

Each partition maintains its own statistics; the planner can prune at query time.

#### PgBouncer Compatibility

Use transaction pooling mode with explicit transactions:

```ini
pool_mode = transaction
server_reset_query = DISCARD ALL
```

Always wrap requests in explicit `BEGIN...COMMIT` — `SET LOCAL` persists only for the transaction.

---

## 6. Interface Design

### 6.1 CLI Interface (Human)

```bash
# Core commands
erp customers list --status=active
erp customers create --name="ACME Corp" --tax-id=12345678
erp invoices create --customer=ACME --items="10xWidget,5xGadget"
erp invoices list --status=pending --customer=ACME
erp inventory check --product=Widget
erp inventory reorder --below-threshold

# Admin commands
erp db migrate
erp db seed
erp config show
erp serve --port=8000
```

### 6.2 MCP Tools (Agent)

**Naming Convention:** `{domain}.{action}.{entity}`

```yaml
tools:
  - name: customers.list
    description: "List customers with optional filters. Returns paginated
                  results with cursor. Use when searching for customers
                  by name, tax ID, or status."
    inputSchema:
      type: object
      properties:
        status:
          type: string
          enum: [active, inactive, all]
          description: Filter by customer status
        limit:
          type: integer
          default: 50
          description: Maximum results (max 100)
        cursor:
          type: string
          description: Pagination cursor from previous response

  - name: customers.create
    description: "Create a new customer with Taiwan tax ID validation.
                  Tax ID must be 8 digits with valid check digit.
                  Idempotent - safe to retry."
    inputSchema:
      type: object
      properties:
        name: { type: string, description: "Company name" }
        tax_id: { type: string, pattern: "^[0-9]{8}$", description: "Taiwan tax ID" }
        email: { type: string, format: email }

  - name: invoices.create
    description: "Create Taiwan eGUI-compliant invoice. Validates tax
                  calculations, generates MIG 4.1 XML, and schedules
                  FIA submission within 48-hour window."
    inputSchema:
      type: object
      properties:
        customer_id: { type: string }
        items:
          type: array
          items:
            type: object
            properties:
              description: { type: string }
              quantity: { type: number }
              unit_price: { type: number }
              tax_rate: { type: string, enum: [5, 10, 0] }
        tax_included: { type: boolean, default: true }
      required: [customer_id, items]

  - name: invoices.list
    description: "List invoices with filters. Includes eGUI submission
                  status (draft, submitted, accepted, rejected)."

  - name: inventory.check
    description: "Check stock levels and reorder status. Returns
                  current quantity, reorder point, and supplier info."

  - name: inventory.adjust
    description: "Adjust stock levels. Triggers alerts if below
                  threshold. Idempotent with quantity delta."
```

### 6.3 REST API (GUI)

Standard REST endpoints for web GUI, following OpenAPI specification.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /customers | List customers |
| POST | /customers | Create customer |
| GET | /invoices | List invoices |
| POST | /invoices | Create invoice |
| GET | /inventory | List stock |
| PATCH | /inventory/{id} | Adjust stock |

---

## 7. Deployment Architecture

### 7.1 Desktop App (Tauri + Sidecar)

```
┌─────────────────────────────────────────────────────────────────┐
│  Tauri App Installer (~30-50MB)                                 │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Vite + React WebView                                     │ │
│  │  - Connects to localhost:8000                            │ │
│  │  - Or 192.168.x.x:8000 (LAN)                            │ │
│  │  - Or erp.company.com (cloud)                           │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Python Sidecar (FastAPI + MCP)                          │ │
│  │  - Spawned by Tauri on startup                           │ │
│  │  - Manages its own process lifecycle                     │ │
│  │  - localhost:8000                                         │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Server Deployment

```yaml
# docker-compose.yml for self-hosted server
services:
  api:
    build: ./api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/erp
      - REDIS_URL=redis://redis:6379
      - MINIO_ENDPOINT=minio:9000
    depends_on:
      - postgres
      - redis
      - minio

  postgres:
    image: postgres:17
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
```

### 7.3 Connection Modes

| User Size | Setup | Data Storage |
| --------- | ----- | ------------ |
| Solo | Tauri App + local sidecar | SQLite or local Postgres |
| Team | Tauri App + NAS server | NAS Postgres + Redis |
| Business | Tauri App + cloud VPS | Cloud Postgres + Redis |

---

## 8. AI Integration

> **Principle:** All financial and compliance decisions (invoice issuance, tax determination, stock movements, payment processing) are determined by **deterministic business logic**. AI assists humans with explanations, search, and drafting — it is never the authoritative source for transactional or compliance data.

### 8.1 Cloud AI (Claude API)

| Task | Use Case | Cost Model |
|------|----------|------------|
| Complex reasoning | Credit decisions (assist), strategy | Pay-per-token |
| Natural language | Query understanding | Pay-per-token |
| Document analysis | Invoice parsing, OCR | Pay-per-token |
| Drafting | Invoice notes, customer communications | Pay-per-token |

### 8.2 Self-Hosted AI (Future)

| Task | Technology | When |
|------|------------|------|
| Semantic search | pgvector | Privacy-sensitive |
| Simple Q&A | Ollama | Cost-sensitive |
| Document processing | Local models | Offline required |

### 8.3 pgvector Scope

**pgvector is a recommended extension, not a core requirement.** Base ERP operations work fully without it.

| Use Case | pgvector Required? |
|----------|-------------------|
| Transactional CRUD (invoices, orders, inventory) | No |
| Tax calculation and compliance | No |
| eGUI submission and tracking | No |
| Semantic document search (contracts, manuals, KB) | Yes |
| AI retrieval for skills/context building | Yes |
| Anomaly detection helpers | Optional |

> **Cloud vs. local:** pgvector is enabled by default in cloud-hosted deployments. In small local/NAS installs, it is optional and can be disabled for simplicity.

### 8.4 AI Retrieval Augmented Generation (RAG)

When AI assistance requires domain knowledge:

1. User or agent triggers a question (e.g., "What are the tax rules for exported services?")
2. Relevant skill files and reference docs are retrieved via semantic search
3. Claude receives the question + retrieved context
4. Response is grounded in the retrieved documents

RAG never bypasses deterministic business logic for compliance-critical decisions.

---

## 9. Security

### 9.1 Authentication

| User Type | Auth Method | Evidence |
| --------- | ----------- | -------- |
| Human (CLI) | Username + password + JWT | FastAPI best practice |
| Human (GUI) | OAuth 2.0 / session cookie | Standard |
| AI Agent | API key with scopes | MCP OAuth 2.1 |

### 9.2 Agent Authorization

```python
# Scoped API keys
API_KEY_SCOPES = [
    "customers:read",
    "customers:write",
    "invoices:read",
    "invoices:write",
    "inventory:read",
    "inventory:write",
    "admin",
]

# Per-tool authorization
@mcp.tool()
async def create_invoice(..., scopes: list[str] = ["invoices:write"]):
    if "invoices:write" not in scopes:
        raise PermissionError("Requires invoices:write scope")
```

### 9.3 MCP Security (from official best practices)

| Layer | Implementation |
|-------|---------------|
| Network | Local binding, firewall |
| Authentication | JWT or OAuth 2.1 |
| Authorization | Capability-based ACL |
| Input validation | JSON Schema enforcement |
| Audit logging | Every invocation logged |

### 9.4 Role-Based Access Control (RBAC)

| Role | customers | invoices | inventory | orders | payments | admin |
|------|-----------|----------|-----------|--------|----------|-------|
| **admin** | CRUD | CRUD | CRUD | CRUD | CRUD | Full |
| **finance** | Read | CRUD + void | — | Read | CRUD | — |
| **warehouse** | Read | — | CRUD | Read | — | — |
| **sales** | CRUD | Create | Read | CRUD | — | — |
| **agent** | Read | Read + create | Read | Read | — | — |

> **Note:** `—` denotes no access. Roles are composable; agents operating via MCP tools inherit the permissions of their assigned role.

### 9.5 Audit Logging

Every write operation via REST, MCP tool call, or CLI is logged to an immutable `audit_log` table:

```sql
CREATE TABLE audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    occurred_utc    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_type      VARCHAR(20) NOT NULL,  -- 'human' or 'agent'
    actor_id        VARCHAR(255) NOT NULL,  -- user ID or agent key ID
    tenant_id       UUID NOT NULL,
    action          VARCHAR(255) NOT NULL,  -- 'invoices.void', 'inventory.adjust', etc.
    target_entity   VARCHAR(255) NOT NULL, -- e.g., 'Invoice', 'Stock'
    target_id       UUID,
    before_state    JSONB,   -- Snapshot before change (where permitted)
    after_state     JSONB,   -- Snapshot after change
    correlation_id  UUID,    -- Links to outbox_events for workflow tracing
    mcp_call_id     VARCHAR(255),  -- MCP invocation ID if agent-initiated
    ip_address      INET,
    metadata        JSONB
);

-- Append-only: no UPDATE or DELETE allowed on this table
-- Enforce via DB-level trigger or policy
CREATE INDEX idx_audit_tenant_time ON audit_log (tenant_id, occurred_utc DESC);
CREATE INDEX idx_audit_correlation ON audit_log (correlation_id);
```

**Immutability:** The `audit_log` table is append-only. `UPDATE` and `DELETE` are blocked by a database-level trigger or RLS policy that only allows `INSERT`.

### 9.6 Approval Workflows for High-Risk Actions

Certain actions require human approval before execution. MCP tools and REST endpoints for these operations must request approval, not execute directly.

| Action | Trigger Condition | Approver Role |
|--------|-------------------|---------------|
| `invoices.void` | Same month | finance, admin |
| `invoices.void` | Different month | admin |
| `invoices.create` (backdated) | Invoice date < today − 1 day | finance |
| `inventory.adjust` | Quantity delta > threshold (configurable) | warehouse, admin |
| `payments.refund` | Amount > threshold | finance, admin |
| `customers.update` (credit limit) | New limit > previous × 1.5 | finance |

**Approval State Machine:**

```
PENDING_APPROVAL → APPROVED → executed
                → REJECTED  → not executed
                → EXPIRED   → not executed (timeout, e.g., 48hr)
```

### 9.7 Secrets Management

- FIA API credentials, API keys, and MCP tokens are stored in an encrypted secrets store (e.g., Vault, AWS Secrets Manager, or encrypted file with proper key management).
- Credentials are never logged or exposed in error messages.
- Rotation procedures are documented per credential type; automated rotation where supported.

---

## 10. Migration from Existing System

### 10.1 Keep (Production Validated)

| Component | Evidence |
|-----------|----------|
| PostgreSQL schema and data | Industry standard; ERPNext uses it |
| Taiwan eGUI compliance logic | MIG 4.1 requirements |
| Domain models (Customer, Invoice, Product) | Extensible |
| Business rules | Tested in production |

### 10.2 Remove (Technical Debt)

| Component | Reason |
|-----------|--------|
| LangChain / ChromaDB coupling | External AI agents replace internal AI |
| Dual authentication complexity | Simplified to JWT + API keys |
| Manual transaction anti-patterns | FastAPI dependency injection |
| Tight AI integration in domain | Separation of concerns |

### 10.3 Rebuild

| Component | Reference |
|-----------|-----------|
| MCP server layer | FastMCP 2.0 pattern |
| Skills directory | Anthropic skill authoring guide |
| Auth system | FastAPI best practices |
| Tauri desktop wrapper | example-tauri-v2-python-server-sidecar |
| Vite/React frontend | Standard React ecosystem |

---

## 11. Reference Architecture Summary

### 11.1 No 1:1 Match Exists

**Evidence:** Research confirms no open-source project combines FastAPI modular-monolith + MCP + Tauri + Taiwan eGUI.

This is on the frontier, but can compose proven pieces:

| Component | Reference | Credibility |
|-----------|-----------|-------------|
| Backend structure | modular-monolith-fastapi | Real GitHub repo |
| Tauri + Python sidecar | example-tauri-v2-python-server-sidecar | Real GitHub repo |
| Domain modeling | ERPNext | Production-proven ERP |
| MCP patterns | modelcontextprotocol/servers | Official |
| Skills packaging | anthropics/skills | 106k stars |

### 11.2 Modular Monolith Trend (2026)

**Evidence:** Multiple sources confirm modular monolith is the 2026 architectural pattern:

| Source | Quote |
|--------|-------|
| Medium (Nov 2025) | "Microservices Are Dead? The Rise of Modular Monoliths in 2025" |
| ThirdEye Data (Mar 2026) | "Modular Monolith: single deployable application internally organized into strict, domain-aligned modules" |
| Japanese Enterprises | "Where a modular monolith works well for AI" |

### 11.3 AI-Native ERP Trend (2026)

| Source | Quote |
|--------|-------|
| LinkedIn (Oct 2025) | "AI-Native by Design: The Modular ERP That Actually Works" |
| Ultra Consultants | "Composable ERP models, where functionality is delivered through modular components" |
| Pexa Works | "AI-first ERP enhances scalability by enabling modular, cloud-native designs" |

---

## 12. Implementation Phases

### Phase 1: Core Infrastructure (4-6 weeks)
- [ ] Clone `modular-monolith-fastapi` as reference
- [ ] Set up FastAPI with SQLAlchemy 2.0 async
- [ ] Configure PostgreSQL + Redis + MinIO
- [ ] Implement basic domain structure
- [ ] Set up Alembic migrations

### Phase 2: Domain Implementation (6-8 weeks)
- [ ] Customer domain (CRUD + Taiwan tax ID validation)
- [ ] Invoice domain (MIG 4.1 XML generation)
- [ ] Inventory domain (stock levels + reorder)
- [ ] Order domain (workflow + status)

### Phase 3: MCP + Skills (4-6 weeks)
- [ ] FastMCP 2.0 server setup
- [ ] MCP tool definitions per domain
- [ ] Claude Skills structure
- [ ] eGUI compliance skill

### Phase 4: Desktop App (4-6 weeks)
- [ ] Clone `example-tauri-v2-python-server-sidecar`
- [ ] Integrate with FastAPI backend
- [ ] Vite + React UI
- [ ] System integration (tray, notifications)

### Phase 5: Polish (2-4 weeks)
- [ ] Error handling
- [ ] Performance optimization
- [ ] Documentation
- [ ] Testing

**Total Estimated: 20-30 weeks**

---

## 13. Evidence Index

| Category | Source | URL |
|----------|--------|-----|
| FastAPI Modular Monolith | modular-monolith-fastapi | github.com/YoraiLevi/modular-monolith-fastapi |
| Tauri Python Sidecar | example-tauri-v2-python-server-sidecar | github.com/dieharders/example-tauri-v2-python-server-sidecar |
| FastAPI Best Practices | zhanymkanov/fastapi-best-practices | github.com/zhanymkanov/fastapi-best-practices |
| MCP Best Practices | modelcontextprotocol | modelcontextprotocol.info/docs/best-practices |
| Claude Skills Guide | Anthropic | resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf |
| ERPNext Architecture | Frappe | github.com/frappe/erpnext |
| Taiwan eGUI | MIG 4.1 | ecosio.com/en/blog/taiwan-einvoicing-explained |
| Taiwan eGUI API | Invoice Data Extraction | invoicedataextraction.com/blog/taiwan-e-invoice-api-integration |
| Tauri Desktop | Evil Martians | evilmartians.com/chronicles/making-desktop-apps-with-revved-up-potential-rust-tauri-sidecar |
| FastMCP | PrefectHQ | github.com/prefecthq/fastmcp |

---

**Status:** ✅ Research complete, architecture validated with evidence.

**Next Step:** Move to implementation planning (writing-plans skill)
