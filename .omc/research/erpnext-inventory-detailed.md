# ERPnext Stock / Inventory Module - Detailed Research

Source: `reference/erpnext-develop/erpnext/stock/`

---

## 1. Item

**DocType:** Setup | **Module:** Stock | **Naming:** By fieldname (`item_code`) | **Quick Entry:** Yes

### Fields

| Field | Type | Label | Options / Notes |
|---|---|---|---|
| item_code | Data | Item Code | reqd, unique, autoname |
| item_name | Data | Item Name | bold, in_global_search |
| naming_series | Select | Series | STO-ITEM-.YYYY.-, set_only_once |
| variant_of | Link | Variant Of | Item, read_only, variant-based linking |
| item_group | Link | Item Group | reqd, in_list_view, in_standard_filter |
| stock_uom | Link | Default Unit of Measure | reqd, UOM |
| disabled | Check | Disabled | default 0 |
| is_stock_item | Check | Maintain Stock | default 1, bold |
| is_fixed_asset | Check | Is Fixed Asset | default 0 |
| asset_category | Link | Asset Category | depends_on: is_fixed_asset |
| auto_create_assets | Check | Auto Create Assets on Purchase | depends_on: is_fixed_asset |
| is_grouped_asset | Check | Create Grouped Asset | |
| opening_stock | Float | Opening Stock | bold, depends_on local+stock_item+no serial/batch |
| standard_rate | Currency | Standard Selling Rate | bold, depends_on: __islocal |
| valuation_rate | Currency | Valuation Rate | depends_on: is_stock_item |
| brand | Link | Brand | Brand |
| description | Text Editor | Description | |
| image | Attach Image | Image | hidden, print_hide |
| end_of_life | Date | End of Life | default 2099-12-31 |
| valuation_method | Select | Valuation Method | FIFO / Moving Average / LIFO |
| warranty_period | Data | Warranty Period (in days) | depends_on: is_stock_item |
| weight_per_unit | Float | Weight Per Unit | non_negative |
| weight_uom | Link | Weight UOM | UOM |
| allow_negative_stock | Check | Allow Negative Stock | |
| over_delivery_receipt_allowance | Float | Over Delivery/Receipt Allowance (%) | depends_on: !__islocal && !is_fixed_asset |
| over_billing_allowance | Float | Over Billing Allowance (%) | |
| has_variants | Check | Has Variants | default 0, in_standard_filter |
| variant_based_on | Select | Variant Based On | Item Attribute / Manufacturer |
| attributes | Table | Variant Attributes | Item Variant Attribute |
| barcodes | Table | Barcodes | Item Barcode |
| uoms | Table | UOMs | UOM Conversion Detail |
| has_batch_no | Check | Has Batch No | default 0 |
| create_new_batch | Check | Automatically Create New Batch | depends_on: has_batch_no |
| batch_number_series | Data | Batch Number Series | depends_on: has_batch_no + create_new_batch |
| has_expiry_date | Check | Has Expiry Date | default 0, depends_on: has_batch_no |
| retain_sample | Check | Retain Sample | depends_on: has_batch_no |
| sample_quantity | Int | Max Sample Quantity | depends_on: retain_sample + has_batch_no |
| shelf_life_in_days | Int | Shelf Life In Days | depends_on: has_expiry_date |
| has_serial_no | Check | Has Serial No | default 0 |
| serial_no_series | Data | Serial Number Series | depends_on: has_serial_no |
| reorder_levels | Table | Reorder level based on Warehouse | Item Reorder |
| min_order_qty | Float | Minimum Order Qty | non_negative |
| safety_stock | Float | Safety Stock | non_negative |
| lead_time_days | Int | Lead Time in days | non_negative |
| last_purchase_rate | Float | Last Purchase Rate | read_only |
| is_purchase_item | Check | Allow Purchase | default 1 |
| purchase_uom | Link | Default Purchase Unit of Measure | UOM |
| is_customer_provided_item | Check | Is Customer Provided Item | |
| customer | Link | Customer | depends_on: is_customer_provided_item |
| delivered_by_supplier | Check | Delivered by Supplier (Drop Ship) | default 0 |
| supplier_items | Table | Supplier Items | Item Supplier |
| country_of_origin | Link | Country of Origin | Country |
| customs_tariff_number | Link | Customs Tariff Number | Customs Tariff Number |
| is_sales_item | Check | Allow Sales | default 1 |
| sales_uom | Link | Default Sales Unit of Measure | UOM |
| max_discount | Float | Max Discount (%) | |
| grant_commission | Check | Grant Commission | default 1 |
| customer_items | Table | Customer Items | Item Customer Detail |
| enable_deferred_revenue | Check | Enable Deferred Revenue | |
| no_of_months | Int | No of Months (Revenue) | depends_on: enable_deferred_revenue |
| enable_deferred_expense | Check | Enable Deferred Expense | |
| no_of_months_exp | Int | No of Months (Expense) | depends_on: enable_deferred_expense |
| taxes | Table | Taxes | Item Tax |
| inspection_required_before_purchase | Check | Inspection Required before Purchase | |
| inspection_required_before_delivery | Check | Inspection Required before Delivery | |
| quality_inspection_template | Link | Quality Inspection Template | |
| default_bom | Link | Default BOM | read_only, no_copy |
| is_sub_contracted_item | Check | Is Subcontracted Item | |
| production_capacity | Int | Production Capacity | |
| total_projected_qty | Float | Total Projected Qty | hidden, read_only |
| customer_code | Small Text | Customer Code | hidden, no_copy, print_hide |
| default_material_request_type | Select | Default Material Request Type | Purchase / Transfer / Issue / Manufacture / Customer Provided |
| item_defaults | Table | Item Defaults | Item Default |
| include_item_in_manufacturing | Check | Include Item In Manufacturing | default 1 |
| default_item_manufacturer | Link | Default Item Manufacturer | read_only |
| default_manufacturer_part_no | Data | Default Manufacturer Part No | read_only |

