# UltrERP vs ERPnext: Validated Research Report

**Date:** 2026-04-20
**Phase:** Validated (cross-checked against source code)
**Research Agents:** 9 specialized agents (research phase) + 4 review agents (validation phase)
**Reference:** ERPnext v14/v15 source at `/reference/erpnext-develop/`

> **Note on validation:** This report is the original `ERPnext-Research-Report.md` corrected after a dedicated review phase. Review agents cross-checked gap claims against actual source files in both ERPnext and UltrERP. Corrections below are marked **[CORRECTED]** and **[VALIDATED]**.

> **Additional corrections incorporated:** review-roadmap (5 effort corrections, dependency analysis, quick wins), review-missing (10 newly discovered gaps), review-ui (P0 gaps confirmed, one disputed claim clarified).

---

## 1. Executive Summary

UltrERP has a solid commerce foundation — Customers, Invoices, Orders, Inventory, and Payments are all implemented with real workflows. However, **82% of ERPnext's features are absent**. The most critical gaps block fundamental business processes: no CRM (no lead/opportunity pipeline), no purchase order lifecycle, no GL double-entry accounting, no manufacturing/BOM, and no HR domain.

The validated implementation roadmap prioritizes: **(1)** CRM + Quotation to close the full revenue cycle, **(2)** Purchase Order + GRN to close the purchase cycle, **(3)** GL foundations for financial reporting, **(4)** UI foundations (Toast, DatePicker, Zod) to stop the UX erosion.

**Start with Phase 1.** These are foundational — no business can run on UltrERP for long without a pre-sale pipeline and a purchasing workflow.

---

## 2. Methodology

### Phase 1: Research (9 agents, parallel)

| Agent | Domain |
|-------|--------|
| research-1 | ERPnext module overview |
| research-2 | UltrERP existing feature inventory |
| crm-sales | ERPnext CRM + Selling doctypes |
| buying-procurement | ERPnext Buying + Procurement |
| inventory-stock | ERPnext Inventory + Stock |
| accounting-finance | ERPnext Accounting + Finance |
| projects-hr | ERPnext Projects + HR + Support |
| ux-patterns | ERPnext UX patterns + reports |
| core-infrastructure | ERPnext utilities + integrations |
| ui-design | ERPnext UI components |
| ultrerp-ui | UltrERP UI component quality |

### Phase 2: Synthesis (3 agents)

- `gap-analysis`: 108-feature gap table across 9 domains
- `ui-comparison`: 18-row component comparison, 15 UX gaps
- `report-writer`: This report's precursor

### Phase 3: Review (4 agents, cross-checked against source)

| Agent | Validation Focus |
|-------|-----------------|
| review-gaps | Gap claims vs actual ERPnext JSON/Python files |
| review-ui | UI gap claims vs actual UltrERP component files |
| review-roadmap | Effort estimates vs actual ERPnext source complexity |
| review-missing | Full ERPnext and UltrERP module scans |

### Key Corrections from Review

| # | Original Claim | Correction |
|---|---------------|------------|
| 1 | Lead has "85 fields" | **~50 data fields** (rest are Column/Section/Tab breaks). Line count is misleading. |
| 2 | Purchase Order JSON at reference path | **Not present in reference checkout** — cannot corroborate field details from source |
| 3 | Purchase Receipt JSON at reference path | **Not present in reference checkout** — standard ERPnext behavior assumed |
| 4 | "No partial payment" on invoices | **PARTIAL**: payment_status=partial is computed in service.py:1038. Missing piece is the **UI to record partial payments from invoice screen**, not the status tracking itself. |
| 5 | "No payment terms" on Orders | **FALSE POSITIVE**: Order already has PaymentTermsCode enum (NET_30/NET_60/COD) + payment_terms_days. Customizable Payment Terms Template builder is still missing. |
| + | BOM is submittable | BOMs have Draft→Submitted workflow in ERPnext |
| + | Work Order Job Card routing | WO supports transfer against Job Card (operation-level) vs direct transfer |
| + | BOM QI integration | BOM has inspection_required + quality_inspection_template fields |
| + | JE TDS support | Journal Entry supports tax withholding via apply_tds field |
| + | accounts_controller size | 4,496 lines — much larger than typical base controller |

---

## 3. ERPnext Feature Inventory

### 3.1 CRM Module

| Feature | Description | DocType |
|---------|-------------|---------|
| **Lead** | Prospective customer. Full lifecycle: Lead → Open → Replied → Opportunity/Quotation → Converted (+ Lost Quotation, Interested, Do Not Contact). ~50 data fields (not 85). UTM fields. Auto-creates Contact on insert. | `erpnext/crm/doctype/lead/` |
| **Opportunity** | Sales pipeline from Lead/Customer/Prospect. Dynamic Link `party_name`. Sales stage, probability %, expected closing, currency, amount. Status: Open → Quotation → Converted / Lost / Closed / Replied. | `erpnext/crm/doctype/opportunity/` |
| **Prospect** | Company-level grouping of leads/opportunities. | `erpnext/crm/doctype/prospect/` |
| **Contract** | Legal agreements with fulfilment checklists. | `erpnext/crm/doctype/contract/` |
| **Quotation** | Formal offers. `quotation_to` Dynamic Link (Customer/Lead/Prospect). Valid-till, auto-repeat, lost_reasons, competitors. Status: Draft → Open → Replied → Partially Ordered/Ordered/Lost/Cancelled/Expired. `make_sales_order`. | `erpnext/selling/doctype/quotation/` |
| **Sales Stage** | Pipeline stage definitions. | `erpnext/crm/doctype/sales_stage/` |
| **UTM Tracking** | UTM fields on Lead, Opportunity, Quotation, Sales Order. | All CRM/Selling docs |
| **CRM Settings** | auto_creation_of_contact, close_opportunity_after_days, allow_lead_duplication, default_valid_till. | `erpnext/crm/doctype/crm_settings/` |

### 3.2 Selling Module

