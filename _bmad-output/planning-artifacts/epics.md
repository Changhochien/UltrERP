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

---

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

### Epic 15: Legacy Data Import Pipeline
Operations and AI agents can stage, map, import, and validate legacy ERP data into UltrERP through a repeatable CLI-backed workflow plus a task-specific skill that preserves lineage and exposes unresolved data-quality issues instead of hiding them.
**FRs covered:** FR56-FR62, NFR32-NFR36, AR15-AR21

### Epic 16: Extended Legacy Import — Purchase Transactions and Payments
Operations and AI agents can stage, normalize, map, import, and validate extended legacy ERP purchase data (purchase invoices, purchase orders, and payment records) into UltrERP through the same repeatable CLI-backed workflow used for Epic 15, adding coverage for the purchase side of the business and completing the financial transaction picture alongside the already-imported sales data.
**FRs covered:** FR63-FR69

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

---

## Epic 1: Project Foundation

### Epic Goal

Establish a production-ready project foundation aligned to the approved hybrid architecture: root Vite/React frontend, modular FastAPI backend under `backend/`, versioned APIs, CI/CD, migrations, and durable backups.

### Stories

### Story 1.1: Developer Environment Setup

As a developer,
I want to set up my development environment in under 10 minutes,
So that I can start coding immediately without configuration headaches.

**Acceptance Criteria:**

**Given** a fresh clone of the repository
**When** I follow the README setup instructions
**Then** I have pnpm 9, UV, and PostgreSQL 17 installed locally
**And** `pnpm --version` reports 9.x
**And** `uv --version` returns success
**And** PostgreSQL 17 is running and accessible on port 5432
**And** `pg_isready -h localhost -p 5432` returns success

### Story 1.2: Project Structure

As a developer,
I want a clear, consistent project structure,
So that I know where to put code and can navigate easily.

**Acceptance Criteria:**

**Given** the project structure is established
**When** I look at the codebase
**Then** frontend code is in `src/` with components/, pages/, domain/, hooks/, lib/ subdirectories
**And** backend code is in `backend/` with `app/`, `common/`, and `domains/` subdirectories
**And** migrations are in `migrations/`
**And** scripts are in `scripts/backup/` and `scripts/restore/`
**And** GitHub Actions workflows are in `.github/workflows/`
**And** empty directories have placeholder files where needed

### Story 1.3: CI/CD Pipeline

As a developer,
I want automated quality gates on every PR,
So that no broken code gets merged.

**Acceptance Criteria:**

**Given** a PR is opened
**When** CI pipeline runs
**Then** frontend job runs: lint → test → build
**And** backend job runs: ruff check → pytest
**And** both jobs must pass for merge
**And** failing checks block merge

### Story 1.4: Cloud Backup Strategy

As a developer/owner,
I want automated daily backups to cloud storage,
So that data is safe and recoverable for 10+ years.

**Acceptance Criteria:**

**Given** the backup scripts are in place
**When** `scripts/backup/pg-dump.sh` runs
**Then** it creates a compressed pg_dump file in `~/Library/Application Support/UltrERP/backups/`
**And** local temporary unencrypted backup artifacts older than 7 days are automatically removed
**And** encrypted archives are copied to Cloudflare R2 without deleting prior remote backups
**And** `scripts/restore/pg-restore.sh` can recover from a local or downloaded backup archive

### Story 1.5: FastAPI Backend Foundation

As a developer,
I want a working FastAPI backend with health check,
So that I can verify the API surface works before adding domain logic.

**Acceptance Criteria:**

**Given** the backend is set up
**When** I run `cd backend && uv run uvicorn app.main:app --reload`
**Then** the server starts on port 8000
**And** `curl localhost:8000/api/v1/health` returns `{"status": "ok"}`
**And** CORS is configured to allow localhost:5173

### Story 1.6: React Frontend Foundation

As a developer,
I want a working React frontend with Vite dev server,
So that I can see the UI and verify the frontend infrastructure.

**Acceptance Criteria:**

**Given** the frontend is set up
**When** I run `pnpm install` and then `pnpm dev`
**Then** Vite starts on port 5173
**And** loading localhost:5173 shows the app
**And** the app can make API calls to localhost:8000 through the proxy

### Story 1.7: Database Migrations Setup

As a developer,
I want Alembic configured for database migrations,
So that I can evolve the schema over time.

**Acceptance Criteria:**

**Given** migrations are configured
**When** I run `cd backend && uv run alembic -c ../migrations/alembic.ini upgrade head`
**Then** it connects to PostgreSQL and runs any pending migrations
**And** the database schema is created according to migration files

### Story 1.8: Legacy Data Analysis

As a developer,
I want to understand the legacy database structure,
So that I can plan the migration strategy.

**Acceptance Criteria:**

**Given** the legacy analysis artifacts are consolidated and reviewed
**When** I review the findings
**Then** I know the 94 tables and 1.1M rows structure
**And** I know the corrected orphan profile: 190 orphan codes affecting 523 rows (0.09%)
**And** I have a documented migration plan for shadow-mode validation

---

## Epic 2: Invoice Lifecycle

### Epic Goal

Finance clerks can create, print, and void invoices with automatic tax calculation and MIG 4.1 compliance.

### Stories

### Story 2.1: Create MIG-Ready Invoice Snapshot

As a finance clerk,
I want to create an invoice with multiple line items, customer reference, and automatic tax calculation,
So that I can quickly issue compliant invoices without manual math.

**Acceptance Criteria:**

**Given** a customer exists in the system
**When** I create a new invoice and add line items (product, quantity, unit price)
**Then** the system auto-calculates line-level TaxType, TaxRate, and tax amount from the approved backend-owned Taiwan tax policy
**And** displays the invoice total with tax breakdown
**And** allocates the next invoice number from the configured government-issued range in format `[A-Z]{2}\d{8}` (MIG 4.1)
**And** links the invoice to the customer

### Story 2.2: Preview and Print on Approved Stationery

As a finance clerk,
I want to preview and print invoices to pre-printed stationery,
So that the printed invoice matches our established A4/A5 format exactly.

**Acceptance Criteria:**

**Given** an invoice has been created
**When** I preview the invoice
**Then** the layout matches pre-printed stationery exactly
**And** the preview surface renders in < 1 second on target hardware
**When** I click print
**Then** the invoice prints correctly on pre-printed stationery

### Story 2.3: Void Invoice Before Filing Deadline

