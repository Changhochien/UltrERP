# UltrERP vs ERPnext: Comprehensive Research Report

**Date:** 2026-04-20
**Research Agents:** 9 specialized agents
**Domains Covered:** 11
**Reference:** ERPnext v14/v15 source at `/reference/erpnext-develop/`

---

## 1. Executive Summary

This report synthesizes deep-dive research across 11 ERP domains comparing ERPnext's comprehensive feature set against UltrERP's current implementation. UltrERP has a solid foundation in core commerce flows (Customers, Invoices, Orders, Inventory, Payments) but faces significant gaps in CRM (no lead/opportunity pipeline), purchasing (no PO→GRN→PI flow), manufacturing (no BOM/work orders), and finance (no GL, multi-currency, or financial reports). The recommended starting point is Phase 1: fill CRM and purchase order gaps — these are foundational to revenue-generating workflows and represent the quickest path to covering the full order-to-cash cycle. UI/UX work should prioritize a Toast notification system and Calendar/DatePicker before tackling advanced patterns like Kanban boards or global command palettes.

---

## 2. Methodology

### Research Conduct

Nine specialized sub-agents conducted parallel research:

| Agent | Focus Area |
|-------|------------|
| Agent 1 | ERPnext CRM & Selling module (Lead, Opportunity, Quotation, Customer, Sales Order) |
| Agent 2 | ERPnext Buying & Procurement (Supplier, RFQ, Supplier Quotation, Purchase Order, Purchase Receipt) |
| Agent 3 | ERPnext Accounting & Finance (GL Entry, Sales/Purchase Invoice, Payment Entry, Journal Entry, Budget) |
| Agent 4 | ERPnext Stock/Inventory (Item, Stock Entry, Warehouse, Serial/Batch, Quality Inspection, Pick List) |
| Agent 5 | ERPnext Projects, HR & Support (Project, Task, Timesheet, Employee, Issue, SLA) |
| Agent 6 | ERPnext Core Infrastructure (Utilities, POS, Barcode, Portal, Regional, Integrations) |
| Agent 7 | ERPnext UX Patterns (workspace, reports, forms, print, navigation) |
| Agent 8 | UltrERP existing modules inventory |
| Agent 9 | UltrERP UI/UX component quality assessment |

### Research Files

| File | Content |
|------|---------|
| `.omc/research/erpnext-modules.md` | ERPnext module reference by domain |
| `.omc/research/erpnext-crm-sales-detailed.md` | CRM & Selling detailed doctype analysis |
| `.omc/research/erpnext-buying-detailed.md` | Buying & Procurement detailed analysis |
| `.omc/research/erpnext-accounting-detailed.md` | Accounting & Finance detailed analysis |
| `.omc/research/erpnext-inventory-detailed.md` | Stock/Inventory detailed analysis |
| `.omc/research/erpnext-projects-hr-detailed.md` | Projects, HR & Support detailed analysis |
| `.omc/research/erpnext-core-infrastructure.md` | Core infrastructure & integrations |
| `.omc/research/erpnext-ux-patterns.md` | UX patterns, workspace, reports |
| `.omc/research/erpnext-ui-design.md` | UI framework and form design patterns |
| `.omc/research/ultrerp-modules.md` | UltrERP modules inventory |
| `.omc/research/ultrerp-ui-design.md` | UltrERP UI/UX quality assessment |

---

## 3. ERPnext Feature Inventory

### 3.1 CRM Module

| Feature | Description | DocType |
|---------|-------------|---------|
| **Lead** | Prospective customer before conversion. Full lifecycle: Lead → Open → Replied → Opportunity/Quotation → Converted. Fields: email, phone, UTM, qualification status, territory, annual_revenue, no_of_employees. Auto-creates Contact on insert. | `erpnext/crm/doctype/lead/` |
| **Opportunity** | Potential sales deal keyed off Lead/Customer/Prospect. Dynamic Link party_name. Fields: sales_stage, probability, expected_closing, currency, opportunity_amount, items table. Status: Open → Quotation → Converted / Lost / Closed. | `erpnext/crm/doctype/opportunity/` |
| **Prospect** | Company-level grouping of leads/opportunities for campaign tracking. Contains Prospect Lead and Prospect Opportunity child tables. | `erpnext/crm/doctype/prospect/` |
| **Contract** | Legal agreements with customers/suppliers. Fulfilment checklist, start/end dates, contract_type. | `erpnext/crm/doctype/contract/` |
| **CRM Settings** | Single-doc settings: auto_creation_of_contact, close_opportunity_after_days, allow_lead_duplication_based_on_emails, default_valid_till. | `erpnext/crm/doctype/crm_settings/` |
| **Appointment** | Booking/scheduling for service businesses. | `erpnext/crm/doctype/appointment/` |
| **SMS Center** | SMS sending configuration and logs. | `erpnext/crm/doctype/sms_center/` |
| **Sales Stage** | Pipeline stage definitions (Prospecting, Qualification, etc.) | `erpnext/crm/doctype/sales_stage/` |
| **UTM Tracking** | utm_source, utm_medium, utm_campaign, utm_content on Lead, Opportunity, Quotation, Sales Order. Enabled via Selling Settings. | All CRM/Selling docs |

### 3.2 Selling Module

| Feature | Description | DocType |
|---------|-------------|---------|
| **Quotation** | Offers to customers with pricing, validity, terms. `quotation_to` Dynamic Link to Customer/Lead/Prospect. Status: Draft → Open → Replied → Partially Ordered / Ordered / Lost / Expired. Auto-repeated. Converts to Sales Order. | `erpnext/selling/doctype/quotation/` |
| **Sales Order** | Confirmed customer purchase. Status: Draft → On Hold / To Deliver and Bill / To Bill / To Deliver / Completed / Cancelled / Closed. Reserves stock on submit. Per-delivered, per-billed, per-picked indicators. Sales team + commission tracking. | `erpnext/selling/doctype/sales_order/` |
| **Delivery Note** | Shipment/delivery record. Creates Sales Invoice, updates stock. Per-billed/per-returned. Transporter, lr_no, vehicle_no, driver fields. | `erpnext/selling/doctype/delivery_note/` |
| **Sales Invoice** | Revenue recognition. `is_return` for credit notes. Payment schedule, advance allocation. Creates GL Entry on submit. Deferred revenue. | `erpnext/accounts/doctype/sales_invoice/` |
| **Product Bundle** | Kit/combination item. Packed items child table auto-populated. | `erpnext/selling/doctype/product_bundle/` |
| **Installation Note** | Post-delivery installation tracking. | `erpnext/selling/doctype/installation_note/` |
| **Customer** | Buyer organization/individual. Per-company receivable accounts (Party Account table). Per-company credit limits. Customer Group, Territory, default_currency, default_price_list. Salesforce-like sales team. Portal users. | `erpnext/selling/doctype/customer/` |
| **Customer Group** | Classification hierarchy. Tree structure. Default price_list, payment_terms. | `erpnext/setup/doctype/customer_group/` |
| **Territory** | Geographic regions. Tree structure. | `erpnext/setup/doctype/territory/` |
| **Sales Partner** | Channel partners earning commission. Commission rate, referral code. | `erpnext/selling/doctype/sales_partner/` |
| **Commission Tracking** | `enable_tracking_sales_commissions` in Selling Settings. `amount_eligible_for_commission` on SO. `total_commission` = amount × rate. `sales_team` table distributes via `allocated_percentage`. | Selling Settings + SO |

### 3.3 Buying Module