### Child Tables (via Table fields)
- **Item Barcode** — barcode, barcode_type (EAN/UPC/GS1/GTIN/ISBN/JAN/PZN/etc.), uom
- **UOM Conversion Detail** — uom, conversion_factor
- **Item Reorder** — warehouse, warehouse_reorder_level, warehouse_reorder_qty, material_request_type, warehouse_group
- **Item Supplier** — supplier, default_supplier, lead_time_days, min_order_qty
- **Item Tax** — idx, tax_type, tax_rate
- **Item Customer Detail** — customer_name, customer_group, ref_code
- **Item Default** — company, default_warehouse, expense_account, income_account, cost_center, buying_cost_center, selling_cost_center

### Permissions
| Role | Permissions |
|---|---|
| Item Manager | CRUD + report/import/share |
| Stock Manager | read/report |
| Stock User | read/report |
| Sales User | read |
| Purchase User | read |
| Maintenance User | read |
| Accounts User | read |
| Manufacturing User | read |
| Desk User | read/select/export |

### States: [] (no workflow states defined)

### Item Variants
- Template item: has_variants=1, defines attributes via `Item Variant Attribute` table
- Variant item: variant_of points to template; inherits description, image, pricing, taxes unless overridden
- variant_based_on: "Item Attribute" or "Manufacturer"
- Item Variant Settings (Single DocType): do_not_update_variants, allow_rename_attribute_value, allow_different_uom, copy_fields_to_variant, fields table (Variant Field)

---

## 2. Item Group

**DocType:** Setup | **Module:** Setup | **Tree:** Yes | **Naming:** By fieldname (item_group_name)

| Field | Type | Label |
|---|---|---|
| item_group_name | Data | Item Group Name (reqd) |
| parent_item_group | Link | Parent Item Group |
| is_group | Check | Is Group |
| defaults_section | Section | Defaults |
| default_warehouse | Link | Default Warehouse |
| default_uom | Link | Default UOM |
|BUYING / SELLING / STOCKING sections with respective accounts |

Permissions: Item Manager (CRUD), Sales User (read), Purchase User (read), Stock User (read), Manufacturing User (read).

---

## 3. Brand

**DocType:** Setup | **Module:** Setup

| Field | Type | Label |
|---|---|---|
| brand | Data | Brand (reqd, unique) |
| brand_name | Data | Brand Name |
| description | Text | |
| logo | Attach | |
| makes_serial_no | Check | Makes Serial No |
| make_batch | Check | Make Batch |
|BUYING / SELLING / accounts sections|

Permissions: Stock User (read), Sales User (read), Purchase User (read), Item Manager (CRUD), System Manager (read).

---

## 4. Warehouse

**DocType:** Setup | **Module:** Stock | **Tree:** Yes | **Naming:** By fieldname

| Field | Type | Label |
|---|---|---|
| warehouse_name | Data | Warehouse Name (reqd) |
| is_group | Check | Is Group Warehouse (bold) |
| parent_warehouse | Link | Parent Warehouse |
| company | Link | Company (reqd) |
| disabled | Check | Disabled (hidden) |
| account | Link | Account |
| is_rejected_warehouse | Check | Is Rejected Warehouse |
| warehouse_type | Link | Warehouse Type |
| default_in_transit_warehouse | Link | Default In-Transit Warehouse |
| customer | Link | Customer (for Subcontracting Inward) |
| email_id, phone_no, mobile_no | Data | Contact info |
| address_line_1/2, city, state, pin | Data | Address |
| lft, rgt | Int | Tree structure (hidden, read_only) |

Permissions: Item Manager (CRUD), Stock User (read), Sales User (read), Purchase User (read), Accounts User (read), Manufacturing User (read).

---

## 5. Stock Entry

**DocType:** Document | **Module:** Stock | **Submittable:** Yes | **Naming:** Naming Series (MAT-STE-.YYYY.-)

### Stock Entry Types (via Stock Entry Type doctype)
Material Issue, Material Receipt, Material Transfer, Material Transfer for Manufacture, Material Consumption for Manufacture, Manufacture, Repack, Send to Subcontractor, Disassemble, Receive from Customer, Return Raw Material to Customer, Subcontracting Delivery, Subcontracting Return

### Fields

