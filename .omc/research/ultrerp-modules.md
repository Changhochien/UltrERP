# UltrERP Modules Inventory

## Overview

Base path: `/Users/changtom/Downloads/UltrERP`

- **Frontend**: React 19 + Vite + TypeScript + Tailwind CSS v4 + Radix UI. Pages in `src/pages/`, domain sections in `src/domain/`, API clients in `src/lib/api/`
- **Backend**: FastAPI + SQLAlchemy 2.0 async + PostgreSQL. Domain modules in `backend/domains/`
- **API prefix**: `/api/v1/<domain>`

---

## Customers

### Backend
**`backend/domains/customers/`**

| File | Purpose |
|---|---|
| `models.py` | `Customer` SQLAlchemy model — tenant_id, company_name, business_number (normalized), billing_address, contact fields, credit_limit, default_discount_percent, status, customer_type, legacy_master_snapshot, version |
| `schemas.py` | `CustomerCreate`, `CustomerUpdate` (PATCH, requires version for optimistic locking), `CustomerResponse`, `CustomerSummary`, `CustomerListParams/Response`, `CustomerOutstandingSummary`, `CustomerStatementResponse`, `StatementLine`, `CustomerAnalyticsSummary`, `CustomerRevenueTrend`, `RevenueTrendPoint` |
| `routes.py` | `GET /` (list, paginated, searchable by q/status), `GET /lookup` (by business_number), `GET /{id}`, `POST /` (create), `PATCH /{id}` (update with version conflict detection), `GET /{id}/outstanding`, `GET /{id}/statement` (date-range), `GET /{id}/analytics/summary`, `GET /{id}/analytics/revenue-trend` |
| `service.py` | Business logic — list, create, update, lookup, outstanding calc, statement generation, analytics |
| `validators.py` | Duplicate business number check |
| `mcp.py` | MCP server exposure |

**Roles**: read = `admin|finance|sales`; write = `admin|sales`

### Frontend
**`src/domain/customers/`** — `types.ts` (payload/response interfaces), `components/` (CustomerForm, etc.)

**`src/pages/customers/`** — `CreateCustomerPage.tsx`, `CustomerDetailPage.tsx`, `CustomerListPage.tsx`

**`src/lib/api/customers.ts`** — API client functions

### Gaps
- No bulk create/update/delete
- No customer import (only legacy-import domain for migrating old data)
- No contact-person CRUD separate from customer
- No customer-specific document attachments

---

## Invoices

### Backend
**`backend/domains/invoices/`**

| File | Purpose |
|---|---|
| `models.py` | `Invoice`, `InvoiceLine`, `EguiSubmission` models |
| `schemas.py` | `InvoiceCreate`, `InvoiceCreateLine`, `VoidInvoiceRequest`, `InvoiceLineResponse`, `InvoicePaymentSummary`, `EguiSubmissionResponse`, `InvoiceResponse`, `InvoiceListItem`, `InvoiceListResponse` |
| `routes.py` | `GET /` (list, filterable by customer_id, payment_status[], date range, search, sort), `POST /` (create), `GET /{id}`, `POST /{id}/egui/refresh`, `POST /{id}/void`, `GET /{id}/pdf`, `PUT/PATCH/DELETE /{id}` all return 405 (immutable) |
| `service.py` | Invoice creation with tax computation, void logic, payment summary computation |
| `pdf.py` | PDF generation |
| `tax.py` | Tax policy codes and computation |
| `enums.py` | `BuyerType` enum |
| `artifact_model.py`, `artifacts.py` | S3 artifact storage for invoice documents |
| `mcp.py`, `mig41.py` | MCP server, migration logic |

**Roles**: `admin|finance|sales`

**Key design**: Invoices are immutable after creation. Payment tracking is computed (not stored as separate Payment records linked to invoices). eGUI tracking is mock mode only in dev.

### Frontend
**`src/domain/invoices/`** — `InvoiceList.tsx`, `InvoiceDetail.tsx`, `CreateInvoicePage.tsx`, `types.ts`

**`src/pages/InvoicesPage.tsx`** — Routing shell with conditional detail/list view

**`src/lib/api/invoices.ts`** — `fetchInvoices`, `fetchInvoice`, `createInvoice`, `refreshInvoiceEguiStatus`, `fetchCustomerOutstanding`

### Gaps
- No invoice editing or cancellation (only void) — cannot correct an invoice, must void and re-issue
- No partial payment recording from invoice UI — payment recording is in the separate Payments domain
- No invoice approval workflow
- No credit note / invoice amendment domain
- eGUI refresh only works in mock mode; live mode returns 503

