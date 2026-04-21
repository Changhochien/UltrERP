# ERPnext UX Patterns - Comprehensive Research

## 1. Web Forms and Portal Pages

### 1.1 Web Template Locations
- **Main portal**: `erpnext/portal/` - Contains portal-specific doctypes
- **WWW pages**: `erpnext/www/` - Public-facing web pages
- **Templates**: `erpnext/templates/` - Shared Jinja2 templates

### 1.2 WWW Pages Found

#### Book Appointment Portal (`erpnext/www/book_appointment/`)
- **Technology**: Flask-like page with `frappe.whitelist` API methods
- **Files**:
  - `index.html` - Multi-step form (date/time selection → details form)
  - `index.py` - Backend API (`get_appointment_settings`, `get_appointment_slots`, `create_appointment`)
  - `index.js` - Client-side interactivity
  - `index.css` - Custom styling
- **UX Patterns**:
  - Multi-step wizard (date selection → timezone → timeslots → details)
  - Uses `frappe.call()` for async API calls
  - URL parameters pre-fill form fields (`?name=...&email=...`)
  - Timezone-aware slot display with moment.js
  - `frappe.show_alert()` for notifications
  - Success redirect after 5 seconds

#### Support Portal (`erpnext/www/support/index.html`)
- **Design**: Hero section with search bar, frequently-read articles, help article categories
- **Features**:
  - Full-width search input with keyboard shortcut hint
  - Article cards with category badges
  - Dropdown menu for search results
  - Uses `frappe.setup_search()` for knowledge base search

#### Shop by Category (`erpnext/www/shop-by-category/`)
- Product grid display

### 1.3 Portal Templates

#### `erpnext/templates/includes/macros.html`
Key macros:
- **`product_image_square()`** - Rounded product image with fallback
- **`product_image()`** - Standard product image with no-image fallback
- **`item_card()`** - Grid card for items (supports `is_featured` variant)
- **`wishlist_card()`** - Wishlist item with price, stock status, "Move to Cart" button
- **`ratings_summary()`** - Star ratings with progress bars
- **`field_filter_section()`** - Checkbox filter with search input for >20 values
- **`attribute_filter_section()`** - Attribute-based product filtering
- **`recommended_item_row()`** - Horizontal recommended item row

#### `erpnext/templates/includes/cart.css`
- Cart-specific styling
- Uses Bootstrap 4 utility classes

### 1.4 Shopping Cart Portal (`erpnext/shopping_cart/`)
- Complete e-commerce cart implementation
- Uses `erpnext.portal.utils.create_customer_or_supplier()` for auto-creating parties from session

### 1.5 Form Grid Templates (`erpnext/templates/form_grid/`)
- `item_grid.html` - Shows items with:
  - Visible column management (`row.get_visible_columns()`)
  - Color-coded warehouse stock indicators (green=in stock, red=not in stock)
  - Delivery status indicators for Sales/Purchase Orders
  - Inline discount percentage badges
  - Mobile-responsive hidden columns
- `stock_entry_grid.html`
- `material_request_grid.html`
- `bank_reconciliation_grid.html`

### 1.6 Portal Access Patterns
- `erpnext/portal/doctype/website_attribute/` - Attributes for website items
- `erpnext/portal/doctype/website_filter_field/` - Filter configurations for portal

---

## 2. Desk Page Layouts and Workspaces

### 2.1 Workspace Structure

**Location**: `erpnext/*/workspace/*/*.json`

**Example**: `erpnext/buying/workspace/buying/buying.json`

```json
{
  "doctype": "Workspace",
  "type": "Workspace",
  "label": "Buying",
  "icon": "buying",
  "charts": [{ "chart_name": "Purchase Order Trends", "label": "Purchase Order Trends" }],
  "number_cards": [
    { "number_card_name": "Purchase Orders Count" },
    { "number_card_name": "Total Purchase Amount" },
    { "number_card_name": "Average Order Values" }
  ],
  "content": "[...JSON blocks...]",
  "links": [
    { "type": "Card Break", "label": "Buying", "hidden": 0 },
    { "type": "Link", "link_to": "Purchase Order", "link_type": "DocType", "dependencies": "Item, Supplier", "onboard": 1 },
    { "type": "Link", "link_to": "Purchase Analytics", "link_type": "Report", "is_query_report": 1, "onboard": 1 },
    // ... more links
  ]
}
```

