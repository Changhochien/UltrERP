---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
inputDocuments:
  - path: "docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md"
    type: "architecture"
  - path: "research/00-consolidation/whole-picture.md"
    type: "research-consolidation"
  - path: "research/00-consolidation/00-survey-consolidation.md"
    type: "survey-consolidation"
  - path: "research/legacy-data/01-survey-memo.md"
    type: "survey"
  - path: "research/tech-viability/01-survey-memo.md"
    type: "survey"
  - path: "research/egui-compliance/01-survey-memo.md"
    type: "survey"
  - path: "research/multi-agent-patterns/01-survey-memo.md"
    type: "survey"
  - path: "research/ui-ux/01-survey-memo.md"
    type: "survey"
workflowType: 'prd'
---

# UltrERP — Product Requirements Document

**Author:** Hcchang
**Date:** 2026-03-30

---

## Project Overview

**What we're building:** AI-native ERP system for Taiwan SMBs (聯泰興實業) serving both human users (via Tauri desktop GUI) and AI agents (via MCP) from a single codebase. The ERP exposes one shared business capability layer: AI agents consume it through MCP, while GUI and CLI clients use the same domain logic through typed application APIs.

**Deployment:** Hybrid topology — one codebase, switchable between solo (local sidecar + PostgreSQL) and team (central server + shared PostgreSQL) via config. MCP endpoint always present.

**Technology:** Tauri 2.x + Vite + React 19 + FastAPI + FastMCP 2.14.6 + PostgreSQL 17 + pgvector + Redis 7 + MinIO

**Key constraint:** Clean switch from legacy 鼎新-style ERP. Shadow-mode validation required before old system is retired.

**Project Type:** Desktop App + SaaS/B2B (hybrid)

**Domain:** ERP for Taiwan SMBs — invoice, inventory, payments, customers, orders

**Complexity:** High — ERP spans multiple business domains; eGUI-ready invoice lifecycle with deferred live submission activation; multi-tenancy; AI agent integration

**Project Context:** Brownfield migration from 聯泰興實業's legacy system; 94 tables, 1.1M rows; 0.09% orphan rate confirmed

**Transition strategy:** Clean break with shadow-mode validation. New system processes same transactions in parallel. Old system remains source of truth until new system proves correctness against a versioned reconciliation spec covering invoice totals/tax, payments, inventory movements, customer balances, and order status.

**eGUI strategy:** Invoice domain is designed around MIG 4.1 data shape and async eGUI states from day 1, but live FIA/eGUI submission is feature-flagged until credentials, filing obligation, and operator readiness are confirmed.

---

## Success Criteria

### User Success

| Moment | What success looks like |
|--------|------------------------|
| Morning check | Owner opens dashboard → sees today's sales, inventory alerts, website traffic — all in < 10 seconds |
| Invoice creation + print | Finance clerk creates invoice → tax auto-calculates → prints on pre-printed stationery → files copy |
| Stock check | Warehouse staff checks product availability via search — instant result |
| New customer order | Sales rep looks up customer, checks history, creates order — all in < 2 minutes |
| AI query | Owner asks Claude Code "What's our inventory for product X?" → structured response via MCP |

### Business Success

- **Revenue visibility:** Owner can answer "What did we sell today?" without calling 3 people
- **Inventory confidence:** Zero stockout incidents on top-20 products within 90 days of launch
- **Website → leads:** Posthog shows visitor-to-inquiry conversion rate improving by ≥20% within 3 months
- **AI search visibility:** Product/category content earns citations or brand mentions in AI-generated answers for 5+ tracked target queries within 6 months
- **User adoption:** 80% of staff complete daily dashboard check by Week 4
- **Shadow validation:** 30-day parallel run completes with zero unresolved severity-1 discrepancies under the reconciliation spec

### Technical Success

- Dashboard loads in < 2 seconds (p95)
- Inventory sync delay: ≤ 5 minutes
- Posthog events visible in dashboard: ≤ 10 minutes
- AEO metadata auto-generates on product create
- Zero data loss on legacy migration (523 orphan rows identified and resolved)

---

## Product Scope

### MVP — Priority Order