| Feature | Description | DocType |
|---------|-------------|---------|
| **Supplier** | Vendor of goods/services. On-hold with hold_type (All/Invoices/Payments) and release_date. `warn_rfqs / prevent_rfqs / warn_pos / prevent_pos` via Supplier Scorecard. Per-company payable accounts. Primary address/contact auto-creation. | `erpnext/buying/doctype/supplier/` |
| **Supplier Scorecard** | Vendor evaluation. Period (Week/Month/Year). Weighting function. Scoring criteria: on_time_shipment, quality, cost. Standing: Very Poor/Poor/Average/Excellent. Auto-updates Supplier blocking fields. | `erpnext/buying/doctype/supplier_scorecard/` |
| **Request for Quotation (RFQ)** | Solicitation to multiple suppliers. Email sending to suppliers. `quote_status` per supplier (Pending/Received). Maps to Supplier Quotation. | `erpnext/buying/doctype/request_for_quotation/` |
| **Supplier Quotation** | Supplier's pricing offer. Valid-till, quotation_number. Maps to Purchase Order. Auto-expiry scheduler job. | `erpnext/buying/doctype/supplier_quotation/` |
| **Purchase Order** | Formal buyer order. `per_received`, `per_billed`. `schedule_date` (Required By). Drop ship section. Inter-company linked to SO. Subcontracting: `fg_item`, `fg_item_qty`. Advance payment. | `erpnext/buying/doctype/purchase_order/` |
| **Purchase Receipt** | Goods received from supplier. Linked to PO via `po_detail`. Updates `received_qty` in Bin. | `erpnext/buying/doctype/purchase_receipt/` |
| **Purchase Invoice** | Supplier billing. `bill_no`, `bill_date` from supplier invoice. 3-way match with PO and PR. | `erpnext/accounts/doctype/purchase_invoice/` |
| **Blanket Order** | Master agreement for qty/rate over a period. `ordered_qty` tracked from PO/SO. Allowance % from Buying Settings. | `erpnext/manufacturing/doctype/blanket_order/` |
| **Subcontracting (Old Flow)** | PO `supplied_items` child table. `supplier_warehouse`. `create_raw_materials_supplied()` on submit. | `erpnext/buying/doctype/supplier/` |
| **Subcontracting (New Flow)** | PO `fg_item + fg_item_qty`. `auto_create_subcontracting_order` in Buying Settings. `Subcontracting Order` manages material transfer and receipt. | `erpnext/manufacturing/doctype/subcontracting_order/` |
| **Buying Settings** | `po_required`, `pr_required`, `maintain_same_rate`, `backflush_raw_materials_of_subcontract_based_on`, `auto_create_subcontracting_order`. | `erpnext/buying/doctype/buying_settings/` |

### 3.4 Inventory Module

| Feature | Description | DocType |
|---------|-------------|---------|
| **Item** | Products bought/sold/kept. `variant_of` for variants. `has_batch_no`, `has_serial_no`, `has_expiry_date`. `valuation_method` (FIFO/Moving Average/LIFO). `reorder_levels` table by warehouse. `inspection_required_before_purchase/delivery`. `is_sub_contracted_item`. `default_bom`. Item Barcode child table. | `erpnext/stock/doctype/item/` |
| **Item Group** | Product hierarchy. Tree. Default warehouse, uom, accounts per group. | `erpnext/setup/doctype/item_group/` |
| **Warehouse** | Storage locations. Tree structure. `warehouse_type`. `is_rejected_warehouse`. Default in-transit warehouse. Per-warehouse accounting. | `erpnext/stock/doctype/warehouse/` |
| **Stock Entry** | General movements: Material Receipt/Issue/Transfer/Manufacture/Repack/Send to Subcontractor. `from_bom`, `bom_no`. `fg_completed_qty`. Additional costs for landed cost. | `erpnext/stock/doctype/stock_entry/` |
| **Stock Reconciliation** | Adjust qty/valuation. Opening Stock or reconciliation purpose. Scan mode. | `erpnext/stock/doctype/stock_reconciliation/` |
| **Serial No** | Individual serial tracking. `status`: Active/Consumed/Delivered/Expired. Warranty tracking. Linked to Asset. | `erpnext/stock/doctype/serial_no/` |
| **Batch** | Lot tracking. `manufacturing_date`, `expiry_date`. `batch_qty`. `use_batchwise_valuation`. | `erpnext/stock/doctype/batch/` |
| **Serial and Batch Bundle** | Central aggregation doc for serial/batch on transaction lines. Inward/Outward/Maintenance/Asset Repair. | `erpnext/stock/doctype/serial_and_batch_bundle/` |
| **Quality Inspection** | Incoming/In Process/Outgoing QC. `quality_inspection_template`. Readings table (parameter, value, status). Triggered from PR/DN/SE. | `erpnext/stock/doctype/quality_inspection/` |
| **Pick List** | Picking for delivery/manufacture/transfer. `Get Item Locations`. Scan mode. Group same items. Links to Work Order/Material Request. | `erpnext/stock/doctype/pick_list/` |
| **Landed Cost Voucher** | Distribute shipping/duties/insurance across PR items. `distribute_charges_based_on`: Qty/Amount/Manual. | `erpnext/stock/doctype/landed_cost_voucher/` |
| **Putaway Rule** | Per item+warehouse capacity. Priority-based. Applied on PR/SE. | `erpnext/stock/doctype/putaway_rule/` |
| **Item Price** | Rate per item+uom+price_list+currency. Valid from/to. Batch-specific pricing. | `erpnext/stock/doctype/item_price/` |
| **Item Variant** | Template `has_variants=1`. Attributes table. `variant_based_on`: Item Attribute or Manufacturer. Variant Settings controls field copying. | `erpnext/stock/doctype/item_variant_settings/` |
| **Barcode Scanning** | `Barcode` field type. `scan_barcode` on Stock Entry, Stock Reconciliation, Pick List. `BarcodeScanner` class. | `erpnext/public/js/utils/barcode_scanner.js` |
| **Stock Closing Entry** | Locks stock transactions for a period. Status: Draft→Queued→In Progress→Completed. | `erpnext/stock/doctype/stock_closing_entry/` |
| **Stock Settings** | Valuation method default. `enable_stock_reservation`. Serial/batch settings. Quality inspection actions. Stock planning (auto_indent, auto_material_request). | `erpnext/stock/doctype/stock_settings/` |

### 3.5 Accounting Module