### 2.2 Workspace Content Block Types
From `content` JSON:
- **`chart`** - Dashboard chart (col: 4/6/12)
- **`number_card`** - KPI number card (col: 4)
- **`card`** - Card grouping links (col: 4)
- **`spacer`** - Spacing element (col: 12)
- **`header`** - Section header (H4 bold)

### 2.3 Dashboard Charts (`erpnext/*/dashboard_chart/`)

**Chart Types Found**:
- **Line charts** - Trend analysis (e.g., Purchase Order Trends)
- **Donut charts** - Composition (e.g., Pending vs Billed)
- **Bar charts** - Comparisons

**Chart Configuration** (`purchase_order_trends.json`):
```json
{
  "chart_type": "Report",
  "type": "Line",
  "use_report_chart": 1,
  "custom_options": "{\"type\": \"line\", \"axisOptions\": {\"shortenYAxisNumbers\": 1}, \"lineOptions\": {\"regionFill\": 1}}"
}
```

### 2.4 Number Cards (`erpnext/*/number_card/`)

**Example**: `total_incoming_bills.json`
```json
{
  "doctype": "Number Card",
  "type": "Document Type",
  "document_type": "Purchase Invoice",
  "function": "Sum",
  "aggregate_function_based_on": "base_net_total",
  "filters_json": "[[\"Purchase Invoice\",\"docstatus\",\"=\",\"1\"],[\"Purchase Invoice\",\"posting_date\",\"Timespan\",\"this year\"]]",
  "stats_time_interval": "Monthly",
  "show_percentage_stats": 1
}
```

**Number Card Types**:
- `Document Type` - Aggregate on a DocType field
- `Report` - From query report

### 2.5 Dashboard Doctype (`*_dashboard.py`)

**Example**: `purchase_order_dashboard.py`
```python
def get_data():
    return {
        "fieldname": "purchase_order",
        "internal_links": {
            "Material Request": ["items", "material_request"],
            "Supplier Quotation": ["items", "supplier_quotation"],
            "Project": ["items", "project"],
        },
        "transactions": [
            {"label": "Related", "items": ["Purchase Receipt", "Purchase Invoice", "Sales Order"]},
            {"label": "Payment", "items": ["Payment Entry", "Journal Entry", "Payment Request"]},
            {"label": "Reference", "items": ["Supplier Quotation", "Project", "Auto Repeat"]},
        ]
    }
```

---

## 3. Report Builder and Analytics

### 3.1 Reports Location
- Domain reports: `erpnext/buying/report/`, `erpnext/selling/report/`, etc.
- Report center: `erpnext/report_center/`

### 3.2 Built-in Reports

**Buying Reports**:
- `procurement_tracker` - Track procurement progress
- `purchase_analytics` - Analytics by various dimensions
- `supplier_quotation_comparison` - Compare supplier quotes
- `subcontracted_item_to_be_received` - Subcontracting tracking
- `requested_items_to_order_and_receive` - Items to order/receive
- `item_wise_purchase_history` - Historical purchase data
- `purchase_order_analysis` - PO status and billing
- `purchase_order_trends` - Trends over time
- `subcontract_order_summary` - Subcontracting summary

**Selling Reports**:
- `sales_analytics` - Multi-dimensional sales analytics
- `sales_partner_transaction_summary` - Partner commissions
- `sales_partner_target_variance_based_on_item_group` - Target tracking
- `available_stock_for_packing_items` - Stock availability
- `territory_target_variance_based_on_item_group` - Territory analysis
- `sales_order_analysis` - SO status and delivery

### 3.3 Report Structure

**Standard Report Pattern** (`purchase_order_analysis.py`):
```python
def execute(filters=None):
    validate_filters(filters)
    columns = get_columns(filters)
    data = get_data(filters)
    update_received_amount(data)
    data, chart_data = prepare_data(data, filters)
    return columns, data, None, chart_data
```

**Returns**: `(columns, data, None, chart_data)` - standard 4-element tuple

### 3.4 Sales Analytics (`sales_analytics.py`) - Advanced Example

**Tree Types Supported**:
- Customer
- Supplier
- Item
- Customer Group
- Supplier Group
- Territory
- Item Group
- Order Type
- Project

**Period Ranges**:
- Weekly
- Monthly
- Quarterly
- Half-Yearly
- Yearly

**Features**:
- Period-over-period comparison
- Value or Quantity toggle
- Group by hierarchies
- Chart type: Line
- Special `doc_type == "All"` aggregates all transaction types

### 3.5 Report Filters

