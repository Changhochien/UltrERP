# ERPnext Buying & Procurement - Comprehensive Module Analysis

**Source:** `/reference/erpnext-develop/erpnext/buying/` and related controllers

---

## 1. BuyingController (erpnext/controllers/buying_controller.py)

Base class for all buying transactions (`Purchase Order`, `Purchase Receipt`, `Purchase Invoice`).

### Key Validate Hooks
- `set_rate_for_standalone_debit_note()` — overrides rate with valuation rate for standalone debit notes
- `validate_items()` — validates item type (is_purchase_item or is_sub_contracted_item)
- `set_qty_as_per_stock_uom()` — converts qty to stock UOM, sets `received_stock_qty`
- `validate_stock_or_nonstock_items()` — auto-sets tax category to "Total" for non-stock items
- `validate_warehouse()` — warehouse required for stock items
- `validate_from_warehouse()` — from_warehouse cannot equal warehouse; cannot use supplier warehouse for subcontracted items
- `set_supplier_address()` — renders address displays
- `validate_asset_return()` — prevents return if submitted assets exist
- `validate_purchase_return()` — clears rejected_warehouse if return with no rejected qty
- `validate_accepted_rejected_qty()` — enforces `received_qty = qty + rejected_qty`
- `validate_for_subcontracting()` — validates BOM for subcontracted items, reserve_warehouse for supplied items
- `validate_purchase_receipt_if_update_stock()` (Purchase Invoice only)
- `update_valuation_rate()` — calculates item valuation including tax, rm_supp_cost, landed_cost_voucher_amount
- `set_incoming_rate()` — overrides rate with valuation rate for internal stock transfers
- `validate_auto_repeat_subscription_dates()`
- `create_package_for_transfer()` — creates serial/batch package for inter-warehouse transfers
- `validate_budget()` — budget validation (legacy or new BudgetValidation controller)

### Key on_submit Hooks
- `process_fixed_asset()` — auto-creates assets for fixed asset items
- `update_last_purchase_rate()` — updates Item.last_purchase_rate (if not disabled in Buying Settings)
- Updates Material Request `per_ordered` via status_updater

### Key on_cancel Hooks
- Reverses `update_last_purchase_rate()`
- `delete_linked_asset()` / `update_fixed_asset(field, delete_asset=True)` for stock-tracked assets
- Calls parent `on_cancel()`

### Stock Ledger (update_stock_ledger)
- For each stock item: creates SLE with `actual_qty`, `incoming_rate = valuation_rate`
- For `from_warehouse`: creates outbound SLE before inbound
- For rejected qty: creates separate SLE into `rejected_warehouse`
- `make_sl_entries_for_supplier_warehouse()` for old subcontracting flow

### GL Entries (set_gl_entry_for_purchase_expense)
- Debits `purchase_expense_account` and credits `purchase_expense_contra_account` for stock items
- Uses `item.valuation_rate * item.stock_qty` as amount

---

## 2. Supplier (erpnext/buying/doctype/supplier/supplier.py + supplier.json)

### Fields
| Field | Type | Label | Options/Notes |
|---|---|---|---|
| naming_series | Select | Series | `SUP-.YYYY.-` (set_only_once) |
| supplier_name | Data | Supplier Name | bold, reqd, in_global_search |
| supplier_type | Select | Supplier Type | Company / Individual / Partnership, reqd, default=Company |
| supplier_group | Link | Supplier Group | in_list_view, in_standard_filter |
| country | Link | Country | |
| is_transporter | Check | Is Transporter | default=0 |
| image | Attach Image | | hidden, no_copy, print_hide |
| default_currency | Link | Billing Currency | |
| default_bank_account | Link | Default Company Bank Account | |
| default_price_list | Link | Price List | |
| payment_terms | Link | Default Payment Terms Template | |
| language | Link | Print Language | |
| website | Data | Website | |
| supplier_details | Text | Supplier Details | |
| disabled | Check | Disabled | default=0 |
| is_frozen | Check | Is Frozen | default=0 |
| on_hold | Check | Block Supplier | default=0 |
| hold_type | Select | Hold Type | All / Invoices / Payments (depends on on_hold) |
| release_date | Date | Release Date | depends on on_hold |
| tax_id | Data | Tax ID | |
| tax_category | Link | Tax Category | |
| tax_withholding_category | Link | Tax Withholding Category | |
| tax_withholding_group | Link | Tax Withholding Group | |
| accounts | Table | Accounts | options=Party Account |
| is_internal_supplier | Check | Is Internal Supplier | default=0 |
| represents_company | Link | Represents Company | depends on is_internal_supplier |
| companies | Table | Allowed To Transact With | options=Allowed To Transact With |
| allow_purchase_invoice_creation_without_purchase_order | Check | | |
| allow_purchase_invoice_creation_without_purchase_receipt | Check | | |
| warn_rfqs | Check | Warn RFQs | read_only, hidden |
| prevent_rfqs | Check | Prevent RFQs | read_only, hidden |
| warn_pos | Check | Warn POs | read_only, hidden |
| prevent_pos | Check | Prevent POs | read_only, hidden |
| mobile_no | Read Only | Mobile No | |
| email_id | Read Only | Email Id | |
| supplier_primary_address | Link | Primary Address | |
| primary_address | Text Editor | Primary Address | read_only |
| supplier_primary_contact | Link | Supplier Primary Contact | |
| portal_users | Table | Supplier Portal Users | options=Portal User |
| customer_numbers | Table | Customer Numbers | options=Customer Number At Supplier |

