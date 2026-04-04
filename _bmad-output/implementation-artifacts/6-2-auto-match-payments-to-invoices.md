# Story 6.2: Auto-Match Payments to Open Invoices

Status: ready-for-dev

## Story

As a system,
I want to auto-match incoming payments to open invoices during reconciliation,
So that finance doesn't have to manually match each payment.

## Acceptance Criteria

**AC1:** Auto-match by exact customer + amount
**Given** an unmatched payment exists (invoice_id is NULL)
**When** reconciliation runs
**Then** the system searches for open invoices where:
  - customer_id matches the payment's customer_id
  - invoice outstanding balance == payment amount (exact match)
  - invoice status is "issued" (not voided/paid)
**And** if exactly one match found: payment is allocated to that invoice
**And** invoice outstanding balance is updated accordingly

**AC2:** Auto-match by customer + date proximity
**Given** an unmatched payment exists and no exact amount match is found
**When** reconciliation runs
**Then** the system searches for open invoices where:
  - customer_id matches
  - invoice date is within 90 days of payment date
  - invoice outstanding balance >= payment amount
**And** matches are ranked by date proximity (closest invoice_date to payment_date first)
**And** the top candidate is presented as a "suggested match" (not auto-allocated)

**AC3:** Flag unmatched payments
**Given** a payment has no auto-match candidate
**When** reconciliation completes
**Then** the payment is flagged with status "unmatched"
**And** appears in the unmatched payments list for manual review

**AC4:** Invoice fully paid on match
**Given** a payment is matched to an invoice
**When** the match allocates the payment
**Then** if payment amount == invoice outstanding: invoice status → "paid"
**And** if payment amount < invoice outstanding: invoice stays "issued" with reduced balance
**And** the payment record's `invoice_id` is set to the matched invoice

**AC5:** Reconciliation endpoint
**Given** finance triggers reconciliation
**When** the reconciliation service runs
**Then** it processes all payments with invoice_id = NULL
**And** returns a summary: { matched_count, suggested_count, unmatched_count, details[] }
**And** each detail includes: payment_ref, match_type ("auto"|"suggested"|"unmatched"), invoice_number (if matched)

**AC6:** Manual match override
**Given** a payment is unmatched or has a suggested match
**When** finance manually assigns it to an invoice
**Then** the system validates: invoice exists, belongs to same customer, has sufficient outstanding balance
**And** the payment is allocated to that invoice
**And** audit_log entry created with action "PAYMENT_MATCHED_MANUAL"

**AC7:** Reconciliation audit trail
**Given** reconciliation runs
**When** any payment is auto-matched
**Then** audit_log entries are created with:
  - action: "PAYMENT_MATCHED_AUTO"
  - entity_type: "payment"
  - entity_id: payment.id
  - after_state: `{ "invoice_id": "...", "match_type": "exact_amount" | "date_proximity" }`

**AC8:** Reconciliation UI
**Given** I navigate to the reconciliation screen
**When** I click "Run Reconciliation"
**Then** the system processes unmatched payments
**And** displays results grouped by: auto-matched, suggested, unmatched
**And** suggested matches show a "Confirm" / "Reject" button
**And** unmatched payments show a manual invoice selector

## Tasks / Subtasks

- [ ] **Task 1: Add Reconciliation Fields to Payment Model** (AC1, AC3)
  - [ ] Migration `ll222nn22o54_add_payment_reconciliation_fields.py` chaining from payments table migration
  - [ ] Add columns to `payments` table:
    ```sql
    match_status    VARCHAR(20) NOT NULL DEFAULT 'pending'
    match_type      VARCHAR(20)    -- 'exact_amount', 'date_proximity', 'manual', NULL
    matched_at      TIMESTAMPTZ
    suggested_invoice_id UUID FK → invoices.id ON DELETE SET NULL  -- stores the suggested match before confirmation
    ```
  - [ ] `suggested_invoice_id` stores which invoice was suggested during reconciliation. On confirm, `invoice_id` is set from `suggested_invoice_id` and `suggested_invoice_id` is cleared.
  - [ ] `match_status` values: "pending" (newly created with invoice_id), "unmatched" (no match found), "matched" (allocated), "suggested" (candidate found but not confirmed)
  - [ ] Add index: `ix_payments_match_status` (tenant_id, match_status)
  - [ ] **CRITICAL:** Payments created via Story 6.1 (with explicit invoice_id) should have match_status = "matched" and match_type = "manual" by default — they are already allocated

