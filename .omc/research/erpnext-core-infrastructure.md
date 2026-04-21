# ERPnext Core Infrastructure Deep-Dive

## 1. Utilities (`erpnext/utilities/`)

### 1.1 `activation.py` - Setup Wizard & Activation Tracking
- **Purpose**: Tracks "how set up" a new ERPnext installation is
- **`get_level(site_info)`**: Returns activation level (0-10+) based on:
  - Document counts for key doctypes (Asset, BOM, Customer, Delivery Note, Employee, Item, Journal Entry, Lead, Material Request, Opportunity, Payment Entry, Project, Purchase Order/Invoice/Receipt, Quotation, Sales Order/Invoice, Stock Entry, Supplier, Task, User, Work Order)
  - Whether setup wizard completed
  - Communication count (>10 emails)
  - Recent login activity (within 2 days)
- **`get_help_messages()`**: Context-aware desktop notifications guiding new users to create essential records (Leads, Quotations, Sales Orders, Purchase Orders, Users, Timesheets, Employees)

### 1.2 `bulk_transaction.py` - Bulk Document Conversion
- **Purpose**: Batch-convert documents between doctypes (e.g., Sales Order → Delivery Note)
- **`transaction_processing()`**: Whitelist method that enqueues bulk conversion jobs
- **Supported mappings**:
  - Sales Order → Sales Invoice, Delivery Note, Payment Entry
  - Sales Invoice → Delivery Note, Payment Entry
  - Delivery Note → Sales Invoice, Packing Slip
  - Quotation → Sales Order, Sales Invoice
  - Supplier Quotation → Purchase Order, Purchase Invoice
  - Purchase Order → Purchase Invoice, Purchase Receipt, Payment Entry
  - Purchase Invoice → Purchase Receipt, Payment Entry
  - Purchase Receipt → Purchase Invoice
- **Error handling**: Uses savepoints, logs failures to `Bulk Transaction Log Detail`
- **Retry mechanism**: `retry()` and `retry_failed_transactions()` for recovering from failures
- **Hooks support**: External apps can extend mapper via `bulk_transaction_task_mapper` hook

### 1.3 `transaction_base.py` - Shared Transaction Logic
- **Class**: `TransactionBase` - base class for all transaction documents
- **Key methods**:
  - `validate_posting_time()`: Sets posting date/time, handles import/restore scenarios
  - `validate_uom_is_integer()`: Ensures UOM quantities are whole numbers when required
  - `validate_with_previous_doc()`: Compares values against referenced documents
  - `validate_rate_with_reference_doc()`: Enforces rate consistency (Stop/Allow based on Buying Settings)
  - `fetch_item_details()`: Calls `get_item_details()` with comprehensive context
  - `process_item_selection()`: Server-side item processing triggered from UI
  - `set_item_rate_and_discounts()`: Handles margin, discount_percentage, discount_amount
  - `conversion_factor()`: Calculates stock_qty from qty × conversion_factor
  - `calculate_net_weight()`: Sums total_weight across items
  - `_apply_price_list()`: Applies price list via `apply_price_list()`
  - `copy_from_first_row()`: Copies fields (including accounting dimensions) from first row

### 1.4 `naming.py` - Naming Series Management
- **`set_by_naming_series()`**: Programmatically toggles doctype naming between autoid and user-defined naming series
- Uses `make_property_setter()` to hide/show name field and make naming_series required/optional

### 1.5 `product.py` - E-commerce Product Utilities
- **`get_price()`**: Fetches item price from price list, applies pricing rules, handles variant item codes
- **`get_item_codes_by_attributes()`**: SQL-based attribute filtering for product finder

### 1.6 `regional.py` - Region-Specific Hooks
- **`check_deletion_permission()`**: Nepal-specific: prevents deletion of submitted documents

---

## 2. Setup DocTypes (`erpnext/setup/doctype/`)

### 2.1 Email Digest (`email_digest/`)
**Doctype**: Scheduled email reports for management
- **Frequency**: Daily, Weekly, Monthly
- **Content sections** (all configurable):
  - Accounting cards: Income, Expenses, Bank Balance, Credit Balance, Payables, Receivables
  - Order metrics: Sales/Purchase Orders (to bill, to deliver/receive)
  - Invoicing: Sales/Purchase Invoices
  - Quotations: New, Pending
  - Project metrics
  - Issue tracking
  - Calendar events, Todo list
  - Notifications