| Field | Type | Label |
|---|---|---|
| naming_series | Select | Series (MAT-STE-.YYYY.-) |
| stock_entry_type | Link | Stock Entry Type (reqd) |
| purpose | Select | Purpose (read_only, from stock_entry_type.purpose) |
| company | Link | Company (reqd) |
| posting_date | Date | Posting Date (default Today) |
| posting_time | Time | Posting Time (default Now) |
| set_posting_time | Check | Edit Posting Date and Time |
| from_warehouse | Link | Default Source Warehouse |
| to_warehouse | Link | Default Target Warehouse |
| add_to_transit | Check | Add to Transit (fetched from Stock Entry Type) |
| apply_putaway_rule | Check | Apply Putaway Rule |
| inspection_required | Check | Inspection Required |
| from_bom | Check | From BOM |
| bom_no | Link | BOM No |
| use_multi_level_bom | Check | Use Multi-Level BOM (default 1) |
| fg_completed_qty | Float | Finished Good Quantity |
| get_items | Button | Get Items |
| process_loss_qty | Float | Process Loss Qty |
| process_loss_percentage | Percent | % Process Loss |
| scan_barcode | Data | Scan Barcode |
| items | Table | Items (Stock Entry Detail, reqd) |
| total_incoming_value | Currency | Total Incoming Value (read_only) |
| total_outgoing_value | Currency | Total Outgoing Value (read_only) |
| value_difference | Currency | Total Value Difference (read_only) |
| additional_costs | Table | Additional Costs (Landed Cost Taxes and Charges) |
| total_additional_costs | Currency | Total Additional Costs |
| work_order | Link | Work Order |
| subcontracting_order | Link | Subcontracting Order |
| purchase_order | Link | Purchase Order |
| subcontracting_inward_order | Link | Subcontracting Inward Order |
| delivery_note_no | Link | Delivery Note No (for Sales Return) |
| sales_invoice_no | Link | Sales Invoice No |
| purchase_receipt_no | Link | Purchase Receipt No (for Purchase Return) |
| outgoing_stock_entry | Link | Stock Entry (Outward GIT) |
| source_stock_entry | Link | Source Stock Entry (Manufacture) |
| supplier | Link | Supplier |
| supplier_name | Data | Supplier Name (read_only) |
| supplier_address | Link | Supplier Address |
| is_opening | Select | Is Opening (No/Yes) |
| project | Link | Project |
| remarks | Text | Remarks |
| per_transferred | Percent | Per Transferred (read_only) |
| total_amount | Currency | Total Amount |
| amended_from | Link | Amended From |
| credit_note | Link | Credit Note (hidden) |
| is_return | Check | Is Return (hidden, read_only) |
| is_additional_transfer_entry | Check | Is Additional Transfer Entry (hidden) |
| job_card | Link | Job Card |
| pick_list | Link | Pick List |
| asset_repair | Link | Asset Repair |
| cost_center | Link | Cost Center |

### Permissions
- **Stock User, Manufacturing User, Manufacturing Manager, Stock Manager** — all CRUD + submit/amend/cancel

### Child Table: Stock Entry Detail (istable, autoname: hash)

| Field | Type | Label |
|---|---|---|
| s_warehouse | Link | Source Warehouse |
| t_warehouse | Link | Target Warehouse |
| item_code | Link | Item Code (reqd) |
| item_name | Data | Item Name (read_only) |
| qty | Float | Qty (reqd) |
| basic_rate | Currency | Basic Rate |
| basic_amount | Currency | Basic Amount |
| additional_cost | Currency | Additional Cost |
| amount | Currency | Amount |
| valuation_rate | Currency | Valuation Rate (read_only) |
| uom | Link | UOM (reqd) |
| stock_uom | Link | Stock UOM (read_only) |
| conversion_factor | Float | Conversion Factor |
| transfer_qty | Float | Qty as per Stock UOM (read_only) |
| batch_no | Link | Batch No |
| serial_no | Text | Serial No |
| quality_inspection | Link | Quality Inspection |
| expense_account | Link | Difference Account |
| cost_center | Link | Cost Center |
| project | Link | Project |
| material_request | Link | Material Request |
| material_request_item | Link | Material Request Item |
| bom_no | Link | BOM No (hidden) |
| is_finished_item | Check | Is Finished Item |
| type | Select | Type (Co-Product/By-Product/Scrap/Additional Finished Good) |
| is_legacy_scrap_item | Check | Is Legacy Scrap Item |
| serial_and_batch_bundle | Link | Serial and Batch Bundle |
| use_serial_batch_fields | Check | Use Serial No / Batch Fields |
| landed_cost_voucher_amount | Currency | Landed Cost Voucher Amount |
| putaway_rule | Link | Putaway Rule |
| against_stock_entry | Link | Against Stock Entry |
| transferred_qty | Float | Transferred Qty (read_only) |
| actual_qty | Float | Actual Qty (read_only, no_copy) |
| allow_zero_valuation_rate | Check | Allow Zero Valuation Rate |

---

## 6. Stock Reconciliation

**DocType:** Document | **Module:** Stock | **Submittable:** Yes | **Naming:** Naming Series (MAT-RECO-.YYYY.-)

### Fields

| Field | Type | Label |
|---|---|---|
| naming_series | Select | Series |
| company | Link | Company (reqd) |
| purpose | Select | Purpose — Opening Stock / Stock Reconciliation (reqd) |
| posting_date | Date | Posting Date (default Today) |
| posting_time | Time | Posting Time (default Now) |
| set_posting_time | Check | Edit Posting Date and Time |
| set_warehouse | Link | Default Warehouse |
| scan_barcode | Data | Scan Barcode |
| scan_mode | Check | Scan Mode (disables auto-fetch of existing qty) |
| items | Table | Items (Stock Reconciliation Item) |
| expense_account | Link | Difference Account |
| cost_center | Link | Cost Center |
| difference_amount | Currency | Difference Amount (read_only) |
| amended_from | Link | Amended From |

Permissions: **Stock Manager** only (CRUD + submit/amend).

### Purpose
- **Opening Stock** — set initial inventory levels
- **Stock Reconciliation** — fix/adjust actual quantity and valuation

---

## 7. Serial No

**DocType:** Setup | **Module:** Stock | **Naming:** By fieldname (serial_no)

| Field | Type | Label |
|---|---|---|
| serial_no | Data | Serial No (reqd, unique, no_copy) |
| item_code | Link | Item Code (reqd) |
| item_name | Data | Item Name (fetched, read_only) |
| warehouse | Link | Warehouse (read_only) |
| batch_no | Link | Batch No (read_only) |
| status | Select | Status — Active / Inactive / Consumed / Delivered / Expired (read_only) |
| purchase_rate | Float | Incoming Rate (read_only) |
| company | Link | Company (reqd) |
| item_group | Link | Item Group (read_only) |
| brand | Link | Brand (read_only) |
| asset | Link | Asset (read_only) |
| asset_status | Select | Issue / Receipt / Transfer |
| location | Link | Location |
| employee | Link | Employee |
| warranty_period | Int | Warranty Period (Days) |
| warranty_expiry_date | Date | Warranty Expiry Date |
| amc_expiry_date | Date | AMC Expiry Date |
| maintenance_status | Select | Under Warranty / Out of Warranty / Under AMC / Out of AMC |
| source_document_section | Section | Source Document |
| reference_doctype | Link | Source Document Type |
| reference_name | Dynamic Link | Source Document Name |
| posting_date | Date | Posting Date (read_only) |
| work_order | Link | Work Order |