---

## Orders

### Backend
**`backend/domains/orders/`**

| File | Purpose |
|---|---|
| `schemas.py` | `OrderCreate`, `OrderCreateLine`, `OrderResponse`, `OrderLineResponse`, `OrderListItem/Response`, `OrderStatusUpdate`, `PaymentTermsItem/ListResponse`, `StockCheckResponse`, `WarehouseStockInfo`. `OrderStatus` enum: PENDING → CONFIRMED → SHIPPED → FULFILLED (or CANCELLED). `PaymentTermsCode`: NET_30, NET_60, COD |
| `routes.py` | `GET /payment-terms`, `GET /check-stock`, `POST /` (create, fires LINE notification async), `GET /`, `GET /{id}`, `PATCH /{id}/status` (transition), `DELETE /{id}` (sets CANCELLED) |
| `services.py` | `create_order`, `list_orders`, `get_order`, `update_order_status`, `check_stock_availability` |
| `handlers.py` | Event handlers |
| `order_confirmation.py` | Order confirmation logic |
| `reorder_point.py` | Reorder point computation |

**Roles**: read = `admin|warehouse|sales`; write = `admin|sales`

**Key design**: Order creation triggers a LINE webhook notification. Order status transitions are state-machine enforced (PENDING can go to CONFIRMED or CANCELLED, etc.). `invoice_id` field exists on order but no API to directly generate invoice from order.

### Frontend
**`src/domain/orders/`** — `OrderList.tsx`, `OrderDetail.tsx`, `OrderForm.tsx`, `types.ts`

**`src/pages/orders/`** — `OrdersPage.tsx`

**`src/lib/api/orders.ts`** — `fetchOrders`, `fetchOrder`, `createOrder`, `checkStock`, `updateOrderStatus`, `fetchPaymentTerms`

### Gaps
- No frontend for creating orders from existing customer — only `OrderForm` component may exist but needs verification
- No order-to-invoice conversion in UI — must create invoice separately
- No shipping/delivery tracking integration
- No order approval workflow
- No backorder management UI — `backorder_note` field exists but no dedicated UI

---

## Inventory

### Backend
**`backend/domains/inventory/`** — the largest and most complex domain

| Subdomain | Endpoints |
|---|---|
| **Warehouses** | `GET /warehouses`, `GET /warehouses/{id}`, `POST /warehouses` |
| **Transfers** | `POST /transfers`, `GET /transfers`, `GET /transfers/{id}` |
| **Physical Counts** | `POST /count-sessions`, `GET /count-sessions`, `GET /count-sessions/{id}`, `PATCH /count-sessions/{id}/lines/{id}`, `POST /count-sessions/{id}/submit`, `POST /count-sessions/{id}/approve` |
| **Products** | `POST /products`, `PUT /products/{id}`, `PATCH /products/{id}/status`, `GET /products/{id}` (detail), `GET /products/search`, `GET /products/{id}/stocks`, `GET /products/{id}/stock-history/{stock_id}`, `GET /products/{id}/monthly-demand`, `GET /products/{id}/planning-support`, `GET /products/{id}/sales-history`, `GET /products/{id}/top-customer`, `GET /products/{id}/suppliers`, `POST /products/{id}/suppliers`, `PATCH /products/{id}/suppliers/{sid}`, `DELETE /products/{id}/suppliers/{sid}`, `GET /products/{id}/audit-log`, `GET /products/{id}/aeo` (AEO content), `GET /products/{id}/jsonld` (schema.org) |
| **Categories** | Full CRUD + status patch |
| **Units of Measure** | Full CRUD + status patch |
| **Stock Adjustments** | `POST /adjustments` (with approval workflow for large qty changes) |
| **Reorder Alerts** | `GET /alerts/reorder`, `PUT /alerts/reorder/{id}/acknowledge`, `PUT /alerts/reorder/{id}/snooze`, `PUT /alerts/reorder/{id}/dismiss` |
| **Reorder Suggestions** | `GET /reorder-suggestions`, `POST /reorder-suggestions/orders` |
| **Reorder Points** | `POST /reorder-points/compute` (preview dry-run), `PUT /reorder-points/apply` |
| **Reports** | `GET /reports/below-reorder` (+ CSV export), `GET /reports/valuation` |
| **Suppliers** | Full CRUD + status |
| **Supplier Orders** | `POST /supplier-orders`, `GET /supplier-orders`, `GET /supplier-orders/{id}`, `PUT /supplier-orders/{id}/status`, `PUT /supplier-orders/{id}/receive` |
| **Reason Codes** | `GET /reason-codes` |

