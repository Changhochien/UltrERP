# Gap Analysis: ERPnext vs UltrERP

## 1. GAP ANALYSIS TABLE

### CRM & Sales

| Feature | ERPnext | UltrERP | Status |
|---------|---------|---------|--------|
| Lead Management | Full lead lifecycle with status machine, conversion, UTM fields, qualification | No dedicated Lead doctype; customers exist but no lead pipeline | MISSING |
| Opportunity / Pipeline | Full pipeline with sales stages, probability, lost reasons, competitors | No Opportunity doctype | MISSING |
| Prospect Tracking | Company-level prospect with linked leads/opportunities | No Prospect doctype | MISSING |
| Contract Management | Contract doctype with fulfilment checklists | No Contract doctype | MISSING |
| Quotation / Quote | Full quotation with validity, taxes, lost reasons, auto-repeating, competitors | No Quotation doctype; orders are created directly | MISSING |
| Sales Order | Full SO with delivery date, reserve stock, project link, commission, inter-company | Orders domain exists (PENDING→CONFIRMED→SHIPPED→FULFILLED) but no reserve stock, no commission tracking, no inter-company | PARTIAL |
| Customer | Full customer with credit limits, payment terms, primary address/contact, loyalty, portal users | Customers domain with basic fields; no credit limit enforcement, no payment terms template, no portal users | PARTIAL |
| Customer Group | Tree structure with defaults | No Customer Group hierarchy | MISSING |
| Territory | Tree structure for geographic regions | No Territory | MISSING |
| Sales Partner / Commission | Partner with commission rate, referral code, commission tracking | No Sales Partner, no commission tracking | MISSING |
| CRM Settings | Auto-contact creation, auto-close days, UTM config | No CRM settings | MISSING |
| Dynamic Links | Party-based dynamic links throughout CRM/Selling | Not applicable (different architecture) | PARTIAL |
| UTM Analytics | UTM fields on Lead, Opportunity, Quotation, SO | No UTM tracking | MISSING |

### Buying & Procurement

| Feature | ERPnext | UltrERP | Status |
|---------|---------|---------|--------|
| Supplier | Full supplier with scorecard, hold/freeze, on-hold controls, represent company, portal users | Suppliers domain in inventory; basic CRUD only, no scorecard, no hold/freeze, no portal | PARTIAL |
| Supplier Scorecard | Per-period scoring with standings (Very Poor → Excellent), prevent/warn RFQs/POs | No supplier scorecard | MISSING |
| Request for Quotation (RFQ) | Solicits multiple suppliers, email sending, quote comparison | No RFQ domain | MISSING |
| Supplier Quotation | Supplier's pricing quote linked to RFQ, compare and convert to PO | No Supplier Quotation | MISSING |
| Purchase Order | Full PO with subcontracting, drop-ship, inter-company, schedule date, project/cost center | No Purchase Order domain (only supplier orders in inventory for stock receipt) | MISSING |
| Purchase Receipt | Inbound receipt linked to PO with rejected qty, QC integration | Supplier Orders in inventory domain; receive endpoint exists but no formal GRN linked to PO | PARTIAL |
| Purchase Invoice | Full PI with update_stock, tax withholding, advance allocation | No Purchase Invoice (purchases domain is read-only for viewing supplier invoices) | MISSING |
| Blanket Order | Rate/qty agreement with ordered_qty tracking | No Blanket Order | MISSING |
| Supplier Portal | Portal for suppliers to receive RFQs, submit quotes | No supplier portal | MISSING |
|buying_settings | Maintain_same_rate, auto-create subcontracting order, backflush settings | No Buying Settings | MISSING |

### Inventory & Stock