### Permissions
| Role | Permissions |
|---|---|
| Purchase User | read, report, print, email |
| Purchase Manager | read, report, print, email, write |
| Purchase Master Manager | create, delete, read, report, print, email, export, import, share, write |
| Stock User | read |
| Stock Manager | read, report, print, email |
| Accounts User | read |
| Accounts Manager | read, report, print, email |

### State Machine
- `Disabled` (flag on record) — blocks all transactions
- `On Hold` with `hold_type` (All/Invoices/Payments) and optional `release_date`
- `warn_rfqs / warn_pos` — shows warning but allows action
- `prevent_rfqs / prevent_pos` — blocks action based on Supplier Scorecard standing

### Key Methods
- `autoname()` — uses `supp_master_name` global default (Supplier Name, Naming Series, or Auto Name)
- `validate_internal_supplier()` — only one internal supplier per represents_company
- `get_supplier_group_details()` — copies accounts and payment terms from Supplier Group
- `create_primary_contact()` / `create_primary_address()` — auto-creates contact/address on insert
- `load_dashboard_info()` — calls `get_dashboard_info("Supplier", self.name)`

### Dashboard Links
- Procurement: Request for Quotation, Supplier Quotation
- Orders: Purchase Order, Purchase Receipt, Purchase Invoice
- Payments: Payment Entry, Bank Account
- Pricing: Pricing Rule

---

## 3. Supplier Scorecard (erpnext/buying/doctype/supplier_scorecard/)

### Fields
| Field | Type | Label |
|---|---|---|
| supplier | Link (unique) | Supplier |
| period | Select | Evaluation Period (Per Week/Per Month/Per Year), reqd, default=Per Month |
| weighting_function | SmallText | Score formula (e.g., `{total_score} * max(0, min(1, (12 - {period_number}) / 12))`) |
| standings | Table | Scoring Standings (options=Supplier Scorecard Scoring Standing) |
| criteria | Table | Scoring Criteria (options=Supplier Scorecard Scoring Criteria) |
| supplier_score | Data (read_only) | Calculated score |
| status | Data (hidden) | Current standing name |
| indicator_color | Data (hidden) | Standing color |
| warn_rfqs / warn_pos / prevent_rfqs / prevent_pos | Check (read_only) | Actions |
| notify_supplier / notify_employee | Check | Notifications |
| employee | Link | Employee to notify |

### Default Standings
| Standing | Score Range | Color | Prevent RFQs | Prevent POs |
|---|---|---|---|---|
| Very Poor | 0-30 | Red | Yes | Yes |
| Poor | 30-50 | Yellow | Warn | Warn |
| Average | 50-80 | Green | No | No |
| Excellent | 80-100 | Blue | No | No |

### Scoring Variables (default)
- `total_accepted_items`, `total_accepted_amount`, `total_rejected_items`, `total_rejected_amount`
- `total_received_items`, `total_received_amount`
- `rfq_response_days`, `sq_total_items`, `sq_total_number`, `rfq_total_number`, `rfq_total_items`
- `tot_item_days`, `on_time_shipment_num`, `cost_of_delayed_shipments`, `cost_of_on_time_shipments`
- `total_working_days`, `tot_cost_shipments`, `tot_days_late`, `total_shipments`
- `total_ordered`, `total_invoiced`