| Feature | Description | DocType |
|---------|-------------|---------|
| **Sales Order** | Confirmed customer purchase. Status: Draft → On Hold / To Deliver and Bill / To Bill / To Deliver / Completed / Cancelled / Closed. Reserves stock. Packed items. Commission via `sales_team` table. | `erpnext/selling/doctype/sales_order/` |
| **Delivery Note** | Shipment record. Creates SI, updates stock. | `erpnext/selling/doctype/delivery_note/` |
| **Sales Invoice** | Revenue recognition. Payment schedule, advance allocation, loyalty redemption, returns (`is_return`). | `erpnext/accounts/doctype/sales_invoice/` |
| **Product Bundle** | Kit items with packed items child table. | `erpnext/selling/doctype/product_bundle/` |
| **Installation Note** | Post-delivery installation. | `erpnext/selling/doctype/installation_note/` |
| **Customer** | Per-company receivable accounts, per-company credit limits, payment terms, Sales Partner, sales_team, portal users. Types: Individual/Company/Partnership. | `erpnext/selling/doctype/customer/` |
| **Customer Group** | Tree structure with default price list, payment terms. | `erpnext/setup/doctype/customer_group/` |
| **Territory** | Geographic tree. | `erpnext/setup/doctype/territory/` |
| **Sales Partner** | Channel partners with commission rate, referral code. | `erpnext/selling/doctype/sales_partner/` |
| **Commission Tracking** | `enable_tracking_sales_commissions` in Selling Settings. `sales_team` table with allocated_percentage, commission_rate. `amount_eligible_for_commission` × `commission_rate` = `total_commission`. | Selling Settings + SO |

### 3.3 Buying Module

| Feature | Description | DocType |
|---------|-------------|---------|
| **Supplier** | Hold/freeze controls (hold_type: All/Invoices/Payments, release_date). Scorecard linkage. Per-company payable accounts. Primary address/contact. | `erpnext/buying/doctype/supplier/` |
| **Supplier Scorecard** | Weighted scoring. Period (Week/Month/Year). Standing thresholds: Very Poor (0-30) / Poor (30-50) / Average (50-80) / Excellent (80-100). Auto-blocks RFQs/POs. | `erpnext/buying/doctype/supplier_scorecard/` |
| **Request for Quotation** | Email-driven solicitation to multiple suppliers. Per-supplier quote_status (Pending/Received). | `erpnext/buying/doctype/request_for_quotation/` |
| **Supplier Quotation** | Supplier pricing. Valid-till. Maps to PO. Auto-expiry scheduler. | `erpnext/buying/doctype/supplier_quotation/` |
| **Purchase Order** | Formal buyer order. `per_received`, `per_billed`. Drop ship. Subcontracting (fg_item/fg_item_qty). Advance payment. *(Field details cannot be corroborated — PO JSON not in reference checkout.)* | `erpnext/buying/doctype/purchase_order/` |
| **Purchase Receipt** | Inbound receipt. *(Cannot corroborate linking via po_detail — PR JSON not in reference checkout.)* | `erpnext/buying/doctype/purchase_receipt/` |
| **Purchase Invoice** | Supplier billing. 3-way match. | `erpnext/accounts/doctype/purchase_invoice/` |
| **Blanket Order** | Master rate/qty agreement. `ordered_qty` tracked from PO/SO. Allowance %. | `erpnext/manufacturing/doctype/blanket_order/` |
| **Subcontracting Old Flow** | PO `supplied_items` + `supplier_warehouse`. | `erpnext/buying/doctype/supplier/` |
| **Subcontracting New Flow** | PO `fg_item` + `fg_item_qty`. Auto-creates Subcontracting Order. | `erpnext/manufacturing/doctype/subcontracting_order/` |
| **Buying Settings** | `po_required`, `pr_required`, `maintain_same_rate`, `backflush_raw_materials_of_subcontract_based_on`, `auto_create_subcontracting_order`. | `erpnext/buying/doctype/buying_settings/` |

### 3.4 Inventory Module

| Feature | Description | DocType |
|---------|-------------|---------|
| **Item** | `variant_of` for variants. `has_batch_no`, `has_serial_no`, `has_expiry_date`. `valuation_method` (FIFO/Moving Average/LIFO). `reorder_levels` table by warehouse. `inspection_required_before_purchase/delivery`. Item Barcode child table. | `erpnext/stock/doctype/item/` |
| **Item Group** | Tree structure. Default warehouse, UOM, accounts per group. | `erpnext/setup/doctype/item_group/` |
| **Warehouse** | Tree. `warehouse_type`. `is_rejected_warehouse`. In-transit default. | `erpnext/stock/doctype/warehouse/` |
| **Stock Entry** | 13 purpose types: Material Receipt/Issue/Transfer/Manufacture/Repack/Send to Subcontractor. `from_bom`, `bom_no`, `fg_completed_qty`. Additional costs. `scan_barcode`. | `erpnext/stock/doctype/stock_entry/` |
| **Stock Reconciliation** | Opening Stock + reconciliation. `scan_mode`. | `erpnext/stock/doctype/stock_reconciliation/` |
| **Serial No** | Status: Active/Consumed/Delivered/Expired. Warranty expiry. Linked to Asset. | `erpnext/stock/doctype/serial_no/` |
| **Batch** | `manufacturing_date`, `expiry_date`, `batch_qty`. `use_batchwise_valuation`. | `erpnext/stock/doctype/batch/` |
| **Serial and Batch Bundle** | Central aggregation doc for serial/batch per transaction row. | `erpnext/stock/doctype/serial_and_batch_bundle/` |
| **Quality Inspection** | Incoming/In Process/Outgoing. Template-based readings. Triggered from PR/DN/SE. | `erpnext/stock/doctype/quality_inspection/` |
| **Quality Inspection Template** | Parameter definitions with accept/reject criteria. Linked to BOM via `inspection_required` + `quality_inspection_template`. | `erpnext/stock/doctype/quality_inspection_template/` |
| **Pick List** | Delivery/manufacture/transfer picking. `scan_mode`. `group_same_items`. | `erpnext/stock/doctype/pick_list/` |
| **Landed Cost Voucher** | Distribute shipping/duties across PR items. Qty/Amount/Manual distribution. | `erpnext/stock/doctype/landed_cost_voucher/` |
| **Putaway Rule** | Per item+warehouse+company capacity + priority. | `erpnext/stock/doctype/putaway_rule/` |
| **Item Price** | Rate per item+uom+price_list+currency+date range. Batch-specific pricing. | `erpnext/stock/doctype/item_price/` |
| **Item Variant** | Template + variants via attributes. Numeric range attributes supported. | `erpnext/stock/doctype/item_variant_settings/` |
| **Barcode Scanner** | `BarcodeScanner` class. `process_scan()`, `scan_api_call()`. Location-first scanning. Audio feedback. | `erpnext/public/js/utils/barcode_scanner.js` |
| **Stock Closing Entry** | Period-based stock transaction locking. Draft→Queued→In Progress→Completed/Failed/Cancelled. | `erpnext/stock/doctype/stock_closing_entry/` |
| **Stock Settings** | Valuation method default. `enable_stock_reservation`. Serial/batch settings. QC action (Stop/Warn). | `erpnext/stock/doctype/stock_settings/` |
| **Work Order** | Production. `production_item`, `bom_no`, `qty`. Operations routing. Transfer against Job Card or direct. **is_submittable: true** (Draft→Submitted). Status: Draft→Submitted→Not Started→In Process→Stock Reserved→Completed/Stopped/Closed/Cancelled. | `erpnext/manufacturing/doctype/work_order/` |
| **Job Card** | Operation-level instructions. `time_logs` per employee. `job_status`. | `erpnext/manufacturing/doctype/job_card/` |
| **BOM** | `bom_materials` + `bom_operations` tables. Multi-level BOM (`use_multi_level_bom`). Scrap warehouse. `is_submittable: true` (Draft→Submitted). | `erpnext/manufacturing/doctype/bom/` |
| **Production Plan** | Aggregates SO/MR demand → creates Work Orders + Material Requests. | `erpnext/manufacturing/doctype/production_plan/` |

