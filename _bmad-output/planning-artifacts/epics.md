stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - path: "_bmad-output/planning-artifacts/prd.md"
    type: "prd"
  - path: "docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md"
    type: "architecture"
  - path: "docs/legacy/migration-plan.md"
    type: "legacy-migration-plan"
  - path: "research/legacy-data/03-findings.md"
    type: "legacy-poc-findings"
---

# UltrERP - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for UltrERP, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

**Invoices:**
- FR1: Finance clerk can create an invoice with line items, auto-calculated tax, and customer reference
- FR2: System auto-calculates tax per line from approved Taiwan tax policy
- FR3: Finance clerk can void an invoice within the allowed regulatory window
- FR4: System validates invoice totals before print
- FR5: Finance clerk can print invoice to pre-printed stationery
- FR6: System allocates invoice numbers from configured government-issued ranges

**Inventory:**
- FR7: Warehouse staff can search products by code or name
- FR8: System displays current stock level and reorder point per product
- FR9: System generates reorder alerts when stock falls below reorder point
- FR10: Warehouse staff can record stock adjustments with reason codes
- FR11: System tracks supplier orders and auto-updates stock on receipt
- FR12: System supports multiple warehouse locations

**Payments:**
- FR13: Finance clerk can record payments against invoices
- FR14: System auto-matches payments to open invoices (reconciliation)
- FR15: System displays outstanding payment status per invoice

**Customers:**
- FR16: Sales rep can search for existing customers by 統一編號 or name
- FR17: System validates Taiwan business-number checksum rules on customer create/update
- FR18: Sales rep can create new customer with tax ID, address, contact, credit limit
- FR19: System flags duplicate 統一編號 on customer create

**Orders:**
- FR20: Sales rep can create an order linked to a customer
- FR21: System checks and displays stock availability for all order line items
- FR22: Sales rep can set payment terms on an order (e.g., 30 days)
- FR23: System auto-generates invoice from confirmed order
- FR24: Sales rep can update order status (pending → confirmed → shipped → fulfilled)

**Dashboard:**
- FR25: Owner can view morning dashboard with today's revenue vs. yesterday
- FR26: Owner can view top selling products by day/week
- FR27: Owner can view low-stock alerts on dashboard
- FR28: Owner can view Posthog visitor count from previous day

**AI Interface (MCP + Skills):**
- FR29: AI agents can query inventory levels via MCP tools
- FR30: AI agents can query customer data via MCP tools
- FR31: AI agents can query invoice data via MCP tools
- FR32: Claude Code can use Taiwan tax domain knowledge from Skills files
- FR33: MCP tools support role-scoped authentication; interactive use requires audience-validated tokens and controlled automation may use scoped API keys

**LINE Integration:**
- FR34: Staff receive LINE notification when new order is created
- FR35: Customers can submit orders via LINE BOT (text parsed into Orders module)
- FR36: System confirms order receipt via LINE to customer

**Posthog Integration:**
- FR37: Posthog tracks website visitor sessions
- FR38: Posthog tracks goal conversions (visitor → inquiry)
- FR39: Posthog data visible in dashboard within 10 minutes

**AEO (AI SEO):**
- FR40: System auto-generates structured data (JSON-LD) for products on create
- FR41: System auto-generates XML sitemap for all products
- FR42: Product content is structured to maximize citation/mention visibility in AI-generated answers

**User Management:**
- FR43: Admin can create users with roles (Owner, Finance, Warehouse, Sales)
- FR44: System enforces RBAC in UI (role-based menu/feature access)
- FR45: System enforces RBAC and auth scopes consistently across UI, API, MCP, and CLI surfaces

**Print & Export:**
- FR46: Finance clerk can preview invoice before print (matches pre-printed stationery)
- FR47: System can export invoice to PDF

**Storage & Retention:**
- FR48: System stores issuer-side invoice artifacts in MinIO/object storage without depending on MOF platform retention windows
- FR49: System stores file attachments in MinIO