| Priority | Feature | Notes |
|----------|---------|-------|
| 1 | **Invoices** | Core ops — creation, tracking, voiding, printing |
| 2 | **Inventory** | Core ops — stock levels, adjustments, reorder alerts |
| 3 | **Payments** | Core ops — linked to invoices, reconciliation |
| 4 | **Customers** | Required FK for invoices + orders |
| 5 | **Orders** | Sales workflow |
| 6 | **Business heartbeat** | KPI dashboard — revenue, stock alerts, daily overview |
| 7 | **LINE** | Order notifications + customer order channel |
| 8 | **Posthog integration** | Website traffic → lead pipeline |
| 9 | **AEO (AI SEO)** | Structured data, product sitemaps, AI-readable descriptions |
| 10 | **Tauri desktop app** | Primary UI for all users |
| 11 | **MCP + Skills** | AI-native differentiation |

### Post-MVP — Phase 2

- AI-powered opportunity detection (business opportunity signals from Posthog + inventory)
- LINE Pay integration
- Mobile companion app

### Post-MVP — Phase 3

- Advanced reporting + forecasting
- Accounting software integration (export to Taiwan accounting software)
- Live FIA/eGUI submission activation (once credentials, filing obligation, and operator readiness are confirmed)

### Deferred

- Live FIA/eGUI transmission is off by default for the current non-retail workflow until credentials and filing obligation are confirmed
- MIG 4.1-ready invoice data model, status model, and submission pipeline are not deferred

---

## User Journeys

### Journey 1 — Morning Pulse Check

**Actor:** Owner/Manager

Owner opens the desktop app first thing in the morning. Dashboard loads in under 10 seconds showing: today's revenue vs. yesterday, top 3 selling products, low-stock alerts (if any), Posthog visitor count from yesterday.

Owner scans the screen, identifies one stock concern. Drills into inventory, sees reorder suggestion already populated. Moves on to the next task — all within 2 minutes.

---

### Journey 2 — Invoice Creation + Print

**Actor:** Finance Clerk

Finance clerk opens the invoice form to close a sale:

1. Searches for existing customer by 統一編號 or name
2. If new customer, creates customer record (current Taiwan business-number checksum validation on tax ID)
3. Adds 3 line items — product, quantity, unit price
4. Tax auto-calculates per line from the approved Taiwan tax policy (backend-owned TaxType and TaxRate mapping, not hardcoded UI rates)
5. Invoice total displays with tax breakdown
6. Previews invoice on screen — confirms layout matches pre-printed stationery
7. Hits print — prints on pre-printed stationery (A4/A5 format already established)
8. Files physical copy, hands invoice to customer
10. If eGUI is enabled for this tenant, invoice enters async status lifecycle with visible state badge and background notification support

---

### Journey 3 — Stock Check & Reorder

**Actor:** Warehouse Staff

Warehouse staff receives a stock inquiry. Searches product by code or name. System shows: current stock 12 units, reorder point 20 units, pending supplier order 50 units arriving in 3 days.

Staff marks item as "monitoring" status. 3 days later: supplier delivery arrives, inventory auto-updates by 50 units.

---

### Journey 4 — New Customer Order

**Actor:** Sales Rep

Sales rep receives a phone inquiry for wholesale order:

1. Checks if customer exists — searches by 統一編號 or company name
2. New customer: creates record with current Taiwan business-number checksum-validated tax ID, address, contact
3. Checks credit limit before confirming large order
4. Adds 5 product lines with quantities
5. System shows available stock for all items simultaneously
6. Creates order with 30-day payment terms
7. Order confirmed → invoice auto-generated

---

### Journey 5 — Ask via AI (MCP)

**Actor:** Owner/Manager using Claude Code

Owner opens terminal and asks: "What's our current inventory for product X?" Claude Code calls `inventory.check` via MCP endpoint. Receives structured response:

```
Product: X123
Stock: 47 units
Location: Warehouse A
Reorder point: 20
Last adjusted: 2026-03-28
Status: OK
```

Owner makes a sourcing decision without opening the desktop app or calling warehouse.

---

## User Types

