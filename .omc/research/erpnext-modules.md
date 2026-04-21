# ERPnext Module Reference

Source: `/Users/changtom/Downloads/UltrERP/reference/erpnext-develop`

---

## 1. CRM Module

### Lead

**Entities Managed:** Prospective customers (individuals or organizations) before they are converted.

**Key Fields:**
- `naming_series`: `CRM-LEAD-.YYYY.-`
- `lead_name`, `first_name`, `middle_name`, `last_name`, `company_name`
- `status`: Lead / Open / Replied / Opportunity / Quotation / Lost Quotation / Interested / Converted / Do Not Contact
- `lead_owner`: User link (defaults to `__user`)
- `email_id`, `mobile_no`, `phone`, `whatsapp_no`
- `type`: Client / Channel Partner / Consultant
- `market_segment`, `industry` (links to Market Segment, Industry Type)
- `territory`, `annual_revenue`, `no_of_employees`
- `qualification_status`: Unqualified / In Process / Qualified
- `qualified_by`, `qualified_on`
- `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`
- `unsubscribed`, `disabled`, `blog_subscriber`
- Address: `city`, `state`, `country` (no dedicated Address link — uses inline fields)
- `customer`: link to Customer (for converted leads)
- Tabs: Contact Info, Qualification, Additional Information, Activities, Notes, Connections

**State Machine:** Lead → Open/Replied → Opportunity/Quotation → Converted (or Lost/Do Not Contact)

**Permissions:** Sales User (CRUD), Sales Manager (CRUD + import/export), System Manager

**Integrations:** Timeline events, email capture, opportunity creation, customer conversion.

---

### Opportunity

**Entities Managed:** Potential sales deals, keyed off a Lead or Customer.

**Key Fields:**
- `naming_series`: `CRM-OPP-.YYYY.-`
- `opportunity_from`: Dynamic Link to any DocType (Lead, Customer, Prospect, etc.)
- `party_name`: Dynamic Link (driven by `opportunity_from`)
- `status`: Open / Quotation / Converted / Lost / Replied / Closed
- `opportunity_type`: Link to Opportunity Type
- `sales_stage`: Link to Sales Stage (default: Prospecting)
- `probability`: Percent (default 100%)
- `expected_closing`: Date
- `currency`, `conversion_rate`, `opportunity_amount`
- `items`: Table (Opportunity Item) — products/services of interest
- `first_response_time`: Duration (read only, tracked)
- `lost_reasons`, `order_lost_reason`, `competitors`
- UTM fields, company, transaction date
- Contact info: `contact_person`, `contact_email`, `contact_mobile`, `address_html`
- Tabs: Items, Contacts, More Information, Activities, Comments, Connections

**State Machine:** Open → Quotation/Converted/Lost/Replied/Closed

**Permissions:** Sales User (CRUD), Sales Manager (CRUD + import/export)

**Integrations:** Links to Lead/Customer, drives Quotation creation, opportunity amount feeds forecasting.

---

### Prospect

**Entities Managed:** A group of leads/opportunities tracked together for a sales campaign.

**Doctypes:** Prospect, Prospect Lead, Prospect Opportunity, Prospect Account (links to CRM deals).

---

### Contract

**Entities Managed:** Legal agreements with customers or suppliers.

**Key Fields:** Contract Template, Fulfilment Checklist (contract_fulfilment_checklist), start/end dates, parties.

---

## 2. Selling Module

### Quotation

**Entities Managed:** Offers to customers (or suspects/prospects) with pricing, validity, and terms.