### Permissions
- Item Manager, Stock Manager: CRUD
- Stock User: read/report

### Status Transitions
Active → Consumed (on delivery/consumption) / Delivered / Expired / Inactive

---

## 8. Batch

**DocType:** Setup | **Module:** Stock | **Naming:** By fieldname (batch_id)

| Field | Type | Label |
|---|---|---|
| batch_id | Data | Batch ID (reqd, unique, no_copy) |
| item | Link | Item (reqd) |
| item_name | Data | Item Name (fetched, read_only) |
| batch_qty | Float | Batch Quantity (read_only) |
| stock_uom | Link | Batch UOM (read_only) |
| manufacturing_date | Date | Manufacturing Date (default Today) |
| expiry_date | Date | Expiry Date |
| disabled | Check | Disabled |
| use_batchwise_valuation | Check | Use Batch-wise Valuation (read_only, set_only_once) |
| description | Small Text | Batch Description |
| supplier | Link | Supplier (read_only) |
| source | Section | Source |
| reference_doctype | Link | Source Document Type (read_only) |
| reference_name | Dynamic Link | Source Document Name (read_only) |
| parent_batch | Link | Parent Batch |
| qty_to_produce | Float | Qty To Produce (read_only) |
| produced_qty | Float | Produced Qty (read_only) |
| image | Attach Image | |

Permissions: **Item Manager** (CRUD + import/export).

---

## 9. Serial and Batch Bundle

**DocType:** Document | **Module:** Stock | **Submittable:** Yes | **Naming:** Random (hash) / SABB-.########

Central document that aggregates serial nos and batch nos for a transaction line. Replaces the older pattern of storing serial_no and batch_no directly on transaction items.

| Field | Type | Label |
|---|---|---|
| naming_series | Select | SABB-.######## |
| company | Link | Company (reqd) |
| item_code | Link | Item Code (reqd) |
| item_name | Data | Item Name (read_only) |
| warehouse | Link | Warehouse |
| type_of_transaction | Select | Inward / Outward / Maintenance / Asset Repair |
| has_serial_no | Check | Has Serial No (read_only) |
| has_batch_no | Check | Has Batch No (read_only) |
| total_qty | Float | Total Qty (allow_on_submit, read_only) |
| avg_rate | Float | Avg Rate (allow_on_submit, read_only) |
| total_amount | Float | Total Amount (allow_on_submit, read_only) |
| voucher_type | Link | Voucher Type (options: DocType, reqd) |
| voucher_no | Dynamic Link | Voucher No |
| voucher_detail_no | Data | Voucher Detail No (read_only) |
| entries | Table | Serial and Batch Entry (reqd) |
| posting_datetime | Datetime | Posting Datetime |
| is_cancelled | Check | Is Cancelled (no_copy, read_only) |
| is_rejected | Check | Is Rejected (read_only) |
| is_packed | Check | Is Packed |
| returned_against | Data | Returned Against |
| item_group | Link | Item Group (hidden, read_only) |

### Child Table: Serial and Batch Entry

| Field | Type | Label |
|---|---|---|
| serial_no | Data | Serial No |
| batch_no | Data | Batch No |
| qty | Float | Qty (positive for inward, negative for outward) |
| is_outward | Check | Is Outward |
| stock_value_difference | Float | Stock Value Difference |
| incoming_rate | Float | Incoming Rate |
| outgoing_rate | Float | Outgoing Rate |
| warehouse | Link | Warehouse |
| serial_no | Data | Serial No |

### Permissions
- System Manager, Purchase User, Purchase Manager, Stock User, Stock Manager, Delivery User, Delivery Manager, Manufacturing User, Manufacturing Manager — all CRUD + submit/cancel

---

## 10. Quality Inspection

**DocType:** Setup | **Module:** Stock | **Submittable:** Yes | **Naming:** Naming Series (MAT-QA-.YYYY.-)

| Field | Type | Label |
|---|---|---|
| naming_series | Select | Series |
| company | Link | Company |
| report_date | Date | Report Date (default Today, reqd) |
| inspection_type | Select | Inspection Type — Incoming / Outgoing / In Process (reqd) |
| status | Select | Status — Accepted / Rejected / Cancelled (default Accepted, reqd) |
| reference_type | Select | Reference Type — Purchase Receipt / Purchase Invoice / Subcontracting Receipt / Delivery Note / Sales Invoice / Stock Entry / Job Card (reqd) |
| reference_name | Dynamic Link | Reference Name (reqd) |
| item_code | Link | Item Code (reqd) |
| item_serial_no | Link | Item Serial No |
| batch_no | Link | Batch No |
| sample_size | Float | Sample Size (reqd) |
| item_name | Data | Item Name (read_only) |
| description | Small Text | Description |
| bom_no | Link | BOM No (read_only) |
| quality_inspection_template | Link | Quality Inspection Template |
| readings | Table | Readings (Quality Inspection Reading) |
| inspected_by | Link | Inspected By (default: user, reqd) |
| verified_by | Data | Verified By |
| remarks | Text | Remarks |
| manual_inspection | Check | Manual Inspection |
| child_row_reference | Data | Child Row Reference (hidden, no_copy, read_only) |
| letter_head | Link | Letter Head |

Permissions: **Quality Manager** (CRUD + submit/amend/cancel).