### Workflow
- On `SupplierScorecard` save: `make_all_scorecards()` creates `SupplierScorecardPeriod` records for each period since supplier creation
- `SupplierScorecardPeriod` is submitted and calculates period score
- Weighted total score is computed using `weighting_function`
- Standing is resolved and supplier's `warn_rfqs / prevent_rfqs / warn_pos / prevent_pos` fields are updated

---

## 4. Request for Quotation (erpnext/buying/doctype/request_for_quotation/)

### Fields
| Field | Type | Label | Notes |
|---|---|---|---|
| naming_series | Select | Series | `PUR-RFQ-.YYYY.-`, reqd |
| company | Link | Company | reqd |
| vendor | Link | Supplier | hidden, in_list_view, in_standard_filter |
| transaction_date | Date | Date | reqd, default=Today |
| schedule_date | Date | Schedule Date | |
| status | Literal | Status | "", Draft, Submitted, Cancelled |
| has_unit_price_items | Check | | hidden |
| amended_from | Link | Amended From | |
| suppliers | Table | Suppliers | options=Request for Quotation Supplier, reqd |
| items | Table | Items | options=Request for Quotation Item, reqd |
| email_template | Link | Email Template | |
| subject | Data | Subject | |
| message_for_supplier | TextEditor | Message for Supplier | mandatory when use_html=0 |
| mfs_html | Code | HTML Message | |
| use_html | Check | Use HTML | |
| send_attached_files | Check | Send Attached Files | |
| send_document_print | Check | Send Document Print | |
| incoterm | Link | Incoterm | |
| named_place | Data | Named Place | |
| tc_name | Link | Terms | |
| terms | TextEditor | Terms and Conditions | |
| letter_head | Link | Letter Head | |
| select_print_heading | Link | Print Heading | |
| opportunity | Link | Opportunity | |
| billing_address | Link | Billing Address | |
| shipping_address | Link | Shipping Address | |

### Request for Quotation Supplier Child Table
| Field | Type |
|---|---|
| supplier | Link, reqd |
| supplier_name | Read Only |
| contact | Link |
| email_id | Data |
| send_email | Check, default=1 |
| quote_status | Literal[Pending/Received] |
| email_sent | Check |

### Request for Quotation Item Child Table
| Field | Type |
|---|---|---|
| item_code | Link, reqd |
| item_name | Data |
| description | TextEditor |
| qty | Float, reqd |
| stock_qty | Float |
| uom | Link |
| stock_uom | Link |
| conversion_factor | Float |
| schedule_date | Date |
| warehouse | Link |
| brand | Link |
| item_group | Link |
| image | Attach |
| material_request | Link |
| material_request_item | Data |
| project_name | Link |
| supplier_part_no | Data |
| page_break | Check |

### Status Transitions
- `Draft` → `Submitted` (on_submit: sends emails to suppliers, sets all quote_status=Pending)
- `Submitted` → `Cancelled` (on_cancel)
- Per-supplier `quote_status` updated to "Received" when Supplier Quotation is submitted

### Key Methods
- `send_to_supplier()` — sends RFQ email via supplier portal, creates User accounts for new suppliers
- `get_supplier_email_preview()` — renders email preview
- `update_rfq_supplier_status()` — marks quote_status as Received/Pending based on linked Supplier Quotations
- `make_supplier_quotation_from_rfq()` — maps RFQ to Supplier Quotation
- `get_item_from_material_requests_based_on_supplier()` — creates RFQ from Material Requests where item's default supplier matches

### Integrations
- Supplier Quotation (via make_supplier_quotation_from_rfq or supplier portal)
- Material Request (items linked)
- Opportunity

### Reports
- Procurement Tracker
- Purchase Analytics
- Supplier Quotation Comparison

---

## 5. Supplier Quotation (erpnext/buying/doctype/supplier_quotation/)

