# Story 3.6: Customer Detail Page

## Epic 3: Customer Management

### Story Goal

As a sales rep,
I want to view a full customer detail page with invoices, orders, and outstanding balance,
So that I can manage the complete customer relationship without being limited by a modal dialog.

---

## Story ID

**3.6** — maps to `3-6-customer-detail-page.md`

---

## Story Name

**Customer Detail Page — Full View with Invoice and Order Tabs**

---

## User

Sales rep, Finance clerk, Admin

---

## Background

The current `CustomerDetailDialog` is a modal that shows basic customer fields. It is insufficient for real customer management. Orders and Invoices each have full detail pages (`OrderDetail`, `InvoiceDetail`). Customers should follow the same pattern.

The backend already supports all needed APIs:
- `GET /api/v1/customers/{id}` — customer details
- `GET /api/v1/customers/{id}/outstanding` — outstanding balance summary
- `GET /api/v1/invoices?customer_id={id}` — invoices for a customer
- `GET /api/v1/orders?customer_id={id}` — orders for a customer

---

## User Experience

### Route

`/customers/:customerId` — new route, analogous to `/orders/:orderId` and `/invoices/:invoiceId`.

### Page Structure

```
┌─ Header ──────────────────────────────────────────────────────┐
│  ← Back to Customers   [Company Name]   [Status Badge] [BAN] │
│                        [Edit] [Suspend] [Delete]              │
├─ Tabs ────────────────────────────────────────────────────────┤
│  [Overview] [Invoices] [Orders] [Outstanding]               │
├─ Tab Content ─────────────────────────────────────────────────┤
│  (varies by tab — see below)                                  │
└──────────────────────────────────────────────────────────────┘
```

### Tab: Overview

Displays:
- Company name, business number (normalized)
- Billing address
- Contact name, phone, email
- Credit limit
- Status (active / inactive / suspended)
- Created at, updated at

### Tab: Invoices

Paginated list of invoices issued to this customer, with:
- Invoice number, date, amount, status
- Clicking a row navigates to invoice detail (`/invoices/:invoiceId`)
- Empty state if no invoices

### Tab: Orders

Paginated list of orders placed by this customer, with:
- Order number, date, amount, status
- Clicking a row navigates to order detail (`/orders/:orderId`)
- Empty state if no orders

### Tab: Outstanding

Shows `CustomerOutstanding` summary card:
- Total outstanding amount
- Invoice count
- Overdue count and overdue amount (highlighted if > 0)

### Header Actions

- **Edit** — opens `EditCustomerDialog` (existing component)
- **Suspend** — changes customer status to `suspended` via PATCH
- **Delete** — soft delete or archive (confirm dialog); only if no outstanding balance
- **Back** — returns to `/customers`

---

## Backend API Requirements

### New Endpoint (optional but recommended)

`GET /api/v1/customers/{customer_id}/invoices` — returns invoices filtered by customer_id.

**If not implemented:** frontend calls `GET /api/v1/invoices?customer_id={id}` (existing query param support).

### Existing endpoints used

| Endpoint | Usage |
|----------|-------|
| `GET /api/v1/customers/{id}` | Customer details |
| `GET /api/v1/customers/{id}/outstanding` | Outstanding summary |
| `GET /api/v1/invoices?customer_id={id}` | Invoice list (if no dedicated endpoint) |
| `GET /api/v1/orders?customer_id={id}` | Order list |
| `PATCH /api/v1/customers/{id}` | Update status (suspend) |

---

## Frontend Files to Create/Modify

### New Files

- `src/pages/customers/CustomerDetailPage.tsx` — new page component
- `src/components/customers/CustomerDetailHeader.tsx` — header with actions (optional)
- `src/components/customers/CustomerInvoicesTab.tsx` — invoice list tab
- `src/components/customers/CustomerOrdersTab.tsx` — order list tab
- `src/components/customers/CustomerOutstandingTab.tsx` — outstanding tab
- `src/lib/api/customers.ts` — add `getCustomerInvoices(customerId)` and `getCustomerOrders(customerId)` if needed

### Modified Files

- `src/lib/routes.ts` — add `CUSTOMER_DETAIL_ROUTE = "/customers/:customerId"`
- `src/App.tsx` — add route for `CUSTOMER_DETAIL_ROUTE`
- `src/components/customers/CustomerResultsTable.tsx` — update row click to navigate to detail page instead of opening modal
- `src/components/customers/CustomerDetailDialog.tsx` — either remove or repurpose (existing dialog was modal-only)
- `src/pages/customers/CustomerListPage.tsx` — may need refresh after edit

### i18n

Add keys for new page and tab labels in `customer.detailPage.*` namespace (both en and zh-Hant).

---

## Acceptance Criteria

### Functional

- [ ] `GET /customers/:customerId` renders the customer detail page
- [ ] Overview tab shows all customer fields (company, BAN, address, contact, credit limit, status)
- [ ] Invoices tab shows paginated list of invoices for the customer
- [ ] Orders tab shows paginated list of orders for the customer
- [ ] Outstanding tab shows outstanding balance summary (total, count, overdue)
- [ ] Edit button opens existing `EditCustomerDialog`; after save, page refreshes
- [ ] Suspend button changes status to `suspended` with confirmation
- [ ] Back button returns to `/customers`
- [ ] Clicking invoice row navigates to `/invoices/:invoiceId`
- [ ] Clicking order row navigates to `/orders/:orderId`
- [ ] Navigating directly to `/customers/:customerId` loads correct data
- [ ] 404 or error state if customer does not exist

### Non-Functional

- [ ] Page follows existing UI patterns (shadcn components, tab layout)
- [ ] Loading skeletons shown while data fetches
- [ ] Error state shown if API call fails
- [ ] Empty state shown when no invoices / no orders / no outstanding
- [ ] All text is i18n-compatible (English + Traditional Chinese)

### URL / Navigation

- [ ] Route `CUSTOMER_DETAIL_ROUTE = "/customers/:customerId"` registered in `routes.ts`
- [ ] Route mounted in `App.tsx` with same `ProtectedAppRoute` guard as other customer routes
- [ ] `CustomerResultsTable` row click navigates to detail page
- [ ] Shell header shows "Customers / [Company Name]" when on detail page

---

## Status

**Status:** `backlog`
**Epic:** Epic 3 — Customer Management
**Stories this blocks:** None directly (follows Story 3.5)
**Stories this is blocked by:** None