As a finance clerk,
I want to void an invoice within the allowed regulatory window,
So that I can correct mistakes while complying with Taiwan tax law.

**Acceptance Criteria:**

**Given** an invoice remains within the allowed void window
**When** I void the invoice
**Then** the invoice status changes to "voided"
**And** replacement linkage is recorded for the follow-up invoice workflow
**And** all state changes are logged to audit_log with actor, timestamp, and reason
**And** the void is recorded in the outbox for FIA notification if eGUI enabled

**Given** an invoice is outside the allowed void window
**When** I attempt to void it
**Then** the system rejects the void with an explicit void-window-expired error

### Story 2.4: Validate Invoice Totals and Rounding

As a finance clerk,
I want the system to validate invoice totals before printing,
So that I don't issue incorrect invoices.

**Acceptance Criteria:**

**Given** I'm creating an invoice
**When** I add line items and tax
**Then** the system validates each line tax calculation and verifies sum of line totals + tax = invoice total using the approved rounding rule
**And** prevents print if validation fails
**And** shows clear error message with discrepancy amount

### Story 2.5: Archive MIG 4.1 XML in MinIO

As a system,
I want to store issuer-side invoice artifacts in MinIO,
So that we have durable archives independent of MOF platform retention.

**Acceptance Criteria:**

**Given** an invoice is issued
**When** the invoice is created
**Then** MIG 4.1 XML is generated and stored in MinIO at `{tenant_id}/mig41/{invoice_id}.xml`
**And** the storage path is recorded in the invoice record
**And** artifacts are accessible for 10+ years per retention policy

### Story 2.6: Export PDF from Shared Invoice Renderer

As a finance clerk,
I want to export an invoice to PDF,
So that I can email it to customers or save for records.

**Acceptance Criteria:**

**Given** an invoice exists
**When** I click "Export to PDF"
**Then** a PDF is generated from the shared print renderer, matching the approved pre-printed stationery layout
**And** downloaded to the user's device

### Story 2.7: Enforce Immutable Invoice Content

As a system,
I want invoices to be immutable after creation,
So that we comply with Taiwan tax requirements.

**Acceptance Criteria:**

**Given** an invoice has been created
**When** any user attempts to modify line items, amounts, or customer
**Then** the system rejects the change with error "Invoices are immutable after creation"
**And** only void operations are permitted

---

## Epic 3: Customer Management

### Epic Goal

Sales reps can search, create, and update customers with validated Taiwan business numbers (統一編號) and scalable lookup workflows.

### Stories

### Story 3.2: Validate Taiwan Business Number Checksum

As a system,
I want to validate Taiwan business numbers using the current Ministry of Finance checksum logic,
So that customer data stays compliant for both legacy and newly issued numbers.

**Acceptance Criteria:**

**Given** I'm creating or updating a customer
**When** I enter an 8-digit Taiwan business number
**Then** the system validates it using the weighted checksum algorithm defined by current Ministry of Finance guidance, including the special-case handling for the seventh digit
**And** the validation accepts legacy and expanded allocations permitted by the official rule
**If** the checksum or format is invalid
**Then** the system shows a clear validation error and prevents save
**And** the validation logic is reusable from both the UI and backend tests

### Story 3.3: Create Customer Record

As a sales rep,
I want to create a new customer with business number, address, contact, and credit limit,
So that I can add new B2B customers to the system without re-entering them in later flows.

**Acceptance Criteria:**

**Given** I'm creating a new customer
**When** I fill in company name, Taiwan business number validated by Story 3.2, billing address, primary contact name, contact phone, contact email, and credit limit
**Then** the customer is saved to the database
**And** tenant_id is set correctly
**And** I receive confirmation with customer ID

### Story 3.1: Search and Browse Customers

As a sales rep,
I want to search for existing customers by 統一編號 or company name and inspect the matching record,
So that I can reuse existing customer data before creating invoices or orders.

**Acceptance Criteria:**

**Given** customers exist in the system
**When** I search by 統一編號 (full or partial) or company name (full or partial)
**Then** matching customers are returned with the summary fields needed to identify the right customer
**And** I can open a selected result to view the full customer record by ID or tax ID
**And** the results experience supports pagination and/or virtualization for 5,000+ rows without visible stutter on target hardware
**And** indexed search results load in < 500ms for expected SMB datasets

### Story 3.4: Flag Duplicate Business Number

As a system,
I want to flag duplicate Taiwan business numbers during customer creation,
So that we don't create conflicting customer masters.

**Acceptance Criteria:**

**Given** a customer with the same Taiwan business number already exists
**When** I attempt to create a new customer with that business number
**Then** the system shows a clear duplicate warning that includes the existing customer name
**And** the normal create flow is blocked until I cancel or choose the existing record instead
**And** the duplicate check occurs before the database insert and is also enforced by a unique persistence constraint

### Story 3.5: Update Customer Record

As a sales rep,
I want to update an existing customer's master data,
So that contact details, address, credit limit, and business number corrections stay accurate over time.

**Acceptance Criteria:**

**Given** an existing customer record
**When** I update company name, Taiwan business number, address, contact details, or credit limit
**Then** the system validates the edited fields before save
**And** changes to the business number re-run Story 3.2 checksum validation and duplicate detection
**And** the updated record is persisted without changing the customer ID
**And** the updated customer can be retrieved immediately through the customer detail and search flows

---

## Epic 4: Inventory Operations

### Epic Goal

Warehouse staff can track stock levels, receive reorder alerts, and manage supplier deliveries.

### Stories

### Story 4.1: Search Products

As a warehouse staff,
I want to search products by code or name,
So that I can quickly find items during stock inquiries.

**Acceptance Criteria:**

**Given** products exist in the system
**When** I search by product code (full or partial)
**Then** matching products are returned
**When** I search by product name (full or partial)
**Then** matching products are returned
**And** results support 5,000+ products without visible stutter

### Story 4.2: View Stock Level and Reorder Point

As a warehouse staff,
I want to view current stock level and reorder point per product,
So that I can make informed decisions about stock.

**Acceptance Criteria:**

**Given** a product exists
**When** I view the product details
**Then** I see: current stock quantity, reorder point, last adjusted date
**And** stock is shown per warehouse location if multiple warehouses exist

### Story 4.3: Reorder Alerts

As a system,
I want to generate reorder alerts when stock falls below reorder point,
So that warehouse staff can proactively reorder.

**Acceptance Criteria:**