| User Type | Role |
|-----------|------|
| Owner/Manager | Morning dashboard check, AI queries, strategic decisions |
| Finance Clerk | Invoice creation + printing, payment recording |
| Warehouse Staff | Stock checks, inventory adjustments, receiving |
| Sales Rep | Customer management, order creation |
| IT Admin | User management, system configuration |
| AI Agent | MCP consumer via Claude Code or other AI tools |

---

## Domain-Specific Requirements

### Taiwan Regulatory Compliance

**Retention & Archival Baseline**
External validation indicates retention duties differ by artifact, so the product must support configurable retention policies instead of hardcoding a single 15-year legal assumption.

Validated baseline:
- 電子發票同意訊息與相關佐證文件 (eGUI consent/supporting records): at least 5 years
- 財政部平台查詢/存證可用性 (MOF platform availability): plan around 7+1 years and do not treat the platform as the archive of record
- 帳簿與核心財務紀錄 (accounting books and core financial records): at least 10 years
- Company policy may choose longer retention (for example 15 years), but that is a policy setting, not the product's sole compliance assumption

Implications:
- Invoice records remain immutable after creation (no edits, only voids)
- Issuer-side invoice artifacts are stored durably and exportably (PostgreSQL + MinIO) independent of MOF platform retention windows
- Retention policy is configurable by record class and validated in backup/restore strategy for 10+ year access

**Tax Rates**

| Rate | Applies To |
|------|------------|
| 5% | Standard business tax — general goods and services (一般稅率) |
| 10% | Specialized industries — banking, insurance, securities, trust investment (特種稅率) |
| 0% | Eligible exports and specific transactions |

System must support per-line tax rate assignment. Default rate: 5%.

**統一編號 (Tax ID) Validation**
All B2B customers require 統一編號 — 8 digits validated by the current Taiwan business-number checksum guidance. System validates on customer create/update.

### Technical Constraints

- **Invoice immutability:** Invoices cannot be modified after creation. Corrections use void + new invoice only.
- **Void restriction:** Void/reissue is allowed only within the regulatory filing window, normally the same tax period and no later than the 13th day of the first month of the next period.
- **Audit trail:** All invoice state changes logged with actor, timestamp, and reason.
- **eGUI readiness:** Invoice domain and UI must support draft/submitted/issued/voided lifecycle from day 1 even if live FIA transmission is feature-flagged off.
- **Counterparty evidence retention:** Void/return/discount consent messages and related supporting documents must be retained according to the applicable record-class policy.
- **Print fidelity:** Invoice print output must match established pre-printed stationery layout exactly.

---

## Innovation & Novel Patterns

### 1. MCP + Skills + CLI Combined Architecture

MCP gives AI agents *access* to ERP operations. Skills give AI agents *domain knowledge* (Taiwan tax rates, eGUI workflows, reorder logic). CLI gives humans a direct command interface.

Pattern: *"MCP for discovery, Skills for execution, CLI for humans."*

### 2. ERP-as-MCP-Server

The ERP is not just "an app with an AI feature" — the business logic lives in one shared domain layer. MCP is the canonical agent surface, while the Tauri GUI and CLI use the same underlying services through typed application APIs.

### 3. AEO (AI Search Engine Optimization)

Structuring product data to be discoverable by AI search engines (Perplexity, ChatGPT search) when potential B2B customers ask for product recommendations.

### Architecture Layers

```
erp-skills/
  SKILL.md                          ← Entry point
  taiwan-tax/SKILL.md               ← 5%/10%/0% rates, Taiwan business-number checksum guidance, configurable retention
  inventory/SKILL.md                ← Reorder thresholds, stock adjustment workflow
  invoices/SKILL.md                 ← Void rules, same-month policy, print layout

erp-mcp/ (FastMCP 2.14.6)          ← Tools: inventory.*, invoices.*, customers.*
erp-cli/ (Typer CLI)                ← `erp invoices list`, `erp inventory check`

ERP backend (FastAPI)               ← Shared business logic
```

### Validation & Risk

- **MCP + Skills:** PoC in tech-viability sprint (multi-agent-patterns/ confirmed working)
- **AEO:** Baseline keyword rankings established before launch; recheck at 3 and 6 months
- **Shadow-mode migration:** 30-day parallel run with discrepancy alerts
- **If MCP proves too complex:** fallback to CLI-only for Phase 1, add MCP post-MVP
- **If AEO rankings don't improve:** focus on Posthog conversion metrics instead