**Key Fields:**
- `naming_series`: `SAL-QTN-.YYYY.-`
- `quotation_to`: Link to DocType (Customer, Lead, Shareholder, etc.)
- `party_name`: Dynamic Link driven by `quotation_to`
- `order_type`: Sales / Maintenance / Shopping Cart
- `transaction_date`, `valid_till`
- `selling_price_list`, `currency`, `conversion_rate`
- `items`: Table (Quotation Item) — with qty, rate, discount, warehouse
- `taxes_and_charges`, `taxes` Table (Sales Taxes and Charges)
- `tax_category`, `shipping_rule`, `incoterm`
- `grand_total`, `rounded_total`, `in_words`
- `additional_discount_percentage`, `discount_amount`, `coupon_code`
- `payment_terms_template`, `payment_schedule`
- `letter_head`, `select_print_heading`, `language`
- `opportunity` link (source opportunity)
- `supplier_quotation` (for comparing supplier quotes)
- `competitors`, `lost_reasons`, `order_lost_reason`
- `auto_repeat` for recurring quotations
- Status: Draft / Open / Replied / Partially Ordered / Ordered / Lost / Cancelled / Expired
- **is_submittable**: Yes (submit → Draft)

**Permissions:** Sales User (submit/amend/cancel), Sales Manager (full), Maintenance Manager/User

**Integrations:** Converts to Sales Order; originates from Opportunity; pulls from Supplier Quotation.

---

### Sales Order

**Entities Managed:** Confirmed customer order, the primary sales fulfillment document.