| Feature | Description | DocType |
|---------|-------------|---------|
| **Chart of Accounts** | Tree structure. `account_type`: Payable, Receivable, Bank, Cash, Stock, Tax, etc. `root_type`: Asset/Liability/Income/Expense/Equity. `freeze_account`. `balance_must_be`. | `erpnext/setup/doctype/account/` |
| **GL Entry** | Individual ledger entries. `account`, `party_type/party`, `debit/credit`, `cost_center`, `project`, `company`. `is_opening`, `is_advance`. `voucher_type`, `voucher_no`. | `erpnext/accounts/doctype/gl_entry/` |
| **Journal Entry** | Manual GL entries. `voucher_type`: Bank Entry, Cash Entry, Credit Note, Debit Note, etc. `multi_currency`. `cheque_no`, `clearance_date`. `is_opening`. | `erpnext/accounts/doctype/journal_entry/` |
| **Payment Entry** | Cash in/out. `payment_type`: Receive/Pay/Internal Transfer. `party_type`: Customer/Supplier/Employee. `paid_from`, `paid_to`. `references` table for invoice allocation. `allocate_advances_automatically`. | `erpnext/accounts/doctype/payment_entry/` |
| **Sales Invoice** | Revenue recognition. Creates GL Entry on submit (debits receivable, credits revenue). `update_billed_amount_in_sales_order`. `redeem_loyalty_points`. | `erpnext/accounts/doctype/sales_invoice/` |
| **Purchase Invoice** | Expense recognition. `credit_to` payable. `allocate_advances_automatically`. | `erpnext/accounts/doctype/purchase_invoice/` |
| **POS Invoice** | Cash sale. `pos_profile`. `payments` table. `change_amount`. `consolidated_invoice`. | `erpnext/accounts/doctype/pos_invoice/` |
| **Payment Terms Template** | Define instalment schedules: due date, invoice_portion, credit_days, discount. | `erpnext/accounts/doctype/payment_terms_template/` |
| **Fiscal Year** | Reporting period. `year_start_date`, `year_end_date`. Can be short year. | `erpnext/accounts/doctype/fiscal_year/` |
| **Cost Center** | Expense allocation. Tree structure. `company`. Budget distribution. | `erpnext/accounts/doctype/cost_center/` |
| **Budget** | Expense control. `budget_against`: Cost Center/Project. Monthly distribution. Action: Stop/Warn/Ignore when exceeded. | `erpnext/accounts/doctype/budget/` |
| **Finance Book** | Separate accounting books within same company. | `erpnext/accounts/doctype/finance_book/` |
| **Exchange Rate Revaluation** | Revalue foreign currency accounts when rates change. Creates GL entries. | `erpnext/accounts/doctype/exchange_rate_revaluation/` |
| **Dunning** | Automated collection letters for overdue invoices. `dunning_type` with rate_of_interest, dunning_fee. Body text templates. | `erpnext/accounts/doctype/dunning/` |
| **Loyalty Program** | Customer retention. Collection rules (tier, min_spent, points). `conversion_factor`. Expiry. Redeem on Sales Invoice. | `erpnext/accounts/doctype/loyalty_program/` |
| **Tax Category** | Tax classification. `tax_rule` for sales/purchase with party/city/state matching. | `erpnext/accounts/doctype/tax_category/` |
| **Sales/Purchase Taxes and Charges Template** | Tax rate templates per company. `charge_type`: Actual/On Net Total/On Previous Row Amount/On Item Quantity. `included_in_print_rate`. | `erpnext/accounts/doctype/purchase_taxes_and_charges/` |
| **Accounting Dimension** | Flexible reporting dimensions beyond Cost Center/Project. Department, Division, Employee, Location. `automatically_post_balancing_entry`. | `erpnext/accounts/doctype/accounting_dimension/` |
| **Company** (accounting fields) | Default accounts (receivable/payable/bank/cash), deferred revenue/expense accounts, advance accounts, exchange gain/loss accounts, asset defaults. | `erpnext/setup/doctype/company/` |
| **Accounts Controller** | Base class for all accounting transactions. `validate()`: date, party accounts, currency, taxes, payment schedule, due date, pricing rules. `on_submit()`: GL entries, outstanding, advances. `on_cancel()`: reverse. | `erpnext/controllers/accounts_controller.py` |
| **Payment Reconciliation** | Match payments to invoices. `get_outstanding_invoices()`. `allocate_amount()`. Unreconcile. | `erpnext/accounts/doctype/unreconcile_payment/` |
| **Credit Limit** | Per-company on Customer. `credit_limit_bypass` per company. Check on SO submit. `credit_days_based_on`: Linked Invoice Date/Due Date. | `erpnext/selling/doctype/customer/` |

### 3.6 Projects Module

| Feature | Description | DocType |
|---------|-------------|---------|
| **Project** | Customer-facing or internal projects. `percent_complete_method`: Manual/Task Completion/Task Progress/Task Weight. `collect_progress` via email. Costing: `total_costing_amount`, `total_purchase_cost`, `total_sales_amount`, `total_billed_amount`. Links to SO. | `erpnext/projects/doctype/project/` |
| **Task** | Work items within project. Tree structure (parent_task). Status: Open/Working/Pending Review/Overdue/Template/Completed/Cancelled. `depends_on` table with auto-rescheduling. `is_milestone`. | `erpnext/projects/doctype/task/` |
| **Timesheet** | Time logging. `activity_type`, `billing_rate`, `costing_rate`. Links to Project/Task. `total_billable_hours`. Status: Draft→Submitted→Partially Billed→Billed. | `erpnext/projects/doctype/timesheet/` |
| **Activity Type** | Activity classification with costing_rate and billing_rate per employee. | `erpnext/projects/doctype/activity_type/` |
| **Activity Cost** | Per employee+activity_type cost/billing rates. | `erpnext/projects/doctype/activity_cost/` |
| **Project Template** | Predefined task structure for new projects. `start` (days offset), `duration`, `task_weight` per task. `dependency_mapping()` creates task dependencies. | `erpnext/projects/doctype/project_template/` |
| **Project Update** | Progress collection via email. `sent` flag. Per-user status. | `erpnext/projects/doctype/project_update/` |
| **Projects Settings** | `collect_progress`, `send_progress_reminder`, `based_on`. | `erpnext/projects/doctype/projects_settings/` |
| **Project Reports** | Daily Timesheet Summary, Timesheet Billing Summary, Project Summary, Delayed Tasks Summary, Project-wise Stock Tracking. | `erpnext/projects/report/` |

### 3.7 Manufacturing Module

| Feature | Description | DocType |
|---------|-------------|---------|
| **Work Order** | Production order. `production_item`, `bom_no`, `qty`. `source_warehouse`, `wip_warehouse`, `fg_warehouse`, `scrap_warehouse`. `operations` table for job card routing. `material_transferred_for_manufacturing`, `produced_qty`. Status: Draft→Submitted→Not Started→In Process→Completed/Stopped/Closed. Reserve stock. Track semi-finished goods. | `erpnext/manufacturing/doctype/work_order/` |
| **Job Card** | Operation-level work instructions. `workstation`, `employee`, `time_logs` (start/end/completed_time). `job_status`. | `erpnext/manufacturing/doctype/job_card/` |
| **BOM** | Bill of Materials. `item` (finished good), `quantity` (of FG), `bom_operations` table, `bom_materials` table (item, qty, rate, operation, source_warehouse). Is_active, is_default. | `erpnext/manufacturing/doctype/bom/` |
| **Production Plan** | Aggregate demand from Sales Orders/Material Requests. Generates Work Orders and Material Requests. | `erpnext/manufacturing/doctype/production_plan/` |
| **Blanket Order** | See Buying Module. | `erpnext/manufacturing/doctype/blanket_order/` |

### 3.8 HR Module (Setup Doctypes)

| Feature | Description | DocType |
|---------|-------------|---------|
| **Employee** | Full HR record. `reports_to` tree. `attendance_device_id` for biometric. `date_of_joining`, `scheduled_confirmation_date`, `relieving_date`. `ctc`, `salary_mode`, bank details. `holiday_list`. `is_group` via reports_to. `create_user_automatically`. Education, work history child tables. | `erpnext/setup/doctype/employee/` |
| **Department** | Tree structure. `company`. `is_group`. | `erpnext/setup/doctype/department/` |
| **Designation** | Job titles. | `erpnext/setup/doctype/designation/` |
| **Branch** | Work location. | `erpnext/setup/doctype/branch/` |
| **Holiday List** | `weekly_off`, `get_weekly_off_dates`. `holidays` table. `get_local_holidays` by country/subdivision. Auto-calculate total holidays. | `erpnext/setup/doctype/holiday_list/` |
| **Employment Type** | Full-time/Part-time/Contractor/etc. | `erpnext/setup/doctype/employment_type/` |
| **Activity Cost** | See Projects. | `erpnext/projects/doctype/activity_cost/` |

### 3.9 Support Module

| Feature | Description | DocType |
|---------|-------------|---------|
| **Issue** | Customer support ticket. `status`: Open/Replied/On Hold/Resolved/Closed. `priority`, `issue_type`. SLA with response_by, resolution_by. `first_response_time`, `resolution_time` tracking. `split_issue()`. Auto-close via scheduler. | `erpnext/support/doctype/issue/` |
| **Service Level Agreement (SLA)** | Per priority response_time and resolution_time. Working hours via `Service Day` table. Holiday list. `sla_fulfilled_on`, `pause_sla_on` status tables. Entity: Customer/Customer Group/Territory. | `erpnext/support/doctype/service_level_agreement/` |
| **Warranty Claim** | Post-sale warranty. `serial_no`, `item_code`. `warranty_amc_status`: Under Warranty/Out of Warranty/Under AMC/Out of AMC. `complaint`, `resolution_date`. | `erpnext/support/doctype/warranty_claim/` |
| **Maintenance Schedule** | Planned maintenance visits. | `erpnext/support/doctype/maintenance_schedule/` |
| **Support Settings** | `close_issue_after_days`. | `erpnext/support/doctype/support_settings/` |

### 3.10 Core Infrastructure