Standard filter pattern:
```python
def validate_filters(filters):
    from_date, to_date = filters.get("from_date"), filters.get("to_date")
    if not from_date and to_date:
        frappe.throw(_("From and To Dates are required."))
    elif date_diff(to_date, from_date) < 0:
        frappe.throw(_("To Date cannot be before From Date."))
```

### 3.6 Dashboard Charts from Reports

Reports can be embedded in dashboards with:
```json
{
  "chart_type": "Report",
  "use_report_chart": 1,
  "report_name": "Purchase Order Trends"
}
```

---

## 4. Data Visualization

### 4.1 Chart Types

**Line Charts**:
- Trend analysis over time
- Options: `regionFill` for area fill
- `axisOptions.shortenYAxisNumbers` for compact display

**Donut Charts**:
- Composition analysis
- Height: 300px
- Example: Pending vs Billed amounts

**Bar Charts**:
- Comparative analysis

### 4.2 Analytics Page Structure

Standard analytics report returns:
```python
return self.columns, self.data, None, self.chart, None, skip_total_row
```

Where:
- `columns` - Column definitions with labels, fieldtypes, widths
- `data` - Row data
- `chart` - Chart config: `{"data": {"labels": [], "datasets": []}, "type": "line"}`
- `skip_total_row` - Hide total row for tree-view reports

### 4.3 Chart Data Format

```python
self.chart = {
    "data": {
        "labels": ["Jan", "Feb", "Mar", ...],
        "datasets": [
            {"name": "Customer A", "values": [100, 200, 150, ...]},
            {"name": "Customer B", "values": [80, 150, 200, ...]}
        ]
    },
    "type": "line",  # or "donut", "bar"
    "fieldtype": "Currency"  # or "Float"
}
```

---

## 5. Form Design Patterns

### 5.1 Quick Entry

**Location**: `erpnext/public/js/utils/*_quick_entry.js`

**Pattern**:
```javascript
frappe.provide("frappe.ui.form");
frappe.ui.form.CustomerQuickEntryForm = frappe.ui.form.ContactAddressQuickEntryForm;
```

**Quick Entry Flow**:
1. User clicks "Quick Add" button
2. Modal dialog opens with minimal required fields
3. On save, full form may open for additional details
4. Reuses `ContactAddressQuickEntryForm` base class

### 5.2 Section and Column Breaks

**From `supplier.json`**:
```json
"field_order": [
  "naming_series",
  "supplier_type",
  "supplier_name",
  "gender",
  "column_break0",  // Column break
  "supplier_group",
  "country",
  "is_transporter",
  // ... later
  "accounting_tab",
  "payment_terms",
  "default_accounts_section",
  "accounts",
  "column_break16",  // Another column break
  "companies"
]
```

### 5.3 Child Table Display

**From `item_grid.html`**:
```html
{% var visible_columns = row.get_visible_columns(["item_code", "qty", "rate", "amount",
    "stock_uom", "uom", "discount_percentage", "warehouse"]); %}

<div class="row">
    <div class="col-sm-6 col-xs-8">
        <!-- Item code with status indicators -->
        <span class="indicator {{ color }}">{{ doc.warehouse }}</span>
        <strong>{%= doc.item_code %}</strong>
    </div>
    <div class="col-sm-2 hidden-xs text-right">
        {%= doc.get_formatted("qty") %}
        <span class="small">{%= doc.uom || doc.stock_uom %}</span>
    </div>
    <!-- Rate, Amount columns -->
</div>
```

**Visible Columns Pattern**:
```javascript
var visible_columns = row.get_visible_columns(["item_code", "qty", "rate", "amount"]);
```

### 5.4 Sidebar Quick Stats

Dashboard doctypes define transactions that appear in the sidebar:
```python
"transactions": [
    {"label": "Related", "items": ["Purchase Receipt", "Purchase Invoice", "Sales Order"]},
    {"label": "Payment", "items": ["Payment Entry", "Journal Entry", "Payment Entry"]},
]
```

### 5.5 Auto-Fetch Patterns

Uses `frappe.call()` with `callback` for async data fetching:
```javascript
window.appointment_settings = (
    await frappe.call({
        method: "erpnext.www.book_appointment.index.get_appointment_settings",
    })
).message;
```

### 5.6 Form Grid Templates

**`templates/form_grid/includes/visible_cols.html`**:
```html
{% $.each(visible_columns || [], function(i, df) { %}
    {% var val = doc.get_formatted(df.fieldname); %}
    {% if((df.fieldname !== "description" && df.fieldname !== "item_name") && val) { %}
        <div class="row">
            <div class="col-xs-4 ellipsis">
                <strong>{%= __(df.label, null, df.parent) %}</strong>
            </div>
            <div class="col-xs-8">{%= doc.get_formatted(df.fieldname) %}</div>
        </div>
    {% } %}
{% }); %}
```