| Feature | ERPnext | UltrERP | Status |
|---------|---------|---------|--------|
| Item | Full item with variants, barcodes, UOM conversions, reorder levels, warranties, inspection flags, deferred revenue/expense, item defaults per company | Products domain exists; basic fields only, no variants, no barcodes, no reorder levels, no UOM conversions, no deferred revenue | PARTIAL |
| Item Group | Tree with default warehouse/uom/accounts | Categories domain exists but no tree structure, no per-company defaults | PARTIAL |
| Item Variants | Template + variant items with attributes | No item variants | MISSING |
| Item Barcode | Barcode child table (EAN/UPC/GS1/etc.) | No barcode support | MISSING |
| UOM Conversion | Multi-UOM with conversion factors | Units of Measure domain exists; conversion factors not fully used | PARTIAL |
| Reorder Levels | Per-warehouse reorder level + material request type | Reorder alerts and suggestions exist; per-warehouse reorder levels not fully implemented | PARTIAL |
| Warehouse | Tree structure, warehouse type, address, account mapping, in-transit default | Warehouses domain exists; tree structure, warehouse types, account mapping not implemented | PARTIAL |
| Stock Entry | Material receipt/issue/transfer, manufacture, repack, subcontracting delivery | Transfers domain exists; manufacture/repack/subcontracting not implemented | PARTIAL |
| Stock Reconciliation | Opening stock + reconciliation with scan mode | No stock reconciliation | MISSING |
| Serial Number | Full serial no registry with warranty, maintenance status | No serial number tracking | MISSING |
| Batch / Lot | Batch with expiry, manufacturing date, qty | No batch/lot tracking | MISSING |
| Serial and Batch Bundle | Aggregated serial/batch for transaction lines | No SABB | MISSING |
| Quality Inspection | QI by type (Incoming/In Process/Outgoing) linked to PR/DN/SE | No quality inspection | MISSING |
| Pick List | For manufacture/delivery with scan mode, pick_manually | No Pick List | MISSING |
| Landed Cost Voucher | Distribute freight/duty across PR items | No landed cost | MISSING |
| Putaway Rule | Per-item-warehouse capacity with priority | No putaway rules | MISSING |
| Item Price | Price list rates with validity dates, batch pricing | No Item Price doctype | MISSING |
| Stock Closing Entry | Period-based stock locking | No stock closing | MISSING |
| Stock Settings | Global defaults, over-delivery allowance, valuation method, QC settings | No Stock Settings | MISSING |
| Manufacturing / BOM | BOM, Work Order, Job Card, Production Plan | No manufacturing module | MISSING |
| Product Bundle | Kit items packed into bundles | No Product Bundle | MISSING |

### Accounting & Finance

| Feature | ERPnext | UltrERP | Status |
|---------|---------|---------|--------|
| Sales Invoice | Full SI with payment terms, advance allocation, write-off, loyalty, timesheet billing, project, tax withholding, multi-currency | Invoices domain exists; immutable (no edit/void except void), no multi-currency, no advance allocation, no write-off | PARTIAL |
| Purchase Invoice | Full PI with update_stock, tax withholding, advance allocation, project | No Purchase Invoice; purchases domain is read-only | MISSING |
| Payment Entry | Pay/Receive/Transfer with advance allocation, references table | Payments domain exists; reconciliation exists, but no dedicated payment entry with bank/cash accounts | PARTIAL |
| Journal Entry | Manual GL entries with voucher types, multi-currency | No Journal Entry | MISSING |
| GL Entry | Submittable ledger entries per transaction | No GL Entry domain; no sub-ledger accounting | MISSING |
| Chart of Accounts | Tree with account types, freeze, balance constraints | No Account doctype or chart | MISSING |
| Fiscal Year | FY with start/end dates, disabled flag | No Fiscal Year | MISSING |
| Cost Center | Tree for expense allocation | No Cost Center | MISSING |
| Budget | Budget against cost center/project with distribution | No Budget | MISSING |
| Finance Book | Multi-book accounting | No Finance Book | MISSING |
| Exchange Rate Revaluation | Auto-revalue foreign-currency accounts | No exchange rate revaluation | MISSING |
| Payment Gateway | Stripe/Razorpay/etc. configuration | No payment gateway | MISSING |
| POS Invoice | Cash sale with payments table, change amount, consolidated invoice | No POS | MISSING |
| Dunning | Automated collection letters for overdue invoices | No dunning | MISSING |
| Loyalty Program | Points earning/redeeming per customer | No loyalty program | MISSING |
| Payment Terms Template | Installment schedule with discount | Payment terms enum exists (NET_30, NET_60, COD) but no template builder | PARTIAL |
| Tax Categories & Rules | Tax category + rule (by city/state/party type) | Tax codes exist in invoices; no tax rules engine | PARTIAL |
| Accounting Dimensions | Flexible dimensions beyond Cost Center/Project | No dynamic accounting dimensions | MISSING |
| Company Defaults | Default accounts, deferred revenue, advance account per company | No company master with defaults | MISSING |
| Payment Reconciliation | Match payments to invoices, unreconcile | Payments domain has reconcile endpoint; no dedicated reconciliation UI | PARTIAL |
| Credit Limit | Per-company credit limits with bypass flag | Customer has credit_limit field; not enforced on SO submit | PARTIAL |
| Payment Schedule | Due date installments on invoices | Payment schedule exists in invoices; not tied to payment terms template | PARTIAL |