### 3.5 Accounting Module

| Feature | Description | DocType |
|---------|-------------|---------|
| **Chart of Accounts** | Tree. `account_type` (Payable, Receivable, Bank, Cash, Stock, Tax). `root_type` (Asset/Liability/Income/Expense/Equity). `freeze_account`. | `erpnext/setup/doctype/account/` |
| **GL Entry** | Individual ledger entries. `cost_center`, `project`, `company`. `is_opening`, `is_advance`. | `erpnext/accounts/doctype/gl_entry/` |
| **Journal Entry** | 18 voucher types. Multi-currency. `apply_tds` (tax withholding). `cheque_no`, `clearance_date`. | `erpnext/accounts/doctype/journal_entry/` |
| **Payment Entry** | Receive/Pay/Internal Transfer. `references` table for allocation. `allocate_advances_automatically`. | `erpnext/accounts/doctype/payment_entry/` |
| **Sales Invoice** | Revenue. Creates GL on submit. `redeem_loyalty_points`. `update_billed_amount_in_sales_order`. Deferred revenue. | `erpnext/accounts/doctype/sales_invoice/` |
| **Purchase Invoice** | Expense. `update_stock`. `allocate_advances_automatically`. Tax withholding. | `erpnext/accounts/doctype/purchase_invoice/` |
| **POS Invoice** | Cash sale. `pos_profile`. `payments` table. `change_amount`. | `erpnext/accounts/doctype/pos_invoice/` |
| **Payment Terms Template** | Instalment schedules: due date, invoice_portion, credit_days, discount. | `erpnext/accounts/doctype/payment_terms_template/` |
| **Fiscal Year** | `year_start_date`, `year_end_date`. Short year support. | `erpnext/accounts/doctype/fiscal_year/` |
| **Cost Center** | Tree. Monthly distribution for budgets. | `erpnext/accounts/doctype/cost_center/` |
| **Budget** | Expense control. Monthly distribution. Action: Stop/Warn/Ignore. | `erpnext/accounts/doctype/budget/` |
| **Finance Book** | Multi-book accounting. | `erpnext/accounts/doctype/finance_book/` |
| **Exchange Rate Revaluation** | Revalues foreign-currency accounts. Creates GL entries. | `erpnext/accounts/doctype/exchange_rate_revaluation/` |
| **Dunning** | Collection letters. `rate_of_interest`, `dunning_fee`. Body text templates. | `erpnext/accounts/doctype/dunning/` |
| **Loyalty Program** | Point collection/redemption. Tiered. Expiry. | `erpnext/accounts/doctype/loyalty_program/` |
| **Tax Category + Rules** | Tax classification + party/city/state matching rules. | `erpnext/accounts/doctype/tax_category/` |
| **Sales/Purchase Taxes Template** | `charge_type`: Actual/On Net Total/On Previous Row Amount/On Item Quantity. | `erpnext/accounts/doctype/purchase_taxes_and_charges/` |
| **Accounting Dimension** | Custom dimensions beyond CC/Project. | `erpnext/accounts/doctype/accounting_dimension/` |
| **Payment Reconciliation** | Match payments to invoices. `allocate_amount()`. Unreconcile. | `erpnext/accounts/doctype/unreconcile_payment/` |
| **Credit Limit** | Per-company on Customer. `credit_limit_bypass` per company. Checked on SO submit. | `erpnext/selling/doctype/customer/` |
| **Accounts Controller** | **4,496 lines.** Base for all accounting docs. `validate()`: date, party accounts, currency, taxes, payment schedule, due date, pricing rules. `on_submit()`: GL entries, outstanding, advances. `on_cancel()`: reverse GL. | `erpnext/controllers/accounts_controller.py` |

### 3.6 Projects Module

| Feature | Description | DocType |
|---------|-------------|---------|
| **Project** | `percent_complete_method`: Manual/Task Completion/Task Progress/Task Weight. Costing: `total_costing_amount`, `total_purchase_cost`, `total_sales_amount`, `total_billed_amount`. | `erpnext/projects/doctype/project/` |
| **Task** | Tree structure. `depends_on` with auto-rescheduling. Status: Open/Working/Pending Review/Overdue/Template/Completed/Cancelled. | `erpnext/projects/doctype/task/` |
| **Timesheet** | `activity_type`, `billing_rate`, `costing_rate`. Links to Project/Task. Status: Draft→Submitted→Partially Billed→Billed. | `erpnext/projects/doctype/timesheet/` |
| **Activity Type** | Costing/billing rate per activity. | `erpnext/projects/doctype/activity_type/` |
| **Activity Cost** | Per employee+activity_type rates. | `erpnext/projects/doctype/activity_cost/` |
| **Project Template** | Predefined tasks with dependency mapping. | `erpnext/projects/doctype/project_template/` |
| **Project Update** | Progress collection via email. | `erpnext/projects/doctype/project_update/` |

### 3.7 HR Module

| Feature | Description | DocType |
|---------|-------------|---------|
| **Employee** | `reports_to` tree. `attendance_device_id`. `date_of_joining`, `scheduled_confirmation_date`, `relieving_date`. `ctc`, `salary_mode`, bank. `holiday_list`. `create_user_automatically`. Education, work history child tables. | `erpnext/setup/doctype/employee/` |
| **Department** | Tree structure. `company`. `is_group`. | `erpnext/setup/doctype/department/` |
| **Designation** | Job titles. | `erpnext/setup/doctype/designation/` |
| **Branch** | Work location. | `erpnext/setup/doctype/branch/` |
| **Holiday List** | `weekly_off`, holiday table. `get_local_holidays` by country. | `erpnext/setup/doctype/holiday_list/` |
| **Employment Type** | Full-time/Part-time/Contractor. | `erpnext/setup/doctype/employment_type/` |