**Roles**: read = `admin|warehouse|sales`; write = `admin|warehouse`

### Frontend
**`src/pages/inventory/`** — extensive set of pages:
`BelowReorderReportPage`, `CategoriesPage`, `CountSessionDetailPage`, `CountSessionsPage`, `InventoryValuationPage`, `ProductDetailPage`, `ReorderSuggestionsPage`, `SupplierDetailPage`, `SuppliersPage`, `TransfersPage`, `UnitsPage`, `inventoryPageTabs.ts`

**`src/domain/inventory/`** — `components/`, `context/`, `hooks/`, `types.ts`, `utils.ts`, `inventory.css`

**`src/lib/api/inventory.ts`** — comprehensive API client

### Gaps
- **Manufacturing/BOM**: No Bill of Materials, no work orders, no production planning
- **Batch tracking**: No lot/batch numbers on stock
- **Expiration tracking**: No shelf-life / expiry date management
- **Multi-warehouse transfers**: Transfer endpoint exists but no UI for managing multi-warehouse stock views
- **Quality management**: No QC checkpoints, no inspection reports
- **Serial number tracking**: No individual serial number registry

---

## Payments

### Backend
**`backend/domains/payments/`**

| File | Purpose |
|---|---|
| `models.py` | `Payment` model — tenant_id, customer_id, invoice_id, amount, payment_date, payment_method, reference_number, notes, status, matched_at, suggested_invoice_id, is_manual_match |
| `schemas.py` | `PaymentCreate`, `PaymentCreateUnmatched`, `ManualMatchRequest`, `PaymentResponse`, `PaymentListItem`, `PaymentListResponse`, `ReconciliationResult` |
| `routes.py` | `POST /` (record payment against invoice), `GET /`, `GET /{id}`, `POST /unmatched` (record payment without invoice link), `POST /reconcile` (run auto-reconciliation), `POST /{id}/confirm-match` (accept suggested match), `POST /{id}/manual-match` (manual invoice assignment) |
| `services.py` | `record_payment`, `record_unmatched_payment`, `list_payments`, `get_payment`, `run_reconciliation`, `confirm_suggested_match`, `manual_match` |

**Roles**: `admin|finance`

**Key design**: Payments are recorded separately and then matched to invoices (auto or manual). Supports unmatched payments (payments received without known invoice reference).

### Frontend
**`src/pages/PaymentsPage.tsx`**, **`src/domain/payments/`** — components, types, hooks

**`src/lib/api/payments.ts`** — API client

### Gaps
- No dedicated "record payment" UI page — payment creation is likely done inline from invoice detail
- No payment method management (no CRUD for payment method types)
- No frontend reconciliation UI — `POST /reconcile` is API-only
- No partial payment recording from invoice context
- No payment advice / remittance slip generation

---

## Purchases

### Backend
**`backend/domains/purchases/`**

| File | Purpose |
|---|---|
| `models.py` | `SupplierInvoice` model — supplier_id, invoice_number, invoice_date, due_date, total_amount, status (open/paid/voided), line items |
| `schemas.py` | `SupplierInvoiceListItem`, `SupplierInvoiceListResponse`, `SupplierInvoiceResponse` |
| `routes.py` | `GET /supplier-invoices` (list with filters/sort/pagination), `GET /supplier-invoices/{id}` |
| `service.py` | `list_supplier_invoices`, `get_supplier_invoice` |

**Roles**: `admin|finance|warehouse`

**Read-only from API perspective** — supplier invoices are listed and viewed, but no create/update/void endpoints visible.

### Frontend
**`src/pages/PurchasesPage.tsx`**, **`src/domain/purchases/`** — components, types, hooks

### Gaps
- **No purchase creation** — only listing/viewing supplier invoices, no create, receive, or approve flow
- **No purchase request / purchase order lifecycle** — no PR → PO → GRN flow
- **No goods receipt**: supplier orders in inventory domain can receive stock, but no formal GRN linked to purchase
- **No landed cost calculation**
- **No 3-way matching** (PO → GRN → Supplier Invoice)

---

## Reports

### Backend
**`backend/domains/reports/`**

| Endpoint | Purpose |
|---|---|
| `GET /ar-aging` | AR aging report — aging buckets for customer receivables |
| `GET /ap-aging` | AP aging report — aging buckets for supplier payables |

**Roles**: `get_current_user` (any authenticated user)

### Frontend
**No dedicated reports pages** — reports are accessed via dashboard or inventory pages. No `src/pages/reports/` directory.