### Fields
| Field | Type | Label | Notes |
|---|---|---|---|
| naming_series | Select | Series | `PUR-SQTN-.YYYY.-`, reqd |
| supplier | Link | Supplier | reqd, in_standard_filter |
| supplier_name | Data | Supplier Name | read_only, fetch from supplier |
| company | Link | Company | reqd |
| status | Literal | Status | Draft/Submitted/Stopped/Cancelled/Expired |
| transaction_date | Date | Date | reqd, default=Today, in_list_view |
| valid_till | Date | Valid Till | |
| quotation_number | Data | Quotation Number | |
| has_unit_price_items | Check | | hidden |
| amended_from | Link | Amended From | |
| items | Table | Items | options=Supplier Quotation Item |
| taxes | Table | Purchase Taxes and Charges | |
| taxes_and_charges | Link | Purchase Taxes and Charges Template | |
| shipping_rule | Link | Shipping Rule | |
| incoterm | Link | Incoterm | |
| named_place | Data | Named Place | |
| billing_address | Link | Billing Address | |
| shipping_address | Link | Shipping Address | |
| contact_person | Link | Contact | |
| tc_name | Link | Terms | |
| terms | TextEditor | Terms and Conditions | |
| apply_discount_on | Literal | Apply Discount On | "", Grand Total, Net Total |
| additional_discount_percentage | Float | Additional Discount % | |
| discount_amount | Currency | Discount Amount | |
| grand_total | Currency | Grand Total | |
| in_words | Data | In Words | |
| rounded_total | Currency | Rounded Total | |
| disable_rounded_total | Check | Disable Rounded Total | |
| letter_head | Link | Letter Head | |
| group_same_items | Check | Group Same Items | |
| language | Data | Print Language | |
| auto_repeat | Link | Auto Repeat | |
| opportunity | Link | Opportunity | |
| is_subcontracted | Check | Is Subcontracted | |
| project | Link | Project | |

### Supplier Quotation Item Child Table Fields
All standard item pricing fields plus:
- `request_for_quotation` (Link), `request_for_quotation_item` (Data) — RFQ linkage
- `material_request` (Link), `material_request_item` (Data)
- `sales_order` (Link)
- `prevdoc_doctype` (Data), `prevdoc_docname` (Link)
- `lead_time_days` (Int)
- `expected_delivery_date` (Date)
- `supplier_part_no` (Data)
- `manufacturer` (Link), `manufacturer_part_no` (Data)
- `is_free_item` (Check)
- `item_tax_rate` (Code — JSON), `item_tax_template` (Link)

### Status Transitions
- `Draft` → `Submitted` (on_submit: updates RFQ supplier quote_status=Received)
- `Submitted` → `Stopped` / `Cancelled`
- Auto-expiry via `set_expired_status()` scheduler job: sets status=Expired when valid_till < today

### Make Methods
- `make_purchase_order()` — maps to Purchase Order, copies items and taxes
- `make_purchase_invoice()` — maps to Purchase Invoice
- `make_quotation()` — maps to Quotation (Selling)

### Supplier Quotation Comparison Report
- Compares quotations by supplier or by item
- Filters: company, date range, item_code, supplier, request_for_quotation, include_expired
- Columns: supplier, item, uom, qty, stock_uom, currency, price, price_per_unit, base_amount, base_rate, quotation link, valid_till, lead_time_days, rfq
- Highlights minimum price per unit

---

## 6. Purchase Order (erpnext/buying/doctype/purchase_order/)