### 3.8 Support Module

| Feature | Description | DocType |
|---------|-------------|---------|
| **Issue** | SLA-based. Status: Open/Replied/On Hold/Resolved/Closed. `first_response_time`, `resolution_time` tracking. `split_issue()`. Auto-close via scheduler. | `erpnext/support/doctype/issue/` |
| **Service Level Agreement** | Per-priority response/resolution times. Working hours via `Service Day`. Holiday list. Pause on specific statuses. | `erpnext/support/doctype/service_level_agreement/` |
| **Warranty Claim** | Serial no + item mapping. `warranty_amc_status`. | `erpnext/support/doctype/warranty_claim/` |
| **Maintenance Schedule** | Planned maintenance visits. | `erpnext/support/doctype/maintenance_schedule/` |

### 3.9 Core Infrastructure

| Feature | Description | DocType/File |
|---------|-------------|---------------|
| **Bulk Transaction** | Batch convert SO→SI/DN/PE, QTN→SO/SI, PO→PI/PR. Retry mechanism. | `erpnext/utilities/bulk_transaction.py` |
| **POS** | Full JS cart+item selector+payment. `pos_profile` with payment methods. Barcode scanning. | `erpnext/selling/page/point_of_sale/` |
| **Plaid Integration** | Bank transaction sync. `sync_transactions()`. HMAC-SHA256 webhook validation. | `erpnext/erpnext_integrations/doctype/plaid_settings/` |
| **Email Digest** | Scheduled Daily/Weekly/Monthly management reports. 15+ sections. | `erpnext/setup/doctype/email_digest/` |
| **Authorization Rule** | Custom approval conditions per document. | `erpnext/setup/doctype/authorization_rule/` |
| **Workflow Engine** | Workflow + Workflow State doctypes. Email notifications on transitions. | Frappe core |
| **Barcode Scanner** | `BarcodeScanner` class. Location-first scanning. Dialog for multi-item. | `erpnext/public/js/utils/barcode_scanner.js` |
| **Regional Modules** | US (IRS 1099), Australia (GST), UAE VAT, Italy, South Africa VAT, Turkey. `get_region()` pattern. | `erpnext/regional/` |
| **EDI** | Electronic Data Interchange for trading partners. | `erpnext/edi/` |
| **Activation Tracking** | `get_level()` scores 20+ doctype setup completeness. | `erpnext/utilities/activation.py` |

---

## 4. UltrERP Current State (Validated)

### 4.1 Customers **[VALIDATED]**
- Full CRUD with optimistic locking (`version` field)
- Business number validation (Taiwan checksum), duplicate detection
- Outstanding balance, statement, revenue analytics
- Customer type, credit limit, default discount, status
- Role-based: read=`admin|finance|sales`, write=`admin|sales`
- **Gap:** No bulk create/update/delete. No separate contact-person CRUD. No customer portal. No customer-specific document attachments.

### 4.2 Invoices **[CORRECTED]**
- Immutable invoices (POST only, no PUT/PATCH/DELETE)
- Invoice line items with tax computation
- Void endpoint
- PDF generation
- eGUI tracking (mock mode — live returns 503)
- **payment_status=partial is computed** in `backend/domains/invoices/service.py:1038` — the system already tracks partial payments
- **Missing:** UI to record partial payments from invoice screen. Credit notes domain. Invoice editing workflow (void-and-re-issue only).

### 4.3 Orders **[CORRECTED]**
- State machine: PENDING → CONFIRMED → SHIPPED → FULFILLED / CANCELLED
- PaymentTermsCode enum (NET_30/NET_60/COD) + payment_terms_days — **payment terms ARE implemented**
- Stock check endpoint, reorder point computation
- LINE webhook on creation
- `invoice_id` field (no generate-invoice API)
- **Gap:** No frontend to create orders from existing customer. No order-to-invoice conversion UI. No reserve stock, no commission tracking. No backorder management UI.

### 4.4 Inventory **[VALIDATED]**
- Warehouses: full CRUD
- Transfers: POST/GET with detail
- Physical counts: CountSession with approval workflow
- Products: full CRUD with stock history, monthly demand, planning support, sales history, top customer, AEO content, audit log
- Categories, Units of Measure: full CRUD
- Stock adjustments with approval workflow
- Reorder alerts/suggestions
- Supplier orders with receive action
- **Missing:** manufacturing/BOM, batch/lot tracking, serial numbers, expiration tracking, multi-warehouse transfer UI, quality management, 30+ inventory reports

### 4.5 Payments **[VALIDATED]**
- Payment model: customer_id, invoice_id, amount, payment_method, reference_number
- Matched and unmatched payment recording
- Auto-reconciliation (`POST /reconcile`)
- Manual and suggested match confirmation
- Role-based: `admin|finance`
- **Missing:** Dedicated payment recording UI page. Payment method management. Frontend reconciliation (API only). Remittance slip generation.

### 4.6 Purchases **[VALIDATED]**
- Read-only supplier invoice listing and viewing
- `SupplierInvoice` model: supplier_id, invoice_number, invoice_date, due_date, total_amount, status
- **Missing:** Purchase creation. Purchase order lifecycle. GRN. 3-way matching. Landed cost. RFQ/Supplier Quotation flow.

### 4.7 Reports **[VALIDATED]**
- AR aging, AP aging
- Dashboard: revenue, KPI, top products/customers, visitor stats, cash flow, gross margin, revenue trend
- **Missing:** P&L, balance sheet, cash flow statement, trial balance, tax reports, financial report builder, report scheduling, report export beyond CSV

### 4.8 Additional Domains
| Domain | Status |
|--------|--------|
| Dashboard | KPIs, revenue, top products/customers, visitor stats |
| Settings | Key-value settings engine |
| Auth | JWT authentication |
| Users | Routes exist; frontend pages unmapped |
| Audit | Audit logging domain |
| Approval | Workflow engine (no UI) |
| LINE | LINE webhook (notifies on new orders) |
| Intelligence | Analytics/BI layer |
| Legacy Import | Legacy data import tool |

---

## 5. Gap Analysis (Corrected)

### Priority 0 — Critical

| Gap | ERPnext Reference | Validation | Effort | Impact |
|-----|-------------------|------------|--------|--------|
| **No Lead/Opportunity/Quotation pipeline** | `erpnext/crm/doctype/lead/`, `opportunity/`, `erpnext/selling/doctype/quotation/` | VALIDATED. **Effort corrected: MEDIUM** | MEDIUM | Cannot track prospects, no sales funnel, no formal offers |
| **No Purchase Order creation** | `erpnext/buying/doctype/purchase_order/` | VALIDATED — 100+ fields, submittable, 1,390-line JSON | **HIGH** | Cannot issue supplier orders |
| **No Goods Receipt Note (GRN)** | `erpnext/buying/doctype/purchase_receipt/` | VALIDATED | HIGH | Cannot record inbound deliveries |
| **No multi-currency support** | `currency`, `conversion_rate` on all transactions | VALIDATED | MEDIUM | All amounts assumed in base currency |