---

## 6. Navigation and Module Structure

### 6.1 Module Definition

**Location**: `erpnext/setup/doctype/`

Notably different from workspace - these are setup/config doctypes:
- `item_group/`
- `customer_group/`
- `supplier_group/`
- `territory/`
- `department/`
- `designation/`

### 6.2 Workspace Organization

**Per-module workspaces**:
- `buying/workspace/buying/` - Buying module
- `selling/workspace/selling/` - Selling module
- `accounts/workspace/financial_reports/` - Financial reports
- `stock/workspace/stock/` - Stock module
- `projects/workspace/projects/` - Projects
- `crm/workspace/crm/` - CRM
- `manufacturing/workspace/manufacturing/` - Manufacturing
- `support/workspace/support/` - Support

**Setup workspaces**:
- `setup/workspace/home/` - Home/Setup
- `setup/workspace/erpnext_settings/` - ERPnext settings

### 6.3 Workspace Structure

```json
{
  "parent_page": "Accounting",  // Nested under parent workspace
  "sequence_id": 5.0,           // Sort order
  "public": 1,                   // Public (shared) vs private
  "for_user": "",                // User-specific workspace
  "restrict_to_domain": "",       // Domain restriction
  "roles": [],                   // Role-based access
  "is_hidden": 0
}
```

### 6.4 Desktop Icons

**Location**: `erpnext/public/desktop_icons/*.svg`

Icons for:
- `accounting.svg`
- `buying.svg`
- `crm.svg`
- `stock.svg`
- `selling.svg`
- `projects.svg`
- `manufacturing.svg`
- `quality.svg`
- `support.svg`
- `asset.svg`
- `subcontracting.svg`
- `erpnext_settings.svg`
- `financials_reports.svg`

---

## 7. Print/Export

### 7.1 Print Format Templates

**Location**: `erpnext/templates/print_formats/`

**Include Templates**:
- `includes/items.html` - Item table with column visibility
- `includes/taxes.html` - Tax breakdown
- `includes/total.html` - Total row (label + formatted value)
- `includes/serial_and_batch_bundle.html` - Serial/batch info
- `includes/item_table_qty.html` - Qty columns
- `includes/item_table_description.html` - Description column

### 7.2 Print Format Structure

**`items.html`**:
```html
{%- set visible_columns = get_visible_columns(doc.get(df.fieldname), table_meta, df) -%}
<table class="table table-bordered table-condensed">
    <thead>
        <tr>
            <th style="width: 40px">Sr</th>
            {% for tdf in visible_columns %}
            <th style="width: {{ get_width(tdf) }}" class="{{ get_align_class(tdf) }}">
                {{ _(tdf.label) }}
            </th>
            {% endfor %}
        </tr>
    </thead>
    <tbody>
        {% for d in data %}
        <tr>
            <td>{{ d.idx }}</td>
            {% for tdf in visible_columns %}
            <td class="{{ get_align_class(tdf) }}">
                <div class="value">{{ print_value(tdf, d, doc, visible_columns) }}</div>
            </td>
            {% endfor %}
        </tr>
        {% endfor %}
    </tbody>
</table>
```

### 7.3 Print Formatting Functions

- `get_visible_columns()` - Determine which columns to show
- `get_width()` - Column width from field definition
- `get_align_class()` - Alignment (text-left/right/center)
- `print_value()` - Format value for print
- `fieldmeta()` - Field metadata attributes

### 7.4 Compact Print Mode

```html
{% if (data and not print_settings.compact_item_print) or tdf.fieldname in doc.flags.compact_item_fields %}
    <!-- Show full column header -->
{% endif %}

{% if not print_settings.compact_item_print or tdf.fieldname in doc.flags.compact_item_fields %}
    <!-- Show cell value -->
{% endif %}
```

### 7.5 PDF Generation

- Uses Frappe's standard print engine
- Print formats defined as HTML templates
- Supports custom print formats per DocType

---

## 8. List Views and Filtering

### 8.1 List Filter Patterns

From reports and doctypes:
- **Date range filters**: `from_date`, `to_date`
- **Status filters**: `status`, `docstatus`
- **Link filters**: `company`, `project`, `supplier`, `customer`
- **Tree filters**: Group-by patterns for Customer Group, Territory, Item Group