**Given** a product's stock falls below its reorder point
**When** a stock adjustment is made
**Then** an alert is generated listing products needing reorder
**And** alerts appear on dashboard (Epic 7)
**And** alerts can be viewed in the inventory module

### Story 4.4: Record Stock Adjustment with Reason Codes

As a warehouse staff,
I want to record stock adjustments with reason codes,
So that we maintain accurate inventory records with audit trail.

**Acceptance Criteria:**

**Given** I need to adjust stock for a product
**When** I record an adjustment (+/- quantity)
**Then** I must select a reason code: received, damaged, returned, correction, other
**And** all adjustments are logged to audit_log with actor, timestamp, and reason
**And** stock levels update immediately

### Story 4.5: Track Supplier Orders and Auto-Update Stock

As a system,
I want to track supplier orders and auto-update stock when goods arrive,
So that inventory stays accurate without manual intervention.

**Acceptance Criteria:**

**Given** a supplier order is marked as received
**When** I confirm receipt
**Then** stock levels automatically increase by the ordered quantity
**And** the adjustment is logged with reason "supplier_delivery"
**And** related reorder alerts are cleared

### Story 4.6: Multiple Warehouse Support

As a warehouse staff,
I want to see and manage stock across multiple warehouse locations,
So that I can allocate inventory properly.

**Acceptance Criteria:**

**Given** multiple warehouses exist
**When** I view stock
**Then** I can filter by warehouse location
**And** I can transfer stock between warehouses
**And** each warehouse shows its own stock levels

---

## Epic 5: Order to Cash

### Epic Goal

Sales reps can create orders, check stock availability, and have invoices auto-generated.

### Stories

### Story 5.1: Create Order Linked to Customer

As a sales rep,
I want to create an order linked to an existing customer,
So that I can track sales and generate invoices.

**Acceptance Criteria:**

**Given** a customer exists
**When** I create a new order and select the customer
**Then** the order is linked to that customer
**And** the order gets a unique order number
**And** payment terms default to customer's terms

### Story 5.2: Check Stock Availability for Order

As a system,
I want to check and display stock availability for all order line items,
So that sales reps know what's in stock before confirming orders.

**Acceptance Criteria:**

**Given** I'm creating an order with line items
**When** I add products to the order
**Then** the system displays available stock for each item in real-time
**And** if stock is insufficient, shows "Insufficient stock: [available] units"
**And** allows order creation with note about backorder

### Story 5.3: Set Payment Terms on Order

As a sales rep,
I want to set payment terms on an order (e.g., 30 days),
So that customers can pay according to agreed terms.

**Acceptance Criteria:**

**Given** I'm creating an order
**When** I set payment terms (e.g., Net 30, Net 60, COD)
**Then** the terms are recorded on the order
**And** the invoice, when generated, reflects these terms

### Story 5.4: Auto-Generate Invoice from Confirmed Order

As a system,
I want to auto-generate an invoice when an order is confirmed,
So that billing happens automatically without manual intervention.

**Acceptance Criteria:**

**Given** a sales rep confirms an order
**When** the order status changes to "confirmed"
**Then** an invoice is automatically created with correct line items, prices, and tax
**And** the invoice is linked to the order
**And** the sales rep receives confirmation

### Story 5.5: Update Order Status

As a sales rep,
I want to update order status through the lifecycle,
So that we track orders from pending to fulfillment.

**Acceptance Criteria:**

**Given** an order exists
**When** I update the status
**Then** valid transitions are: pending → confirmed → shipped → fulfilled
**And** each transition is logged to audit_log
**And** status change triggers appropriate notifications

---

## Epic 6: Payment Handling

### Epic Goal

Finance can record payments against invoices with automatic reconciliation.

### Stories

### Story 6.1: Record Payment Against Invoice

As a finance clerk,
I want to record payments against invoices,
So that we track what's been paid.

**Acceptance Criteria:**

**Given** an invoice exists with outstanding balance
**When** I record a payment (amount, method, date)
**Then** the payment is saved and linked to the invoice
**And** the invoice's outstanding balance is reduced
**And** the payment is logged to audit_log

### Story 6.2: Auto-Match Payments to Open Invoices

As a system,
I want to auto-match payments to open invoices during reconciliation,
So that finance doesn't have to manually match.

**Acceptance Criteria:**

**Given** a payment is recorded
**When** reconciliation runs
**Then** the system matches payments to open invoices by: customer → amount → date range
**And** if exact match found, invoices are marked as paid
**And** unmatched payments are flagged for manual review

### Story 6.3: Display Outstanding Payment Status

As a finance clerk,
I want to see outstanding payment status per invoice,
So that I know what customers owe.

**Acceptance Criteria:**

**Given** invoices exist
**When** I view the invoices list
**Then** each invoice shows: total amount, amount paid, outstanding balance
**And** invoices are sortable by outstanding balance
**And** overdue invoices are highlighted

---

## Epic 7: Business Dashboard

### Epic Goal

Owners can view morning KPIs: revenue, top products, stock alerts, and Posthog visitor data.

### Stories

### Story 7.1: Morning Dashboard - Revenue Comparison

As an owner,
I want to see today's revenue vs. yesterday's,
So that I can quickly assess business performance.

**Acceptance Criteria:**

**Given** I'm on the dashboard
**When** the page loads
**Then** I see today's total revenue
**And** I see yesterday's total revenue
**And** I see the percentage change
**And** dashboard loads in < 2 seconds (p95)

### Story 7.2: Top Selling Products

As an owner,
I want to view top selling products by day/week,
So that I can identify trends.

**Acceptance Criteria:**

**Given** I'm on the dashboard
**When** I view the top products section
**Then** I see the top 3 selling products for today
**And** I can toggle to view by week
**And** products show: name, quantity sold, revenue

### Story 7.3: Low-Stock Alerts

As an owner,
I want to view low-stock alerts on the dashboard,
So that I can address inventory issues quickly.

**Acceptance Criteria:**

**Given** products exist with stock below reorder point
**When** I view the dashboard
**Then** I see alerts listing products needing reorder
**And** alerts show: product name, current stock, reorder point
**And** clicking an alert takes me to the product detail

### Story 7.4: Posthog Visitor Count

As an owner,
I want to see Posthog visitor count from the previous day,
So that I can track website traffic.

**Acceptance Criteria:**

**Given** Posthog is integrated
**When** I view the dashboard
**Then** I see yesterday's visitor count
**And** I see the conversion rate (visitor → inquiry)
**And** data is visible within 10 minutes of session end
**And** data refreshes automatically