- [ ] **Task 2: Reconciliation Service** (AC1, AC2, AC3, AC4, AC5, AC7)
  - [ ] Add to `backend/domains/payments/services.py`:
  - [ ] Implement `run_reconciliation(session, tenant_id, actor_id) -> ReconciliationResult`:
    - Call `await set_tenant(session, tid)`
    - Within `async with session.begin():`
    - Query all payments where `invoice_id IS NULL AND match_status = 'unmatched'`
    - For each unmatched payment:
      1. **Exact match:** Query invoices where customer_id matches AND outstanding == amount
         - Outstanding computed as: `invoice.total_amount - COALESCE(SUM(allocated_payments.amount), 0)`
         - Use subquery for outstanding calculation
         - If exactly 1 match: auto-allocate (set invoice_id, match_status="matched", match_type="exact_amount")
         - If multiple exact matches: treat as "suggested" with first (oldest invoice)
      2. **Date proximity match:** (if no exact match) Query invoices where customer_id matches AND outstanding >= amount AND date within 90 days
         - Order by ABS(invoice_date - payment_date) ASC
         - If candidates exist: mark first as "suggested" (match_status="suggested")
      3. **No match:** Leave as match_status="unmatched"
    - For each auto-match: update invoice status if fully paid, create audit_log
    - Return `ReconciliationResult(matched=[], suggested=[], unmatched=[])`

  - [ ] Implement `confirm_suggested_match(session, tenant_id, payment_id, actor_id) -> Payment`:
    - Validate payment has match_status="suggested" and a suggested invoice_id
    - Allocate the payment (same logic as auto-match allocation)
    - Update match_status to "matched", match_type to keep original type
    - Create audit_log entry

  - [ ] Implement `manual_match(session, tenant_id, payment_id, invoice_id, actor_id) -> Payment` (AC6):
    - Validate payment is unmatched/suggested
    - Validate invoice belongs to same customer
    - Validate invoice has sufficient outstanding balance
    - Allocate payment to invoice
    - match_status="matched", match_type="manual"
    - Create audit_log entry

- [ ] **Task 3: Reconciliation Schemas** (AC5)
  - [ ] Add to `backend/domains/payments/schemas.py`:
  - [ ] `ReconciliationResultItem(BaseModel)`: payment_ref, match_status, match_type, invoice_number (nullable), suggested_invoice_number (nullable)
  - [ ] `ReconciliationResult(BaseModel)`: matched_count, suggested_count, unmatched_count, details: list[ReconciliationResultItem]
  - [ ] `ManualMatchRequest(BaseModel)`: invoice_id: uuid.UUID

- [ ] **Task 4: Reconciliation Routes** (AC5, AC6)
  - [ ] Add to `backend/domains/payments/routes.py`:
  - [ ] POST `/reconcile` — triggers reconciliation, returns ReconciliationResult
  - [ ] POST `/{payment_id}/confirm-match` — confirms a suggested match
  - [ ] POST `/{payment_id}/manual-match` — manually assigns invoice, accepts ManualMatchRequest body

- [ ] **Task 5: Update record_payment for match_status** (AC1)
  - [ ] In `record_payment()` from Story 6.1: when creating payment WITH invoice_id (direct recording), set:
    - `match_status = "matched"`
    - `match_type = "manual"`
    - `matched_at = datetime.now(UTC)`
  - [ ] When creating payment WITHOUT invoice_id (for reconciliation flow): set:
    - `match_status = "unmatched"`
    - `match_type = None`
  - [ ] Add `PaymentCreateUnmatched(BaseModel)` schema for unmatched payments:
    - customer_id: uuid.UUID (required when no invoice_id)
    - amount, payment_method, payment_date, reference_number, notes

- [ ] **Task 6: Frontend — Reconciliation Screen** (AC8)
  - [ ] Create `src/domain/payments/components/ReconciliationScreen.tsx`:
    - "Run Reconciliation" button triggers POST /reconcile
    - Results displayed in 3 sections: Auto-Matched, Suggested, Unmatched
    - Auto-matched: read-only confirmation list
    - Suggested: each row has "Confirm" and "Reject" buttons
    - Unmatched: each row has invoice selector dropdown for manual match
  - [ ] Create `src/domain/payments/hooks/useReconciliation.ts`:
    - `useRunReconciliation()` — mutation hook for POST /reconcile
    - `useConfirmMatch(paymentId)` — mutation hook for POST /confirm-match
    - `useManualMatch(paymentId)` — mutation hook for POST /manual-match

- [ ] **Task 7: Frontend — Unmatched Payment Entry** (AC8)
  - [ ] Create `src/domain/payments/components/RecordUnmatchedPayment.tsx`:
    - Form for recording payments without a specific invoice (bank deposits, etc.)
    - Required: customer_id (searchable dropdown), amount, method, date
    - After creation, payment appears in next reconciliation run

- [ ] **Task 8: Backend Tests** (AC1-AC7)
  - [ ] Create `backend/tests/domains/payments/test_reconciliation.py`
  - [ ] Test: exact amount match — single invoice matched
  - [ ] Test: exact amount match — multiple invoices, first suggested
  - [ ] Test: date proximity match — closest date suggested
  - [ ] Test: no match — payment stays unmatched
  - [ ] Test: auto-match marks invoice as paid when fully covered
  - [ ] Test: confirm suggested match
  - [ ] Test: manual match validates customer and outstanding
  - [ ] Test: manual match rejects cross-customer allocation
  - [ ] Test: reconciliation creates audit_log entries
  - [ ] Test: reconciliation returns correct summary counts