---

## Platform & Integration Requirements

### Platform Requirements

- **Cross-platform:** Tauri 2.x — Windows and macOS
- **Auto-update:** Tauri updater (systemd or manual install for server)
- **Offline:** Solo mode works offline via local PostgreSQL
- **System integration:** Print (pre-printed stationery), file system (PDF export, backup)

### Multi-Tenancy Model

| Mode | RLS | Connection | Use Case |
|------|-----|-----------|----------|
| Solo | Off | Single | Personal use |
| Team | Off | Shared pool | Small teams, trust-based |
| Business | On | Pooled + RLS | Customer-facing SaaS (future) |

Solo and Team modes do not require RLS (tenant_id present for future migration).

### RBAC Matrix

| Role | Invoices | Inventory | Payments | Customers | Orders | Admin |
|------|----------|-----------|----------|----------|--------|-------|
| Owner/Admin | CRUD | CRUD | CRUD | CRUD | CRUD | Full |
| Finance | CRUD+void | — | CRUD | R | — | — |
| Warehouse | — | CRUD | — | — | R | — |
| Sales | R | R | — | CRUD | CRUD | — |

Roles enforced in UI. API key scopes enforced for MCP/CLI access.

### Integrations

| System | Purpose | MVP Priority |
|--------|---------|-------------|
| Posthog | Website analytics → lead pipeline | High |
| MinIO | Invoice XML archives, file attachments | High |
| LINE | Order notifications + customer order channel | High |

LINE integration scope:
- Order notifications to staff via LINE Notify/Messaging API
- Customer can submit orders via LINE BOT (text-based, auto-parsed into Orders module)
- LINE Pay consideration for future (not MVP)

---

## Functional Requirements

### Invoices

- FR1: Finance clerk can create an invoice with line items, auto-calculated tax, and customer reference
- FR2: System auto-calculates tax per line from approved Taiwan tax policy
- FR3: Finance clerk can void an invoice within the allowed regulatory window
- FR4: System validates invoice totals before print
- FR5: Finance clerk can print invoice to pre-printed stationery
- FR6: System allocates invoice numbers from configured government-issued ranges

### Inventory

- FR7: Warehouse staff can search products by code or name
- FR8: System displays current stock level and reorder point per product
- FR9: System generates reorder alerts when stock falls below reorder point
- FR10: Warehouse staff can record stock adjustments with reason codes
- FR11: System tracks supplier orders and auto-updates stock on receipt
- FR12: System supports multiple warehouse locations

### Payments

- FR13: Finance clerk can record payments against invoices
- FR14: System auto-matches payments to open invoices (reconciliation)
- FR15: System displays outstanding payment status per invoice

### Customers

- FR16: Sales rep can search for existing customers by 統一編號 or name
- FR17: System validates 統一編號 using the current Taiwan business-number checksum guidance on customer create/update
- FR18: Sales rep can create new customer with tax ID, address, contact, credit limit
- FR19: System flags duplicate 統一編號 on customer create

### Orders

- FR20: Sales rep can create an order linked to a customer
- FR21: System checks and displays stock availability for all order line items
- FR22: Sales rep can set payment terms on an order (e.g., 30 days)
- FR23: System auto-generates invoice from confirmed order
- FR24: Sales rep can update order status (pending → confirmed → shipped → fulfilled)

### Dashboard

- FR25: Owner can view morning dashboard with today's revenue vs. yesterday
- FR26: Owner can view top selling products by day/week
- FR27: Owner can view low-stock alerts on dashboard
- FR28: Owner can view Posthog visitor count from previous day

### AI Interface (MCP + Skills)

- FR29: AI agents can query inventory levels via MCP tools
- FR30: AI agents can query customer data via MCP tools
- FR31: AI agents can query invoice data via MCP tools
- FR32: Claude Code can use Taiwan tax domain knowledge from Skills files
- FR33: MCP tools support role-scoped authentication; interactive use requires audience-validated tokens and controlled automation may use scoped API keys

### LINE Integration