### Story 7.5: Posthog Integration - Visitor Tracking

As a system,
I want to track website visitor sessions via Posthog,
So that we understand user behavior.

**Acceptance Criteria:**

**Given** Posthog is configured
**When** visitors browse the website
**Then** sessions are tracked in Posthog
**And** page views, events, and sessions are captured
**And** data flows to dashboard within 10 minutes

### Story 7.6: Posthog Integration - Goal Conversions

As a system,
I want to track goal conversions (visitor → inquiry),
So that we measure marketing effectiveness.

**Acceptance Criteria:**

**Given** Posthog is integrated
**When** a visitor completes an inquiry action
**Then** the conversion is tracked as a goal
**And** conversion rate is calculated and displayed on dashboard
**And** trend data is available for comparison

---

## Epic 8: AI Agent Interface

### Epic Goal

AI agents (Claude Code, etc.) can query ERP data via MCP with Taiwan tax domain knowledge.

### Stories

### Story 8.1: MCP Tool - Inventory Check

As an AI agent,
I want to check inventory levels via MCP tools,
So that I can answer questions about stock.

**Acceptance Criteria:**

**Given** I'm an AI agent with MCP access
**When** I call `inventory.check` with a product identifier
**Then** I receive: product name, current stock, location, reorder point, last adjusted, status
**And** response time is < 1 second (p95)

### Story 8.2: MCP Tool - Customer Query

As an AI agent,
I want to query customer data via MCP tools,
So that I can retrieve customer information.

**Acceptance Criteria:**

**Given** I'm an AI agent with MCP access
**When** I call `customers.list` or `customers.get`
**Then** I receive customer data based on my scopes
**And** current Taiwan business-number checksum validation is applied if searching by 統一編號

### Story 8.3: MCP Tool - Invoice Query

As an AI agent,
I want to query invoice data via MCP tools,
So that I can retrieve invoice information.

**Acceptance Criteria:**

**Given** I'm an AI agent with MCP access
**When** I call `invoices.list` or `invoices.get`
**Then** I receive invoice data based on my scopes
**And** invoice totals and tax are included

### Story 8.4: MCP Tool - Role-Scoped Authentication

As a system,
I want MCP tools to support role-scoped authentication,
So that agents only access what they're permitted to.

**Acceptance Criteria:**

**Given** an MCP tool is called
**When** the request includes bearer token or API key
**Then** the system validates scopes: customers:read, invoices:write, etc.
**And** requests without valid scopes are rejected with 403

### Story 8.5: Taiwan Tax Domain Knowledge (Skills)

As an AI agent,
I want Claude Code to use Taiwan tax domain knowledge from Skills files,
So that I can answer tax-related questions correctly.

**Acceptance Criteria:**

**Given** Claude Code is configured with ERP skills
**When** I ask about tax rates, void rules, or eGUI workflows
**Then** the Skills files provide accurate Taiwan tax knowledge
**And** Skills include: MIG-permitted tax policy mapping, Taiwan business-number checksum rules, and regulatory void-window policy

### Story 8.6: MCP Server - Session Mode HTTP

As a system,
I want FastMCP 2.14.6 to use session-mode HTTP transport,
So that agents can maintain persistent connections.

**Acceptance Criteria:**

**Given** FastMCP is configured
**When** agents connect to `/mcp` endpoint
**Then** transport is streamable-http (NOT stateless_http)
**And** concurrent agent connections are supported

---

## Epic 9: LINE Integration

### Epic Goal

Staff receive LINE notifications for new orders; customers can submit orders via LINE BOT.

### Stories

### Story 9.1: LINE Notification on New Order

As a staff member,
I want to receive LINE notifications when new orders are created,
So that I can respond quickly to customer orders.

**Acceptance Criteria:**

**Given** a new order is created
**When** the order is saved
**Then** a LINE notification is sent to configured staff channel
**And** notification includes: order number, customer name, order total
**And** notification is sent via LINE Notify or Messaging API

### Story 9.2: LINE BOT - Order Submission

As a customer,
I want to submit orders via LINE BOT,
So that I can place orders easily through our existing communication channel.

**Acceptance Criteria:**

**Given** a customer messages the LINE BOT
**When** the customer sends order details in text format
**Then** the BOT parses the message
**And** creates a draft order in the system
**And** sends confirmation to the customer

### Story 9.3: LINE Order Confirmation

As a system,
I want to confirm order receipt via LINE to customers,
So that they know their order was received.

**Acceptance Criteria:**

**Given** a customer submits an order via LINE
**When** the order is parsed and created
**Then** a confirmation message is sent to the customer via LINE
**And** the message includes: order number, items, estimated processing time

---

## Epic 10: AEO (AI SEO)

### Epic Goal

Products are structured for discoverability in AI-generated search answers.

### Stories

### Story 10.1: Auto-Generate JSON-LD Structured Data

As a system,
I want to auto-generate JSON-LD structured data for products on create,
So that search engines can understand our product data.

**Acceptance Criteria:**

**Given** a product is created or updated
**When** the product is saved
**Then** JSON-LD structured data is automatically generated
**And** includes: name, description, price, availability, SKU
**And** is accessible at `/products/{id}/jsonld` endpoint

### Story 10.2: Auto-Generate XML Sitemap

As a system,
I want to auto-generate an XML sitemap for all products,
So that search engines can crawl our catalog.

**Acceptance Criteria:**

**Given** products exist
**When** the sitemap is requested
**Then** an XML sitemap is generated at `/sitemap-products.xml`
**And** includes all active product URLs
**And** is updated when products are created/modified
**And** is submitted to search engines automatically

### Story 10.3: Product Content for AI Citation

As a system,
I want product content to be structured for maximum citation in AI-generated answers,
So that our products appear in AI search recommendations.

**Acceptance Criteria:**

**Given** a product exists
**When** AI systems crawl or query our data
**Then** product descriptions are written in clear, factual format
**And** include: specifications, use cases, differentiators
**And** structured data follows schema.org Product specification

---

## Epic 11: User & Access Management

### Epic Goal

Admins can manage users with role-based access control across all surfaces (UI, API, MCP, CLI).

### Stories

### Story 11.1: Create Users with Roles

As an admin,
I want to create users with specific roles,
So that I can control who has access to what.

**Acceptance Criteria:**

**Given** I'm an admin
**When** I create a new user
**Then** I can assign one of these roles: Owner, Finance, Warehouse, Sales
**And** the user receives an invitation to set up their account
**And** RBAC is enforced immediately upon activation