**Key Fields:**
- `naming_series`: `SAL-ORD-.YYYY.-`
- `customer`, `customer_name` (fetched from Customer)
- `order_type`: Sales / Maintenance / Shopping Cart
- `transaction_date`, `delivery_date`
- `skip_delivery_note`: checkbox for maintenance orders
- `is_subcontracted`: checkbox
- `project`: Link to Project (for project costing)
- `items`: Table (Sales Order Item) — with qty, rate, warehouse, reserved stock
- `set_warehouse`, `reserve_stock` (reserves on submit)
- `per_delivered`, `per_billed`, `per_picked` (percent indicators)
- `delivery_status`: Not Delivered / Fully Delivered / Partly Delivered / Closed / Not Applicable
- `billing_status`: Not Billed / Fully Billed / Partly Billed / Closed
- `advance_payment_status`: Not Requested / Requested / Partly Paid / Fully Paid
- `sales_partner`, `commission_rate`, `total_commission`
- `sales_team`: Table (Sales Team) for team-based commissions
- `packed_items`: auto-populated from product bundles
- `auto_repeat`
- `po_no`, `po_date` (customer's PO reference)
- `is_internal_customer`, `inter_company_order_reference` (for inter-company SO/PO)
- Status: Draft / On Hold / To Pay / To Deliver and Bill / To Bill / To Deliver / Completed / Cancelled / Closed
- **is_submittable**: Yes

**Permissions:** Sales User (submit), Sales Manager (full), Maintenance User; Stock User (read); Accounts User (read)

**Integrations:**
- Creates Delivery Note (and auto-links)
- Creates Sales Invoice (and auto-links)
- Advances against Payment Entry
- Updates Project cost
- Reserves stock on submit
- Inter-company: links to Purchase Order via `inter_company_order_reference`

---

### Customer

**Entities Managed:** The end-customer (organization or individual).

**Key Fields:**
- `naming_series`: `CUST-.YYYY.-`
- `customer_name`, `customer_group`, `territory`
- `default_currency`, `default_price_list`
- `payment_terms` (link to Payment Terms Template)
- `credit_limit`, `blocked`, `沸腾`
- `loyalty_program`, `market_segment`, `industry`
- `customer_primary_address`, `customer_primary_contact`
- `accounts` (Table: Party Account — per-company accounts)
- `default_receivable_account`, `default_payable_account`
- Tabs: Address & Contact, Accounting, Settings, CRM, Portal Users, Connections

---

## 3. Buying Module

### Supplier

**Entities Managed:** Vendors of goods and services.

**Key Fields:**
- `naming_series`: `SUP-.YYYY.-`
- `supplier_name`, `supplier_type`: Company / Individual / Partnership
- `supplier_group` (link with `link_filters` for non-group)
- `country`, `website`
- `default_currency`, `default_price_list`, `payment_terms`
- `default_bank_account`, `accounts` (Table: Party Account)
- `is_internal_supplier`, `represents_company`
- `is_transporter`
- `tax_id`, `tax_category`, `tax_withholding_category`, `tax_withholding_group`
- `on_hold`, `hold_type`, `release_date`
- `is_frozen` (blocks all transactions)
- `disabled`
- `warn_rfqs`, `prevent_rfqs`, `warn_pos`, `prevent_pos` (RFQ/PO blocking controls)
- `allow_purchase_invoice_creation_without_purchase_order`
- `allow_purchase_invoice_creation_without_purchase_receipt`
- `supplier_primary_address`, `supplier_primary_contact`
- `customer_numbers` Table (Customer Number At Supplier)
- Tabs: Address & Contact, Tax, Accounting, Settings, Portal Users, Connections

**Integrations:** RFQ, Purchase Order, Purchase Receipt, Purchase Invoice.

---

### Request for Quotation (RFQ)

**Entities Managed:** A solicitation sent to multiple suppliers to get quotes.

**Key Fields:**
- `naming_series`: `PUR-RFQ-.YYYY.-`
- `company`, `transaction_date`
- `suppliers` Table (Request for Quotation Supplier) — with `supplier`, `email`, `send_email` flag
- `items` Table (Request for Quotation Item) — item, qty, uom, desired date
- `supplier_response_section`: email template, message, send options
- `incoterm`, `tc_name`, `terms`
- `opportunity` link
- `status`: Draft / Sent / Received / Cancelled
- Address/billing/shipping

**Workflow:** Draft → Send (emails suppliers) → Receive supplier responses → Compare → Create Supplier Quotation

---

### Supplier Quotation

**Entities Managed:** A supplier's pricing offer in response to an RFQ or direct request.

**Key Fields:**
- `naming_series`: `SQ-.YYYY.-`
- `supplier`, `transaction_date`, `valid_till`
- `items` Table (Supplier Quotation Item)
- `currency`, `buying_price_list`
- `taxes`, `totals`
- `supplier_address`, `contact_person`
- `is_submittable**: Yes

---

### Purchase Order

**Entities Managed:** Formal buyer-issued order to a supplier for goods/services.

**Key Fields:**
- `naming_series`: `PUR-ORD-.YYYY.-`
- `supplier`, `supplier_name`
- `order_confirmation_no`, `order_confirmation_date`
- `transaction_date`, `schedule_date` (Required By)
- `is_subcontracted`, `supplier_warehouse` (for subcontracting)
- `company`
- `currency`, `conversion_rate`, `buying_price_list`, `price_list_currency`
- `items` Table (Purchase Order Item) — with qty, rate, uom, warehouse, `bom_no`, received qty
- `set_warehouse`, `set_from_warehouse` (for internal transfers)
- `supplied_items`: raw materials for subcontracting (Table: Purchase Order Item Supplied)
- `per_received`, `per_billed` (percent)
- `advance_paid`
- `drop_ship` section: `customer`, `customer_name`, customer contact
- `project`, `cost_center`, `accounting_dimensions`
- `inter_company_order_reference`: links to Sales Order
- `mps`: Master Production Schedule link
- `is_internal_supplier`, `represents_company`
- `amended_from`
- Status: Draft / On Hold / To Receive and Bill / To Bill / To Receive / Completed / Cancelled / Closed / Delivered
- **is_submittable**: Yes

**Permissions:** Purchase Manager (full), Purchase User (full), Stock User (read only)

**Integrations:**
- Originates from Supplier Quotation
- Creates Purchase Receipt (receives goods)
- Creates Purchase Invoice (bills)
- Subcontracting: transfers raw materials to supplier warehouse
- Inter-company: linked to Sales Order via `inter_company_order_reference`

---

## 4. Stock / Inventory Module

### Item

**Entities Managed:** Products or services that are bought, sold, or kept in stock.

**Key Fields:**
- `autoname`: `field:item_code` (item code is user-defined, not auto-generated)
- `item_code` (unique), `item_name`, `item_group`
- `stock_uom` (default unit of measure)
- `disabled`
- `is_stock_item`, `is_fixed_asset`, `is_grouped_asset`
- `has_variants`, `variant_of`, `variant_based_on`, `attributes`
- `asset_category`, `asset_naming_series`
- `valuation_method`: FIFO / Moving Average / Standard
- `valuation_rate`, `standard_rate`, `opening_stock`
- `allow_negative_stock`
- `has_batch_no`, `create_new_batch`, `batch_number_series`, `has_expiry_date`, `shelf_life_in_days`, `retain_sample`, `sample_quantity`
- `has_serial_no`, `serial_no_series`
- `end_of_life`, `warranty_period`
- `is_purchase_item`, `purchase_uom`, `lead_time_days`, `last_purchase_rate`, `safety_stock`, `min_order_qty`
- `is_sales_item`, `sales_uom`, `max_discount`, `grant_commission`
- `is_sub_contracted_item`, `default_bom`, `production_capacity`
- `include_item_in_manufacturing`
- `inspection_required_before_purchase`, `inspection_required_before_delivery`
- `taxes`: Table (Item Tax) — per tax category
- `item_defaults` Table: per-company defaults (warehouse, price list, tax account, etc.)
- `uoms` Table (UOM Conversion Detail)
- `barcodes` Table
- `reorder_levels` Table (Item Reorder) — by warehouse/sales partner
- `website_specifications`, `item_customer_detail`, `item_supplier`
- `enable_deferred_expense`, `enable_deferred_revenue`
- **Document Type**: Setup (not submittable)

**Integrations:** Used in Quotation, SO, PO, DN, SI, Stock Entry, BOM, Work Order, Project.

---

### Delivery Note

**Entities Managed:** Document confirming shipment/delivery of goods to customer.

**Key Fields:**
- `naming_series`: `MAT-DN-.YYYY.-`
- `customer`, `customer_name`, `tax_id`
- `posting_date`, `posting_time`, `set_posting_time`
- `is_return`, `return_against`
- `update_stock` (for POS scenarios)
- `set_warehouse`, `set_target_warehouse`
- `items` Table (Delivery Note Item) — with qty, rate, warehouse, `bom_no`, `si_no`, `dn_revised_qty`, `against_sales_order`, `against_sales_invoice`
- `per_installed`, `installation_status`
- `per_billed` (percent), `per_returned`
- `transporter`, `lr_no`, `lr_date`, `vehicle_no`, `driver`, `driver_name`
- `delivery_trip` link
- `po_no`, `po_date` (customer's PO reference)
- `sales_team`: Table
- `packing_slip` link
- Status: Draft / Submitted / Returned / Cancelled
- **is_submittable**: Yes

**Integrations:** Created from Sales Order (or directly); creates Sales Invoice; updates stock (decrement from warehouse); linked to Installation Note.

---

### Stock Entry

**Entities Managed:** General stock movements (receipt, issue, transfer, manufacture).

**Key Fields:**
- `naming_series`: `STE-.YYYY.-`
- `stock_entry_type`: Material Receipt / Material Issue / Material Transfer / Material Transfer for Manufacture / Manufacture / Repack / Send to Subcontractor
- `add_to_transit`
- `items` Table (Stock Entry Detail): `s_warehouse`, `t_warehouse`, item, qty, uom, `stock_uom`, rate, `basic_amount`, `transfer_qty`, `seq`
- `purchase_receipt`, `delivery_note`, `sales_invoice`, `purchase_invoice` (source documents)
- `from_bom`, `bom_no`
- `fg_warehouse`, `wip_warehouse`, `scrap_warehouse`
- `operating_cost`, `additional_operating_cost`, `total_amount`
- `total_outgoing_value`, `total_incoming_value`
- `difference_account`
- **is_submittable**: Yes

**Integrations:** Stock ledger updates, work order consumption/creation, quality inspection.

---

### Warehouse

**Entities Managed:** Storage locations.

**Key Fields:** `warehouse_name`, `warehouse_type`, `address`, `is_group`, `parent_warehouse`, `company`, `default_incoming_outgoing_rate`.

---

### Purchase Receipt

**Entities Managed:** Record of goods received from a supplier.

**Key Fields:** Similar to Delivery Note but for inbound. `supplier`, `posting_date`, `items` with `po_detail` (link to PO Item), `bom_no`, `warehouse`, `qty`, `rejected_qty`, `uom`, `rate`, `taxes`, `grand_total`.

**Status:** Draft / Submitted / Returned / Cancelled. **is_submittable**: Yes.

---

## 5. Accounts Module

### Sales Invoice

**Entities Managed:** Customer invoice (revenue recognition document).

**Key Fields:**
- `naming_series`: `ACC-SINV-.YYYY.-`
- `customer`, `customer_name`, `tax_id`
- `posting_date`, `posting_time`, `due_date`
- `is_pos`, `pos_profile`
- `is_return`, `return_against`
- `update_stock` (for POS)
- `is_consolidated`, `is_debit_note`, `is_created_using_pos`
- `items` Table (Sales Invoice Item): `item_code`, `qty`, `rate`, `income_account`, `cost_center`, `warehouse`, `batch_no`, `serial_no`, `sales_order`/`delivery_note` links, `bom_no`
- `update_billed_amount_in_sales_order`, `update_billed_amount_in_delivery_note`
- `per_billed` (100% on submit)
- `total_qty`, `net_total`, `grand_total`, `rounded_total`
- `taxes_and_charges`, `taxes` Table (Sales Taxes and Charges)
- `total_advance`, `outstanding_amount`
- `payment_terms_template`, `payment_schedule`
- `allocate_advances_automatically`, `advances` Table
- `write_off_amount`, `base_write_off_amount`
- `cash_bank_account`, `payments` (for POS)
- `timesheets` (for billing hours to customers)
- `total_billing_hours`, `total_billing_amount`
- `tax_withholding_entries`, `tax_withholding_category`
- `amended_from`
- Status: Draft / Submitted / Returned / Cancelled / Closed
- **is_submittable**: Yes

**Permissions:** Accounts User (read/email/print), Accounts Manager (full)

**Integrations:**
- Creates GL Entry on submit (debits receivable, credits revenue)
- Updates Sales Order `% billed`
- Updates Delivery Note `% billed`
- Creates Payment Entry for advances
- Auto-allocates advances/repayments
- Deferred revenue recognition

---

### Purchase Invoice

**Entities Managed:** Supplier invoice (payables document).

**Key Fields:** Similar to Sales Invoice but for suppliers. `supplier`, `is_return`, `bill_no`, `bill_date`, `items` with `purchase_order`/`purchase_receipt` links, `tax_withholding_category`.

**Status:** Draft / Submitted / Returned / Cancelled / Closed. **is_submittable**: Yes.

---

### Payment Entry

**Entities Managed:** Records money in/out (receipts from customers, payments to suppliers, internal transfers).

**Key Fields:**
- `payment_type`: Pay / Receive / Internal Transfer / Transfer
- `party_type`: Customer / Supplier / Shareholder / Employee
- `party`
- `paid_from`, `paid_to` (account links)
- `paid_amount`, `received_amount`
- `reference_no`, `reference_date` (for bank references)
- `allocate_advances_automatically`
- `deductions` Table (Payment Entry Deduction)
- `references` Table (Payment Entry Reference) — links to Sales/Purchase Invoices

**is_submittable**: Yes

---

### Journal Entry

**Entities Managed:** Manual GL entries for adjustments, opening balances, corrections.

**Key Fields:** `voucher_type` (Journal Entry, Bank Entry, Cash Entry, etc.), `accounts` Table (Journal Entry Account) with `account`, `debit_in_account_currency`, `credit_in_account_currency`, `party_type`, `party`, `cost_center`, `project`.

**is_submittable**: Yes

---

### General Ledger / GL Entry

Individual ledger entries created by all accounting transactions. Key fields: `account`, `posting_date`, `accounting_dimension` (Cost Center/Project/etc.), `debit`, `credit`, `account_currency`, `party_type`, `party`, `voucher_type`, `voucher_no`, `company`.

---

## 6. Projects Module

### Project

**Entities Managed:** Customer-facing or internal projects with tasks, costing, and time tracking.

**Key Fields:**
- `naming_series`: `PROJ-.YYYY.-`
- `project_name` (unique)
- `status`: Open / Completed / Cancelled
- `project_type`: Link to Project Type
- `is_active`: Yes / No
- `percent_complete_method`: Manual / Task Completion / Task Progress / Task Weight
- `percent_complete` (auto or manual)
- `customer`, `sales_order`
- `expected_start_date`, `expected_end_date`, `actual_start_date`, `actual_end_date`, `actual_time`
- `estimated_costing`: estimated cost breakdown
- `total_costing_amount`, `total_purchase_cost`, `total_sales_amount`, `total_billable_amount`, `total_billed_amount`, `total_consumed_material_cost`
- `cost_center`, `gross_margin`, `per_gross_margin`
- `department`
- `holiday_list`, `collect_progress` (for auto timesheet)
- `frequency`, `from_time`, `to_time`, `daily_time_to_send`, `day_to_send` (email notifications)
- `users`: Table (Project User) — team members
- `sales_order` link
- **Document Type**: Setup

**Integrations:** Linked to Sales Order, Purchase Orders (for project materials), Timesheets, Tasks, Cost Center.

---

### Task

**Entities Managed:** Work items within a project.

**Key Fields:**
- `subject`, `project`
- `status`: Open / Working / Pending Review / Completed / Cancelled
- `priority`: Low / Medium / High / Urgent
- `task_weight` (for project % completion)
- `depends_on`: Table (Task Depends On) — task dependencies
- `description`, `color`
- `task_type`
- `expected_time`, `total_costing_amount`, `total_billable_amount`
- `hourly_rate`
- `progress` (percent)
- `notes`, `comment`
- **Document Type**: Setup

---

### Timesheet

**Entities Managed:** Time logged by employees against projects/tasks.

**Key Fields:**
- `employee`, `company`
- `employee_name`, `department`
- `salary_slip` link
- `timesheet_details` Table: `activity_type`, `project`, `task`, `billing_hours`, `billing_amount`, `costing_hours`, `costing_rate`, `operating_cost`

**is_submittable**: Yes

---

## 7. Manufacturing Module

### Work Order

**Entities Managed:** Production order to manufacture finished goods from raw materials.

**Key Fields:**
- `naming_series`: `MFG-WO-.YYYY.-`
- `production_item` (Item to Manufacture), `bom_no`, `qty`
- `sales_order`, `sales_order_item`
- `material_transferred_for_manufacturing`, `produced_qty`, `process_loss_qty`
- `source_warehouse`, `wip_warehouse`, `fg_warehouse`, `scrap_warehouse`
- `transfer_material_against`: Job Card / Material Transfer
- `operations`: Table (for job card routing)
- `required_items`: Table with `operation`, `item_code`, `qty`, `source_warehouse`
- `use_multi_level_bom`, `skip_transfer`
- `reserve_stock`, `track_semi_finished_goods`
- `planned_start_date`, `planned_end_date`, `expected_delivery_date`
- `actual_start_date`, `actual_end_date`, `lead_time`
- `planned_operating_cost`, `actual_operating_cost`, `additional_operating_cost`, `corrective_operation_cost`, `total_operating_cost`
- `project`, `production_plan`, `mps`, `material_request`, `material_request_item`
- `has_serial_no`, `has_batch_no`, `batch_size`
- Status: Draft / Submitted / Not Started / In Process / Stock Reserved / Stock Partially Reserved / Completed / Stopped / Closed / Cancelled
- **is_submittable**: Yes (but Document Type is Setup)

---

### Job Card

**Entities Managed:** Operation-level work instructions within a Work Order.

**Key Fields:** `operation`, `workstation`, `work_order`, `employee`, `time_logs` (start/end time, completed_time, operation_time), `job_status`.

**is_submittable**: Yes

---

### BOM (Bill of Materials)

**Entities Managed:** Recipe/routing for manufacturing an item.

**Key Fields:** `item` (finished good), `company`, `is_active`, `is_default`, `quantity` (of finished good produced), `bom_operations` Table, `bom_materials` Table (item, qty, rate, operation, `source_warehouse`).

**Document Type:** Setup

---

## 8. Additional Modules

### Asset Module (`erpnext/assets`)

**Doctypes:** Asset, Asset Movement, Asset Capitalization, Asset Depreciation Schedule, Asset Maintenance, Asset Repair.

**Key Fields (Asset):** `asset_name`, `asset_category`, `company`, `purchase_date`, `gross_purchase_amount`, `location`, `custodian`, `supplier`, `item_code` (linked inventory item), `serial_no`, ` depreciation_method`, `total_number_of_depreciations`, `frequency_of_depreciation`, `depreciation_start_date`, `expected_life`.

---

### Quality Management Module (`erpnext/quality_management`)

**Doctypes:** Quality Inspection, Quality Inspection Template, Quality Inspection Reading.

**Key Fields (Quality Inspection):** `inspection_type`: Incoming / In Process / Outgoing; `reference_type`, `reference_name`; `inspected_by`; `items` Table with readings (parameter, value, status, remark).

---

### Support Module (`erpnext/support`)

**Doctypes:** Issue, Service Level Agreement, Maintenance Schedule, Maintenance Visit, Warranty Claim.

**Key Fields (Issue):** `subject`, `description`, `status`: Open / Working / Closed / Cancelled; `priority`; `customer`, `contact`, `raised_by`; `resolution_date`, `resolution`, `user` (customer); `project`.

---

### Portal (`erpnext/portal`)

- **Customer Portal**: Allows customers to view Orders, Invoices, Payments, Issues.
- **Supplier Portal**: For suppliers to receive RFQs and submit quotes.
- **Patient Portal** (healthcare).

---

### EDI (`erpnext/edi`)

Electronic Data Interchange for exchanging orders/invoices with trading partners.

---

## Key Patterns Across Modules

### Document Structure
- **Naming Series**: Every transaction uses `naming_series` (e.g., `SAL-ORD-.YYYY.-`)
- **Company field**: Required on all transaction documents for multi-company
- **Accounting Dimensions**: `cost_center`, `project` on all financial documents
- **Dual currency**: Most transactions have `currency` + `conversion_rate` + base currency fields
- **Multi-tab layout**: Address & Contact, Terms, More Info, Connections tabs

### State Machines
- Transactions: **Draft → Submitted → Cancelled/Closed**
- Some have intermediate states: e.g., Sales Order has On Hold, To Deliver, To Bill, etc.
- Amendment creates new version linked via `amended_from`

### Workflow Common to All Modules
1. Create (Draft) → 2. Submit → 3. [Auto-create downstream docs] → 4. [Optional: Amend/Cancel/Close]

### Common Integration Patterns
- **Item** is central — used by Sales, Buying, Stock, Manufacturing
- **Address/Contact** are shared via Dynamic Links across CRM, Selling, Buying
- **Project** links to SO, PO, Timesheet, Asset
- **Payment Schedule** on all billing documents
- **Pricing Rules** apply across Quotation, SO, DN, SI, PO
- **Auto-repeat** on recurring transactions (Quotation, SO, PO, SI)

### Permissions Model
- **Roles**: Sales User/Manager, Purchase User/Manager, Stock User/Manager, Accounts User/Manager
- **Perm levels**: 0 (standard CRUD), 1 (read/report for sensitive fields)
- **Role-based**: only specific roles can submit/amend/cancel