### Fields
| Field | Type | Label | Notes |
|---|---|---|---|
| naming_series | Select | Series | `PUR-ORD-.YYYY.-`, reqd |
| supplier | Link | Supplier | reqd, in_global_search |
| supplier_name | Data | | fetch from supplier |
| order_confirmation_no | Data | Order Confirmation No | allow_on_submit |
| order_confirmation_date | Date | Order Confirmation Date | allow_on_submit |
| transaction_date | Date | Transaction Date | reqd |
| schedule_date | Date | Schedule Date | |
| is_subcontracted | Check | Is Subcontracted | |
| has_unit_price_items | Check | | hidden |
| supplier_warehouse | Link | Supplier Warehouse | for subcontract |
| title | Data | Title | print_hide |
| cost_center | Link | Cost Center | |
| project | Link | Project | |
| currency | Link | Currency | reqd |
| conversion_rate | Float | Conversion Rate | |
| buying_price_list | Link | Buying Price List | |
| price_list_currency | Link | Price List Currency | |
| plc_conversion_rate | Float | Price List Conv. Rate | |
| ignore_pricing_rule | Check | Ignore Pricing Rule | |
| scan_barcode | Data | Scan Barcode | |
| set_from_warehouse | Link | From Warehouse | |
| set_warehouse | Link | Set Warehouse | |
| items | Table | Items | options=Purchase Order Item |
| supplied_items | Table | Raw Materials Supplied | options=Purchase Order Item Supplied |
| set_reserve_warehouse | Link | Reserve Warehouse | |
| taxes | Table | Purchase Taxes and Charges | |
| taxes_and_charges | Link | Purchase Taxes and Charges Template | |
| shipping_rule | Link | Shipping Rule | |
| incoterm | Link | Incoterm | |
| named_place | Data | Named Place | |
| grand_total | Currency | Grand Total | |
| in_words | Data | In Words | |
| disable_rounded_total | Check | | |
| advance_paid | Currency | Advance Paid | |
| apply_discount_on | Literal | | "", Grand Total, Net Total |
| additional_discount_percentage | Float | | |
| discount_amount | Currency | | |
| other_charges_calculation | TextEditor | Tax Breakdown | |
| supplier_address | Link | Supplier Address | |
| address_display | TextEditor | | read_only |
| contact_person | Link | Contact | |
| shipping_address | Link | Shipping Address | |
| dispatch_address | Link | Dispatch Address | |
| billing_address | Link | Billing Address | |
| payment_terms_template | Link | Payment Terms Template | |
| payment_schedule | Table | Payment Schedule | |
| tc_name | Link | Terms | |
| terms | TextEditor | Terms | |
| status | Literal | Status | (set via set_status()) |
| advance_payment_status | Literal | | Not Initiated/Initiated/Partially Paid/Fully Paid |
| per_billed | Percent | Per Billed | |
| per_received | Percent | Per Received | |
| letter_head | Link | Letter Head | |
| group_same_items | Check | | |
| auto_repeat | Link | Auto Repeat | |
| from_date / to_date | Date | Auto Repeat Period | |
| mps | Link | MPS | |
| is_internal_supplier | Check | | |
| inter_company_order_reference | Link | Inter Company Order Reference | |
| represents_company | Link | Represents Company | |
| ref_sq | Link | Reference SQ | |
| amended_from | Link | Amended From | |
| is_old_subcontracting_flow | Check | | |
| drop_ship | Section | Drop Ship | |
| customer | Link | Customer | for drop ship |
| customer_name | Data | | |

### Purchase Order Item Child Table (97 fields)
Key fields:
- `item_code`, `item_name`, `description`, `qty`, `uom`, `stock_uom`, `conversion_factor`
- `warehouse`, `from_warehouse`
- `rate`, `price_list_rate`, `base_rate`, `net_rate`, `amount`, `base_amount`, `net_amount`
- `discount_percentage`, `discount_amount`, `margin_rate_or_amount`, `margin_type`
- `received_qty`, `returned_qty`, `billed_amt`
- `fg_item`, `fg_item_qty` — for subcontracting
- `bom` — for subcontracting
- `is_fixed_asset`, `asset_location`
- `delivered_by_supplier` — for drop ship
- `sales_order`, `sales_order_item`, `sales_order_packed_item` — drop ship linkage
- `material_request`, `material_request_item`
- `production_plan`, `production_plan_item`, `production_plan_sub_assembly_item`
- `project`, `cost_center`, `expense_account`
- `blanket_order`, `blanket_order_rate`, `against_blanket_order`
- `supplier_quotation`, `supplier_quotation_item`
- `subcontracted_qty`
- `manufacturer`, `manufacturer_part_no`
- `item_tax_rate`, `item_tax_template`
- `last_purchase_rate` (read_only)
- `stock_qty`, `total_weight`
- `job_card` (for subcontracting)
- `wip_composite_asset`

### Purchase Order Item Supplied Child Table (for old subcontracting flow)
| Field | Type |
|---|---|
| rm_item_code | Link |
| stock_uom | Link |
| required_qty | Float |
| consumed_qty | Float |
| returned_qty | Float |
| supplied_qty | Float |
| total_supplied_qty | Float |
| reserve_warehouse | Link |
| bom_detail_no | Data |
| conversion_factor | Float |
| rate | Currency |
| amount | Currency |
| reference_name | Data |
| main_item_code | Link |

### Status Values
Draft, On Hold, To Receive and Bill, To Bill, To Receive, Completed, Cancelled, Closed, Delivered

Status is managed via `set_status()` which also:
- Updates `per_received` and `per_billed`
- Calls `update_ordered_qty()` on Bin
- Updates Material Request `per_ordered`
- For drop ship: updates Sales Order delivered_qty