### Story 11.2: RBAC in UI

As a system,
I want to enforce RBAC in the UI,
So that users only see features appropriate to their role.

**Acceptance Criteria:**

**Given** a user is logged in
**When** they access the UI
**Then** menu items are filtered by role
**And** Finance users see: Invoices, Payments, Customers (read-only)
**And** Warehouse users see: Inventory, Orders (read-only)
**And** Sales users see: Customers, Orders, Inventory (read-only)

### Story 11.3: RBAC in API

As a system,
I want to enforce RBAC consistently in the API layer,
So that unauthorized access is blocked at all endpoints.

**Acceptance Criteria:**

**Given** an API request is made
**When** the request includes authentication
**Then** the system validates role permissions
**And** returns 403 for unauthorized endpoints
**And** audit_log records the access attempt

### Story 11.4: RBAC for MCP/CLI

As a system,
I want to enforce RBAC and auth scopes consistently across MCP and CLI surfaces,
So that all access methods are equally secure.

**Acceptance Criteria:**

**Given** an MCP or CLI request is made
**When** the request includes bearer token or API key
**Then** the system validates scopes: customers:read, invoices:write, etc.
**And** returns 403 for unauthorized tool calls
**And** audit_log records the access attempt

### Story 11.5: Human-in-the-Loop for Sensitive Writes

As a system,
I want to require explicit human confirmation for sensitive write actions via AI or automation,
So that we prevent unauthorized changes.

**Acceptance Criteria:**

**Given** a sensitive write action is triggered through AI or automation
**When** the action is: invoices.void, invoices.submit, or inventory.adjust above threshold
**Then** an approval record is created
**And** a human must explicitly confirm before execution
**And** the action is logged with approval status

### Story 11.6: Audit Log

As a system,
I want to record all invoice state changes, inventory adjustments, and user actions,
So that we have a complete audit trail.

**Acceptance Criteria:**

**Given** any of these events occur: invoice create/void, inventory adjustment, login/logout, RBAC change
**When** the event completes
**Then** audit_log records: actor_type, actor_id, action, target_entity, before_state, after_state, timestamp
**And** audit_log entries cannot be modified or deleted

---

## Epic 12: Desktop Shell & Tray

### Epic Goal

Users can run the app from system tray with keyboard shortcuts and background notifications.

### Stories

### Story 12.1: Virtualized Lists for 5,000+ Rows

As a user,
I want customer and inventory lists to remain responsive with 5,000+ rows,
So that I don't experience lag when browsing large datasets.

**Acceptance Criteria:**

**Given** I'm viewing a list with 5,000+ items
**When** I scroll through the list
**Then** there is no visible stutter or lag
**And** list renders within 2 seconds (p95)

### Story 12.2: Keyboard Shortcuts with Overlay

As a power user,
I want to access primary screens and actions through global keyboard shortcuts plus a screen-local shortcut overlay,
So that I can work efficiently without mouse.

**Acceptance Criteria:**

**Given** I'm using the app
**When** I press `?` or `Ctrl+/`
**Then** the shortcut overlay appears showing all available shortcuts
**And** global shortcuts work across the app
**And** shortcuts are discoverable and documented

### Story 12.3: eGUI Status Badge and State Persistence

As a user,
I want invoice screen to show async eGUI status badge, deadline awareness, and persisted state,
So that I can track invoice submissions.

**Acceptance Criteria:**

**Given** eGUI is enabled for the tenant
**When** I view an invoice
**Then** I see an async status badge (PENDING, QUEUED, SENT, ACKED, FAILED)
**And** I see deadline awareness for submission windows
**And** I can manually refresh status
**And** state persists across app restarts

### Story 12.4: System Tray Mode with Notifications

As a user,
I want the desktop app to run in system tray and send notifications,
So that I can monitor async operations while the main window is closed.

**Acceptance Criteria:**

**Given** the app is running
**When** I close the main window
**Then** the app continues running in system tray
**And** I receive desktop notifications for async invoice/eGUI state changes
**And** clicking the tray icon restores the main window

### Story 12.5: Print Preview Performance

As a finance clerk,
I want invoice print preview to render in < 1 second,
So that I can quickly review before printing.

**Acceptance Criteria:**

**Given** an invoice exists
**When** I click preview
**Then** the print preview renders in < 1 second

---

## Epic 13: Shadow-Mode Validation

### Epic Goal

System validates correctness against legacy ERP during parallel run before cutover.

### Stories

### Story 13.1: Versioned Reconciliation Spec

As a system,
I want to use a versioned reconciliation specification,
So that we can track what should be compared during shadow-mode.

**Acceptance Criteria:**

**Given** shadow-mode is running
**When** comparing systems
**Then** the comparison follows the versioned reconciliation spec
**And** spec covers: invoice totals/tax, payments, inventory movements, customer balances, order status
**And** severity levels are defined: severity_1 (blocking), severity_2 (warning)

### Story 13.2: Shadow-Mode Discrepancy Detection

As a system,
I want to detect and report discrepancies between old and new systems,
So that we can identify issues before cutover.

**Acceptance Criteria:**

**Given** both systems are processing transactions
**When** a discrepancy is detected
**Then** an alert is generated
**And** severity_1 discrepancies block cutover
**And** discrepancy report is generated daily
**And** alerts are actionable (not vague warnings)

### Story 13.3: 30-Day Parallel Run

As a system,
I want to run in shadow-mode for 30 days with zero unresolved severity-1 discrepancies,
So that we can confidently cutover to the new system.

**Acceptance Criteria:**

**Given** shadow-mode has been running
**When** 30 days have passed with zero unresolved severity-1 discrepancies
**Then** the system is cleared for cutover
**And** a cutover readiness report is generated

### Story 13.4: Backup Strategy for 10+ Year Retention

As a system,
I want to support policy-based 10+ year retention for records,
So that we comply with Taiwan tax requirements.

**Acceptance Criteria:**

**Given** retention policies are configured
**When** records are stored
**Then** retention is enforced by record class
**And** backups support 10+ year recovery
**And** company-policy can extend beyond 10 years

---

## Epic 14: Traditional Chinese i18n (Duolanguage Support)

### Epic Goal

System displays all UI text in both English and Traditional Chinese (zh-Hant), with automatic browser language detection and manual language switching, providing a truly bilingual ERP experience for Taiwan SMB users.