| Feature | Description | DocType |
|---------|-------------|---------|
| **Bulk Transaction** | Batch convert documents (SO→SI/DN/PE, QTN→SO/SI, PO→PI/PR). Retry mechanism. `Bulk Transaction Log Detail`. Extensible via `bulk_transaction_task_mapper` hook. | `erpnext/utilities/bulk_transaction.py` |
| **Transaction Base** | Shared logic: `validate_posting_time`, `validate_uom_is_integer`, `validate_with_previous_doc`, `fetch_item_details`, `_apply_price_list`. | `erpnext/utilities/transaction_base.py` |
| **Activation Tracking** | `get_level()` scores setup completeness. `get_help_messages()` for desktop notifications guiding new users. | `erpnext/utilities/activation.py` |
| **POS** | `pos_item_cart`, `pos_item_selector`, `pos_payment`. Barcode scanning. `pos_profile` with payment methods. `pos_settings`. | `erpnext/selling/page/point_of_sale/` + `erpnext/accounts/doctype/pos_invoice/` |
| **Plaid Integration** | Bank account aggregation and transaction sync. `sync_transactions()`. HMAC-SHA256 webhook validation. | `erpnext/erpnext_integrations/doctype/plaid_settings/` |
| **Email Digest** | Scheduled management reports. Daily/Weekly/Monthly. Accounting cards, order metrics, project metrics, issue tracking. | `erpnext/setup/doctype/email_digest/` |
| **Authorization Rule** | Custom approval conditions based on document fields and user/role. | `erpnext/setup/doctype/authorization_rule/` |
| **Workflow Engine** | Frappe core: `Workflow` + `Workflow State` doctypes. Email notifications on transitions. | Frappe core |
| **EDi** | Electronic Data Interchange for trading partners. | `erpnext/edi/` |
| **Regional Modules** | US (IRS 1099), Australia (GST), UAE (VAT), Italy, South Africa (VAT), Turkey. `get_region()` hook pattern. | `erpnext/regional/` |

### 3.11 UX Patterns

| Pattern | Implementation |
|---------|---------------|
| **Workspace** | JSON config with charts, number_cards, links. Block types: chart, number_card, card, spacer, header. Per-module workspaces (Buying, Selling, Stock, Projects, CRM, Manufacturing, Support). | `erpnext/*/workspace/*/` |
| **Reports** | Standard 4-tuple return: `(columns, data, None, chart)`. `execute(filters)` with `validate_filters`. Tree-view hierarchies. Period ranges. Group-by dimensions. | `erpnext/*/report/` |
| **Print Formats** | Jinja2 HTML templates in `erpnext/templates/print_formats/`. `get_visible_columns()`, `get_width()`, `get_align_class()`, `print_value()`. Include templates for items, taxes, total. | `erpnext/templates/print_formats/` |
| **Child Table Grid** | `templates/form_grid/item_grid.html`. `get_visible_columns()`. Stock indicators (green/orange/red). Warehouse color coding. Responsive hidden columns. | `erpnext/templates/form_grid/` |
| **Quick Entry** | `*_quick_entry.js`. Modal dialog with minimal required fields. Reuses ContactAddressQuickEntryForm base class. | `erpnext/public/js/utils/` |
| **Dashboard Charts** | Line (trends), Donut (composition), Bar (comparisons). Config via JSON. Report-embedded charts. | `erpnext/*/dashboard_chart/` |
| **Barcode Scanner** | `BarcodeScanner` class with `process_scan()`, `scan_api_call()`. Location-first scanning. Audio feedback. Duplicate detection. | `erpnext/public/js/utils/barcode_scanner.js` |

---

## 4. UltrERP Current State

### 4.1 Customers

**Implemented:**
- Full CRUD with optimistic locking (`version` field, PATCH conflict detection)
- Business number validation (Taiwan checksum), duplicate detection
- Customer outstanding balance, statement generation, revenue analytics
- Customer type, credit limit, default discount, status management
- Role-based permissions: read=`admin|finance|sales`, write=`admin|sales`
- API endpoints: list (paginated, searchable), lookup by business_number, detail, outstanding, statement, analytics
- Frontend: `CustomerListPage`, `CustomerDetailPage`, `CreateCustomerPage`, `CustomerForm`, `CustomerCombobox`

**Gaps:**
- No bulk create/update/delete
- No contact-person CRUD separate from customer
- No customer-specific document attachments
- No customer portal

### 4.2 Invoices

**Implemented:**
- Immutable invoices (POST create only, no PUT/PATCH/DELETE)
- Invoice line items with tax computation
- Void endpoint with `VoidInvoiceRequest`
- eGUI tracking (mock mode only, live returns 503)
- PDF generation
- Payment tracking computed (not separate Payment records)
- Role-based: `admin|finance|sales`
- Frontend: `InvoiceList` with URL-synced filters, `InvoiceDetail`, `CreateInvoicePage`, `InvoiceLineEditor`, `InvoicePrintPreviewModal`

**Gaps:**
- No partial payment recording from invoice UI
- No credit note / invoice amendment domain
- No invoice approval workflow
- No invoice editing (only void-and-re-issue)
- eGUI live mode not functional

### 4.3 Orders

**Implemented:**
- State machine: PENDING → CONFIRMED → SHIPPED → FULFILLED (or CANCELLED)
- Payment terms codes: NET_30, NET_60, COD
- Stock check endpoint, reorder point computation
- LINE webhook notification on creation
- `invoice_id` field on order (but no API to generate invoice from order)
- Role-based: read=`admin|warehouse|sales`, write=`admin|sales`
- Frontend: `OrderList`, `OrderDetail`, `OrderForm`

**Gaps:**
- No frontend for creating orders from existing customer
- No order-to-invoice conversion in UI
- No shipping/delivery tracking integration
- No order approval workflow
- No backorder management UI (field exists)

### 4.4 Inventory

**Implemented:**
- Warehouses: full CRUD
- Transfers: POST/GET with detail endpoint
- Physical counts: `CountSession` with lines, submit/approve workflow
- Products: full CRUD with status, `stock_history`, `monthly_demand`, `planning_support`, `sales_history`, `top_customer`, suppliers management, AEO content, audit log
- Categories, Units of Measure: full CRUD
- Stock adjustments with approval workflow
- Reorder alerts and suggestions
- Supplier orders with `receive` action
- Reports: below-reorder, valuation
- Role-based: read=`admin|warehouse|sales`, write=`admin|warehouse`
- Extensive frontend: `BelowReorderReportPage`, `CategoriesPage`, `CountSessionDetailPage`, `ProductDetailPage`, `ReorderSuggestionsPage`, etc.

**Gaps:**
- **No manufacturing/BOM**: no Bill of Materials, work orders, production planning
- **No batch tracking**: no lot numbers
- **No expiration tracking**: no shelf-life/expiry
- **No multi-warehouse transfer UI**: endpoint exists but no dedicated UI
- **No quality management**: no QC checkpoints, inspection reports
- **No serial number tracking**

### 4.5 Payments

**Implemented:**
- Payment model: `customer_id`, `invoice_id`, `amount`, `payment_method`, `reference_number`
- Matched and unmatched (standalone) payment recording
- Auto-reconciliation endpoint (`POST /reconcile`)
- Manual and suggested match confirmation
- Role-based: `admin|finance`
- Frontend: `PaymentsPage`, `RecordPaymentForm`, `RecordUnmatchedPayment`, `ReconciliationScreen`

**Gaps:**
- No dedicated "record payment" standalone UI page
- No payment method management (no CRUD for payment method types)
- No frontend reconciliation UI (API-only)
- No payment advice / remittance slip generation

### 4.6 Purchases

**Implemented:**
- Read-only supplier invoice listing and viewing
- `SupplierInvoice` model: supplier_id, invoice_number, invoice_date, due_date, total_amount, status (open/paid/voided)
- Role-based: `admin|finance|warehouse`
- Frontend: `PurchasesPage`, `SupplierInvoiceDetail`, `SupplierInvoiceList`