---

## 11. Pick List

**DocType:** Document | **Module:** Stock | **Submittable:** Yes | **Naming:** Naming Series (STO-PICK-.YYYY.-)

| Field | Type | Label |
|---|---|---|
| naming_series | Select | Series |
| company | Link | Company (reqd) |
| purpose | Select | Purpose — Material Transfer for Manufacture / Material Transfer / Delivery (default: Material Transfer for Manufacture) |
| customer | Link | Customer (depends_on: purpose==='Delivery') |
| work_order | Link | Work Order (depends_on: purpose==='Material Transfer for Manufacture') |
| parent_warehouse | Link | Warehouse — items under this warehouse will be suggested |
| for_qty | Float | Qty of Finished Goods Item (read_only) |
| material_request | Link | Material Request (depends_on: Material Transfer/Material Issue) |
| locations | Table | Item Locations (Pick List Item) |
| group_same_items | Check | Group Same Items (allow_on_submit) |
| scan_barcode | Data | Scan Barcode |
| scan_mode | Check | Scan Mode — picked qty won't auto-fulfill on submit |
| prompt_qty | Check | Prompt Qty |
| pick_manually | Check | Pick Manually — system won't override picked qty/batches/serial/warehouse |
| ignore_pricing_rule | Check | Ignore Pricing Rule |
| consider_rejected_warehouses | Check | Consider Rejected Warehouses |
| status | Select | Status — Draft / Open / Partly Delivered / Completed / Cancelled (hidden, read_only) |
| delivery_status | Select | Delivery Status — Not Delivered / Fully Delivered / Partly Delivered |
| per_delivered | Percent | % Delivered (read_only) |
| amended_from | Link | Amended From |
| customer_name | Data | Customer Name (read_only) |

### Permissions
- Stock Manager, Stock User, Manufacturing Manager, Manufacturing User — all CRUD + submit/amend/cancel

---

## 12. Landed Cost Voucher

**DocType:** Document | **Module:** Stock | **Submittable:** Yes | **Naming:** Naming Series (MAT-LCV-.YYYY.-)

| Field | Type | Label |
|---|---|---|
| naming_series | Select | Series |
| company | Link | Company (reqd) |
| posting_date | Date | Posting Date (default Today, reqd) |
| purchase_receipts | Table | Vouchers (Landed Cost Purchase Receipt) |
| get_items_from_purchase_receipts | Button | Get Items |
| items | Table | Receipt Items (Landed Cost Item) |
| vendor_invoices | Table | Vendor Invoices (Landed Cost Vendor Invoice) |
| taxes | Table | Landed Cost (Landed Cost Taxes and Charges) |
| total_taxes_and_charges | Currency | Total Landed Cost (read_only) |
| total_vendor_invoices_cost | Currency | Total Vendor Invoices Cost (read_only) |
| distribute_charges_based_on | Select | Distribute Charges Based On — Qty / Amount / Distribute Manually |
| amended_from | Link | Amended From |

### Purpose
Distribute landed costs (shipping, duties, insurance) across items in a Purchase Receipt.

Permissions: **Stock Manager** (CRUD + submit/amend/cancel).

---

## 13. Putaway Rule

**DocType:** (Child doctype / standalone) | **Naming:** PUT-.####

| Field | Type | Label |
|---|---|---|
| item_code | Link | Item (reqd) |
| warehouse | Link | Warehouse (reqd) |
| capacity | Float | Capacity (reqd) |
| stock_uom | Link | Stock UOM (read_only) |
| priority | Int | Priority (default 1, in_list_view) |
| company | Link | Company (reqd) |
| disable | Check | Disable |
| uom | Link | UOM |
| conversion_factor | Float | Conversion Factor (read_only) |
| stock_capacity | Float | Capacity in Stock UOM (read_only) |

Permissions: Stock Manager (CRUD level 0, read level 1), Stock User (read).

---

## 14. Stock Settings

**DocType:** Single | **Module:** Stock | **Naming:** Single

### Key Settings

#### Defaults Tab
- item_naming_by: Item Code / Naming Series
- default_item_group: Link → Item Group
- default_warehouse: Link → Warehouse
- sample_retention_warehouse: Link → Warehouse
- valuation_method: FIFO / Moving Average / LIFO
- auto_insert_price_list_rate_if_missing
- update_existing_price_list_rate
- update_price_list_based_on: Rate / Price List Rate

#### Stock Transactions Settings
- over_delivery_receipt_allowance: Float (%)
- mr_qty_allowance: Float (%)
- over_picking_allowance: Percent
- role_allowed_to_over_deliver_receive
- allow_negative_stock
- show_barcode_field
- clean_description_html
- allow_internal_transfer_at_arms_length_price
- validate_material_transfer_warehouses

#### Serial & Batch Item Settings
- enable_serial_and_batch_no_for_item
- allow_existing_serial_no
- do_not_use_batchwise_valuation
- auto_create_serial_and_batch_bundle_for_outward
- pick_serial_and_batch_based_on: FIFO / LIFO / Expiry
- disable_serial_no_and_batch_selector
- use_serial_batch_fields
- do_not_update_serial_batch_on_creation_of_auto_bundle
- allow_negative_stock_for_batch
- set_serial_and_batch_bundle_naming_based_on_naming_series
- use_naming_series
- naming_series_prefix

#### Stock Reservation
- enable_stock_reservation
- auto_reserve_stock
- allow_partial_reservation
- auto_reserve_stock_for_sales_order_on_purchase
- auto_reserve_serial_and_batch

#### Quality Inspection Settings
- action_if_quality_inspection_is_not_submitted: Stop / Warn
- action_if_quality_inspection_is_rejected: Stop / Warn
- allow_to_make_quality_inspection_after_purchase_or_delivery