### Story 14.1: i18n Infrastructure Setup

As a system,
I want to integrate react-i18next with locale detection and lazy-loaded translation files,
So that the application is ready for multilingual support.

**Acceptance Criteria:**

**Given** the React application is bootstrapped
**When** the user first loads the application
**Then** i18next is configured with react-i18next, i18next-browser-languagedetector, and i18next-http-backend
**And** supported languages are ['en', 'zh-Hant']
**And** fallback language is 'en'
**And** translation files are lazy-loaded from /locales/{lng}/{ns}.json
**And** detection order is: localStorage → navigator.language → querystring
**And** language preference is cached in localStorage under key 'i18nextLng'

### Story 14.2: English Translation Baseline

As a system,
I want all current UI strings extracted to English translation files,
So that we have a complete English baseline to translate from.

**Acceptance Criteria:**

**Given** i18next is configured
**When** the application renders UI components
**Then** all visible text strings are sourced from translation keys
**And** English translation files exist at /public/locales/en/common.json
**And** common.json contains keys for: nav, buttons, labels, messages, errors, validation
**And** all existing React components use the useTranslation hook or t() function
**And** no hardcoded English strings remain in component render methods

### Story 14.3: Traditional Chinese Translation

As a system,
I want complete Traditional Chinese (zh-Hant) translation files,
So that Taiwanese users see all text in their native language.

**Acceptance Criteria:**

**Given** English baseline exists
**When** user selects zh-Hant language
**Then** all UI text displays in Traditional Chinese
**And** translation files exist at /public/locales/zh-Hant/common.json
**And** Chinese plural handling uses only 'other' category (no singular/plural distinction)
**And** all vocabulary uses Taiwanese variants (例如: 電腦 rather than 計算機 for computer)
**And** character conversion (OpenCC-style) is NOT used for UI translation

### Story 14.4: Language Switcher Component

As a user,
I want to manually switch between English and Traditional Chinese,
So that I can use the app in my preferred language.

**Acceptance Criteria:**

**Given** the application is loaded
**When** the user clicks the language switcher
**Then** a dropdown shows available languages: English, 繁體中文
**And** selecting a language immediately re-renders all UI text without page reload
**And** selected language is persisted to localStorage
**And** the switcher displays the current language name/flag
**And** the switcher is accessible from the sidebar or header

### Story 14.5: Browser Language Auto-Detection

As a system,
I want to automatically detect and apply the user's browser language preference,
So that users see the correct language on first visit without manual selection.

**Acceptance Criteria:**

**Given** it's the user's first visit
**When** the application loads
**Then** navigator.language is read (e.g., "zh-TW", "zh-Hant", "zh-CN")
**And** the system maps it to supported locale (zh-TW/zh-Hant → zh-Hant, others → en)
**And** detected language is applied before first render
**And** if navigator.language starts with 'zh', zh-Hant is selected by default

### Story 14.6: Chinese Font Integration

As a system,
I want proper Traditional Chinese font rendering,
So that all Chinese characters display correctly without missing glyph issues.

**Acceptance Criteria:**

**Given** the application displays Chinese text
**When** the page renders
**Then** the font stack includes: "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif
**And** Noto Sans TC is loaded via Google Fonts (or self-hosted for China accessibility)
**And** font-display is set to 'optional' for performance
**And** Chinese text renders without tofu (missing character) issues

---

## Epic 15: Legacy Data Import Pipeline

### Epic Goal

Operations and AI agents can stage, map, import, and validate legacy ERP data into UltrERP through a repeatable CLI-backed workflow plus a task-specific skill that preserves lineage and exposes unresolved data-quality issues instead of hiding them.

### Stories

### Story 15.1: Raw Legacy Staging Import

As a migration operator,
I want extracted legacy CSVs loaded into a read-only staging schema,
So that every migration run starts from a reproducible source snapshot inside PostgreSQL.

**Acceptance Criteria:**

**Given** a verified legacy export set is available
**When** I run the staging import command
**Then** the pipeline creates or refreshes `raw_legacy` tables for the configured batch
**And** the staging workflow is exposed through a stable CLI command surface that later skill automation can call
**And** loads the source files with PostgreSQL-native bulk loading rather than row-by-row inserts
**And** records source table, source key, batch/run identifier, and import status for every staged row

### Story 15.2: Canonical Master Data Normalization

As a migration operator,
I want ROC dates, sentinel dates, and core master records normalized before canonical import,
So that downstream loads use consistent customer, supplier, product, and warehouse data.

**Acceptance Criteria:**

**Given** raw legacy tables are loaded
**When** the normalization step runs
**Then** ROC-encoded dates are converted to AD dates
**And** `1900-01-01` sentinel values are converted according to the documented import policy
**And** customer/supplier, product, and warehouse staging outputs are generated with deterministic legacy-to-canonical keys

### Story 15.3: Product Variant Mapping Workflow

As a data analyst,
I want unresolved legacy product variants managed through an explicit mapping workflow,
So that transaction history is preserved without claiming false product certainty.

**Acceptance Criteria:**

**Given** the migration pipeline encounters legacy product codes not present in the product master
**When** the mapping workflow runs
**Then** exact matches are auto-linked into `raw_legacy.product_code_mapping`
**And** unresolved codes are surfaced for analyst review with confidence metadata
**And** rows that remain unresolved are routed to an `UNKNOWN` placeholder product instead of being dropped

### Story 15.4: Canonical Historical Transaction Import

As a migration operator,
I want staged legacy headers and lines imported into UltrERP's canonical tables,
So that historical sales, purchase, inventory, and party data are available in the new system.

**Acceptance Criteria:**

**Given** normalized master data and product mappings are available
**When** I run the canonical import step
**Then** parties, products, warehouses, inventory, sales headers/lines, and purchase headers/lines load into the approved UltrERP schema
**And** every canonical record retains lineage back to the originating legacy table and source identifier
**And** unresolved variant rows use the documented fallback behavior rather than violating foreign keys

### Story 15.5: Migration Validation and Replay Safety

As a cutover owner,
I want migration runs to emit actionable validation reports and support safe reruns,
So that cutover is blocked by real data problems while repeat imports remain auditable.

**Acceptance Criteria:**

**Given** a migration batch completes
**When** validation runs
**Then** the system produces row-count reconciliation, orphan/mapping summaries, and severity-ranked discrepancy reports
**And** emits machine-readable artifacts that a reviewed agent skill can inspect without scraping prose only
**And** unresolved severity-1 issues block cutover readiness
**And** rerunning the same batch or cutoff window does not create duplicate canonical records