### Gaps
- No profit & loss statement (P&L / income statement)
- No balance sheet
- No cash flow statement beyond the dashboard's cash flow widget
- No trial balance
- No tax reports (VAT/GST)
- No financial report customization
- No report scheduling or subscriptions
- No report export beyond CSV from inventory

---

## Dashboard

### Backend
**`backend/domains/dashboard/`**

| Endpoint | Purpose |
|---|---|
| `GET /revenue-summary` | Revenue totals |
| `GET /kpi-summary` | KPIs (with 5-min cache) |
| `GET /top-products` | Top selling products (day/week period) |
| `GET /top-customers` | Top customers by revenue (month/quarter/year) |
| `GET /visitor-stats` | PostHog-powered visitor, inquiry, conversion stats |
| `GET /cash-flow` | Cash inflows/outflows over date range |
| `GET /gross-margin` | Gross margin data |
| `GET /revenue-trend` | Revenue over time (day/week/month granularity) |

### Frontend
**`src/pages/owner-dashboard/`** — dashboard page

**`src/lib/api/dashboard.ts`** — API client

### Gaps
- No goal / target tracking (vs. actual)
- No cohort analysis
- No customer acquisition analytics
- No product performance comparison

---

## Settings

### Backend
**`backend/domains/settings/`**

| File | Purpose |
|---|---|
| `models.py` | Settings model |
| `schemas.py` | `SettingItem`, `SettingSection`, `SettingUpdate` |
| `routes.py` | `GET /` (all settings by section), `GET /categories`, `GET /{key}`, `PATCH /{key}`, `DELETE /{key}` (reset to env default) |
| `service.py` | `get_all_settings`, `set_setting`, `reset_setting` |
| `seed.py` | Default settings seed |
| `introspection.py` | Schema introspection |

**Roles**: `owner|admin|finance`

### Frontend
**`src/pages/SettingsPage.tsx`**, **`src/lib/api/settings.ts`**

### Gaps
- No user-facing settings UI sections visible beyond the page shell
- No tenant / organization profile settings
- No user management UI (users domain exists in backend with routes but frontend pages not clearly mapped)

---

## Intelligence

### Backend
**`backend/domains/intelligence/`** — `routes.py`, `schemas.py`, `services.py` (no detailed routes read)

### Frontend
**`src/pages/IntelligencePage.tsx`** — separate intelligence/analytics page

### Gaps
- Not analyzed in detail; appears to be a separate analytics layer

---

## Additional Domains

| Domain | Notes |
|---|---|
| `backend/domains/health/` | Health check endpoints |
| `backend/domains/auth/` | Authentication |
| `backend/domains/users/` | User management |
| `backend/domains/audit/` | Audit logging |
| `backend/domains/approval/` | Approval workflow engine |
| `backend/domains/line/` | LINE webhook integration (notifies on new orders) |
| `backend/domains/aeo/` | AEO (Authorized Economic Operator) content generation |
| `backend/domains/product_analytics/` | Product analytics |
| `backend/domains/legacy_import/` | Legacy data import tool |
| `backend/domains/intelligence/` | Analytics/BI layer |

---

## Cross-Domain Gaps vs. ERP Standards

### Finance & Accounting
- **No multi-currency** support
- **No fixed assets** module (depreciation, asset register)
- **No tax engine** beyond Taiwan invoice tax codes — no VAT/GST reporting
- **No financial report builder** (P&L, balance sheet, cash flow statement)
- **No bank reconciliation** — payments exist but no bank feed import or matching

### Supply Chain
- **No manufacturing / BOM** — no work orders, routing, production planning
- **No batch/lot tracking** or expiration management
- **No serial number registry**
- **No quality management** (QC, inspections)
- **No freight management** / shipping integration

### Sales & CRM
- **No lead/oppportunity pipeline** — only customer records
- **No quote/quotation** module (orders directly)
- **No sales target / commission tracking**
- **No email integration** beyond LINE webhook

### Purchases
- **No purchase requisition** → PO → GRN flow
- **No 3-way matching**
- **No landed cost**

### HR / Organization
- **No employee records**
- **No role-based permissions beyond basic role strings** — no per-document permission rules
- **No leave/attendance**
- **No payroll**

### Infrastructure
- **No attachment/storage management** beyond invoice artifacts in S3
- **No print layout designer** — only hardcoded invoice PDF template
- **No workflow builder** — approval engine exists but no UI to configure workflows
- **No audit trail UI** — audit domain exists in backend but no dedicated frontend
- **No document versioning**
- **No integration framework** visible (MCP exists for AI, no iPaaS/API integration hub)