**Gaps:**
- **No purchase creation**: only listing/viewing
- **No purchase order lifecycle**: no PR → PO → GRN flow
- **No goods receipt**: supplier orders can receive stock but no formal GRN
- **No landed cost calculation**
- **No 3-way matching** (PO → GRN → Supplier Invoice)

### 4.7 Reports

**Implemented:**
- AR aging report (`GET /ar-aging`)
- AP aging report (`GET /ap-aging`)
- Dashboard: revenue summary, KPI summary, top products/customers, visitor stats, cash flow, gross margin, revenue trend

**Gaps:**
- No P&L statement
- No balance sheet
- No cash flow statement (beyond dashboard widget)
- No trial balance
- No tax reports (VAT/GST)
- No financial report customization
- No report scheduling or subscriptions
- No report export beyond CSV from inventory

### 4.8 Additional Domains

| Domain | Implemented |
|--------|-------------|
| Dashboard | KPI summary, revenue, top products/customers, visitor stats, cash flow, gross margin |
| Settings | Key-value settings with sections, categories, seed data |
| Health | Health check endpoints |
| Auth | JWT authentication |
| Users | User management routes (frontend pages not mapped) |
| Audit | Audit logging domain |
| Approval | Approval workflow engine (no UI to configure) |
| LINE | LINE webhook integration (notifies on new orders) |
| AEO | AEO content generation |
| Product Analytics | Product analytics |
| Legacy Import | Legacy data import tool |
| Intelligence | Analytics/BI layer, separate page |

### 4.9 Cross-Domain Gaps

| Category | Gaps |
|----------|------|
| **Finance & Accounting** | No GL, no multi-currency, no fixed assets, no tax engine beyond Taiwan invoice codes, no financial report builder, no bank reconciliation |
| **Supply Chain** | No manufacturing/BOM, no batch/lot or expiry tracking, no serial number registry, no QC, no freight/shipping |
| **Sales & CRM** | No lead/opportunity pipeline, no quotation module, no sales target/commission tracking, no email integration beyond LINE |
| **Purchases** | No PR→PO→GRN flow, no 3-way matching, no landed cost |
| **HR & Org** | No employee records, no per-document permission rules, no leave/attendance, no payroll |
| **Infrastructure** | No attachment management beyond invoice S3 artifacts, no print layout designer, no workflow builder UI, no audit trail UI, no document versioning, no iPaaS/API hub |

---

## 5. Gap Analysis

### Priority 0 (Critical — Immediate)

| Gap | ERPnext Reference | Impact |
|-----|-------------------|--------|
| **No Lead/Opportunity pipeline** | `erpnext/crm/doctype/lead/`, `erpnext/crm/doctype/opportunity/` | Cannot track prospective customers, no sales funnel, no CRM lifecycle |
| **No Quotation module** | `erpnext/selling/doctype/quotation/` | Cannot send formal offers to customers before orders; no pricing validity, no quotation-to-SO flow |
| **No Purchase Order creation** | `erpnext/buying/doctype/purchase_order/` | Cannot issue formal orders to suppliers; only read-only supplier invoice tracking |
| **No Goods Receipt Note (GRN)** | `erpnext/buying/doctype/purchase_receipt/` | Cannot record inbound deliveries against PO; no 3-way matching foundation |
| **No multi-currency support** | `currency`, `conversion_rate` on all transactions in ERPnext | Cannot transact in foreign currencies; all amounts assumed in base currency |

### Priority 1 (Important — Next Sprint)

| Gap | ERPnext Reference | Impact |
|-----|-------------------|--------|
| **No Bill of Materials (BOM)** | `erpnext/manufacturing/doctype/bom/` | Cannot define product recipes; blocks work orders, production planning |
| **No Work Orders** | `erpnext/manufacturing/doctype/work_order/` | Cannot plan/track manufacturing; no production floor integration |
| **No GL/financial statements** | `erpnext/accounts/doctype/journal_entry/`, `erpnext/accounts/doctype/account/` | No double-entry accounting; no P&L, balance sheet, trial balance |
| **No commission tracking** | `sales_team` table, `total_commission` on SO in ERPnext | Cannot track/allocate sales commissions |
| **No HR/Employee domain** | `erpnext/setup/doctype/employee/` | No employee records; blocks timesheets, project costing by person |
| **No Quality Inspection** | `erpnext/stock/doctype/quality_inspection/` | Cannot QC incoming/outgoing goods |
| **No serial/batch tracking** | `erpnext/stock/doctype/serial_no/`, `erpnext/stock/doctype/batch/` | Cannot track individual items or lots; compliance gap for certain goods |
| **No RFQ/Supplier Quotation flow** | `erpnext/buying/doctype/request_for_quotation/` | Cannot solicit competitive quotes from suppliers |
| **No contact-person CRUD** | Dynamic Links in ERPnext (Address/Contact separate from Customer/Supplier) | Contacts managed only as embedded fields; no separate address book |

### Priority 2 (Polish — Later)

| Gap | ERPnext Reference | Impact |
|-----|-------------------|--------|
| **No fixed assets module** | `erpnext/assets/doctype/asset/` | No depreciation tracking, asset register |
| **No timesheets** | `erpnext/projects/doctype/timesheet/` | No time tracking against projects |
| **No bank reconciliation** | `erpnext/erpnext_integrations/doctype/plaid_settings/` | No matching payments to bank statements |
| **No warehouse transfer UI** | Transfer endpoint exists; ERPnext has `Stock Entry` for transfers | Multi-warehouse stock views missing |
| **No SLA/Issue tracking** | `erpnext/support/doctype/issue/`, `erpnext/support/doctype/service_level_agreement/` | No customer support ticketing |
| **No landed cost** | `erpnext/stock/doctype/landed_cost_voucher/` | Cannot absorb shipping/duties into item cost |
| **No auto-replenishment/MPS** | `erpnext/manufacturing/doctype/production_plan/` | No master production scheduling |
| **No regional tax modules** | `erpnext/regional/` (US, UAE, Australia, etc.) | Limited international compliance |
| **No Loyalty Program** | `erpnext/accounts/doctype/loyalty_program/` | No customer retention programs |
| **No Dunning** | `erpnext/accounts/doctype/dunning/` | No automated collection letters |
| **No POS** | `erpnext/selling/page/point_of_sale/` | No point-of-sale interface |
| **No blanke orders** | `erpnext/manufacturing/doctype/blanket_order/` | No master purchase/sales agreements |

### UI/UX Gaps by Priority

| Priority | Gap | Impact |
|----------|-----|--------|
| **P0** | No Toast notification system | Users get no feedback on save/error actions |
| **P0** | No Calendar/DatePicker | Native `<input type="date">` everywhere; poor UX on mobile |
| **P1** | Inconsistent form validation (some use react-hook-form, some use raw useState) | Maintenance burden, inconsistent UX |
| **P1** | No Zod schema centralization | Validation scattered across custom resolvers |
| **P1** | No Breadcrumb navigation | Users lose context in deep hierarchies |
| **P1** | AlertFeed and CommandBar use raw CSS instead of Tailwind | Inconsistent with rest of app |
| **P2** | No global command palette (⌘K) | No quick navigation |
| **P2** | No Kanban board | Task/project views limited |
| **P2** | No inline editing in tables | All data is read-only in lists |
| **P2** | Chart colors all monochrome | Limited data visualization expressiveness |
| **P2** | Mobile table experience (horizontal scroll only) | Poor mobile UX |

---

## 6. Recommended Implementation Roadmap

### Phase 1: Core P0 Gaps — Quick Wins

**Goal:** Complete the order-to-cash and purchase-to-pay cycles with minimal missing pieces.

#### 1.1 CRM Foundation — Lead + Opportunity + Quotation

**Why:** UltrERP can create customers and orders but has no pre-sale pipeline. Adding Lead/Opportunity/Quotation closes the full revenue lifecycle from prospecting to cash collection.

**Effort:** High — requires new domain (CRM) with state machines, Dynamic Links, whitelist methods, UTM tracking.