- **`send()`**: Uses `frappe.sendmail()` with unsubscribe
- **`get_msg_html()`**: Renders template with context
- **Module-level `send()`**: Called by scheduler for all enabled digests

### 2.2 Authorization Control (`authorization_control/`)
- **Purpose**: Custom authorization rules engine
- Hooks into `VALUATE` and `DOCPJ` events for custom validation

### 2.3 Authorization Rule (`authorization_rule/`)
- **Purpose**: Define conditions for document approval workflows
- Supports conditions on document fields and user/role properties

### 2.4 Other Setup DocTypes
| DocType | Purpose |
|---------|---------|
| `company/` | Company master with default settings |
| `currency_exchange/` | Currency conversion rates |
| `customer_group/` | Customer categorization |
| `department/` | HR department hierarchy |
| `designation/` | Job titles |
| `driver/` | Delivery/pickup drivers |
| `employee/` | Employee records with HR integration |
| `holiday_list/` | Define holidays per region/company |
| `incoterm/` | International Commercial Terms |
| `item_group/` | Product categorization |
| `sales_partner/` | Channel partners and commissions |
| `sales_person/` | Sales team members |
| `supplier_group/` | Supplier categorization |
| `terms_and_conditions/` | Reusable T&C templates |
| `territory/` | Geographic sales territories |
| `uom/` & `uom_conversion_factor/` | Units of measure |
| `vehicle/` | Fleet management |
| `website_item_group/` | E-commerce item categories |

---

## 3. Regional Features (`erpnext/regional/`)

### 3.1 Supported Countries
- **Australia**: Tax reporting, GST compliance
- **Italy**: Italian fiscal regulations
- **South Africa**: VAT, VAT 201 return
- **Turkey**: Turkish localization
- **United Arab Emirates**: UAE VAT compliance
- **United States**: IRS 1099 reporting

### 3.2 US Regional (`united_states/`)
- **IRS 1099 Report**: Generates 1099-MISC for US tax reporting
- **Custom fields**: `irs_1099` flag on Supplier doctype
- **Test**: Verifies supplier creation with tax ID and report generation

### 3.3 Regional Hooks Pattern
Each country module implements country-specific overrides via `regional.py`:
```python
def get_region(company):
    return frappe.get_cached_value("Company", company, "country")
```

---

## 4. E-Commerce / Shopping Cart (`erpnext/shopping_cart/`)

### 4.1 Overview
- **Status**: Mature feature being deprecated in favor of standalone Frappe e-commerce
- **Note**: V15+ patches delete old e-commerce doctypes

### 4.2 Shopping Cart DocTypes
- `shopify_settings/`: Shopify integration (deprecated, being removed)
- Cart operations handled via Frappe's `web_form` module

---

## 5. Point of Sale (`erpnext/selling/page/point_of_sale/`)

### 5.1 POS Architecture
**Frontend** (JavaScript):
- `pos_controller.js`: Main controller, handles opening entry, POS profile setup
- `pos_item_cart.js`: Shopping cart UI
- `pos_item_selector.js`: Product search/selection grid
- `pos_payment.js`: Payment method handling
- `pos_item_details.js`: Item details/editing panel
- `pos_past_order_list.js`: Order history
- `pos_past_order_summary.js`: Order details view
- `pos_number_pad.js`: Numeric keypad UI

### 5.2 POS Invoice DocType (`erpnext/accounts/doctype/pos_invoice/`)
- Extends `SalesInvoice` class
- Key differences from standard Sales Invoice:
  - POS Profile linkage
  - Opening/closing entry tracking
  - Cash drawer management
  - Faster, simplified UI workflow
- **Features**: Barcode scanning, automatic pricing rule application

### 5.3 POS Profile (`erpnext/accounts/doctype/pos_profile/`)
- Company + warehouse + customer group associations
- Payment methods configuration
- Print format selection
- Tax category mapping

### 5.4 POS Settings (`erpnext/accounts/doctype/pos_settings/`)
- Default POS profile
- Automatic invoice posting
- Cashiers list
- Merge log for invoice consolidation