**Desktop UX & Operational Safety:**
- FR50: Customer and inventory lists support virtualization and/or pagination for 5,000+ rows without visible stutter on target hardware
- FR51: Power users can access primary screens and actions through global keyboard shortcuts plus a screen-local shortcut overlay
- FR52: If eGUI is enabled, invoice screen shows async status badge, deadline awareness, manual refresh, and persisted state across app restarts
- FR53: Desktop app can run in system tray and send notifications for async invoice/eGUI state changes while the main window is closed
- FR54: Sensitive write actions triggered through AI or automation require explicit human confirmation before execution
- FR55: Shadow-mode comparison uses a separately versioned reconciliation spec and produces actionable discrepancy alerts

**Legacy Import & Cutover Readiness:**
- FR56: Admin can bulk-load extracted legacy ERP tables into a read-only `raw_legacy` staging schema without altering the source exports
- FR57: System normalizes ROC dates, sentinel dates, and core master data into canonical import-ready values during migration
- FR58: System resolves legacy product-code variants through an explicit mapping table and preserves unresolved rows via `UNKNOWN` fallback instead of dropping transactions
- FR59: Admin can import historical parties, products, warehouses, inventory, sales, and purchase data into UltrERP with source lineage preserved
- FR60: System generates import validation, orphan, and discrepancy reports after each migration run
- FR61: Admin can rerun a migration batch idempotently for a defined tenant and cutoff window without duplicating canonical records
- FR62: Operators and AI agents can invoke the reviewed legacy-import workflow through a stable CLI surface and a task-specific skill that wraps it safely

### NonFunctional Requirements

**Performance:**
- NFR1: Dashboard loads in < 2 seconds (p95)
- NFR2: Inventory sync delay: ≤ 5 minutes
- NFR3: Posthog events visible in dashboard: ≤ 10 minutes
- NFR4: AI agent query response via MCP: < 1 second (p95)
- NFR5: Print preview renders in < 1 second
- NFR6: Customer and inventory screens remain responsive at 5,000+ rows through virtualization and/or pagination

**Usability & Desktop Operation:**
- NFR7: Primary daily workflows are keyboard-accessible for power users and discoverable via shortcut overlay
- NFR8: Async invoice/eGUI states remain visible and recoverable after app restart
- NFR9: Background tray mode and notifications are available when async invoice tracking is enabled

**Security:**
- NFR10: All data encrypted at rest (PostgreSQL encryption) and in transit (TLS 1.3)
- NFR11: Interactive human and agent access uses role-scoped tokens with audience validation; scoped API keys are limited to controlled automation contexts
- NFR12: Sensitive write actions require explicit human-in-the-loop confirmation before execution
- NFR13: Audit log records all invoice state changes, inventory adjustments, and user actions
- NFR14: RBAC enforced in both UI and API layers
- NFR15: Retention policy is enforced by record class and issuer-side archival does not depend on MOF platform retention windows

**Scalability:**
- NFR16: Solo mode: single user, single database connection
- NFR17: Team mode: supports 2-50 concurrent users
- NFR18: Database connection pool: 20 connections + 10 overflow (asyncpg + PgBouncer)
- NFR19: MCP session-mode HTTP supports concurrent agent connections

**Reliability:**
- NFR20: Shadow-mode validation: new system processes same transactions as old system during transition using a versioned reconciliation spec
- NFR21: All invoice records immutable after creation (void only, no edits)
- NFR22: Database backup strategy must support policy-based 10+ year retention with optional longer company-policy retention
- NFR23: eGUI-ready outbox/state pipeline provides durability when live FIA/eGUI submission is enabled

**Integration:**
- NFR24: Posthog: visitor tracking, goal conversion, dashboard integration
- NFR25: MinIO: invoice XML archives, file attachments (S3-compatible)
- NFR26: LINE: Notify/Messaging API for order notifications; BOT for customer orders
- NFR27: PostgreSQL 17: primary data store with pgvector for semantic search
- NFR28: Redis 7: session cache, rate limiting, job queue

**Data Architecture:**
- NFR29: PostgreSQL for both solo and team modes (no SQLite)
- NFR30: asyncpg with statement_cache_size=0 for PgBouncer compatibility
- NFR31: tenant_id present in all tables for future multi-tenant migration