### Key Transitions
- `close_or_unclose_purchase_orders(names, status)` — bulk close/unclose
- `update_status(status)` — single PO status change
- On Cancel: unlink inter-company docs, update ordered qty, blanket order

### Key Methods
- `validate_supplier()` — checks Supplier Scorecard standing for prevent/warn
- `validate_minimum_order_qty()` — compares against Item.min_order_qty
- `validate_fg_item_for_subcontracting()` — fg_item required for subcontract PO
- `get_last_purchase_rate()` — fetches last purchase rate and last purchase details
- `update_ordered_qty()` — updates Bin.ordered_qty for stock items
- `update_reserved_qty_for_subcontract()` — updates Bin.reserved_qty_for_sub_contracting
- `has_drop_ship_item()` — checks any item with delivered_by_supplier=1
- `is_against_so()` / `is_against_pp()` — checks for linked Sales Order / Production Plan
- `auto_create_subcontracting_order()` — on submit, if Buying Settings.auto_create_subcontracting_order
- `make_purchase_receipt()` — maps to Purchase Receipt
- `make_purchase_invoice()` / `make_purchase_invoice_from_portal()` — maps to Purchase Invoice
- `make_subcontracting_order()` — creates Subcontracting Order
- `make_inter_company_sales_order()` — for internal supplier scenario

### Integrations
- Material Request (via `material_request` / `material_request_item`)
- Supplier Quotation (via `supplier_quotation` / `supplier_quotation_item`)
- Sales Order (drop ship)
- Production Plan
- Blanket Order
- BOM (subcontracting)
- Subcontracting Order
- Subcontracting Receipt
- Stock Entry (subcontracting)

### Dashboard Links
- Related: Purchase Receipt, Purchase Invoice, Sales Order
- Payment: Payment Entry, Journal Entry, Payment Request
- Reference: Supplier Quotation, Project, Auto Repeat
- Manufacturing: Material Request, BOM, Production Plan, Blanket Order
- Sub-contracting: Subcontracting Order, Subcontracting Receipt, Stock Entry

---

## 7. Purchase Receipt & Purchase Invoice

### Purchase Receipt Fields (from BuyingController + specific)
- `purchase_order`, `purchase_order_item` linkage
- `supplier_warehouse` for subcontract
- `is_return`, `return_against`
- `rejected_warehouse`, `rejected_qty`
- `serial_and_batch_bundle`, `rejected_serial_and_batch_bundle`
- `from_warehouse` for inter-warehouse transfers
- `is_internal_transfer()`

### Purchase Invoice Fields (from BuyingController + specific)
- `purchase_order`, `po_detail` linkage
- `update_stock` check
- `is_return`, `return_against`
- `credit_to` (payable account)
- `allocate_advances_automatically`
- `payment_schedule`

### Key Differences from PO
- PR/PI update `received_qty` in Bin (not `ordered_qty`)
- Both trigger `update_last_purchase_rate()` on submit
- Both create Assets for fixed asset items
- PI with `update_stock=0` skips GL entries and stock ledger
- `set_incoming_rate()` only for PR and PI with update_stock=1

---

## 8. Purchase Taxes and Charges (erpnext/accounts/doctype/purchase_taxes_and_charges/)

### Fields
| Field | Type | Options/Notes |
|---|---|---|
| category | Literal | Valuation and Total / Valuation / Total |
| add_deduct_tax | Literal | Add / Deduct |
| charge_type | Literal | Actual / On Net Total / On Previous Row Amount / On Previous Row Total / On Item Quantity |
| account_head | Link | Account, reqd |
| description | SmallText | reqd |
| rate | Float | |
| tax_amount | Currency | |
| total | Currency | |
| net_amount | Currency | |
| net_amount | Currency | |
| tax_amount_after_discount_amount | Currency | |
| base_tax_amount | Currency | |
| base_total | Currency | |
| base_net_amount | Currency | |
| cost_center | Link | |
| row_id | Data | for charge_type=On Previous Row |
| included_in_paid_amount | Check | |
| included_in_print_rate | Check | |
| is_tax_withholding_account | Check | |
| dont_recompute_tax | Check | |
| set_by_item_tax_template | Check | |

---

## 9. Blanket Order (erpnext/manufacturing/doctype/blanket_order/)

