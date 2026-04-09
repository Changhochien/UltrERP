# Story 3.7: Customer Account Statement (Receivables Ledger)

## Epic 3: Customer Management

### Story Goal

As a finance clerk,
I want to view a per-customer receivables ledger showing every invoice and payment,
So that I can answer customer queries about their balance and provide account statements.

---

## Story ID

**3.7** — maps to `3-7-customer-account-statement.md`

---

## Story Name

**Customer Account Statement — Receivables Ledger**

---

## User

Finance clerk, Admin, Owner

---

## Background

After Story 3.6, a sales rep can see a customer's overview, invoices, orders, and outstanding balance. However, there is no view that shows the running balance: every invoice (debit) and every payment (credit) in date order with a running balance column. This is the standard "account statement" format that finance teams use to answer customer balance questions and that owners use for AR health.

This builds on top of Story 3.6 (the detail page infrastructure).

---

## User Experience

### Route

`/customers/:customerId/statement` — accessible as a tab or sub-route within the Customer Detail Page (Story 3.6).

### Tab Name

`Statement` — added alongside Overview, Invoices, Orders, Outstanding tabs from Story 3.6.

### Statement Table Columns

| Date | Type | Reference | Description | Debit (NT$) | Credit (NT$) | Balance (NT$) |
|------|------|-----------|-------------|--------------|--------------|---------------|
|       |      |           |             | (Invoice amt) | (Payment amt) | Running bal |

- **Invoice lines** show invoice number, date, amount as **debit** (positive)
- **Payment lines** show payment date, invoice reference, amount as **credit** (negative / deducted)
- **Balance** is cumulative: starts at 0, increases with debits, decreases with credits
- Rows sorted by date ascending
- Current balance shown prominently at top or bottom

### Filters

- **Date range** — from / to date pickers (default: last 12 months)
- **Invoice status** — All / Open / Paid (default: All)

### Summary Box

Above the table:
- **Total Outstanding** (current balance)
- **Oldest Unpaid Invoice** (date and amount)
- **Average Days to Pay** (if payment data available)

### Actions

- **Print Statement** — opens print-optimized view (no interactive elements, clean layout)
- **Export CSV** — downloads statement as CSV file

---

## Backend API Requirements

### New Endpoint (required)

`GET /api/v1/customers/{customer_id}/statement`

Query params:
- `from` (date, optional) — start date
- `to` (date, optional) — end date

Response shape:
```json
{
  "customer_id": "uuid",
  "company_name": "string",
  "currency_code": "TWD",
  "opening_balance": "0.00",
  "current_balance": "15000.00",
  "lines": [
    {
      "date": "2026-01-15",
      "type": "invoice",
      "reference": "INV-2026-0001",
      "description": "Invoice INV-2026-0001",
      "debit": "50000.00",
      "credit": "0.00",
      "balance": "50000.00"
    },
    {
      "date": "2026-01-20",
      "type": "payment",
      "reference": "PAY-2026-0001",
      "description": "Payment for INV-2026-0001",
      "debit": "0.00",
      "credit": "35000.00",
      "balance": "15000.00"
    }
  ]
}
```

**Implementation approach:**
- Pull all invoices for the customer in the date range
- Pull all payments for those invoices
- Interleave by date, compute running balance
- Return opening_balance (sum of all invoices before `from` minus all payments before `from`)

### Alternative (if new endpoint not built yet)

Frontend computes the statement client-side from `GET /invoices?customer_id=` and `GET /payments?invoice_id=`. But this requires multiple round-trips and more frontend logic. Backend aggregation is preferred.

---

## Frontend Files to Create/Modify

### New Files

- `src/components/customers/CustomerStatementTab.tsx` — statement tab component with table and filters
- `src/components/customers/CustomerStatementTable.tsx` — table with running balance
- `src/lib/api/customers.ts` — add `getCustomerStatement(customerId, from?, to?)`

### Modified Files

- `src/pages/customers/CustomerDetailPage.tsx` (from Story 3.6) — add Statement tab
- `src/lib/routes.ts` — optionally add `CUSTOMER_STATEMENT_ROUTE` if it's a standalone page

---

## Acceptance Criteria

### Functional

- [ ] Statement tab visible on Customer Detail Page
- [ ] Table shows all invoices and payments for the customer in date order
- [ ] Running balance updates correctly after each line
- [ ] Date range filter filters the statement to the selected period
- [ ] Print view is clean, no interactive elements, company name and date range visible
- [ ] CSV export downloads correctly formatted file
- [ ] Opening balance reflects the cumulative balance before the selected date range
- [ ] Current balance at top matches the Outstanding tab total

### Edge Cases

- [ ] Customer with no invoices: shows empty state "No transactions found"
- [ ] Customer with invoices but no payments: balance = sum of all invoices
- [ ] Customer with payments covering all invoices: balance = 0
- [ ] Date range with no transactions: shows empty state
- [ ] Payment linked to invoice shows both lines with correct references

### Non-Functional

- [ ] Statement loads in < 2 seconds for customers with up to 500 transaction lines
- [ ] Running balance never goes negative (credits cannot exceed debits)

---

## Status

**Status:** `backlog`
**Epic:** Epic 3 — Customer Management
**Stories this blocks:** None
**Stories this is blocked by:** Story 3.6 (Customer Detail Page)