**ERPnext Reference:**
- `erpnext/crm/doctype/lead/lead.json` — 85 fields including UTM, qualification_status, territory, auto_create_contact
- `erpnext/crm/doctype/opportunity/opportunity.json` — Dynamic Link `party_name`, sales_stage, probability, expected_closing
- `erpnext/crm/doctype/quotation/quotation.json` — `quotation_to` Dynamic Link, `valid_till`, auto-repeat, lost_reasons
- `erpnext/controllers/selling_controller.py` — base controller for all selling docs

**Key Features:**
- Lead: Lead → Open → Replied → Opportunity → Quotation → Converted state machine
- Lead conversion: `make_customer`, `make_opportunity`, `make_quotation` whitelist methods
- Opportunity: from Lead/Customer/Prospect, `opportunity_amount`, `sales_stage`, `probability`
- Quotation: `quotation_to` Dynamic Link (Customer/Lead/Prospect), `valid_till`, taxes, `make_sales_order`
- UTM fields on Lead, Opportunity, Quotation, Sales Order
- CRM Settings: `auto_creation_of_contact`, `close_opportunity_after_days`

#### 1.2 Purchase Order + Purchase Receipt (GRN)

**Why:** UltrERP has read-only supplier invoices but cannot issue POs or receive goods. PO + GRN is the foundation for 3-way matching and inventoryreceiving.

**Effort:** Medium — new domain with standard transaction patterns.

**ERPnext Reference:**
- `erpnext/buying/doctype/purchase_order/purchase_order.json` — 100+ fields: supplier, items with `po_detail`, `received_qty`, `billed_amt`, `schedule_date`, `drop_ship`, `supplied_items` for subcontracting
- `erpnext/buying/doctype/purchase_receipt/purchase_receipt.json` — linked to PO via `po_detail`, `rejected_qty`, `rejected_warehouse`
- `erpnext/controllers/buying_controller.py` — base controller: `validate_items`, `validate_warehouse`, `validate_for_subcontracting`, `update_last_purchase_rate`

**Key Features:**
- Purchase Order: issue to supplier with qty, rate, warehouse, schedule_date
- PO → GRN flow: GRN receives goods, updates `received_qty` on PO
- PO Item: `bom_no` for subcontracting, `fg_item`/`fg_item_qty` for new subcontracting
- `warn_rfqs / prevent_rfqs / prevent_pos` from Supplier Scorecard integration (Phase 2)
- Status: Draft → Submitted → To Receive → To Bill → Completed / Cancelled / Closed

#### 1.3 Multi-Currency Support

**Why:** All current transactions assume single currency. Businesses operating internationally need multi-currency invoicing, payments, and GL.

**Effort:** Medium — requires currency field on transactions, exchange rate lookup, conversion calculation.

**ERPnext Reference:**
- `currency`, `conversion_rate` on all transaction doctypes in ERPnext
- `erpnext/setup/doctype/currency_exchange/` — exchange rate table
- `erpnext/accounts/doctype/exchange_rate_revaluation/` — periodic revaluation
- `erpnext/controllers/accounts_controller.py` — `validate_currency()` method

**Key Features:**
- `currency` + `conversion_rate` on Customer/Supplier/Transactions
- `base_opportunity_amount`, `base_total`, etc. in company currency alongside transaction currency
- Exchange rate lookup by date on transaction save
- GL entries in both transaction and company currency

### Phase 2: Important P1 Gaps

**Goal:** Add manufacturing, financial accounting, HR, and quality management.

#### 2.1 Bill of Materials + Work Orders

**Why:** Businesses with any manufacturing need BOM to define recipes and Work Orders to plan production.

**Effort:** High — complex domain with operations, scheduling, stock reservations.

**ERPnext Reference:**
- `erpnext/manufacturing/doctype/bom/bom.json` — `item`, `bom_materials` (item, qty, rate, source_warehouse), `bom_operations` (operation, workstation, time)
- `erpnext/manufacturing/doctype/work_order/work_order.json` — `production_item`, `bom_no`, `qty`, `operations`, `required_items`, `reserve_stock`, `transfer_material_against: Job Card / Material Transfer`

**Key Features:**
- BOM: multi-level (use_multi_level_bom), operations routing, scrap warehouse
- Work Order: from Sales Order or standalone, `planned_start_date`, `actual_start_date`, `produced_qty`, `process_loss_qty`
- Job Card: operation-level time logging, employee assignment
- Stock Entry for manufacture: consumes raw materials, produces finished goods
- Integration: Production Plan aggregates SO demand → creates Work Orders

#### 2.2 GL + Financial Reports

**Why:** Without GL, UltrERP cannot produce P&L, balance sheet, or trial balance. This is the single largest accounting gap.

**Effort:** High — requires account model, GL entry creation from transactions, report engine.

**ERPnext Reference:**
- `erpnext/setup/doctype/account/account.json` — tree: `account_type`, `root_type`, `company`, `freeze_account`, `balance_must_be`
- `erpnext/accounts/doctype/journal_entry/journal_entry.json` — manual GL entries
- `erpnext/controllers/accounts_controller.py` — `make_gl_entries()` on submit, `make_reverse_gl_entries()` on cancel
- `erpnext/accounts/doctype/gl_entry/gl_entry.json` — individual ledger entries

**Key Features:**
- Chart of Accounts tree with types: Asset, Liability, Income, Expense, Equity
- GL Entry creation from Sales Invoice, Purchase Invoice, Payment Entry, Journal Entry
- Account types: Receivable (links to Customer), Payable (links to Supplier), Bank, Cash, Stock
- Financial reports: P&L, Balance Sheet, Trial Balance, Cash Flow Statement
- Accounting Dimensions: Cost Center, Project on all GL entries
- Fiscal Year with year_start/year_end

#### 2.3 Sales Commission Tracking

**Why:** Businesses with sales teams need to track and allocate commissions.

**Effort:** Low — add fields to existing Order domain and a commission report.

**ERPnext Reference:**
- `sales_team` child table on Sales Order: `sales_person`, `allocated_percentage`, `commission_rate`, `allocated_amount`
- `enable_tracking_sales_commissions` in Selling Settings
- `calculate_commission()` in `erpnext/controllers/selling_controller.py`
- `calculate_contribution()` distributes among team based on `allocated_percentage`

**Key Features:**
- Sales Partner with commission rate
- Sales Team table on Customer (defaults) and Sales Order (override)
- `amount_eligible_for_commission` = items with `grant_commission=1` × net rate
- `total_commission` = eligible amount × rate
- Commission report per salesperson/period

#### 2.4 HR/Employee Domain

**Why:** Project costing by person and timesheet billing require employee records.

**Effort:** Medium — new domain with tree structure and user linking.

**ERPnext Reference:**
- `erpnext/setup/doctype/employee/employee.json` — 80+ fields: personal, company (department, designation, branch), reports_to (tree), salary, attendance_device_id,holiday_list
- `erpnext/projects/doctype/timesheet/timesheet.json` — `employee`, `timesheet_details`: activity_type, project, task, billing_hours, costing_rate
- `erpnext/setup/doctype/department/department.json` — tree structure

**Key Features:**
- Employee: reports_to hierarchy (tree), department, designation, branch
- `create_user_automatically` on employee save
- Holiday List: weekly_off, holiday table, country-based local holidays
- Department tree: `parent_department`, `company`, `is_group`

#### 2.5 Quality Inspection

**Why:** Manufacturing and regulated goods require incoming/outgoing QC.

**Effort:** Medium — new domain linked to stock transactions.

**ERPnext Reference:**
- `erpnext/stock/doctype/quality_inspection/quality_inspection.json` — `inspection_type`: Incoming/In Process/Outgoing, `reference_type`: PR/DN/SE, readings table
- `erpnext/stock/doctype/quality_inspection_template/quality_inspection_template.json` — parameter definitions
- `erpnext/stock/doctype/stock_settings/stock_settings.json` — `action_if_quality_inspection_is_not_submitted`: Stop/Warn