### Projects & Time Tracking

| Feature | ERPnext | UltrERP | Status |
|---------|---------|---------|--------|
| Project | Full project with costing, billing, gross margin, template, auto-progress email | No Project doctype | MISSING |
| Task | Task with dependencies, reschedule, progress, weight, template | No Task doctype | MISSING |
| Timesheet | Time logging with billing/costing rates, per-activity rates | No Timesheet | MISSING |
| Activity Type | Activity with costing_rate, billing_rate | No Activity Type | MISSING |
| Project Template | Template tasks with dependencies mapped on project creation | No Project Template | MISSING |
| Project Dashboard | Charts and number cards for project metrics | No project dashboard | MISSING |

### HR

| Feature | ERPnext | UltrERP | Status |
|---------|---------|---------|--------|
| Employee | Full employee with reports_to tree, biometric attendance_device_id, holiday list, exit workflow | No Employee | MISSING |
| Department | Tree structure with company | No Department | MISSING |
| Designation | Job titles | No Designation | MISSING |
| Branch | Office location | No Branch | MISSING |
| Holiday List | Holidays with weekly offs, local import | No Holiday List | MISSING |
| Employment Type | Contract type | No Employment Type | MISSING |

### Support

| Feature | ERPnext | UltrERP | Status |
|---------|---------|---------|--------|
| Issue | Issue with SLA, first response time, resolution tracking, split, auto-close | No Issue doctype | MISSING |
| Service Level Agreement | SLA with priorities, response/resolution times, working hours, holiday list | No SLA | MISSING |
| Warranty Claim | Warranty claim with serial no, item, maintenance status | No Warranty Claim | MISSING |
| Maintenance Schedule | Scheduled maintenance visits | No Maintenance Schedule | MISSING |
| Support Dashboard | Issue analytics, first response time report | No support dashboard | MISSING |

### Core Infrastructure

| Feature | ERPnext | UltrERP | Status |
|---------|---------|---------|--------|
| Bulk Transaction | Batch-convert SO→DN/SI, with retry log | No bulk transaction | MISSING |
| Email Digest | Scheduled management summary email | No email digest | MISSING |
| POS Page | Full POS UI with item cart, payment, barcode | No POS UI | MISSING |
| Barcode Scanner | Dedicated BarcodeScanner class with audio feedback | No barcode scanning utility | MISSING |
| Portal Auto-Party | Auto-create Customer/Supplier from portal session | No portal auto-party | MISSING |
| Authorization Rules | Conditional approval workflows | Approval engine exists in backend; no UI rule builder | PARTIAL |
| Workflow Engine | Frappe Workflow with state transitions, notifications | No workflow builder UI | MISSING |
| Notifications | Email notifications on docstatus transitions | No notification builder | MISSING |
| Regional Modules | Country-specific tax compliance (US, AU, UAE, etc.) | No regional modules | MISSING |
| Plaid Integration | Bank account aggregation and sync | No Plaid integration | MISSING |
| Transaction Deletion Log | Compliance record of deleted transactions | No deletion log UI | MISSING |
| Auto-Repeat | Recurring document generation | No auto-repeat | MISSING |

### UX Patterns

| Feature | ERPnext | UltrERP | Status |
|---------|---------|---------|--------|
| Workspace / Dashboard | JSON workspace with charts, number cards, link cards | Dashboard exists with revenue/KPI/charts but no configurable workspace | PARTIAL |
| Report Builder | Standard 4-tuple report pattern with tree view, group-by | Reports exist in backend; no frontend report builder | PARTIAL |
| Print Formats | HTML templates with visible columns, compact mode | Hardcoded invoice PDF only | MISSING |
| Quick Entry | Modal quick-add form | No quick entry | MISSING |
| Child Table Grid | Visible columns with warehouse color indicators | No specialized grid templates | MISSING |