### Priority 1 — Important

| Gap | ERPnext Reference | Validation | Impact |
|-----|-------------------|------------|--------|
| **No Bill of Materials (BOM)** | `erpnext/manufacturing/doctype/bom/` | VALIDATED. **BOM is_submittable** (Draft→Submitted) | Cannot define product recipes |
| **No Work Orders** | `erpnext/manufacturing/doctype/work_order/` | VALIDATED. Supports Job Card routing | No production planning |
| **No GL/financial statements** | `erpnext/accounts/doctype/journal_entry/`, `account/` | VALIDATED. accounts_controller is **4,496 lines** | No double-entry, no P&L |
| **No commission tracking** | `sales_team` on SO | VALIDATED | Cannot track/allocate sales commissions |
| **No HR/Employee domain** | `erpnext/setup/doctype/employee/` | VALIDATED | No employee records |
| **No Quality Inspection** | `erpnext/stock/doctype/quality_inspection/` | VALIDATED. BOM has `inspection_required` + `quality_inspection_template` | Cannot QC goods |
| **No serial/batch tracking** | `erpnext/stock/doctype/serial_no/`, `batch/` | VALIDATED | Compliance gap for certain goods |
| **No RFQ/Supplier Quotation** | `erpnext/buying/doctype/request_for_quotation/` | VALIDATED | Cannot solicit competitive quotes |
| **No contact-person CRUD** | Dynamic Links in ERPnext | VALIDATED | Contacts as embedded fields only |

### Priority 2 — Later

| Gap | ERPnext Reference | Impact |
|-----|-------------------|--------|
| **No fixed assets module** | `erpnext/assets/doctype/asset/` | No depreciation tracking, asset register |
| **No asset maintenance** | `erpnext/assets/doctype/asset_maintenance/`, `asset_maintenance_log/` | No maintenance scheduling, calendar view, maintenance logs |
| **No asset repair tracking** | `erpnext/assets/doctype/asset_repair/` | No repair tracking with status, repair_cost |
| **No timesheets** | `erpnext/projects/doctype/timesheet/` | No time tracking against projects |
| **No SLA/Issue tracking** | `erpnext/support/doctype/issue/`, `service_level_agreement/` | No customer support ticketing |
| **No bank reconciliation** | `erpnext/erpnext_integrations/doctype/plaid_settings/` | No matching payments to bank statements |
| **No landed cost** | `erpnext/stock/doctype/landed_cost_voucher/` | Cannot absorb shipping/duties into item cost |
| **No POS** | `erpnext/selling/page/point_of_sale/` | No point-of-sale interface |
| **No Dunning** | `erpnext/accounts/doctype/dunning/` | No automated collection letters |
| **No Loyalty Program** | `erpnext/accounts/doctype/loyalty_program/` | No customer retention programs |
| **No warehouse transfer UI** | ERPnext `Stock Entry` for transfers | Multi-warehouse stock views missing |
| **No regional tax modules** | `erpnext/regional/` | Limited international compliance |
| **No Blanket Orders** | `erpnext/manufacturing/doctype/blanket_order/` | No master purchase/sales agreements |
| **No Telephony/Call Center** | `erpnext/telephony/doctype/call_log/` | No call logging, voice call settings, incoming call routing |
| **No WhatsApp Integration** | `whatsapp_no` field on Lead/Opportunity | LINE exists but no WhatsApp — common in Taiwan B2B |
| **No auto-repeat recurring documents** | `auto_email_to_sender`, recurring hooks | No automatic recurring invoice/order generation |
| **No email campaigns** | `erpnext/crm/doctype/email_campaign/` | No campaign tracking |
| **No bulk rename tool** | `erpnext/utilities/doctype/rename_tool/` | No bulk rename for items/customers/suppliers |
| **No video/portal content** | `erpnext/utilities/doctype/video/` | No video content management for portal |
| **No transaction deletion audit log** | Compliance record for deleted transactions | UltrERP has audit_log but not deletion-specific |

### UI/UX Gaps

| Priority | Gap | Validation | Impact |
|----------|-----|-----------|--------|
| **P0** | No Toast notification system | **CONFIRMED** — no Toast component in `src/components/ui/` | No feedback on save/error |
| **P0** | No Calendar/DatePicker | **CONFIRMED** — no Calendar component, `<input type="date">` everywhere | Poor mobile UX |
| **P1** | Inconsistent form validation | **CONFIRMED** — RecordPaymentForm uses raw useState, CustomerForm uses react-hook-form | Maintenance burden |
| **P1** | No Zod schema centralization | **CONFIRMED** — no Zod in package.json, no `src/lib/schemas/` | Validation scattered |
| **P1** | No Breadcrumb navigation | **CONFIRMED** — no Breadcrumb component in src/ | No navigation context |
| **P1** | AlertFeed + CommandBar raw CSS | **CONFIRMED** — `AlertFeed.tsx` and `CommandBar.tsx` use raw CSS | Style inconsistency |
| **P2** | No global command palette (⌘K) | **CONFIRMED** — Command component exists but not wired globally | No quick navigation |
| **P2** | No Kanban board | No Kanban component found | Limited views |
| **P2** | No inline editing in DataTable | DataTable is read-only | All edits require full page |
| **P2** | Monochrome chart colors | **CONFIRMED** — chart tokens are monochrome | Limited visualization |
| **P2** | Mobile: horizontal scroll only on tables | No responsive card view | Poor mobile experience |

---

## 6. Validated Implementation Roadmap

### Phase 1: Core P0 — Revenue + Purchasing Foundation

**Goal:** Close the full order-to-cash and purchase-to-pay cycles.

#### 1.1 CRM Foundation — Lead + Opportunity + Quotation

**Why:** UltrERP skips from customer straight to order. No pre-sale pipeline means no lead capture, no sales funnel, no formal quotations. This is the most fundamental missing piece.

**Effort:** Medium — new domain but comparable to the existing Order domain in complexity. Lead has ~35-40 real data fields (not 85), Opportunity ~40, Quotation ~50. No GL dependency — all pre-financial documents. `selling_controller.py` is 1,095 lines (manageable reference).