### 8.2 Group By Patterns

From `sales_analytics.py`:
```python
if self.filters.tree_type in ["Customer Group", "Supplier Group", "Territory"]:
    self.get_sales_transactions_based_on_customer_or_territory_group()
    self.get_rows_by_group()
```

### 8.3 Save Filter Features

Standard Frappe pattern - filters saved per user/workspace

---

## 9. Styling and CSS Patterns

### 9.1 Bootstrap 4 Base

Portal pages use Bootstrap 4 classes:
- `container`, `row`, `col-md-*`
- `form-control`, `btn`, `card`
- `mt-*`, `mb-*`, `p-*` (spacing)
- `text-muted`, `text-center`, `text-right`
- `d-flex`, `align-items-*`

### 9.2 Custom CSS Classes

**Cart CSS** (`cart.css`):
```css
.product-image { }
.card-img-container { }
.wishlist-card { }
.item-card { }
.product-title { }
.product-description { }
.product-price { }
.remove-wish { }
.rating-pill { }
```

### 9.3 Responsive Patterns

- `hidden-xs` - Hide on mobile
- `visible-xs` - Show only on mobile
- `col-sm-*`, `col-md-*`, `col-lg-*` - Responsive columns

---

## 10. Key Frappe UI Patterns

### 10.1 JavaScript API

```javascript
// Async call
frappe.call({
    method: "module.path.function",
    args: { key: value },
    callback: function(response) {
        // Handle response.message
    }
});

// Show alert
frappe.show_alert(__("Operation successful"));

// Throw error
frappe.throw(__("Error message"));

// Format value
doc.get_formatted("fieldname")

// Check permission
frappe.perm.is_visible("fieldname", doc, frm.perm)
```

### 10.2 Jinja2 Template Patterns

```jinja2
{% extends "templates/web.html" %}
{% block title %}{{ _("Page Title") }}{% endblock %}
{% block page_content %}
    <div class="container">{{ content }}</div>
{% endblock %}
{% block script %}
<script>frappe.ready(() => { ... });</script>
{% endblock %}
```

### 10.3 Translation

```jinja2
{{ _("String to translate") }}
```

### 10.4 URL Generation

```jinja2
{{ frappe.utils.quoted(value) | abs_url }}
```

---

## 11. Portal Access Control

### 11.1 Session-Based Role Detection

`erpnext/portal/utils.py`:
```python
def create_customer_or_supplier():
    """Based on the default Role (Customer, Supplier), create a Customer / Supplier."""
    user = frappe.session.user
    if frappe.db.get_value("User", user, "user_type") != "Website User":
        return

    user_roles = frappe.get_roles()
    portal_settings = frappe.get_single("Portal Settings")
    default_role = portal_settings.default_role
```

### 11.2 Auto Role Assignment

```python
def set_default_role(doc, method):
    """Set customer, supplier, student, guardian based on email."""
    contact_name = frappe.get_value("Contact", dict(email_id=doc.email))
    if contact_name:
        contact = frappe.get_doc("Contact", contact_name)
        for link in contact.links:
            if link.link_doctype == "Customer" and "Customer" not in roles:
                doc.add_roles("Customer")
```

---

## 12. Summary of Key UX Patterns

### 12.1 Web Forms (Portal)
- Multi-step wizards for complex flows
- URL parameter pre-filling
- Timezone-aware date/time handling
- Bootstrap 4 responsive design
- `frappe.call()` async API pattern

### 12.2 Workspace/Dashboard
- JSON-based workspace configuration
- Drag-and-drop block arrangement
- Number cards for KPIs
- Chart widgets (Line, Donut, Bar)
- Card groupings for related links
- Public/shared workspaces

### 12.3 Reports
- Standard 4-tuple return: `(columns, data, None, chart)`
- Tree-view hierarchy support
- Period range filters (Weekly/Monthly/Quarterly/Yearly)
- Group-by dimensions (Customer/Supplier/Item/Group/Territory/Project)
- Chart integration

### 12.4 Forms
- Quick Entry modal pattern
- Section/Column breaks for layout
- Child table grid display with visible columns
- Auto-fetch from linked docs
- Sidebar quick stats from dashboard doctype

### 12.5 Print
- HTML template-based print formats
- Compact vs full mode
- Include templates for reusable parts
- Column visibility control

### 12.6 Navigation
- Module-based workspace organization
- Role-based workspace access
- Desktop icon shortcuts
- Parent-child workspace nesting