---

## 2. PRIORITY MATRIX

### P0 — Must Have (Core ERP Functionality)

| Gap | Effort | ERPnext Reference |
|----|--------|-----------------|
| Chart of Accounts + GL Entry | High | erpnext-accounting-detailed.md |
| Sales Invoice → full lifecycle (edit, advance allocation, write-off) | Medium | erpnext-accounting-detailed.md |
| Journal Entry (manual GL adjustments) | Medium | erpnext-accounting-detailed.md |
| Payment Entry (bank/cash, party allocation) | Medium | erpnext-accounting-detailed.md |
| Purchase Order | High | erpnext-buying-detailed.md |
| Purchase Invoice | Medium | erpnext-accounting-detailed.md |
| Lead + Opportunity pipeline | High | erpnext-crm-sales-detailed.md |
| Item variants, barcodes, UOM conversions | Medium | erpnext-inventory-detailed.md |
| Project + Task + Timesheet | High | erpnext-projects-hr-detailed.md |
| Supplier + Supplier Scorecard | Medium | erpnext-buying-detailed.md |
| Cost Center + Accounting Dimensions | Medium | erpnext-accounting-detailed.md |

### P1 — Should Have (Complete Business Workflows)

| Gap | Effort | ERPnext Reference |
|----|--------|-----------------|
| Quotation with validity, lost reasons | Medium | erpnext-crm-sales-detailed.md |
| Sales Order commission + reserve stock | Low | erpnext-crm-sales-detailed.md |
| Customer Group + Territory trees | Low | erpnext-crm-sales-detailed.md |
| RFQ + Supplier Quotation | Medium | erpnext-buying-detailed.md |
| Serial Number + Batch tracking | High | erpnext-inventory-detailed.md |
| Quality Inspection | Medium | erpnext-inventory-detailed.md |
| Pick List for warehouse picking | Medium | erpnext-inventory-detailed.md |
| Stock Reconciliation | Low | erpnext-inventory-detailed.md |
| Payment Terms Template builder | Low | erpnext-accounting-detailed.md |
| Credit Limit enforcement on SO | Low | erpnext-crm-sales-detailed.md |
| Fiscal Year + Budget | Medium | erpnext-accounting-detailed.md |
| Customer credit limits, payment terms per customer | Low | erpnext-crm-sales-detailed.md |
| Tax Rules engine | Medium | erpnext-accounting-detailed.md |
| Employee + Department + Holiday List | Medium | erpnext-projects-hr-detailed.md |
| Issue + SLA with working hours | High | erpnext-projects-hr-detailed.md |

### P2 — Nice to Have (Competitive Feature Parity)

| Gap | Effort | ERPnext Reference |
|----|--------|-----------------|
| POS Invoice + POS UI | High | erpnext-core-infrastructure.md |
| Batch/lot expiration management | Medium | erpnext-inventory-detailed.md |
| Landed Cost Voucher | Medium | erpnext-inventory-detailed.md |
| Putaway Rules | Low | erpnext-inventory-detailed.md |
| Product Bundle | Low | erpnext-inventory-detailed.md |
| Manufacturing / BOM / Work Order | High | erpnext-inventory-detailed.md |
| Sales Partner + commission tracking | Medium | erpnext-crm-sales-detailed.md |
| Blanket Order | Low | erpnext-buying-detailed.md |
| Dunning (collection letters) | Medium | erpnext-accounting-detailed.md |
| Loyalty Program | Medium | erpnext-accounting-detailed.md |
| Exchange Rate Revaluation | Low | erpnext-accounting-detailed.md |
| Finance Book (multi-book) | Medium | erpnext-accounting-detailed.md |
| Warranty Claim + Maintenance Schedule | Medium | erpnext-projects-hr-detailed.md |
| Supplier Scorecard auto-prevent RFQ/PO | Medium | erpnext-buying-detailed.md |
| Bulk Transaction with retry | Medium | erpnext-core-infrastructure.md |
| Email Digest | Medium | erpnext-core-infrastructure.md |
| Barcode scanner with audio | Medium | erpnext-core-infrastructure.md |
| UTM analytics on CRM docs | Low | erpnext-crm-sales-detailed.md |
| Contract Management | Low | erpnext-crm-sales-detailed.md |
| Prospect tracking | Low | erpnext-crm-sales-detailed.md |
| Print layout designer | High | erpnext-ux-patterns.md |
| Workflow builder UI | Medium | erpnext-core-infrastructure.md |
| Plaid bank integration | High | erpnext-core-infrastructure.md |
| Regional tax modules | High | erpnext-core-infrastructure.md |
| Auto-repeat recurring documents | Medium | erpnext-core-infrastructure.md |

