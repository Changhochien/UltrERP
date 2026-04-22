# Epic 34: Taiwan Localization Plus

## Epic Goal

Extend UltrERP's Taiwan-specific capabilities beyond e-invoice and LINE messaging with payment gateway integrations (LINE Pay, ECPay), local banking reconciliation, and optional logistics API connectivity — providing a complete Taiwan e-commerce and payment ecosystem that differentiates UltrERP from generic ERP solutions.

## Business Value

- Customers gain familiar local payment options (LINE Pay, ECPay) increasing checkout conversion.
- Finance teams can reconcile Taiwan bank statements without manual data entry.
- E-commerce and POS operations can connect to local logistics providers for streamlined fulfillment.
- Taiwan banking integration completes the payment-to-reconciliation cycle for domestic transactions.
- UltrERP achieves differentiated Taiwan market fit beyond what ERPNext or generic regional ERPs offer.

## Scope

**Backend (LINE Pay):**
- LINE Pay API integration for payment initiation and confirmation.
- LINE Pay refund processing.
- Transaction status tracking and webhook handling.

**Backend (ECPay):**
- ECPay payment gateway integration (all-in-one, CVS, barcode).
- ECPay transaction query and refund APIs.
- Payment status synchronization.

**Backend (Taiwan Banking):**
- Taiwan bank statement import (CSV,固定格式).
- Bank account reconciliation with payment records.
- Reconciliation reporting and exception handling.

**Backend (Taiwan Logistics - Optional):**
- Taiwan logistics provider API integration (HCT, 黑貓宅急便, etc.).
- Shipping order creation and tracking.
- Label generation integration.

**Frontend:**
- Payment gateway configuration workspace.
- Bank reconciliation UI with matching and exception handling.
- Logistics integration settings and shipping order management.
- Payment status dashboards for LINE Pay and ECPay transactions.

**Data Model:**
- Payment Gateway Configuration (LINE Pay merchant ID, secret, sandbox/production).
- ECPay Merchant Configuration (Merchant ID, Hash key, Hash IV).
- Bank Account and Bank Statement records.
- Bank Reconciliation Line and Match Status.
- Logistics Provider Configuration and Shipping Order.

## Non-Goals

- Full accounting integration with LINE Pay merchant settlements (future Epic 26 work).
- Cross-border payment processing beyond Taiwan domestic transactions.
- All Taiwan logistics providers (focus on major carriers first; extendable architecture).
- LINE Official Account management beyond payment notification integration.
- Credit card acquiring directly (LINE Pay and ECPay handle this).

## Technical Approach

- Treat LINE Pay and ECPay as external payment gateways with callback (webhook) handling.
- Use outbox/inbox pattern for reliable webhook processing (from Epic 1 patterns).
- Implement bank statement import with configurable field mapping per bank.
- Use fuzzy matching for bank reconciliation to handle minor amount discrepancies.
- Keep logistics integration pluggable with provider-specific adapters.
- All payment gateway credentials stored securely (not in code, use environment/config).

## Key Constraints

- LINE Pay and ECPay require merchant accounts; integration should support sandbox testing.
- Taiwan bank formats vary by bank; start with common formats (CSV) and extend.
- Logistics API integration is optional; implement if business need is confirmed.
- Payment and reconciliation work should integrate with Epic 6 payment recording and Epic 26 banking workflows.
- Epic 38 is high value but should not block core accounting foundations.

## Dependency and Phase Order

1. LINE Pay and ECPay integrations land after Epic 2 (Invoice) and Epic 6 (Payments) to integrate with existing payment flows.
2. Taiwan banking reconciliation lands after Epic 26 (GL & Banking) for account and journal integration.
3. Logistics integration can land independently or after Epic 21 (Orders) for shipping order creation.
4. Epic 34 stories can be split across teams (payment gateways vs. banking) if dependencies are met.

---

## Story 34.1: LINE Pay Integration
- Add LINE Pay as a payment method option for orders and invoices.
- Implement payment initiation: create LINE Pay payment URL/QR code for customer redirect.
- Handle LINE Pay payment confirmation callback (server-side notification).
- Support LINE Pay refund processing for approved payments.
- Track LINE Pay transaction status: Pending, Confirmed, Cancelled, Refunded.
- Store LINE Pay transaction IDs for reconciliation and dispute handling.

**Acceptance Criteria:**

- Given a customer selects LINE Pay at checkout, the system generates a valid LINE Pay payment URL.
- Given a LINE Pay payment is confirmed, the corresponding order/invoice status updates automatically.
- Given a refund is requested, the system processes LINE Pay refund API and updates transaction status.
- Given a LINE Pay webhook fails to process, the system retries using outbox pattern and logs the failure.
- Given finance reviews LINE Pay transactions, they see transaction ID, amount, status, and timestamp.

---

## Story 34.2: ECPay Integration

- Add ECPay as a payment method (all-in-one, CVS, barcode options).
- Implement ECPay payment initiation: generate payment form or CVS/barcode codes.
- Handle ECPay payment notification callback (server-side).
- Support ECPay query API to check payment status.
- Implement ECPay refund and cancellation processing.
- Track ECPay merchant trade numbers and trade status.

**Acceptance Criteria:**

- Given a customer selects ECPay all-in-one at checkout, the system generates an ECPay payment form with correct parameters.
- Given a customer selects CVS payment, the system returns valid CVS code or barcode data.
- Given an ECPay payment notification arrives, the system updates the order/invoice status accordingly.
- Given a finance user queries an ECPay transaction, the system shows current payment status from ECPay.
- Given a refund is initiated, the system calls ECPay refund API and updates local transaction records.

---

## Story 34.3: Taiwan Banking Reconciliation

- Add bank statement import from Taiwan bank CSV exports (configurable per bank).
- Parse bank statement lines: transaction date, description, amount, balance.
- Auto-match bank transactions against payment records by amount and date range.
- Support manual matching for unmatched transactions.
- Generate reconciliation reports: matched, unmatched, discrepancies.
- Flag unusual patterns: duplicate payments, missing receipts, amount mismatches.

**Acceptance Criteria:**

- Given a bank statement CSV is imported, the system parses transaction date, description, debit, and credit correctly.
- Given a bank transaction matches a payment record by amount and date, the system auto-links them.
- Given a bank transaction does not auto-match, a user can manually select the corresponding payment record.
- Given reconciliation is complete, the report shows matched transactions, unmatched deposits, and unmatched withdrawals.
- Given a discrepancy exists (amount differs by more than tolerance), the system flags it for review before closing reconciliation.
- Given multiple bank accounts exist, each has its own reconciliation workspace.

---

## Story 34.4: Taiwan Logistics API (Optional)

- Add Taiwan logistics provider configurations (HCT, 黑貓宅急便, other major carriers).
- Implement shipping order creation via logistics provider API.
- Support shipping label generation or URL retrieval.
- Track shipment status via logistics provider tracking API.
- Integrate shipping status with order delivery tracking.
- Handle logistics API errors gracefully with retry and manual fallback.

**Acceptance Criteria:**

- Given an order is ready for shipment, a warehouse staff can create a shipping order with the selected logistics provider.
- Given a shipping order is created, the system generates a shipping label or provides label print instructions.
- Given a shipment is in transit, tracking status updates reflect in the order view.
- Given a logistics API call fails, the system logs the error and allows manual retry.
- Given multiple logistics providers are configured, staff can select the appropriate carrier per order.
- Given a shipment is delivered, the order delivery status updates automatically if tracking API supports it.

**Note:** This story is marked optional based on business need confirmation. If logistics integration is not required for MVP, defer to post-MVP phase.