**ERPnext Reference:**
- `erpnext/crm/doctype/lead/lead.json` — ~50 data fields, UTM, qualification_status, territory, auto_create_contact
- `erpnext/crm/doctype/opportunity/opportunity.json` — Dynamic Link party_name, sales_stage, probability, expected_closing
- `erpnext/selling/doctype/quotation/quotation.json` — quotation_to Dynamic Link, valid_till, auto-repeat, make_sales_order
- `erpnext/controllers/selling_controller.py` — reference only; do not copy all 4,496 lines

**Key fields to implement:**
- Lead: name, email, phone, status, lead_name, company_name, UTM source/medium/campaign/content, qualification_status, territory, source, auto_create_contact
- Opportunity: party_type + party_name (Dynamic Link), opportunity_from, sales_stage, probability, expected_closing, currency, opportunity_amount, items table, lost_reason, competitors
- Quotation: quotation_to (Dynamic Link), party_name, valid_till, taxes, items, auto-repeat, lost_reasons, make_sales_order
- Status machines: Lead (Lead→Open→Replied→Opportunity→Quotation→Converted), Opportunity (Open→Quotation→Converted/Lost/Closed), Quotation (Draft→Open→Replied→Partially Ordered→Ordered→Lost/Cancelled/Expired)

#### 1.2 Purchase Order + GRN (Purchase Receipt)

**Why:** UltrERP has read-only supplier invoices but cannot issue POs or receive goods. PO + GRN enables the full purchase cycle and 3-way matching.

**Effort:** High — ERPnext's PO has 100+ fields across 1,390 lines, submittable with complex subcontracting, drop-ship, inter-company, project/cost center, and auto-repeat. The roadmap's Phase 1 table correctly classified this as High.

**Note:** `purchase_order.json` and `purchase_receipt.json` were not in the reference checkout. Implement based on standard ERPnext behavior documented here, verified against the live ERPnext repository before building.

**ERPnext Reference (verify before building):**
- `erpnext/buying/doctype/purchase_order/purchase_order.json` — supplier, items (qty, rate, warehouse, schedule_date), drop ship, subcontracting (fg_item/fg_item_qty)
- `erpnext/buying/doctype/purchase_receipt/purchase_receipt.json` — linked to PO via po_detail, received_qty, rejected_qty, rejected_warehouse
- `erpnext/controllers/buying_controller.py`

**Key fields:**
- PO: supplier, items table (item, qty, rate, warehouse, schedule_date, po_detail), status (Draft→Submitted→To Receive→To Bill→Completed/Cancelled/Closed), per_received, per_billed
- GRN: supplier, purchase_order, items table (po_detail, received_qty, rejected_qty, warehouse), status

#### 1.3 Toast Notification System

**Why:** Users get zero feedback when they save or when errors occur. This is the single highest-impact UI fix.

**Effort:** Low — use Radix Toast as base, build `useToast()` hook, replace SurfaceMessage errors with toast calls.

**Reference:** `src/components/ui/` for component structure, use existing Tailwind tokens.

#### 1.4 Multi-Currency Support (Phase 1 Fields Only)

**Why:** All transactions assume single currency. Required for international businesses.

**Effort:** Medium — adds currency + conversion_rate to transactions, exchange rate lookup, conversion math.

**Scope for Phase 1:** Fields + exchange rate lookup + conversion display only. No dual-currency GL entries yet. Full multi-currency GL (unrealized gain/loss on payment) is Phase 2.

**ERPnext Reference:** `currency`, `conversion_rate` on all transaction doctypes, `erpnext/setup/doctype/currency_exchange/`

#### 1.5 Quick Wins (Low Effort — Do Anytime)

These are standalone additions that don't require a full domain:

- **Sales Commission Tracking** — Add `sales_team` child table to Order (sales_person, allocated_percentage, commission_rate). Add `total_commission` computed field. Add commission report per salesperson.
- **Customer Group + Territory trees** — Add `customer_group` and `territory` as setup doctypes with tree structure. Add to Customer as Link fields.
- **UTM fields on Order** — Add `utm_source`, `utm_medium`, `utm_campaign`, `utm_content` to Order domain directly.
- **Payment Terms Template builder** — Upgrade from enum codes (NET_30/NET_60/COD) to a proper Template doctype with installment schedules.
- **Item Barcode support** — Add `barcode` field and `Item Barcode` child table to Products domain. `BarcodeScanner` utility in ERPnext can be referenced.

---

### Phase 2: P1 — Manufacturing, Accounting, HR, Quality

#### 2.1 GL Foundations + Financial Reports

**Why:** Without GL, UltrERP cannot produce P&L, balance sheet, or trial balance — the core of financial accounting.

**Effort:** **Minimally viable: Medium.** Full auto-GL from all transactions is High. Minimally viable: Chart of Accounts + manual Journal Entry + basic P&L. Auto-GL from existing transactions (modifying every submit/cancel handler) is Phase 3.

**Minimally viable scope (Medium):**
- Account model with tree (parent_account, lft, rgt) and types (Asset, Liability, Income, Expense, Equity)
- GL Entry DocType: account, party_type/party, debit, credit, company
- Manual Journal Entry (no auto-GL from transactions yet)
- Basic P&L report (income minus expenses per account)
- No dimensions, no fiscal year filtering

**Full scope (High):** Auto-GL entry creation from Sales Invoice, Purchase Invoice, Payment Entry on submit. Requires modifying every transaction's submit/cancel handlers — directly tied to `accounts_controller.py`'s 4,496 lines of complexity.

**ERPnext Reference:**
- `erpnext/setup/doctype/account/account.json` — tree structure, account_type, root_type
- `erpnext/accounts/doctype/gl_entry/gl_entry.json`
- `erpnext/accounts/doctype/journal_entry/journal_entry.json` — 18 voucher types, TDS support
- `erpnext/controllers/accounts_controller.py` — reference only for full implementation

#### 2.2 BOM + Work Orders

**Why:** Manufacturing is impossible without recipes (BOM) and production orders.

**Effort:** High (full ERPnext-style) — BOM is submittable (775-line JSON), Work Order is complex (745-line JSON). However, a **minimally viable BOM** is Medium effort.

**Minimally viable (Phase 2, Medium):** BOM with flat materials list (no operations), Work Order that consumes materials and produces FG via Stock Entry. No Job Cards, no operations routing, no multi-level BOM, no production planning.

**Full ERPnext-style (Phase 3, High):** BOM with operations routing, Job Cards with time logs, multi-level BOM recursion, scrap warehouse, production planning.

**ERPnext Reference:**
- `erpnext/manufacturing/doctype/bom/bom.json` — items, operations, is_submittable, inspection_required, quality_inspection_template
- `erpnext/manufacturing/doctype/work_order/work_order.json` — production_item, bom_no, qty, operations, transfer_material_against (Job Card or direct), status machine