### Fields
| Field | Type | Label | Notes |
|---|---|---|---|
| naming_series | Select | Series | `MFG-BLR-.YYYY.-` |
| blanket_order_type | Literal | Type | Selling / Purchasing |
| company | Link | Company | reqd |
| supplier | Link | Supplier | for Purchasing type |
| customer | Link | Customer | for Selling type |
| customer_name | Data | | |
| supplier_name | Data | | |
| from_date | Date | From Date | reqd |
| to_date | Date | To Date | reqd |
| items | Table | Items | options=Blanket Order Item |
| tc_name | Link | Terms | |
| terms | TextEditor | Terms | |

### Blanket Order Item Fields
| Field | Type |
|---|---|
| item_code | Link |
| item_name | Data |
| qty | Float |
| rate | Currency |
| ordered_qty | Float (db maintained) |
| party_item_code | Data |
| item_code | Link |
| description | TextEditor |
| uom | Link |

### Validation
- `from_date` cannot be after `to_date`
- No duplicate items
- Qty cannot be negative
- Party item code set from Item Supplier (for Purchasing) or Item Customer Detail (for Selling)

### Quantity Tracking
- `update_ordered_qty()` recalculates from linked Purchase/Sales Orders
- Queries `{PO/Sales Order} Item` where `blanket_order = name`, `docstatus = 1`, `status not in (Stopped, Closed)`

### Against Blanket Order
- `validate_against_blanket_order()` checks PO/SO items
- Respects `blanket_order_allowance` from Buying/Selling Settings
- Formula: `allowed_qty = remaining_qty + (remaining_qty * allowance / 100)`

---

## 10. Item Supplier (erpnext/stock/doctype/item_supplier/)

### Fields
| Field | Type |
|---|---|
| supplier | Link, reqd |
| supplier_part_no | Data |

Part of Item's `item_suppliers` child table (Table multi-select).

---

## 11. Buying Settings (erpnext/buying/doctype/buying_settings/)

### Fields
| Field | Type | Label | Default |
|---|---|---|---|
| supp_master_name | Select | Supplier Naming By | Supplier Name |
| supplier_group | Link | Default Supplier Group | |
| buying_price_list | Link | Default Buying Price List | |
| po_required | Select | PO Required for PI & PR? | No |
| pr_required | Select | PR Required for PI? | No |
| maintain_same_rate | Check | Maintain Same Rate Throughout Purchase Cycle | 0 |
| maintain_same_rate_action | Select | Action if Same Rate Not Maintained | Stop |
| role_to_override_stop_action | Link | Role Allowed to Override Stop Action | |
| blanket_order_allowance | Float | Blanket Order Allowance (%) | |
| allow_multiple_items | Check | Allow Item To Be Added Multiple Times | 0 |
| allow_zero_qty_in_purchase_order | Check | | 0 |
| allow_zero_qty_in_request_for_quotation | Check | | 0 |
| allow_zero_qty_in_supplier_quotation | Check | | 0 |
| allow_negative_rates_for_items | Check | | 0 |
| set_landed_cost_based_on_purchase_invoice_rate | Check | | 0 |
| bill_for_rejected_quantity_in_purchase_invoice | Check | Bill for Rejected Qty in PI | 1 |
| set_valuation_rate_for_rejected_materials | Check | | 0 |
| disable_last_purchase_rate | Check | | 0 |
| show_pay_button | Check | | 0 |
| backflush_raw_materials_of_subcontract_based_on | Select | Backflush Based On | BOM |
| over_transfer_allowance | Float | Over Transfer Allowance (%) | |
| validate_consumed_qty | Check | | 0 |
| auto_create_subcontracting_order | Check | | 0 |
| auto_create_purchase_receipt | Check | | 0 |
| project_update_frequency | Select | Project Update Frequency | Each Transaction |
| fixed_email | Link | Fixed Email Account | |

---

## 12. Subcontracting Flow (Summary)

Two flows exist:

### Old Subcontracting Flow (`is_old_subcontracting_flow = True`)
- PO has `supplied_items` child table (raw materials to be supplied)
- `supplier_warehouse` must be set on PO
- `create_raw_materials_supplied()` on PO submit
- `make_sl_entries_for_supplier_warehouse()` creates SLE for supplier warehouse
- `update_reserved_qty_for_subcontract()` updates Bin reserved_qty_for_sub_contracting

### New Subcontracting Flow (default)
- PO has `fg_item` + `fg_item_qty` instead of supplied_items
- `set_service_items_for_finished_goods()` auto-populates service item from BOM
- `auto_create_subcontracting_order()` on PO submit (if Buying Settings.auto_create_subcontracting_order)
- Creates `Subcontracting Order` which manages `Material Transferred for Subcontract` and `Subcontracting Receipt`