---

## 3. PHASE GROUPING

### Phase 1: P0 Gaps — Low/Medium Effort (Foundation First)

**Accounting Foundation**
- Chart of Accounts + GL Entry
- Journal Entry
- Payment Entry with party allocation
- Cost Center + Accounting Dimensions
- Fiscal Year + Budget
- Tax Rules engine

**Core Sales/Purchase**
- Purchase Order
- Purchase Invoice
- Full Sales Invoice lifecycle (edit, advance allocation, write-off)
- Payment Terms Template builder
- Credit Limit enforcement

**Master Data**
- Supplier + Supplier Scorecard
- Customer Group + Territory trees
- Item variants + UOM conversions

**Effort estimate: Medium | ~3-4 sprints**

---

### Phase 2: P1 Gaps, or P0 with High Effort

**CRM Pipeline**
- Lead + Opportunity pipeline
- Quotation with validity, lost reasons
- Sales Order commission + reserve stock
- UTM analytics on CRM docs

**Supply Chain**
- RFQ + Supplier Quotation
- Serial Number + Batch tracking
- Quality Inspection
- Pick List for warehouse picking
- Stock Reconciliation
- Item Barcode support

**Projects & HR**
- Project + Task + Timesheet + Activity Type
- Project Template
- Employee + Department + Holiday List

**Customer & Finance**
- Customer credit limits, payment terms per customer
- Customer portal users
- Dunning (collection letters)

**Effort estimate: High | ~4-6 sprints**

---

### Phase 3: P2 Gaps (Competitive Parity)

**Operations**
- POS Invoice + POS UI
- Manufacturing / BOM / Work Order
- Batch/lot expiration management
- Landed Cost Voucher
- Putaway Rules
- Product Bundle

**Advanced Sales**
- Sales Partner + commission tracking
- Blanket Order
- Contract Management
- Prospect tracking
- Loyalty Program

**Advanced Accounting**
- Exchange Rate Revaluation
- Finance Book (multi-book)
- Warranty Claim + Maintenance Schedule
- Supplier Scorecard auto-prevent RFQ/PO

**Infrastructure**
- Bulk Transaction with retry
- Email Digest
- Barcode scanner with audio
- Print layout designer
- Workflow builder UI
- Auto-repeat recurring documents
- Plaid bank integration
- Regional tax modules

**Effort estimate: Very High | ~6+ sprints**

---

## SUMMARY COUNTS

| Category | Total Features | IMPLEMENTED | PARTIAL | MISSING |
|----------|--------------|-------------|---------|---------|
| CRM & Sales | 17 | 0 | 3 | 14 |
| Buying & Procurement | 10 | 0 | 2 | 8 |
| Inventory & Stock | 20 | 0 | 6 | 14 |
| Accounting & Finance | 24 | 0 | 5 | 19 |
| Projects & Time | 7 | 0 | 0 | 7 |
| HR | 6 | 0 | 0 | 6 |
| Support | 5 | 0 | 0 | 5 |
| Core Infrastructure | 14 | 0 | 1 | 13 |
| UX Patterns | 5 | 0 | 2 | 3 |
| **TOTAL** | **108** | **0** | **19** | **89** |

**Coverage: 17.6% implemented or partial, 82.4% missing**

---

*Generated from gap analysis of ERPnext v14/v15 source and UltrERP codebase*  
*Research sources: .omc/research/erpnext-*.md, .omc/research/ultrerp-modules.md*