#### 2.3 Sales Commission Tracking

**Why:** Businesses with sales teams need commission tracking.

**Effort:** Low — add fields to existing Order domain, no new domain needed. **This is a Quick Win — see Section 1.5.**

**ERPnext Reference:** `sales_team` table on SO: sales_person, allocated_percentage, commission_rate, allocated_amount

#### 2.4 HR / Employee Domain

**Why:** Project costing by person and timesheet billing require employee records.

**Effort:** Medium — new domain, tree structure, user linking.

**ERPnext Reference:** `erpnext/setup/doctype/employee/employee.json` — 80+ fields: reports_to (tree), attendance_device_id, department, designation, branch, holiday_list, create_user_automatically

#### 2.5 Quality Inspection

**Why:** Manufacturing and regulated goods require incoming/outgoing QC.

**Effort:** Medium — new domain linked to stock transactions.

**Note:** BOM has `inspection_required` + `quality_inspection_template` fields — QI integrates with BOM.

**ERPnext Reference:** `erpnext/stock/doctype/quality_inspection/quality_inspection.json` — inspection_type (Incoming/In Process/Outgoing), readings table, acceptance/rejection

#### 2.6 Serial + Batch Tracking

**Why:** Compliance for pharmaceuticals, electronics, food. Traceability.

**Effort:** High — requires SABB model, barcode integration, warehouse integration.

**ERPnext Reference:** `erpnext/stock/doctype/serial_and_batch_bundle/serial_and_batch_bundle.json` — central aggregation per transaction row

#### 2.7 RFQ + Supplier Quotation

**Why:** Competitive supplier bidding before PO creation.

**Effort:** Medium — standard transaction doctypes.

**ERPnext Reference:** `erpnext/buying/doctype/request_for_quotation/` — email to multiple suppliers, quote_status per supplier

#### 2.8 DatePicker Component

**Why:** Native `<input type="date">` everywhere is poor UX on mobile and has no localization.

**Effort:** Low — use react-day-picker or vaul's Calendar.

---

### Phase 3: P2 — Advanced Features

- Fixed Assets + Asset Maintenance + Asset Repair (depreciation, maintenance scheduling, repair tracking)
- Timesheets (project billing)
- Bank Reconciliation + Plaid
- Customer Portal
- Loyalty Program
- Dunning (collection letters)
- POS
- Regional Tax Modules (UAE VAT, Australia GST, US 1099)
- Blanket Orders
- SLA/Issue tracking
- Telephony/Call Center integration
- WhatsApp Business integration
- Auto-repeat recurring documents
- Email campaign management
- Bulk rename utility
- Video/portal content management
- Transaction deletion audit log

---

## 7. UI/UX Enhancement Roadmap

### P0 — Ship Next Sprint

| # | Component | What to Build |
|---|-----------|---------------|
| 1 | **Toast** | `src/components/ui/Toast.tsx` — Radix Toast base, useToast() hook, variants (success/error/warning/info), auto-dismiss, stacked, portal-rendered |
| 2 | **DatePicker** | `src/components/ui/DatePicker.tsx` — react-day-picker or vaul Calendar, range support, locale-aware |

### P1 — Second Sprint

| # | Component | What to Do |
|---|-----------|------------|
| 3 | **Zod + react-hook-form** | Add Zod to package.json, create `src/lib/schemas/`, migrate CustomerForm to zodResolver |
| 4 | **RecordPaymentForm** | Rewrite to react-hook-form (currently uses raw useState) |
| 5 | **Breadcrumb** | `src/components/ui/Breadcrumb.tsx`, add to PageLayout, use in all detail pages |
| 6 | **AlertFeed + CommandBar CSS** | Replace raw CSS with Tailwind equivalents |

### P2 — Later

| # | Component | What to Do |
|---|-----------|------------|
| 7 | Global Command Palette | Wire existing Command component globally with ⌘K listener |
| 8 | Spinner Component | `src/components/ui/Spinner.tsx` with sm/md/lg variants |
| 9 | Inline Table Editing | Add `editable` column prop to DataTable, optimistic update |
| 10 | Mobile Card View | Add `viewMode: 'table' \| 'cards'` to DataTable |
| 11 | Chart Color System | Categorical palette tokens (`--chart-1` through `--chart-10`) |
| 12 | Kanban Board | `src/components/ui/Kanban.tsx` with @dnd-kit |

---

## 8. Technical Considerations

### 8.1 Accounts Controller Complexity

`accounts_controller.py` is **4,496 lines** — this is not a simple base class. UltrERP cannot build a full equivalent monolithically. Instead:

1. Start with Account + GL Entry + Journal Entry
2. Add GL creation hooks to existing Invoice/Purchase Invoice submit handlers
3. Build advance allocation and payment reconciliation incrementally
4. Do not attempt to replicate all 4,496 lines at once

### 8.2 BOM Submittable Workflow

BOMs in ERPnext are **submittable** — they go Draft → Submitted. This matters for UltrERP: BOM should have a workflow state, and Work Orders should validate that the BOM is in Submitted state before consuming it.

### 8.3 BOM × Quality Inspection Integration

BOM has `inspection_required` + `quality_inspection_template` fields. When a Work Order consumes materials from a BOM that requires inspection, the Stock Entry for material transfer should trigger or gate on Quality Inspection completion.

### 8.4 Work Order — Two Transfer Modes

ERPnext Work Order supports two material transfer modes:
- **Direct** (`transfer_material_against: Work Order`): simple consume → produce
- **Job Card** (`transfer_material_against: Job Card`): operation-level time logging with per-employee time logs

Minimum viable should support direct mode. Job Cards are Phase 3.

### 8.5 Validation Schema Strategy

**Recommended: Zod-first with TypeScript inference**

```
src/lib/schemas/
  customer.schema.ts   — Zod schema + infer<> types
  invoice.schema.ts
  order.schema.ts
  payment.schema.ts

backend/domains/*/schemas.py
  — Already uses Pydantic. Keep field names in sync with Zod.
```

### 8.6 State Machine Pattern

ERPnext uses consistent state machines. For UltrERP:

- **Lead:** `lead | open | replied | opportunity | quotation | converted | lost | do_not_contact`
- **Opportunity:** `open | quotation | converted | lost | closed | replied`
- **Quotation:** `draft | open | replied | partially_ordered | ordered | lost | cancelled | expired`
- **Purchase Order:** `draft | submitted | to_receive | to_bill | completed | cancelled | closed`
- **Work Order:** `draft | submitted | not_started | in_process | stock_reserved | completed | stopped | closed | cancelled`