**Migration Reliability:**
- NFR32: Bulk legacy staging import completes within an operator-acceptable window on target hardware by using PostgreSQL-native bulk loading rather than row-by-row inserts
- NFR33: Every imported canonical record preserves source lineage metadata sufficient for audit, replay, and discrepancy investigation
- NFR34: Migration runs are idempotent and resumable at batch scope without creating duplicate canonical records
- NFR35: Unresolved severity-1 migration discrepancies block cutover and produce operator-readable reports
- NFR36: Agent-invoked migration steps are constrained to reviewed CLI commands and require explicit confirmation for destructive or high-impact import scopes

### Additional Requirements

From Architecture Document:

**Project Foundation:**
- AR1: pnpm 9 for the root Vite frontend workspace (source in `src/`), UV for backend Python dependencies under `backend/`
- AR2: PostgreSQL 17 is the day-one local prerequisite; Redis 7 and MinIO are introduced for team-mode and integration workflows and may be provisioned locally with Docker Compose or equivalent tooling
- AR3: GitHub Actions CI/CD pipeline (lint → test → build)
- AR4: Alembic for database migrations
- AR5: rclone + Cloudflare R2 for cloud backups (pg_dump daily, 10+ year retention)
- AR6: FastAPI modular monolith pattern with sub-apps at /api/v1/{domain}
- AR7: FastMCP 2.14.6 integration with session-mode HTTP transport (NOT stateless_http)
- AR8: asyncpg with statement_cache_size=0 for PgBouncer compatibility
- AR9: Shadow-mode reconciliation system (versioned reconciliation spec, discrepancy alerts)
- AR10: Audit log table capturing actor_type, action, before/after state, correlation_id
- AR11: Outbox/Inbox pattern for durable async operations (eGUI, FIA submissions)
- AR12: Tauri 2.x spawns Python sidecar via CARGO_MANIFEST_DIR for solo mode
- AR13: tenant_id in all tables, SET LOCAL for session context
- AR14: API versioning at /api/v1/* path level

**Legacy Import Investigation:**
- AR15: Legacy import reads from exported CSV assets or SQL-dump-derived extracts only; the legacy source remains strictly read-only
- AR16: Raw import lands in PostgreSQL `raw_legacy` staging tables first and uses bulk-loading plus lineage columns (`_legacy_table`, `_legacy_pk`, batch/run identifiers, import status)
- AR17: Migration schema changes and canonical writes follow the repo's Alembic/SQLAlchemy/PostgreSQL conventions; the PoC `psycopg2` scripts remain reference material, not the production implementation surface
- AR18: Product-code resolution uses `raw_legacy.product_code_mapping` plus analyst-reviewed mappings and an `UNKNOWN` placeholder to preserve unresolved transactions without inventing false certainty
- AR19: `1900-01-01` is treated as a legacy empty-date sentinel and ROC dates are normalized to AD before canonical import
- AR20: Severity-1 migration discrepancies block cutover; severity-2 issues remain reportable and auditable during shadow-mode
- AR21: The reusable import entry point is a CLI-first workflow under the backend codebase, while the agent-facing skill lives in a supported skills directory and references the CLI/resources instead of embedding business logic in markdown alone

### UX Design Requirements

(No UX document found - this section will be populated if/when UX design is created)

## Epic List

### Epic 1: Project Foundation
Establish a production-ready project foundation aligned to the approved hybrid architecture: root Vite/React frontend, modular FastAPI backend under `backend/`, versioned APIs, CI/CD, migrations, and durable backups.
**FRs covered:** AR1-AR14 (technical requirements)

### Epic 2: Invoice Lifecycle
Finance clerks can create, print, and void invoices with automatic tax calculation and MIG 4.1 compliance.
**FRs covered:** FR1-FR6, FR46-FR47, FR48-FR49, NFR21

### Epic 3: Customer Management
Sales reps can find, create, and update customers with validated Taiwan business numbers (統一編號).
**FRs covered:** FR16-FR19

### Epic 4: Inventory Operations
Warehouse staff can track stock levels, receive reorder alerts, and manage supplier deliveries.
**FRs covered:** FR7-FR12

### Epic 5: Order to Cash
Sales reps can create orders, check stock availability, and have invoices auto-generated.
**FRs covered:** FR20-FR24

### Epic 6: Payment Handling
Finance can record payments against invoices with automatic reconciliation.
**FRs covered:** FR13-FR15

### Epic 7: Business Dashboard
Owners can view morning KPIs: revenue, top products, stock alerts, and Posthog visitor data.
**FRs covered:** FR25-FR28, FR39

### Epic 8: AI Agent Interface
AI agents (Claude Code, etc.) can query ERP data via MCP with Taiwan tax domain knowledge.
**FRs covered:** FR29-FR33, NFR4

### Epic 9: LINE Integration
Staff receive LINE notifications for new orders; customers can submit orders via LINE BOT.
**FRs covered:** FR34-FR36

### Epic 10: AEO (AI SEO)
Products are structured for discoverability in AI-generated search answers.
**FRs covered:** FR40-FR42

### Epic 11: User & Access Management
Admins can manage users with role-based access control across all surfaces (UI, API, MCP, CLI).
**FRs covered:** FR43-FR45, NFR10-NFR15, NFR18

### Epic 12: Desktop Shell & Tray
Users can run the app from system tray with keyboard shortcuts and background notifications.
**FRs covered:** FR50-FR54, NFR5-NFR9

### Epic 13: Shadow-Mode Validation
System validates correctness against legacy ERP during parallel run before cutover.
**FRs covered:** FR55, NFR20, NFR22

### Epic 14: Traditional Chinese i18n (Duolanguage Support)
Provides Traditional Chinese language support throughout the application with dynamic language switching.
**FRs covered:** FR37-FR38, NFR16-NFR17

### Epic 15: Legacy Data Import Pipeline
Operations and AI agents can stage, map, import, and validate legacy ERP data into UltrERP through a repeatable CLI-backed workflow plus a task-specific skill that preserves lineage and exposes unresolved data-quality issues instead of hiding them.
**FRs covered:** FR56-FR62, NFR32-NFR36, AR15-AR21

### Epic 16: Extended Legacy Import — Purchase Transactions and Payments
Operations and AI agents can stage, normalize, map, import, and validate extended legacy ERP purchase data (purchase invoices, purchase orders, and payment records) into UltrERP through the same repeatable CLI-backed workflow used for Epic 15, adding coverage for the purchase side of the business and completing the financial transaction picture alongside the already-imported sales data.
**FRs covered:** FR63-FR69

### Epic 17: TBD
Planned - no content yet in this file.

### Epic 18: Legacy Inventory Receiving Audit Trail
Complete the inventory audit trail for all historical goods received before UltrERP deployment by creating `StockAdjustment(SUPPLIER_DELIVERY)` records from legacy purchase invoice data, filling the gap left by the legacy system's snapshot-only inventory model.
**FRs covered:** (see epic-18.md for full story list)

### Epic 19: Customer Product Intelligence
Enable AI agents and sales staff to understand what customers are buying, how purchasing behavior is changing, and where market opportunities exist — so agents can prospect intelligently and staff can manage accounts proactively.
**FRs covered:** (see epic-19.md for full story list)

### Epic 20: Product Sales Analytics
Provide multi-dimensional sales analytics covering revenue diagnosis, inventory planning, product performance, and customer buying behavior — with accurate historical attribution via product snapshots on order lines, SCD Type 2 product dimension, and pre-computed monthly aggregation tables.
**FRs covered:** (see epic-20.md for full story list)


---

## FR Coverage Map

FR1: Epic 2 - Invoice creation with line items and customer reference
FR2: Epic 2 - Tax auto-calculation per line from approved policy
FR3: Epic 2 - Void invoice within regulatory window
FR4: Epic 2 - Validate invoice totals before print
FR5: Epic 2 - Print invoice to pre-printed stationery
FR6: Epic 2 - Allocate invoice numbers from configured ranges
FR7: Epic 4 - Search products by code or name
FR8: Epic 4 - Display stock level and reorder point
FR9: Epic 4 - Generate reorder alerts when below reorder point
FR10: Epic 4 - Record stock adjustments with reason codes
FR11: Epic 4 - Track supplier orders and auto-update stock
FR12: Epic 4 - Support multiple warehouse locations
FR13: Epic 6 - Record payments against invoices
FR14: Epic 6 - Auto-match payments to open invoices
FR15: Epic 6 - Display outstanding payment status
FR16: Epic 3 - Search customers by 統一編號 or name
FR17: Epic 3 - Validate Taiwan business-number checksum rules
FR18: Epic 3 - Create customer with tax ID, address, contact, credit limit
FR19: Epic 3 - Flag duplicate 統一編號 on create
FR20: Epic 5 - Create order linked to customer
FR21: Epic 5 - Check stock availability for order items
FR22: Epic 5 - Set payment terms on order
FR23: Epic 5 - Auto-generate invoice from confirmed order
FR24: Epic 5 - Update order status (pending → confirmed → shipped → fulfilled)
FR25: Epic 7 - Morning dashboard with revenue vs. yesterday
FR26: Epic 7 - View top selling products by day/week
FR27: Epic 7 - View low-stock alerts
FR28: Epic 7 - View Posthog visitor count
FR29: Epic 8 - AI agents query inventory via MCP
FR30: Epic 8 - AI agents query customers via MCP
FR31: Epic 8 - AI agents query invoices via MCP
FR32: Epic 8 - Claude Code uses Taiwan tax domain knowledge
FR33: Epic 8 - MCP supports role-scoped authentication
FR34: Epic 9 - Staff receive LINE notification on new order
FR35: Epic 9 - Customers submit orders via LINE BOT
FR36: Epic 9 - Confirm order receipt via LINE
FR37: Epic 7 - Posthog tracks website visitor sessions
FR38: Epic 7 - Posthog tracks goal conversions
FR39: Epic 7 - Posthog data visible in dashboard within 10 minutes
FR40: Epic 10 - Auto-generate JSON-LD structured data for products
FR41: Epic 10 - Auto-generate XML sitemap for products
FR42: Epic 10 - Structure product content for AI citation
FR43: Epic 11 - Admin creates users with roles
FR44: Epic 11 - Enforce RBAC in UI
FR45: Epic 11 - Enforce RBAC consistently across all surfaces
FR46: Epic 2 - Preview invoice before print
FR47: Epic 2 - Export invoice to PDF
FR48: Epic 2 - Store invoice artifacts in MinIO
FR49: Epic 2 - Store file attachments in MinIO
FR50: Epic 12 - Virtualized lists for 5,000+ rows
FR51: Epic 12 - Keyboard shortcuts and shortcut overlay
FR52: Epic 12 - eGUI status badge and state persistence
FR53: Epic 12 - System tray mode with notifications
FR54: Epic 11 - Human confirmation for AI/automation writes
FR55: Epic 13 - Shadow-mode reconciliation with discrepancy alerts
FR56: Epic 15 - Bulk-load extracted legacy data into raw_legacy staging
FR57: Epic 15 - Normalize ROC dates, sentinel dates, and master data for import
FR58: Epic 15 - Resolve product variants through mapping table and UNKNOWN fallback
FR59: Epic 15 - Import parties, products, warehouses, inventory, and transactions with source lineage
FR60: Epic 15 - Generate migration validation, orphan, and discrepancy reports
FR61: Epic 15 - Rerun migration batches idempotently without duplicate canonical records
FR62: Epic 15 - Expose the migration workflow through a stable CLI and agent-usable skill
FR63: Epic 16 - Stage purchase invoice headers (tbsslipj) and line items (tbsslipdtj) into raw_legacy
FR64: Epic 16 - Normalize purchase master data (suppliers as parties, ROC dates, product refs)
FR65: Epic 16 - Stage purchase order headers (tbsslipo) into raw_legacy
FR66: Epic 16 - Import canonical purchase orders and order lines from normalized staging data
FR67: Epic 16 - Import canonical purchase invoice headers and lines from normalized staging data
FR68: Epic 16 - Stage special payments (tbsspay) and prepayments (tbsprepay) into raw_legacy
FR69: Epic 16 - Import currency settings from tbscurrency into app_settings
INTEL-001: Epic 19 - Product affinity map via MCP (co-occurrence analysis on order lines)
INTEL-002: Epic 19 - Category trend radar with period-over-period growth
INTEL-003: Epic 19 - Customer product profile (per-customer purchase breakdown)
INTEL-004: Epic 19 - Customer risk signals (dormant/at-risk/growing account flags)
INTEL-005: Epic 19 - Prospect gap analysis (customers not buying in a category)
INTEL-006: Epic 19 - Market opportunities signal feed (macro market signals)
INTEL-007: Epic 19 - Intelligence feature gate and MCP scope configuration
INTEL-008: Epic 19 - Backend test coverage for intelligence services