- [ ] **Task 9: Frontend Tests** (AC8)
  - [ ] Create `src/domain/payments/__tests__/ReconciliationScreen.test.tsx`
  - [ ] Test: reconciliation results render in correct sections
  - [ ] Test: confirm match calls API and refreshes
  - [ ] Test: manual match shows invoice selector

## Dev Notes

### Architecture Compliance

- **Domain event pattern:** Architecture §4.4 defines `PaymentReceived` → "Reconcile invoice" as a domain event side effect. For MVP, reconciliation is triggered manually via API endpoint. Future: integrate with outbox pattern for automatic reconciliation on payment creation.
- **MCP tool:** Architecture §6.5 defines `payments.reconcile` — auto-match payments to invoices (scopes: payments:write). The reconciliation endpoint maps to this MCP tool.
- **Reconciliation matching algorithm:** Customer → Amount → Date range (from epics.md acceptance criteria). Implementation uses a 2-tier strategy: exact match first, then date proximity.

### Outstanding Balance Computation

- **CRITICAL:** Outstanding balance is computed, not stored. Formula: `invoice.total_amount - SUM(payments.amount WHERE payments.invoice_id = invoice.id AND payments.match_status = 'matched')`
- This avoids data inconsistency between stored balance and actual payments
- Use a subquery or scalar subquery in SQLAlchemy for efficient computation
- For the reconciliation matching query, compute outstanding inline:
  ```python
  outstanding_subq = (
      select(func.coalesce(func.sum(Payment.amount), Decimal('0')))
      .where(Payment.invoice_id == Invoice.id, Payment.match_status == 'matched')
      .correlate(Invoice)
      .scalar_subquery()
  )
  # Then: Invoice.total_amount - outstanding_subq == payment.amount
  ```

### Reconciliation Design Decisions

- **Batch processing:** Reconciliation processes ALL unmatched payments in a single transaction
- **90-day window:** Date proximity matching uses 90 days as the default window — configurable later
- **No split matching:** One payment maps to one invoice (not split across invoices). Multi-invoice allocation is a future enhancement.
- **Idempotency:** Running reconciliation multiple times is safe — already-matched payments are skipped
- **Match status flow:** unmatched → matched (auto) / suggested → matched (confirmed) / matched (manual)

### Critical Warnings

- **Watch for N+1 queries** — when processing multiple unmatched payments, batch the outstanding balance computation rather than querying per-payment
- **Lock invoices during reconciliation** — use `with_for_update()` on invoice rows to prevent concurrent payment recording during reconciliation
- **Decimal precision** — all amount comparisons must use `Decimal`. Never compare with float. SQL `NUMERIC(20,2)` maps to Python `Decimal`
- **set_tenant before ALL queries** — including the initial unmatched payments query
- **Customer_id validation** — unmatched payments must have customer_id set (required for matching). Enforce this in schema validation.

### Project Structure Notes

- **No new files** needed beyond Story 6.1 directory structure
- Additional files:
  - `backend/tests/domains/payments/test_reconciliation.py` — new test file
  - `src/domain/payments/components/ReconciliationScreen.tsx` — new component
  - `src/domain/payments/hooks/useReconciliation.ts` — new hook
  - `src/domain/payments/components/RecordUnmatchedPayment.tsx` — new component
- Migration: `migrations/versions/ll222nn22o54_add_payment_reconciliation_fields.py`

### Previous Story Intelligence

- **Story 6.1 dependency:** This story extends the Payment model and service from Story 6.1. The migration chains from 6.1's migration.
- **Invoice status "paid":** Story 6.1 introduces the "paid" status for invoices. This story's reconciliation must use the same transition logic.
- **Outstanding balance pattern:** Reuse the outstanding balance computation from Story 6.1's `record_payment()` service function.
- **Test pattern:** Follow `FakeAsyncSession` with `queue_scalar(None)` for set_tenant calls.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 6.2] Auto-match by customer → amount → date range
- [Source: docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md#4.4] PaymentReceived → Reconcile invoice
- [Source: docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md#6.5] payments.reconcile MCP tool
- [Source: docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md#4.5] Shadow-mode reconciliation: payment_allocation_mismatch is severity-1
- [Source: _bmad-output/planning-artifacts/prd.md#Payments] FR14: System auto-matches payments to open invoices
- [Source: backend/domains/orders/services.py] Set_tenant + session.begin() + with_for_update() patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (via GitHub Copilot)

### Completion Notes List

- Story designed with 2-tier matching algorithm (exact → date proximity) per epics.md AC
- Outstanding balance computed dynamically to avoid stored-balance drift
- Reconciliation idempotency ensured by match_status state machine
- Cross-referenced with architecture domain events and MCP tool contracts