---

## 6. Integrations (`erpnext/erpnext_integrations/`)

### 6.1 Plaid Integration (`doctype/plaid_settings/`)
**Purpose**: Bank account aggregation and transaction sync via Plaid
- **DocType**: `PlaidSettings`
  - `plaid_client_id`, `plaid_secret`, `plaid_env` (sandbox/development/production)
  - `enable_european_access`, `automatic_sync` flags
- **Key functions**:
  - `get_link_token()`: Initialize Plaid Link
  - `add_institution()`: Create Bank record with access token
  - `add_bank_accounts()`: Create Bank Account + GL Account entries
  - `sync_transactions()`: Fetch and create Bank Transaction records
  - `automatic_synchronization()`: Scheduler job for auto-sync
- **Webhook security**: HMAC-SHA256 signature validation via `validate_webhooks_request()`
- **Connector**: `plaid_connector.py` wraps Plaid API

### 6.2 Webhook Utilities (`erpnext/erpnext_integrations/utils.py`)
- `validate_webhooks_request()`: Decorator for HMAC webhook validation
- `get_webhook_address()`: Generate webhook endpoint URLs
- `get_tracking_url()`: Format tracking URLs for shipping carriers

### 6.3 Payment Gateway Account (`erpnext/accounts/doctype/payment_gateway_account/`)
- Configure payment gateways (Stripe, Razorpay, etc.)
- Link to Bank Account for settlement
- API keys and credentials management

---

## 7. Barcode/QR/Scanner (`erpnext/public/js/utils/barcode_scanner.js`)

### 7.1 BarcodeScanner Class
```javascript
erpnext.utils.BarcodeScanner = class BarcodeScanner {
    constructor(opts)
    process_scan()  // Main entry point
    scan_api_call(input, callback)
    update_table(data)  // Add/update item rows
}
```

### 7.2 Features
- **Scan API**: Calls `erpnext.stock.utils.scan_barcode`
- **Supports**: Item code, barcode, batch_no, serial_no, uom, warehouse scanning
- **Location-first scanning**: Scans warehouse before items
- **Dialog for multi-item**: Shows dialog when multiple items match
- **Audio feedback**: Success/fail sounds
- **Duplicate serial no detection**
- **Max qty enforcement**: For pick lists

### 7.3 Item Barcode (`erpnext/stock/doctype/item_barcode/`)
- Child table on Item doctype
- Stores barcode per item with UOM support

---

## 8. Portal (`erpnext/portal/`)

### 8.1 Portal Utils (`utils.py`)
- `set_default_role()`: Hook to assign Customer/Supplier roles based on email
- `create_customer_or_supplier()`: Auto-create party on session creation
- `party_exists()`: Check if contact already linked to party

### 8.2 Portal DocTypes
- `website_attribute/`: Attributes for website items
- `website_filter_field/`: Filter configurations for web listings

---

## 9. Data Migration

### 9.1 Bulk Transaction Log (`erpnext/utilities/bulk_transaction.py`)
- **Table**: `Bulk Transaction Log Detail`
- Tracks: from/to doctype, transaction name, status, error description, retry count
- **Status**: Success, Failed
- **Retry**: Increments `retried` flag

### 9.2 Transaction Deletion (`erpnext/setup/doctype/transaction_deletion_record/`)
- Track document deletions for compliance/audit
- Tables: `transaction_deletion_record_item`, `transaction_deletion_record_to_delete`

---

## 10. Scheduled Jobs / Automation

### 10.1 Email Digest
- Module-level `send()` called by Frappe scheduler
- Evaluates `next_send` date before sending

### 10.2 Auto-Repeat
- **Note**: Not found in core; likely handled by Frappe's core Auto Repeat module
- Pattern: Documents can have `auto_repeat` field linking to repeat schedule

### 10.3 Plaid Sync
```python
def automatic_synchronization():
    settings = frappe.get_doc("Plaid Settings", "Plaid Settings")
    if settings.enabled == 1 and settings.automatic_sync == 1:
        enqueue_synchronization()
```

---

## 11. Permissions System

### 11.1 Role Permission Manager
- ERPnext uses Frappe's core permissions: `tabDocPerm`
- **Custom**: `erpnext/setup/doctype/authorization_rule/` for conditional approvals
- **Authorization Control**: `erpnext/setup/doctype/authorization_control/` for custom validate hooks

