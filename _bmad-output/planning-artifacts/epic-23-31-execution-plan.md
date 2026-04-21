# Epic 23-31 Gap Closure Sequence

Date: 2026-04-20
Project: UltrERP
Author: GitHub Copilot

## 1. Decision Summary

Epic 21 and Epic 22 are necessary, but they are not sufficient to close the validated ERPnext gap.

After Epic 21 and Epic 22, the next implementation sequence should:

- close the missing pre-sale CRM pipeline before widening the order surface further
- close the purchase cycle with sourcing, purchase order, and receipt workflows
- add currency-aware commercial foundations before full dual-currency accounting
- land a minimally viable GL backbone before attempting ERPnext-style accounting parity
- add manufacturing, workforce, service, and traceability in a second wave
- defer the longest-tail commercial and asset utilities until the operational core is stable

This keeps ownership clean:

- Epic 21 owns order-domain workflow semantics
- Epic 22 owns reusable frontend primitives and shared UI architecture
- Epics 23-31 own the validated domain gaps that remain after orders and shared UI are stabilized

## 2. Recommended Delivery Order

### Wave 1: Revenue pipeline and commercial foundations

1. Epic 23 - CRM Foundation and Quotation Pipeline
2. Epic 25 - Multi-Currency, Payment Terms, and Commercial Defaults

Reason:

- The validated report identifies the missing pre-sale pipeline as the most fundamental commercial gap.
- Multi-currency and reusable payment terms are cross-cutting commercial primitives that should land before deeper accounting automation.

### Wave 2: Purchase-to-pay operations

3. Epic 24 - Supplier Sourcing, Purchase Orders, and Goods Receipt

Reason:

- RFQ, supplier quotations, purchase orders, and receipts close the inbound operations gap without waiting on full GL or manufacturing parity.
- Procurement can rely on existing suppliers, products, and warehouses already present in UltrERP.

### Wave 3: Finance backbone

4. Epic 26 - General Ledger, Banking, and Core Financial Reports

Reason:

- The roadmap correction is explicit: minimally viable GL is medium effort and should land before full ERPnext-style accounting automation.
- Banking, collections, and finance reports depend on a ledger foundation more than they depend on manufacturing.

### Wave 4: Production and people foundations

5. Epic 27 - Manufacturing Foundation
6. Epic 28 - Workforce, Contacts, and Service Desk Foundations

Reason:

- Manufacturing and workforce/service foundations are validated Phase 2 gaps that do not need to block Wave 1 revenue and procurement work.
- Epic 28 also gives later portal, support, and omnichannel work a shared people/contact base.

### Wave 5: Quality and traceability

7. Epic 29 - Quality Control, Traceability, and Warehouse Mobility

Reason:

- ERPnext's BOM-to-quality and warehouse traceability patterns become materially more valuable after manufacturing, procurement, and shared contacts are in place.

### Wave 6: Customer-facing extension work

8. Epic 30 - Customer Operations and Omnichannel Engagement

Reason:

- POS, loyalty, recurring documents, customer portal, and outbound engagement are important, but they should extend a stable commercial and accounting core instead of compensating for missing fundamentals.

### Wave 7: Long-tail operations and compliance

9. Epic 31 - Assets, Regional Compliance, and Administrative Controls

Reason:

- Asset maintenance, regional compliance packs, fleet/admin utilities, and deletion-grade audit controls are real gaps, but they should not delay the higher-value operational core.

## 3. Gap Coverage Map

| Validated Gap Cluster | Owning Epic |
|---|---|
| Lead / Opportunity / Quotation | Epic 23 |
| Customer group, territory, sales stages, CRM attribution setup | Epic 23 |
| RFQ / Supplier Quotation / Purchase Order / Goods Receipt | Epic 24 |
| Procurement lineage and three-way-match-ready controls | Epic 24 |
| Multi-currency phase 1 | Epic 25 |
| Payment Terms Template builder and commercial defaults | Epic 25 |
| Chart of Accounts / Journal Entry / GL Entry | Epic 26 |
| P&L / Balance Sheet / Trial Balance / banking / dunning | Epic 26 |
| BOM / Work Order / production planning | Epic 27 |
| Employee / contact-person CRUD / timesheets / issue-SLA | Epic 28 |
| Quality inspection / serial-batch / barcode / warehouse mobility | Epic 29 |
| POS / portal / loyalty / recurring docs / omnichannel outreach | Epic 30 |
| Assets / regional tax packs / fleet / admin utilities | Epic 31 |

Items that stay owned by existing epics:

- commission tracking and order metadata remain with Epic 21
- toast, breadcrumb, date picker, Zod forms, and shared tables remain with Epic 22

## 4. Minimum Cross-Epic Gates

The only gates that should be treated as hard blockers are:

- Epic 22 stories for toast, breadcrumb, date picker, and shared Zod form architecture before the main user-facing screens in Epic 23, Epic 24, and Epic 25
- Epic 23 before the CRM-dependent engagement work inside Epic 30
- Epic 24 before the purchase-side auto-posting and three-way-match features in Epic 26
- Epic 25 before dual-currency finance automation in Epic 26
- Epic 27 before BOM-driven quality hooks in Epic 29
- Epic 28 before customer portal and issue-routing work in Epic 30

## 5. Explicit Do / Do Not Guidance

### Do

- do treat Epic 23 and Epic 24 as the next operationally meaningful gaps after Epics 21 and 22
- do keep Epic 26 minimally viable first instead of chasing full ERPnext accounting parity immediately
- do keep Phase 1 focused on revenue, procurement, and commercial foundations
- do reuse Epic 22 primitives in every new domain surface instead of creating local UI systems

### Do Not

- do not block CRM or procurement delivery on full GL automation
- do not let Epic 26 turn into a single-shot rewrite of `accounts_controller.py`
- do not let purchase-order implementation depend on manufacturing scope that ERPnext itself treats separately
- do not assume purchase-order or purchase-receipt field parity from the local reference checkout without re-verifying the live ERPnext source before implementation
- do not move validated order quick wins out of Epic 21 just because later epics also touch commercial data

## 6. Execution Note For Sprint Tracking

If sprint planning needs one compact chain, use:

`22 shared blockers -> 23 + 25 -> 24 -> 26 -> 27 + 28 -> 29 -> 30 -> 31`

with Epic 21 continuing in parallel only for order-domain work that remains explicitly inside its scope.