#### Stock Planning
- auto_indent (raise MR when stock reaches re-order level)
- reorder_email_notify
- auto_material_request

#### Control Historical Transactions
- stock_frozen_upto: Date
- stock_frozen_upto_days: Int
- role_allowed_to_create_edit_back_dated_transactions
- role_allowed_to_edit_frozen_stock

#### Conversion
- allow_to_edit_stock_uom_qty_for_sales
- allow_to_edit_stock_uom_qty_for_purchase
- allow_uom_with_conversion_rate_defined_in_item

Permissions: Stock Manager (CRUD), Sales User (read).

---

## 15. Item Price

**DocType:** Setup | **Module:** Stock | **Naming:** Random (hash)

| Field | Type | Label |
|---|---|---|
| item_code | Link | Item Code (reqd) |
| uom | Link | UOM (reqd) |
| packing_unit | Int | Packing Unit |
| item_name | Data | Item Name (read_only) |
| brand | Link | Brand (read_only) |
| price_list | Link | Price List (reqd, in_standard_filter) |
| customer | Link | Customer (depends_on: selling) |
| supplier | Link | Supplier (depends_on: buying) |
| buying | Check | Buying (read_only) |
| selling | Check | Selling (read_only) |
| currency | Link | Currency (fetched from price_list, read_only) |
| price_list_rate | Currency | Rate (reqd) |
| valid_from | Date | Valid From (default Today) |
| valid_upto | Date | Valid Up To |
| lead_time_days | Int | Lead Time in days |
| batch_no | Link | Batch No |
| reference | Data | Reference |

Permissions: **Sales Master Manager**, **Purchase Master Manager** (both CRUD + import/export).

---

## 16. Item Attribute

**DocType:** Setup | **Module:** Stock | **Naming:** By fieldname (attribute_name)

| Field | Type | Label |
|---|---|---|
| attribute_name | Data | Attribute Name (reqd, unique) |
| numeric_values | Check | Numeric Values |
| from_range | Float | From Range (depends_on: numeric_values) |
| to_range | Float | To Range (depends_on: numeric_values) |
| increment | Float | Increment (depends_on: numeric_values) |
| item_attribute_values | Table | Item Attribute Values (non-numeric) |
| disabled | Check | Disabled |

Permissions: **Item Manager** (CRUD).

---

## 17. Stock Closing Entry