**Key Features:**
- Quality Inspection Template: reading parameters with accept/reject criteria
- Inspection triggered from PR/DN/SE via `inspection_required_before_purchase/delivery` on Item
- Readings: parameter, value, status, remark
- Status: Accepted/Rejected/Cancelled
- Blocks stock submission if QI is required and not submitted

#### 2.6 Serial and Batch Tracking

**Why:** Compliance for pharmaceuticals, electronics, food. Individual item traceability.

**Effort:** High — requires SABB model, barcode integration, warehouse integration.

**ERPnext Reference:**
- `erpnext/stock/doctype/serial_no/serial_no.json` — `item_code`, `warehouse`, `status`: Active/Consumed/Delivered/Expired, `purchase_rate`, warranty_expiry
- `erpnext/stock/doctype/batch/batch.json` — `item`, `batch_qty`, `manufacturing_date`, `expiry_date`, `use_batchwise_valuation`
- `erpnext/stock/doctype/serial_and_batch_bundle/serial_and_batch_bundle.json` — central SABB doc aggregates serial/batch per transaction line
- `erpnext/public/js/utils/barcode_scanner.js` — `BarcodeScanner` class with `process_scan()`, `scan_api_call()`, location-first scanning

**Key Features:**
- Item flags: `has_batch_no`, `has_serial_no`, `has_expiry_date`, `shelf_life_in_days`, `retain_sample`
- Batch auto-creation: `batch_number_series`, `create_new_batch` on Item
- Serial No auto-creation: `serial_no_series`
- SABB created per transaction row for serial/batch tracking
- Fifo/expiry-based picking in Pick List
- Barcode scanning in Stock Entry, Stock Reconciliation, Pick List

#### 2.7 RFQ + Supplier Quotation Flow

**Why:** Competitive supplier bidding before PO creation.

**Effort:** Medium — RFQ and SQ are standard transaction doctypes.

**ERPnext Reference:**
- `erpnext/buying/doctype/request_for_quotation/request_for_quotation.json` — `suppliers` table (email, send_email, quote_status), `items` table, email template, send_to_supplier()
- `erpnext/buying/doctype/supplier_quotation/supplier_quotation.json` — from RFQ, valid_till, maps to PO
- Supplier Quotation Comparison report

**Key Features:**
- RFQ: send to multiple suppliers, track quote_status per supplier
- Supplier Quotation: supplier pricing, valid_till, maps to PO
- Compare quotations side-by-side before creating PO

### Phase 3: P2 Polish

**Goal:** Advanced features for complex business scenarios.

#### 3.1 Fixed Assets Module

**Why:** Asset tracking with depreciation for equipment purchases.

**Reference:** `erpnext/assets/doctype/asset/`, `erpnext/assets/doctype/asset_movement/`, `erpnext/assets/doctype/asset_depreciation_schedule/`

#### 3.2 Bank Reconciliation + Plaid Integration

**Why:** Match payments to bank statement transactions automatically.

**Reference:** `erpnext/erpnext_integrations/doctype/plaid_settings/` + `erpnext/accounts/doctype/bank_reconciliation_tool/`

#### 3.3 Regional Tax Modules

**Why:** VAT/GST compliance for specific countries.

**Reference:** `erpnext/regional/united_states/` (IRS 1099), `erpnext/regional/uae/` (UAE VAT), `erpnext/regional/australia/` (GST)

#### 3.4 Customer Portal

**Why:** Self-service for customers to view orders, invoices, payments.

**Reference:** `erpnext/portal/` — customer portal doctypes, `erpnext/www/`

#### 3.5 Loyalty Program

**Why:** Customer retention through points/rewards.

**Reference:** `erpnext/accounts/doctype/loyalty_program/`

#### 3.6 Dunning / Collection Letters

**Why:** Automated overdue invoice reminders.

**Reference:** `erpnext/accounts/doctype/dunning/`

---

## 7. UI/UX Enhancement Roadmap

### P0 — Critical (Ship in Next Sprint)

#### 7.1 Toast Notification System

**Why:** Users have no feedback on form submission success or API errors. The only current feedback is form re-render or alert boxes.

**Implementation:**
```
Component: Toast
Location: src/components/ui/Toast.tsx
Variants: success, error, warning, info
Features: auto-dismiss (5s), manual close, action button, stacked toasts
Animation: slide-in from top-right
Stack: useToast() hook pattern (similar to Sonner/experimental-use-toast)
```

**Usage:** Every mutation (create/update/delete) should call `toast.success()` or `toast.error()`. Replace inline `SurfaceMessage` error displays with toast.

#### 7.2 Calendar / DatePicker Component

**Why:** Native `<input type="date">` is used everywhere — poor UX on mobile, no range selection, no localization.

**Implementation:**
```
Component: Calendar
Location: src/components/ui/Calendar.tsx
Features: single date, date range, min/max constraints, locale-aware month/year navigation
Integration: Replaces DateRangeFilter inputs, Invoice date fields, Order delivery dates
Consider: Use a headless library (e.g., react-day-picker or vaul's Calendar)
```

### P1 — Important (Ship in 2nd Sprint)

#### 7.3 Zod Schema Centralization

**Why:** Validation is scattered between custom native resolvers and HTML5 attributes. No schema is reusable across client validation, API validation, and test fixtures.

**Implementation:**
- Introduce Zod as the standard validation library
- Create `src/lib/schemas/` directory with one file per domain: `customer.schema.ts`, `invoice.schema.ts`, `order.schema.ts`, etc.
- Replace `buildNativeResolver()` in CustomerForm with Zod resolver
- Generate TypeScript types from schemas (infer<>)
- Use schemas for API request/response typing

#### 7.4 Form Library Consolidation

**Why:** CustomerForm uses react-hook-form with custom resolver; RecordPaymentForm uses raw useState. Inconsistent.

**Implementation:**
- Standardize ALL forms on react-hook-form + Zod
- Replace RecordPaymentForm (`src/domain/payments/components/`) to use react-hook-form
- InvoiceLineEditor should use `useFieldArray` from react-hook-form
- Add `useForm()` base hook in `src/hooks/` that wraps react-hook-form with default config

#### 7.5 Breadcrumb Navigation

**Why:** Users navigating deep hierarchies (e.g., `/inventory/products/:id`) have no breadcrumbs.

**Implementation:**
```
Component: Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbSeparator
Location: src/components/ui/Breadcrumb.tsx
Features: separator (chevron/slash), ellipsis for long paths, current page non-link
Integration: Add to PageLayout, use in all detail pages
```

#### 7.6 CSS Consistency Fix — AlertFeed and CommandBar

**Why:** These components use raw CSS classes instead of Tailwind, inconsistent with rest of app.

**Implementation:**
- Audit `inventory.css` and `command-bar` CSS in `src/domain/inventory/components/AlertFeed.tsx` and `src/domain/inventory/components/CommandBar.tsx`
- Replace with Tailwind equivalents
- Remove orphaned CSS files after migration

### P2 — Nice to Have (Later)

#### 7.7 Global Command Palette (⌘K)

**Why:** Quick navigation for power users. `Command` component already exists but isn't wired globally.

**Implementation:**
- Wrap app in CommandPalette context
- Add ⌘K listener at root
- Index routes, customers, orders, products for fuzzy search
- Use existing Radix UI + cmdk `Command` component

#### 7.8 Loading Spinner Component

**Why:** Submit buttons lack spinner during async operations. Only Skeleton components exist.

**Implementation:**
```
Component: Spinner
Location: src/components/ui/Spinner.tsx
Variants: sm, md, lg
Usage: inside Button during isPending state, in dialog headers, inline with text
```

#### 7.9 Inline Editing in DataTable

**Why:** All DataTable cells are read-only. ERPnext supports inline editing in some grids.

**Implementation:**
- Add `editable: boolean` prop to DataTable column definition
- `onCellEdit(rowId, columnId, value)` callback
- Optimistic update with rollback on error
- Add `EditableCell` component with click-to-edit pattern

#### 7.10 Responsive Table Views (Mobile Cards)

**Why:** DataTable overflows on mobile with just horizontal scroll. No card-based mobile view.