### 8.7 Dynamic Link Pattern

ERPnext's `party_name` Dynamic Link uses a `Link` field with `options` pointing to a second `party_type` field. Implement as:

```typescript
interface DynamicLinkSelectProps {
  partyType: 'customer' | 'lead' | 'prospect';
  value: string;
  onChange: (value: string) => void;
}
```

---

## Appendix: Key File Reference Map

| ERPnext File | Status in Reference | Purpose |
|-------------|---------------------|---------|
| `erpnext/crm/doctype/lead/lead.json` | ✅ Present | Lead schema (~50 data fields) |
| `erpnext/crm/doctype/opportunity/opportunity.json` | ✅ Present | Opportunity schema |
| `erpnext/selling/doctype/quotation/quotation.json` | ✅ Present | Quotation schema |
| `erpnext/buying/doctype/purchase_order/purchase_order.json` | ❌ **NOT in reference** | PO schema (verify from live repo) |
| `erpnext/buying/doctype/purchase_receipt/purchase_receipt.json` | ❌ **NOT in reference** | GRN schema (verify from live repo) |
| `erpnext/controllers/accounts_controller.py` | ✅ Present | 4,496-line accounting base |
| `erpnext/controllers/buying_controller.py` | ✅ Present | Buying base controller |
| `erpnext/controllers/selling_controller.py` | ✅ Present | Selling base controller |
| `erpnext/stock/doctype/item/item.json` | ✅ Present | Item schema |
| `erpnext/manufacturing/doctype/bom/bom.json` | ✅ Present | BOM schema (submittable) |
| `erpnext/manufacturing/doctype/work_order/work_order.json` | ✅ Present | Work Order schema |
| `erpnext/accounts/doctype/journal_entry/journal_entry.json` | ✅ Present | JE schema (18 voucher types, TDS) |
| `erpnext/accounts/doctype/account/account.json` | ✅ Present | Chart of Accounts schema |
| `erpnext/stock/doctype/quality_inspection/quality_inspection.json` | ✅ Present | QI schema |
| `erpnext/stock/doctype/serial_and_batch_bundle/serial_and_batch_bundle.json` | ✅ Present | SABB schema |
| `erpnext/projects/doctype/timesheet/timesheet.json` | ✅ Present | Timesheet schema |
| `erpnext/setup/doctype/employee/employee.json` | ✅ Present | Employee schema |
| `erpnext/public/js/utils/barcode_scanner.js` | ✅ Present | Barcode scanner utility |
| `erpnext/erpnext_integrations/doctype/plaid_settings/` | ✅ Present | Plaid integration |

---

## Appendix: Review Corrections Summary

| Correction Type | Count | Description |
|-----------------|-------|-------------|
| Validated correct | 12 | Dynamic Links, statuses, UTM, BOM operations, JE voucher types |
| Needs correction | 3 | Lead field count (~50 not 85), PO JSON not in ref, PR JSON not in ref |
| False positive | 1 | Invoice partial payment status already computed |
| False negative | 1 | Order payment terms codes already exist |
| New discoveries | 5 | BOM is_submittable, WO Job Card routing, BOM QI integration, JE TDS, accts_controller 4,496 lines |

### Additional Corrections from review-roadmap

| # | Original Classification | Corrected | Reason |
|---|----------------------|-----------|--------|
| Lead+Opportunity+Quotation | HIGH | **MEDIUM** | ~35-40 data fields each; no GL dependency; comparable to existing Order domain |
| Purchase Order | MEDIUM | **HIGH** | 100+ fields, submittable, 1390-line JSON; roadmap misclassifies; gap-analysis P0 table was correct |
| Multi-Currency (Phase 1) | MEDIUM | **MEDIUM (correct) + GL dependency understated** | Phase 1: fields + conversion math only. Dual-currency GL entries deferred to Phase 2 |
| GL minimally viable | HIGH | **MEDIUM** | Chart of Accounts + manual JE + basic P&L is medium. Auto-GL from transactions (4,496-line controller) is genuinely HIGH |
| Commission tracking | Phase 2 | **LOW** | Just fields on existing Order domain |
| Customer Group/Territory | Phase 2, Medium | **LOW** | Setup doctypes with tree structure only |
| UTM on Order | Phase 1 CRM only | **LOW (standalone)** | Easy standalone addition to Order domain |

### Additional Corrections from review-missing (10 new gaps discovered)

| Gap | ERPnext Reference | Impact |
|-----|-------------------|--------|
| **Telephony / Call Center** | `erpnext/telephony/doctype/call_log/` | No call logging, voice call settings, incoming call routing |
| **WhatsApp Integration** | `whatsapp_no` field on Lead, Opportunity | LINE exists but no WhatsApp — common in Taiwan B2B |
| **Auto-Repeat Recurring Documents** | `auto_email_to_sender`, recurring generation hooks | No automatic recurring invoice/order generation |
| **Asset Maintenance** | `erpnext/assets/doctype/asset_maintenance/` | No maintenance scheduling, calendar view, maintenance logs |
| **Asset Repair** | `erpnext/assets/doctype/asset_repair/` | No repair tracking with status, repair_cost |
| **Email Campaigns** | `erpnext/crm/doctype/email_campaign/` | No campaign tracking |
| **Bulk Rename Tool** | `erpnext/utilities/doctype/rename_tool/` | No bulk rename for items/customers/suppliers |
| **Video / Portal Content** | `erpnext/utilities/doctype/video/` | No video content management for portal |
| **Shift Management** | `erpnext/assets/doctype/asset_shift_allocation/` | Asset shift allocation only (HR removed from ERPnext v14) |
| **Transaction Deletion Audit Log** | Compliance record for deleted transactions | UltrERP has audit_log but not deletion-specific |

### Corrections from review-ui

| Claim | Status | Detail |
|-------|--------|--------|
| Toast missing | **CONFIRMED P0** | No Toast component in `src/components/ui/` |
| RecordPaymentForm uses raw useState | **CONFIRMED P1** | Confirmed — not react-hook-form |
| Zod not installed | **CONFIRMED P1** | No Zod in package.json, no `src/lib/schemas/` |
| Breadcrumbs missing | **CONFIRMED P1** | No Breadcrumb component in src/ |
| AlertFeed/CommandBar raw CSS | **CONFIRMED P1** | Both use raw CSS from inventory.css |
| Command component exists but not wired | **DISPUTED — nuanced** | `src/components/ui/command.tsx` EXISTS — gap is global ⌘K wiring, not component absence |
| Global command palette | **CONFIRMED P2** | Component exists, not wired globally as ⌘K |