### Story 15.6: Agent-Invocable Legacy Import Skill

As an operator working with an AI agent,
I want the agent to invoke the reviewed legacy-import workflow through a dedicated skill backed by the CLI,
So that the workflow is reusable, guided, and safe across VS Code, Copilot CLI, and coding-agent contexts.

**Acceptance Criteria:**

**Given** the legacy import CLI exposes stable subcommands
**When** the agent loads the legacy-import skill
**Then** the skill tells the agent which CLI subcommands to run for staging, normalization, canonical import, and validation
**And** references supporting resources from the skill directory rather than duplicating the import logic in markdown alone

**Given** the skill is packaged for agent discovery
**When** the skill is installed in the repository
**Then** it lives in a supported skills directory with valid frontmatter (`name`, `description`, and invocation behavior)
**And** its directory name matches the skill name

**Given** the skill may invoke terminal commands
**When** tool permissions are configured
**Then** shell execution is left unapproved by default or tightly scoped to the reviewed CLI path
**And** destructive or high-impact import scopes still require explicit operator confirmation

---

## Epic 16: Extended Legacy Import — Purchase Transactions and Payments

### Epic Goal

Operations and AI agents can stage, normalize, map, import, and validate extended legacy ERP purchase data (purchase invoices, purchase orders, and payment records) into UltrERP through the same repeatable CLI-backed workflow used for Epic 15, adding coverage for the purchase side of the business and completing the financial transaction picture alongside the already-imported sales data.

### Stories

### Story 16.1: Raw Purchase Invoice Staging

As a migration operator,
I want extracted purchase invoice headers and line items loaded into the raw_legacy staging schema,
So that the purchase transaction data is available for normalization and canonical import alongside the sales data already staged in Epic 15.

**Acceptance Criteria:**

**Given** the verified legacy export set includes tbsslipj and tbsslipdtj CSV files
**When** I run the staging import command for the purchase tables
**Then** the pipeline creates or refreshes raw_legacy.tbsslipj and raw_legacy.tbsslipdtj tables for the configured batch
**And** the CLI supports --table tbsslipj and --table tbsslipdtj flags to stage only purchase invoice tables
**And** loads source files with PostgreSQL-native bulk loading (COPY)
**And** records source table, source key, batch/run identifier, and import status for every staged row
**And** tbsslipj.supplier_code (field 7) is validated as a FK to tbscust.customer_code where type='1' (supplier)
**And** ROC-encoded dates in tbsslipj and tbsslipdtj are preserved as-is during staging for later normalization

**Given** the staging job completes for a batch that already has tbsslipj/tbsslipdtj staged
**When** I re-run the staging command for the same batch
**Then** the existing rows for those tables are replaced atomically without affecting other already-staged tables in the batch

### Story 16.2: Normalize Purchase Master Data

As a migration operator,
I want purchase master data normalized before canonical import,
So that suppliers, products, and warehouses are consistent with the canonical schema and the same product mapping used in Epic 15.

**Acceptance Criteria:**

**Given** raw_legacy.tbsslipj and raw_legacy.tbsslipdtj are staged
**When** the normalization step runs for the purchase batch
**Then** supplier records are derived from tbscust rows where type='1' (matching the pattern used in Epic 15 normalization)
**And** ROC-encoded dates are converted to AD dates using the same ROC→AD conversion applied in Epic 15
**And** tbscust type='1' suppliers are written to the canonical customers table with supplier role
**And** the same product_code_mapping table used in Epic 15 is referenced for tbsslipdtj.product_code
**And** warehouse codes in tbsslipj are resolved using the warehouse mapping established during Epic 15 staging of tbsstkhouse
**And** the normalization output for purchase data is idempotent — re-running produces the same canonical keys

### Story 16.3: Raw Purchase Order Staging

As a migration operator,
I want extracted purchase order headers loaded into the raw_legacy staging schema,
So that purchase orders are available for canonical import.

**Acceptance Criteria:**

**Given** the verified legacy export set includes tbsslipo CSV
**When** I run the staging import command for tbsslipo
**Then** the pipeline creates or refreshes raw_legacy.tbsslipo for the configured batch
**And** the CLI supports --table tbsslipo to stage only the purchase order table
**And** records source table, source key, batch/run identifier, and import status for every staged row
**And** tbsslipo.supplier_code (field 5) is validated as a FK to tbscust.customer_code where type='1'
**And** ROC-encoded dates are preserved during staging

### Story 16.4: Canonical Purchase Order Import

As a migration operator,
I want staged purchase orders imported into the canonical orders schema,
So that historical purchase order data is available in UltrERP alongside sales orders from Epic 15.

**Acceptance Criteria:**

**Given** normalized master data and product mappings are available from Epic 15 and Story 16.2
**When** I run the canonical import step for purchase orders
**Then** tbsslipo rows are imported into the canonical orders table with order_type='PURCHASE_ORDER'
**And** each purchase order line is imported into order_lines linked to the canonical product
**And** supplier is resolved through the tbscust→canonical customer mapping from Story 16.2
**And** every canonical record retains lineage back to the originating legacy table and source identifier (doc_number)
**And** the same replay-safety rules from Epic 15 Story 15.5 apply — rerunning does not create duplicate canonical records

### Story 16.5: Payment Transaction Staging

As a migration operator,
I want special payment and prepayment records staged into raw_legacy,
So that the full payment picture from the legacy system is available for canonical import.

**Acceptance Criteria:**

**Given** the verified legacy export set includes tbsspay and tbsprepay CSV files
**When** I run the staging import for payment tables
**Then** raw_legacy.tbsspay (special payments, 6 rows) and raw_legacy.tbsprepay (prepayments, 508 rows) are created
**And** the CLI supports --table tbsspay and --table tbsprepay flags
**And** customer/supplier references in these tables are validated against tbscust
**And** ROC-encoded dates are preserved during staging
**And** the payment staging is tracked in legacy_import_table_runs with the same batch_id and attempt semantics

### Story 16.6: Currency Settings Import

As a migration operator,
I want currency settings from the legacy system available in UltrERP,
So that the canonical app_settings reflects the currencies used in historical transactions.

**Acceptance Criteria:**