**Implementation:**
- Add `viewMode: 'table' | 'cards'` prop to DataTable
- In cards mode: stack key-value pairs per row as a Card
- Detect mobile via `useMediaQuery` or viewport width
- Persist preference in localStorage

#### 7.11 Kanban Board Component

**Why:** ERPnext uses Kanban for task views. UltrERP has no board component.

**Implementation:**
```
Component: KanbanBoard<T>, KanbanColumn, KanbanCard
Location: src/components/ui/Kanban.tsx
Features: drag-and-drop via @dnd-kit, column headers with count, add card button
Usage: Task board (if Project domain is built), Opportunity pipeline (if CRM built)
```

#### 7.12 Chart Color System Enhancement

**Why:** All chart colors are monochrome. Limited expressiveness for data visualization.

**Implementation:**
- Extend CSS design tokens with a categorical color palette
- `--chart-1` through `--chart-10` with perceptually distinct colors
- Update `src/lib/api/dashboard.ts` to use categorical colors for multi-series charts
- Replace monochrome chart tokens with a diverging + categorical palette

---

## 8. Technical Considerations

### 8.1 Validation Schema Strategy

**Recommendation: Zod-first with TypeScript inference**

Current state:
- CustomerForm: custom native resolver (`buildNativeResolver()`) — manual field-to-error-key mapping
- RecordPaymentForm: raw useState, manual validation
- No shared schema between frontend validation and API Pydantic models

Target state:
```
src/lib/schemas/
  customer.schema.ts   — Zod schema, exports infer<> types
  invoice.schema.ts
  order.schema.ts
  payment.schema.ts

backend/domains/customers/schemas.py
  — Already uses Pydantic. Keep in sync with Zod schema field names.

src/components/customers/CustomerForm.tsx
  — useForm({ resolver: zodResolver(customerSchema) })
```

### 8.2 Form Library Consolidation

**Recommendation: Standardize on react-hook-form + Zod across all forms**

| Form | Current Approach | Target Approach |
|------|-----------------|------------------|
| CustomerForm | react-hook-form + custom resolver | react-hook-form + Zod |
| RecordPaymentForm | useState | react-hook-form + Zod |
| InvoiceLineEditor | (not read fully) | useFieldArray + Zod |
| OrderForm | (not analyzed) | react-hook-form + Zod |
| CreateProductForm | (not analyzed) | react-hook-form + Zod |

Create `src/hooks/useForm.ts` that wraps react-hook-form with defaults:
- `mode: "onSubmit"`
- `defaultValues` from schema defaults
- Error display via `<FieldError>` component

### 8.3 State Machine Patterns

ERPnext uses consistent state machine patterns. UltrERP's Order domain has a basic state machine (PENDING → CONFIRMED → SHIPPED → FULFILLED). When building new domains:

**For Lead/Opportunity:**
- Define status constants as a union type: `"lead" | "open" | "replied" | "opportunity" | "quotation" | "converted" | "lost"`
- Implement `canTransition(current, next)` guard
- Use `status` field with explicit state transitions

**For Purchase Order:**
- Define statuses: `"draft" | "submitted" | "to_receive" | "to_bill" | "completed" | "cancelled" | "closed"`
- `per_received` and `per_billed` as computed percentage fields
- `set_status()` helper updates status based on percentages

### 8.4 Dynamic Link Pattern

ERPnext's Dynamic Link (`party_name` pointing to Lead/Customer/Prospect) is implemented via a `Link` field with `options: "DynamicLink"` and a companion `party_type` field. UltrERP should implement this as:

```typescript
// DynamicLinkSelect component
interface DynamicLinkSelectProps {
  partyType: 'customer' | 'lead' | 'prospect' | 'supplier';
  value: string;
  onChange: (value: string) => void;
}
// Shows filtered list based on partyType selection
```

### 8.5 MCP Tool Exposure

ERPnext uses Frappe's `whitelist` decorator to expose Python methods as RPC. UltrERP's MCP server (`backend/domains/*/mcp.py`) already exposes some tools. For new domains, follow the existing pattern:

```python
# backend/domains/crm/mcp.py
@mcp.tool()
def create_lead(data: LeadCreate) -> LeadResponse:
    ...

@mcp.tool()
def get_lead(id: str) -> LeadResponse:
    ...

@mcp.tool()
def transition_lead(id: str, new_status: str) -> LeadResponse:
    ...
```

### 8.6 Document Versioning and Optimistic Locking

Customer domain already implements optimistic locking with a `version` field. Extend this pattern:
- PATCH endpoint returns `409 Conflict` if `If-Match` header version doesn't match
- Frontend sends `If-Match: <version>` header on all updates
- This prevents concurrent edit conflicts

### 8.7 GL Creation Strategy

Adding GL requires careful design:

1. **Account model** — tree structure with `lft/rgt` for hierarchy
2. **Transaction → GL mapping** — when Invoice is submitted, create GL entries:
   - DR Customer Receivable (from `debit_to`) | CR Revenue Account
   - DR Tax Payable | CR Tax collected
3. **Reversal on cancel** — create reversing entries with `is_cancelled` flag
4. **Dimensions** — `cost_center` and `project` on all GL entries for drill-down

### 8.8 Multi-Currency GL

When multi-currency is added:
- GL entry stores both `debit`/`credit` (company currency) and `debit_in_account_currency`/`credit_in_account_currency`
- Exchange rate stored on transaction header
- Unrealized gain/loss recognized on payment if exchange rate changed

---

## Appendix: Key File Reference Map

| ERPnext File | Purpose |
|-------------|---------|
| `erpnext/crm/doctype/lead/lead.json` | Lead doctype schema |
| `erpnext/crm/doctype/lead/lead.py` | Lead controller |
| `erpnext/selling/doctype/quotation/quotation.json` | Quotation doctype schema |
| `erpnext/selling/doctype/sales_order/sales_order.json` | Sales Order schema |
| `erpnext/selling/doctype/sales_order/sales_order.py` | Sales Order controller |
| `erpnext/buying/doctype/purchase_order/purchase_order.json` | Purchase Order schema |
| `erpnext/buying/doctype/purchase_receipt/purchase_receipt.json` | Purchase Receipt schema |
| `erpnext/buying/doctype/supplier/supplier.json` | Supplier schema |
| `erpnext/accounts/doctype/sales_invoice/sales_invoice.json` | Sales Invoice schema |
| `erpnext/accounts/doctype/payment_entry/payment_entry.json` | Payment Entry schema |
| `erpnext/accounts/doctype/journal_entry/journal_entry.json` | Journal Entry schema |
| `erpnext/controllers/accounts_controller.py` | Base accounting controller |
| `erpnext/controllers/buying_controller.py` | Base buying controller |
| `erpnext/controllers/selling_controller.py` | Base selling controller |
| `erpnext/stock/doctype/stock_entry/stock_entry.json` | Stock Entry schema |
| `erpnext/stock/doctype/item/item.json` | Item schema |
| `erpnext/stock/doctype/warehouse/warehouse.json` | Warehouse schema |
| `erpnext/stock/doctype/quality_inspection/quality_inspection.json` | Quality Inspection schema |
| `erpnext/stock/doctype/serial_and_batch_bundle/serial_and_batch_bundle.json` | SABB schema |
| `erpnext/manufacturing/doctype/bom/bom.json` | BOM schema |
| `erpnext/manufacturing/doctype/work_order/work_order.json` | Work Order schema |
| `erpnext/projects/doctype/project/project.json` | Project schema |
| `erpnext/projects/doctype/task/task.json` | Task schema |
| `erpnext/projects/doctype/timesheet/timesheet.json` | Timesheet schema |
| `erpnext/setup/doctype/employee/employee.json` | Employee schema |
| `erpnext/setup/doctype/account/account.json` | Account schema |
| `erpnext/public/js/utils/barcode_scanner.js` | Barcode scanner utility |
| `erpnext/erpnext_integrations/doctype/plaid_settings/plaid_settings.json` | Plaid integration |