### 11.2 Field-Level Permissions
- Handled via Frappe's `Field Level Permission` feature
- `read`, `write`, `create`, `delete`, `submit` permissions per role

### 11.3 User Types
- Standard Users: Full system access
- Website Users: Portal-only access
- API Users: Token-based programmatic access

---

## 12. Custom Fields & Property Setters

### 12.1 Custom Field Pattern
ERPnext uses `make_property_setter()` in code:
```python
make_property_setter(
    doctype, "fieldname", "hidden", 0, "Check", validate_fields_for_doctype=False
)
```

### 12.2 Dynamicield Updates
- `erpnext/patches/` contain migrations for field additions
- Examples:
  - `create_company_custom_fields.py`
  - `create_custom_field_for_finance_book.py`
  - `add_custom_field_for_south_africa.py`

---

## 13. Workflow Engine

### 13.1 Status
- Workflow functionality is **in Frappe core**, not ERPnext-specific
- ERPnext workflow examples in patches:
  - `update_recipient_email_digest.py`
  - `set_update_field_and_value_in_workflow_state.py`

### 13.2 Pattern
- `Workflow` DocType defines states and transitions
- `Workflow State` DocType per state (Is Active, Is Terminal)
- `Workflow Action` recorded for each transition
- Email notifications on state changes via core Frappe notifications

---

## 14. Notifications

### 14.1 Email Notifications
- Triggered by docstatus transitions (submit, cancel, etc.)
- Frappe core `Notification` doctype with:
  - Document types
  - Events (create, submit, cancel, value change)
  - Recipients (users, roles, document fields)
  - Message template

### 14.2 Document Follow/Seen
- Handled by Frappe core (Communication, seen_count, followed_to)

---

## 15. Key Architectural Patterns

### 15.1 Transaction Base Class
All transaction doctypes inherit from `TransactionBase` which provides:
- Posting time validation
- UOM integer validation
- Rate validation against reference
- Item detail fetching
- Price list application
- Dimension handling

### 15.2 Status Updater Mixin
Provides:
- Status update logic
- Submission/cancellation handling
- Timeline tracking

### 15.3 Mapper Pattern
Bulk transactions use a mapper dictionary:
```python
mapper = {
    "Sales Order": {
        "Sales Invoice": sales_order.make_sales_invoice,
        "Delivery Note": sales_order.make_delivery_note,
    }
}
```
Extensible via `bulk_transaction_task_mapper` hook.

### 15.4 Regional Pattern
```python
from erpnext import get_region
region = get_region(doc.company)
if region == "United States":
    # US-specific logic
```

---

## 16. Summary Table

| Feature Area | Key Files | Status |
|-------------|-----------|--------|
| Utilities | bulk_transaction.py, transaction_base.py, activation.py | Active |
| Setup DocTypes | email_digest, authorization_* | Active |
| Regional | us, australia, uae, italy, south_africa, turkey | Active |
| E-Commerce | shopping_cart/ | Deprecated |
| POS | selling/page/point_of_sale/, pos_invoice | Active |
| Integrations | plaid_settings | Active |
| Barcode | public/js/utils/barcode_scanner.js | Active |
| Portal | portal/utils.py | Active |
| Workflow | Frappe core | Core-based |
| Notifications | Frappe core | Core-based |

---

## 17. UltrERP Gaps (Comparison Notes)

Based on this analysis, UltrERP lacks:

1. **Bulk Transaction System**: No equivalent to ERPnext's bulk document conversion with retry mechanism
2. **Email Digest**: No scheduled summary emails for management
3. **POS System**: No POS page or POS Invoice doctype
4. **Plaid Integration**: No bank account aggregation
5. **Regional Features**: No country-specific tax compliance modules
6. **Barcode Scanner**: No dedicated barcode scanning utility (uses basic input only)
7. **Portal Auto-Party**: No automatic Customer/Supplier creation from portal users
8. **Authorization Rules**: No custom approval workflow rules beyond standard permissions
9. **Multi-UOM**: Item Barcode child table exists in ERPnext stock module

---

*Document generated from ERPnext v16 source analysis*