---

## 13. Key Integration Points

### With Material Request
- PO items can be linked to MR via `material_request` / `material_request_item`
- PO submit updates `per_ordered` on MR Item
- PO cancel updates `per_ordered` on MR Item
- RFQ can be created from Material Requests based on Item's default supplier

### With Stock / Inventory
- `update_ordered_qty()` updates Bin.ordered_qty on PO submit/cancel
- `update_received_qty()` pattern for PR
- PR creates Stock Ledger Entries (inward for stock items)
- Valuation rate calculated with taxes, rm_supp_cost, landed cost

### With Accounts
- GL Entry: Debit `purchase_expense_account`, Credit `purchase_expense_contra_account`
- Party Account currency validated on PO
- Payment schedule for PO
- Advance allocation for PI
- Tax categories (Valuation / Total / Valuation and Total)

### With Asset
- `auto_make_assets()` on PR/PI submit for fixed asset items
- Asset naming series from Item
- Links back: `purchase_receipt`, `purchase_receipt_item`, `purchase_invoice`, `purchase_invoice_item`
- On PI/PR cancel: deletes or unlinks assets

### With Quality Inspection
- Onload check: `allow_to_make_qc_after_submission` from Stock Settings
- Quality Inspection created separately and linked

---

## 14. Reports in Buying Module

| Report | Path | Purpose |
|---|---|---|
| Procurement Tracker | `procurement_tracker/` | Tracks procurement progress |
| Purchase Analytics | `purchase_analytics/` | Analytics by item, supplier, date |
| Supplier Quotation Comparison | `supplier_quotation_comparison/` | Compare SQ prices side-by-side |
| Subcontracted Item To Be Received | `subcontracted_item_to_be_received/` | |
| Requested Items To Order And Receive | `requested_items_to_order_and_receive/` | |
| Item-wise Purchase History | `item_wise_purchase_history/` | |
| Subcontracted Raw Materials To Be Transferred | `subcontracted_raw_materials_to_be_transferred/` | |
| Subcontract Order Summary | `subcontract_order_summary/` | |
| Purchase Order Analysis | `purchase_order_analysis/` | |
| Purchase Order Trends | `purchase_order_trends/` | |

---

## 15. Key Validation Rules

1. **Supplier Scorecard Blocking**: PO/RFQ creation blocked if supplier scorecard standing has `prevent_pos` / `prevent_rfqs`
2. **Minimum Order Qty**: PO qty must meet Item.min_order_qty
3. **Schedule Date**: Cannot be before Transaction Date; inherited from MR if linked
4. **Accepted + Rejected = Received**: enforced in `validate_accepted_rejected_qty()`
5. **Blanket Order Allowance**: PO/SO cannot exceed blanket order qty + allowance %
6. **BOM Required**: For subcontracted items (old flow), BOM must be specified
7. **FG Item Required**: For subcontracted POs (new flow), fg_item must be specified
8. **Reserve Warehouse**: Required for supplied_items in subcontract PO
9. **Supplier Warehouse**: Required for subcontract PR/PI in old flow
10. **Internal Supplier**: Only one internal supplier per company
11. **Exchange Rate**: Uses transaction date or posting date for exchange rate (configurable)
12. **Same Rate**: If Buying Settings.maintain_same_rate, rate must match Supplier Quotation

---

## 16. Document Status Summary

| Doctype | Draft | Submitted | Stopped/Hold | Cancelled | Closed | Expired |
|---|---|---|---|---|---|---|
| Supplier | N/A (active/disabled) | N/A | On Hold | N/A | N/A | N/A |
| Supplier Scorecard | Draft | Period tracked | N/A | N/A | N/A | N/A |
| Request for Quotation | Draft | Submitted | N/A | Cancelled | N/A | N/A |
| Supplier Quotation | Draft | Submitted | Stopped | Cancelled | N/A | Expired (auto) |
| Purchase Order | Draft | Submitted | On Hold | Cancelled | Closed | N/A |
| Purchase Receipt | Draft | Submitted | N/A | Cancelled | N/A | N/A |
| Purchase Invoice | Draft | Submitted | N/A | Cancelled | N/A | N/A |
| Blanket Order | Draft | N/A | N/A | Cancelled | N/A | N/A |