- FR34: Staff receive LINE notification when new order is created
- FR35: Customers can submit orders via LINE BOT (text parsed into Orders module)
- FR36: System confirms order receipt via LINE to customer

### Posthog Integration

- FR37: Posthog tracks website visitor sessions
- FR38: Posthog tracks goal conversions (visitor → inquiry)
- FR39: Posthog data visible in dashboard within 10 minutes

### AEO (AI SEO)

- FR40: System auto-generates structured data (JSON-LD) for products on create
- FR41: System auto-generates XML sitemap for all products
- FR42: Product content is structured to maximize citation/mention visibility in AI-generated answers, not only traditional page rankings

### User Management

- FR43: Admin can create users with roles (Owner, Finance, Warehouse, Sales)
- FR44: System enforces RBAC in UI (role-based menu/feature access)
- FR45: System enforces RBAC and auth scopes consistently across UI, API, MCP, and CLI surfaces

### Print & Export

- FR46: Finance clerk can preview invoice before print (matches pre-printed stationery)
- FR47: System can export invoice to PDF

### Storage & Retention

- FR48: System stores issuer-side invoice artifacts in MinIO/object storage without depending on MOF platform retention windows
- FR49: System stores file attachments in MinIO

### Desktop UX & Operational Safety

- FR50: Customer and inventory lists support virtualization and/or pagination for 5,000+ rows without visible stutter on target hardware
- FR51: Power users can access primary screens and actions through global keyboard shortcuts plus a screen-local shortcut overlay
- FR52: If eGUI is enabled, invoice screen shows async status badge, deadline awareness, manual refresh, and persisted state across app restarts
- FR53: Desktop app can run in system tray and send notifications for async invoice/eGUI state changes while the main window is closed
- FR54: Sensitive write actions triggered through AI or automation require explicit human confirmation before execution
- FR55: Shadow-mode comparison uses a separately versioned reconciliation spec and produces actionable discrepancy alerts

---

## Non-Functional Requirements

### Performance

- Dashboard loads in < 2 seconds (p95)
- Inventory sync delay: ≤ 5 minutes
- Posthog events visible in dashboard: ≤ 10 minutes
- AI agent query response via MCP: < 1 second (p95)
- Print preview surface renders in < 1 second on target hardware, excluding OS print-dialog and PDF-pipeline startup time
- Customer and inventory screens remain responsive at 5,000+ rows through virtualization and/or pagination

### Usability & Desktop Operation

- Primary daily workflows are keyboard-accessible for power users and discoverable via shortcut overlay
- Async invoice/eGUI states remain visible and recoverable after app restart
- Background tray mode and notifications are available when async invoice tracking is enabled

### Security

- All data encrypted at rest (PostgreSQL encryption) and in transit (TLS 1.3)
- Interactive human and agent access uses role-scoped tokens with audience validation; scoped API keys are limited to controlled automation contexts
- Sensitive write actions require explicit human-in-the-loop confirmation before execution
- Audit log records all invoice state changes, inventory adjustments, and user actions
- RBAC enforced in both UI and API layers
- Retention policy is enforced by record class and issuer-side archival does not depend on MOF platform retention windows

### Scalability

- Solo mode: single user, single database connection
- Team mode: supports 2-50 concurrent users
- Database connection pool: 20 connections + 10 overflow (asyncpg + PgBouncer)
- MCP session-mode HTTP supports concurrent agent connections

### Reliability

- Shadow-mode validation: new system processes same transactions as old system during transition using a versioned reconciliation spec
- All invoice records immutable after creation (void only, no edits)
- Database backup strategy must support policy-based 10+ year retention with optional longer company-policy retention
- eGUI-ready outbox/state pipeline provides durability when live FIA/eGUI submission is enabled

### Integration

- Posthog: visitor tracking, goal conversion, dashboard integration
- MinIO: invoice XML archives, file attachments (S3-compatible)
- LINE: Notify/Messaging API for order notifications; BOT for customer orders
- PostgreSQL 17: primary data store with pgvector for semantic search
- Redis 7: session cache, rate limiting, job queue

### Data Architecture

- PostgreSQL for both solo and team modes (no SQLite)
- asyncpg with `statement_cache_size=0` for PgBouncer compatibility
- tenant_id present in all tables for future multi-tenant migration