**DocType:** Document | **Module:** Stock | **Submittable:** Yes | **Naming:** Naming Series (CBAL-.#####)

| Field | Type | Label |
|---|---|---|
| naming_series | Select | CBAL-.##### |
| company | Link | Company |
| status | Select | Draft / Queued / In Progress / Completed / Failed / Cancelled (read_only) |
| from_date | Date | From Date |
| to_date | Date | To Date |
| amended_from | Link | Amended From |

Permissions: System Manager, Stock User, Stock Manager — all CRUD + submit/amend/cancel.

---

## 18. Stock Ledger Entry (SLE)

Not a DocType JSON but the core `stock_ledger.py` module. Key fields (from controller logic):
- item_code, warehouse, actual_qty, qty_after_transaction
- incoming_rate, valuation_rate, stock_value, stock_value_difference
- voucher_type, voucher_no, voucher_detail_no
- posting_date, posting_time, posting_datetime
- is_cancelled
- serial_and_batch_bundle
- project
- (inventory dimension fields dynamically attached)

---

## 19. Key Controller Logic (stock_controller.py)

`StockController` extends `AccountsController` and provides:

### Validation Methods
- `validate()` — calls validate_duplicate_serial_and_batch_bundle, validate_inspection, validate_warehouse_of_sabb, validate_serialized_batch, clean_serial_nos, validate_customer_provided_item, set_rate_of_stock_uom, validate_internal_transfer, validate_putaway_capacity, reset_conversion_factor
- `validate_inspection()` — checks quality inspection presence/submission/rejection based on inspection_required_before_purchase/delivery flags and Stock Settings actions
- `validate_serialized_batch()` — checks serial no belongs to batch; checks batch expiry
- `validate_warehouse_of_sabb()` — warehouse on SABB must match transaction row warehouse for outward transactions
- `validate_putaway_capacity()` — validates against Putaway Rule capacity
- `validate_internal_transfer()` — validates in-transit warehouses for internal transfers; multi-currency checks; packed items restrictions
- `check_zero_rate()` — toast warning for zero-rate items (not blocking)

### Bundle Management
- `make_bundle_using_old_serial_batch_fields()` — creates Serial and Batch Bundle from legacy serial_no/batch_no fields on save
- `make_bundle_for_sales_purchase_return()` — handles returns (rejected + non-rejected qty)
- `create_serial_batch_bundle()` — creates the SABB document
- `set_serial_and_batch_bundle()` — sets serial/batch values from bundle onto item rows
- `delete_auto_created_batches()` — cleanup on cancel

### GL & Stock Entries
- `make_gl_entries()` — creates GL entries for perpetual inventory; handles provisional accounting
- `make_sl_entries()` — delegates to stock_ledger module
- `get_gl_entries()` — builds GL entry map from SLE data
- `get_stock_ledger_details()` — queries SLE for a voucher
- `get_inventory_account_map()` — warehouse-account or item-account mapping
- `update_inventory_dimensions()` — maps inventory dimension fields (e.g., batch_no, serial_no) to SLE

### Reposting
- `repost_future_sle_and_gle()` — triggers item-valuation repost after transaction
- `delete_auto_created_batches()` — cleanup on cancel

### Serial/Batch Reservation
- `validate_reserved_batches()` — checks batch is not over-reserved via Stock Reservation Entry
- `update_stock_reservation_entries()` — updates SRE delivered_qty on Stock Entry submit/cancel

### Quality Inspection
- `make_quality_inspections()` — bulk-creates QI from transaction items
- `check_item_quality_inspection()` — filters items needing inspection

### Other
- `is_serial_batch_item()` — @request_cache — checks item has serial or batch tracking
- `get_serialized_items()` — returns items with has_serial_no=1
- `validate_warehouse()` — checks warehouse disabled status and company linkage
- `validate_duplicate_serial_and_batch_bundle()` — prevents SABB reuse across submitted SLEs

---

## 20. Key Reports

Located in `reference/erpnext-develop/erpnext/stock/report/`:

| Report | Purpose |
|---|---|
| stock_ledger | Full stock movement by item/warehouse/date |
| stock_balance | Current qty and value per item-warehouse |
| stock_value_by_item_group | Stock value aggregated by item group |
| warehouse_wise_stock_balance | Stock balance per warehouse |
| stock_ageing | Age analysis of stock holdings |
| stock_projected_qty | Projected stock including pending orders |
| item_prices | Item price list rates |
| batch_wise_balance_history | Batch-level stock history |
| batch_item_expiry_status | Upcoming/expiring batches |
| available_batch_report | Available batches per item |
| available_serial_no | Available serial numbers |
| serial_no_ledger | Serial no movement history |
| serial_no_status | Serial no current status |
| incorrect_serial_and_batch_bundle | Bundles with quantity mismatches |
| fifo_queue_vs_qty_after_transaction | Valuation queue vs actual qty |
| stock_and_account_value_comparison | GL stock account vs stock value |
| stock_analytics | Analytics with configurable filters |
| itemwise_recommended_reorder_level | Suggested reorder levels |
| items_to_be_requested | Items below reorder level |
| product_bundle_balance | Product bundle component stock |
| delayed_item_report | Items with delayed transactions |
| total_stock_summary | Summary of total stock across warehouses |

---

## 21. Dashboard / Analytics

### Dashboard Charts (erpnext/stock/dashboard_chart/)
- warehouse_wise_stock_value
- stock_value_by_item_group
- item_shortage_summary
- oldest_items
- delivery_trends
- purchase_receipt_trends

### Number Cards
- total_warehouses
- total_active_items
- total_stock_value

### Pages
- stock_balance — tree/grid view of stock by warehouse
- warehouse_capacity_summary — capacity utilization per warehouse

### Item Dashboard (`item_dashboard.py`, `item_dashboard.js`)
Per-item dashboard showing:
- Stock balance, valuation rate, value
- Price history
- Warehouse-wise qty
- reorder levels
- Pending stock movements (incoming/outgoing)
- Stock reconciliation history

---

## 22. Barcode Functionality

- **Item Barcode** child table on Item: barcode (unique), barcode_type (EAN/UPC/GS1/GTIN/ISBN/JAN/PZN etc.), uom
- Barcode field available in: Stock Entry, Stock Reconciliation, Pick List, Stock Entry Detail (row level)
- Scan Barcode button on Stock Entry header and rows
- `scan_barcode` field type with `Barcode` option triggers barcode scanner
- Stock Settings: `show_barcode_field` — toggle barcode field visibility in stock transactions
- Barcode can be used to auto-populate item in transactions (via `has_item_scanned` check on Stock Entry Detail)

---

## 23. Item Variant Management

### Architecture
- **Template Item**: has_variants=1, defines attributes table
- **Variant Items**: variant_of points to template, inherit unless overridden
- **Item Attribute**: defines attribute name + values (e.g., Color: Red/Green/Blue; Size: S/M/L/XL)
- **Item Variant Attribute**: links variant to attribute + value; supports numeric ranges (from_range, to_range, increment)
- **Item Variant Settings** (Single): controls behavior (do_not_update_variants, allow_rename_attribute_value, allow_different_uom)

### Variant-Based-On Options
1. **Item Attribute** — classic: pick attributes to generate variants
2. **Manufacturer** — variant is determined by manufacturer instead of attributes

### Variant Fields
Template can define which additional fields to copy to variants via `Variant Field` table in Item Variant Settings (e.g., description, image, pricing, taxes, uom, etc.)

---

## 24. Pricing (Item Price + Pricing Rule)

### Item Price
- Stores rate per item + uom + price_list + currency + customer/supplier
- Valid from/to date range
- Batch-specific pricing supported
- Lead time per price record
- Buying and Selling flags

### Pricing Rule (note: pricing_rule.json not found in erpnext-develop; likely under erpnext/accounts/doctype)
Pricing rules typically handle:
- Item-wise or group-wise discount/surcharge
- Based on qty, rate, customer group, supplier, etc.
- Apply on: Item Code, Item Group, Brand
- Rate or discount type
- Margin type (Base / Portion of AMT / PERCENT)
- Valid from/to
- Mixed conditions (qty breaks, etc.)

---

## 25. Inventory Analytics and Reporting

### Built-in Analytics
- Stock Analytics report with customizable filters (date range, item, warehouse, company)
- Item-wise price list rate report
- Warehouse-wise item balance with age and value analysis
- Stock projected qty (considers pending orders, material requests)
- Item shortage report
- Delayed item/order reports

### Dashboard
- Item Dashboard with live stock qty, value, reorder status
- Stock balance page with tree view
- Warehouse capacity summary

### Valuation
- FIFO, Moving Average, LIFO (per item or global default in Stock Settings)
- Batch-wise valuation possible (use_batchwise_valuation on Batch)
- Landed Cost Voucher distributes additional costs to item valuations
- Repost Item Valuation entry for fixing valuation errors
- `Stock Reposting Settings` controls item-based vs voucher-based reposting

---

## 26. Stock Closing / Reconciliation Workflow

### Stock Closing Entry
- Closes stock for a period (from_date to_date) per company
- Statuses: Draft → Queued → In Progress → Completed / Failed / Cancelled
- System Manager + Stock User + Stock Manager can operate
- Purpose: lock stock transactions for a period, prevent post-closing modifications

### Stock Reconciliation
- Purpose: Opening Stock (initial) or Stock Reconciliation (adjust)
- Scan Mode: disables auto-fetch of existing qty
- Updates: qty and valuation_rate per warehouse
- Generates: difference_amount (booked to expense/revenue account)
- Can trigger: reposting of item valuation

---

## 27. Putaway and Pick Strategy

### Putaway Rule
- Per item + warehouse + company
- capacity: max qty the warehouse can hold
- priority: used when multiple rules match (lower number = higher priority)
- Applied automatically on Purchase Receipt, Stock Entry, Purchase Invoice (if update_stock)
- `apply_putaway_rule` checkbox on Stock Entry / Purchase Receipt
- `validate_putaway_capacity()` in stock_controller validates capacity

### Pick List
- Purpose: Delivery, Material Transfer for Manufacture, Material Transfer
- Gets item locations automatically (Get Item Locations button)
- Supports: scan_mode, prompt_qty, pick_manually (don't auto-override)
- group_same_items for combining identical items
- ignore_pricing_rule to skip pricing rules on delivery
- Status: Draft → Open → Partly Delivered → Completed
- Links to: Work Order (for manufacture), Material Request (for transfer/issue), Customer (for delivery)
- Consider rejected warehouses option for manufacturing

### Warehouse Capacity Summary
- Page showing capacity utilization per warehouse
- Based on Putaway Rules

---

## 28. State Machines / Statuses

| DocType | Statuses |
|---|---|
| Stock Entry | Draft → Open (implicit on save) → Submitted → Cancelled |
| Stock Reconciliation | Draft → Submitted → Cancelled |
| Stock Closing Entry | Draft → Queued → In Progress → Completed / Failed / Cancelled |
| Pick List | Draft → Open → Partly Delivered → Completed / Cancelled |
| Quality Inspection | Accepted / Rejected / Cancelled |
| Serial No | Active / Inactive / Consumed / Delivered / Expired |
| Serial and Batch Bundle | Inward / Outward / Maintenance / Asset Repair |
| Landed Cost Voucher | Draft → Submitted → Cancelled |

Note: Most stock documents use implicit status via docstatus (0=Draft, 1=Submitted, 2=Cancelled). Explicit status fields exist for Pick List and Stock Closing Entry.

---

## 29. Permissions Summary

| Role | Item | Warehouse | Stock Entry | Stock Recon | Serial/Batch | QI | Pick List | LCV | Item Price |
|---|---|---|---|---|---|---|---|---|---|
| Stock Manager | CRUD | — | CRUD+Sub | CRUD+Sub | — | — | CRUD+Sub | CRUD+Sub | — |
| Stock User | read | read | CRUD+Sub | — | read | — | CRUD+Sub | — | — |
| Item Manager | CRUD | CRUD | — | — | CRUD | — | — | — | — |
| Quality Manager | — | — | — | — | — | CRUD+Sub | — | — | — |
| Manufacturing Manager/User | read | — | CRUD+Sub | — | — | — | CRUD+Sub | — | — |
| Purchase Manager/User | — | — | — | — | — | — | — | — | — |
| Sales Manager/User | — | — | — | — | — | — | — | — | — |
| System Manager | — | — | — | — | CRUD+Sub | — | — | — | — |
| Sales Master Manager | — | — | — | — | — | — | — | — | CRUD |
| Purchase Master Manager | — | — | — | — | — | — | — | — | CRUD |

---

## 30. Key Integrations with Other Modules

### Manufacturing
- Work Order → Stock Entry (Material Transfer for Manufacture / Manufacture)
- Job Card → Quality Inspection
- BOM → affects stock transactions (via Stock Entry with from_bom)
- Production Plan → Material Request → Stock Entry

### Buying/Purchase
- Purchase Receipt → Stock Entry (Material Receipt) + Landed Cost Voucher
- Purchase Invoice (with update_stock) → affects stock
- Subcontracting Receipt → Stock Entry

### Selling/Delivery
- Delivery Note → Stock Entry (Material Issue) + Quality Inspection
- Sales Invoice (with update_stock) → affects stock
- Sales Return → Stock Entry (Material Receipt / Purchase Return pattern)

### Accounts
- GL Entry created via StockController.make_gl_entries for perpetual inventory
- Stock-in-hand account (per warehouse or per item)
- Expense account for outgoing items
- Cost Center + Project tracking
- Landed Cost Voucher distributes costs

### Projects
- Project-linked stock transactions
- Project-wise stock valuation tracking

### Assets
- Serial No linked to Asset
- Fixed Asset items auto-create Asset on purchase
- Asset repair linked to Stock Entry

---

## 31. Important Files Summary

| File | Purpose |
|---|---|
| stock_controller.py | Base controller for all stock transactions (2433 lines) |
| stock_ledger.py | Core SLE logic — actual_qty, valuation, queue management |
| valuation.py | Valuation rate computation (FIFO, Moving Average, LIFO) |
| get_item_details.py | 55KB — item detail fetching (pricing, stock, UOM conversion, etc.) |
| serial_batch_bundle.py | Serial/Batch Bundle creation and management |
| reorder_item.py | Reorder level and auto-MR generation |
| utils.py | Stock utilities (validate_warehouse, get_warehouse_account_map, etc.) |
| stock_balance.py | Stock balance computation |
| item_dashboard.py | Per-item analytics dashboard data |
| deprecated_serial_batch.py | Legacy serial/batch handling (deprecated) |
| item/item.py | Item controller |
| warehouse/warehouse.py | Warehouse controller (tree structure) |