**Given** tbscurrency contains currency configuration (6 rows)
**When** the currency import step runs
**Then** each currency row is upserted into app_settings with keys like 'currency.{code}.symbol', 'currency.{code}.decimal_places'
**And** the default currency is marked in app_settings as 'currency.default'
**And** existing app_settings.currency.* keys are preserved unless the same currency code is being re-imported
**And** the import is idempotent — re-running does not create duplicate currency settings

### Story 16.7: Canonical Purchase Invoice Import

As a migration operator,
I want staged purchase invoice headers and lines imported into a canonical AP schema,
So that historical supplier invoice data is available in UltrERP without forcing purchase history into sales AR tables or unsupported holding records.

**Acceptance Criteria:**

**Given** normalized supplier master data, product mappings, and staged tbsslipj/tbsslipdtj rows are available
**When** I run the canonical import step for purchase invoices
**Then** each purchase invoice header is upserted into `supplier_invoices`
**And** each purchase invoice line is upserted into `supplier_invoice_lines`
**And** supplier references resolve through the normalized supplier-party mapping from Story 16.2
**And** product references reuse the same product_code_mapping flow already established for Epic 15

**Given** the same purchase-invoice batch is imported again
**When** the canonical import reruns for that batch
**Then** deterministic tenant-scoped IDs and upsert semantics prevent duplicate supplier invoices or supplier invoice lines
**And** unsupported payment-adjacent tables remain in holding until a verified AP payment model exists

### Story 16.8: Supplier Invoice Read API

As a finance or warehouse operator,
I want read-only API access to imported supplier invoices,
So that I can inspect and verify migrated AP history after canonical import completes.

**Acceptance Criteria:**

**Given** supplier invoices exist in the canonical AP tables
**When** I call the purchase read API
**Then** `GET /api/v1/purchases/supplier-invoices` returns paginated supplier invoice summaries with supplier name, totals, status, and line count
**And** `GET /api/v1/purchases/supplier-invoices/{invoice_id}` returns supplier invoice detail with line-level product enrichment
**And** only finance, warehouse, or owner roles can access these endpoints

**Given** a requested supplier invoice does not exist
**When** I request the detail route
**Then** the API returns a 404 response
**And** the new surface remains read-only with no purchase-invoice write endpoints introduced

### Story 16.9: Purchases Frontend Workspace

As a finance or warehouse operator,
I want a purchases workspace inside the UltrERP shell,
So that I can review imported supplier invoices without calling backend endpoints manually.

**Acceptance Criteria:**

**Given** a finance, warehouse, or owner user signs into the frontend shell
**When** they navigate to `/purchases`
**Then** the route is available through feature gating, navigation, and shortcut wiring
**And** unauthorized roles are blocked from the new purchases surface

**Given** imported supplier invoices exist in the purchases API
**When** the workspace loads
**Then** the list view shows supplier invoice summaries with supplier name, status, totals, and line count
**And** selecting a row opens a read-only detail view with invoice summary, notes, and imported line enrichment

**Given** the purchases API fails or returns no data
**When** the operator opens the workspace
**Then** the page shows a clear empty or error state
**And** the operator can return from detail to the list without leaving the page

### Story 16.10: AP Payment Model Design

As a migration operator and ERP architect,
I want a verified canonical model for supplier payments and prepayments,
So that `tbsspay` and `tbsprepay` can be imported later without corrupting AR payment semantics.

**Acceptance Criteria:**

**Given** the current AR-side `payments` table is reviewed
**When** the AP settlement design is documented
**Then** the design explains why the existing customer/invoice payment model is not a safe target for supplier-side history
**And** it defines dedicated AP tables for supplier cash events and supplier-invoice allocations

**Given** supplier prepayments and special payments may be unapplied or partially applied
**When** the canonical target is defined
**Then** one supplier payment may allocate to many supplier invoices
**And** prepayments are represented as a supplier payment kind rather than a separate ad hoc operational table

**Given** legacy payment-column semantics remain partially unverified
**When** import rules are written down
**Then** `tbsspay` and `tbsprepay` remain on the holding path until supplier linkage, amount/sign rules, ROC dates, and invoice-link columns are verified
**And** the design includes an explicit verification checklist before implementation starts

### Story 16.11: Canonical AP Payment Architecture

As an ERP engineer,
I want the canonical AP payment tables and relationships implemented,
So that the deferred supplier-payment import has a stable backend target before legacy allocation logic is turned on.

**Acceptance Criteria:**

**Given** AP settlement history needs its own schema foundation
**When** the backend migration runs
**Then** `supplier_payments` and `supplier_payment_allocations` exist as first-class tables
**And** they use AP-specific enums for payment kind, status, and allocation kind
**And** supplier payments relate to `supplier` while allocations bridge supplier payments to `supplier_invoices`

**Given** supplier prepayments and later settlements will share the same cash-event model
**When** the ORM layer is implemented
**Then** `supplier_payments` supports prepayment, special-payment, and adjustment kinds
**And** the many-to-many allocation model is available without reusing the AR `payments` table

**Given** legacy column semantics are still only partially verified
**When** this architecture ships
**Then** no guessed canonical import is added for `tbsspay` or `tbsprepay`
**And** the new schema is validated with focused backend tests and lint checks only

### Story 16.12: Supplier Payment Import CLI

As a migration operator,
I want a dedicated CLI step to import staged supplier payment history into the canonical AP payment tables,
So that `tbsprepay` and `tbsspay` can be migrated deliberately without coupling payment import to `canonical-import`.

**Acceptance Criteria:**

**Given** staged `tbsprepay` and `tbsspay` rows exist for a batch and the AP payment schema from Story 16.11 is present
**When** I run the new AP payment import CLI command
**Then** the legacy-import CLI exposes an explicit payment import step for that batch
**And** the command remains separate from `canonical-import`
**And** the run is tracked with batch/attempt semantics

**Given** verified payment mapping rules from Story 16.10 are available
**When** the AP payment import command runs
**Then** supplier-side cash events are written into `supplier_payments`
**And** verified invoice allocations are written into `supplier_payment_allocations`
**And** deterministic IDs and lineage records make the import replay-safe

**Given** some legacy payment rows still cannot be linked safely to a supplier invoice or have unresolved semantics
**When** the command processes those rows
**Then** they stay on the holding path or fail with explicit diagnostics instead of guessed imports
**And** unrelated verified rows in the batch still import safely when the design allows partial progress

**Given** the story is implemented
**When** focused backend validation runs
**Then** pytest covers the CLI command and canonical AP payment import behavior
**And** Ruff passes on the touched legacy-import and AP payment files
