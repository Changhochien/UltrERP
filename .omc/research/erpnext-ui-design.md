# ERPnext UI/UX Components and Design Patterns Research

**Date:** 2026-04-20  
**Focus:** ERPnext Frontend Architecture, UI Components, and Design Patterns  
**Reference:** `/reference/erpnext-develop/`

---

## 1. UI Framework and Architecture

### 1.1 Framework Stack
ERPnext uses a **server-side rendered Jinja2 template system** with vanilla JavaScript for interactivity. The frontend is not a modern SPA framework but rather:

- **Templates:** Jinja2 HTML templates (`.html`) for all pages
- **JavaScript:** Vanilla JavaScript with jQuery-like patterns, bundled as `.bundle.js` files
- **CSS:** Bootstrap 4.x with custom overrides, Sass/SCSS for theming
- **No React/Vue/Angular** in the main ERPnext codebase (unlike modern stacks)
- **Frappe Framework** provides the underlying form/view rendering engine

### 1.2 Directory Structure for Frontend Code
```
erpnext/
├── public/js/                    # Main JavaScript files
│   ├── controllers/              # Shared controller logic
│   │   ├── transaction.js       # Sales/Purchase transaction base
│   │   ├── accounts.js          # Accounting-specific logic
│   │   ├── taxes_and_totals.js  # Tax calculations
│   │   ├── buying.js            # Purchase-specific logic
│   │   └── stock_controller.js  # Stock transaction logic
│   ├── utils/                   # Utility functions
│   │   ├── sales_common.js      # Sales utilities
│   │   ├── party.js             # Customer/Supplier logic
│   │   └── item_selector.js     # Item selection component
│   ├── templates/              # HTML template snippets
│   └── *.bundle.js              # Bundled components (POS, BOM, etc.)
├── templates/                   # Jinja2 page templates
│   ├── pages/                   # Full page templates
│   ├── includes/                # Reusable includes
│   └── print_formats/           # Print output templates
├── www/                         # Public-facing pages (portal)
│   ├── book_appointment/        # Appointment booking
│   └── support/                 # Support portal
├── page_templates/              # (not found in this repo)
└── web_template/                # (not found in this repo)
```

### 1.3 Key JavaScript Bundles
- `erpnext.bundle.js` - Core ERPnext functionality
- `point-of-sale.bundle.js` - POS interface
- `bom_configurator.bundle.js` - Bill of Materials configurator
- `item-dashboard.bundle.js` - Item dashboard widget
- `bank-reconciliation-tool.bundle.js` - Bank reconciliation

---

## 2. Form Components

### 2.1 Form Field Rendering
Forms are rendered server-side by Frappe framework. Fields are defined in DocType JSON schemas. The client-side JavaScript (`frappe.ui.form`) handles:
- Field validation
- Conditional display
- Dynamic updates
- Child table management

### 2.2 Field Types Observed
Based on code analysis:
- `Link` - Autocomplete links to other documents
- `Currency` - Money fields with currency symbol
- `Date` / `Datetime` - Date pickers
- `Select` - Dropdown select
- `Check` - Boolean checkboxes
- `Text` / `Small Text` - Text inputs
- `Int` / `Float` - Number inputs
- `Link` - Searchable dropdown with type-ahead
- `Dynamic Link` - Conditional linking
- `Table` - Child table (grid of repeatable items)
- `Attach` / `Attach Image` - File uploads

### 2.3 Child Tables (Grid/Table Component)
The `templates/form_grid/item_grid.html` shows the child table structure:

```html
<!-- Uses Bootstrap table classes -->
<table class="table table-bordered table-condensed">
    <thead>
        <tr>
            <th style="width: 40px" class="table-sr">Sr</th>
            <!-- Dynamic columns based on visible_fields -->
        </tr>
    </thead>
    <tbody>
        <!-- Rows rendered via Jinja2 loop -->
    </tbody>
</table>
```

Features:
- Row numbering (Sr column)
- Column visibility control (`get_visible_columns()`)
- Inline editing support
- Stock indicators (green/orange/red based on qty)
- Warehouse color coding with indicators
- Responsive hidden columns for mobile (`hidden-xs`, `hidden-sm`)

### 2.4 Item Selector Component
Located in `erpnext/public/js/utils/item_selector.js` and POS selector:
- Grid of items with images
- Search/filter functionality
- Quantity available badges
- Quick add to cart
- Barcode scanning support (via `onscan.js`)

### 2.5 File Upload
Standard HTML file inputs with Frappe's `Attach` field type. Custom handling in specific doctypes for:
- Image uploads with preview
- Document attachments
- Drag-and-drop support (in newer versions)

---

## 3. Layout Patterns

### 3.1 Page Structure
All pages extend `templates/web.html` base template with blocks:
```jinja2
{% block breadcrumbs %}...{% endblock %}
{% block title %}...{% endblock %}
{% block header %}...{% endblock %}
{% block header_actions %}...{% endblock %}
{% block page_content %}...{% endblock %}
{% block script %}...{% endblock %}
{% block style %}...{% endblock %}
```

### 3.2 Bootstrap Grid System
ERPnext heavily uses Bootstrap 4.x grid:
- `.row` and `.col-*` classes
- Responsive breakpoints: `col-xs-*`, `col-sm-*`, `col-lg-*`
- Flexbox utilities: `d-flex`, `align-items-center`
- Spacing utilities: `m-0`, `mt-1`, `p-0`, `mb-2`

### 3.3 Section and Column Layout
From print templates and forms:
```html
<div class="row section-break">
    <div class="col-xs-6">Left column</div>
    <div class="col-xs-3"></div> <!-- Spacer -->
    <div class="col-xs-3">Right column</div>
</div>
```

### 3.4 Cards and Dashboard Widgets
From workspace JSON files and CSS:
```html
<div class="card card-md h-100 kb-card">
    <div class="card-body">
        <h6 class="card-subtitle">Category</h6>
        <h3 class="card-title">Title</h3>
        <p class="card-text">Content</p>
    </div>
    <a href="#" class="stretched-link"></a>
</div>
```

Cards use:
- Bootstrap card classes
- `card-md` custom size variant
- `h-100` for equal heights
- `stretched-link` for full-card click targets

### 3.5 Modals/Dialogs
Frappe provides `frappe.ui.dialog` and `frappe.msgprint`:
```javascript
frappe.msgprint(__("Error message"));
frappe.confirm(__("Are you sure?"), () => { /* action */ });
```

Custom dialogs created via:
```javascript
let d = new frappe.ui.Dialog({
    title: "Title",
    fields: [{ fieldtype: "Data", label: "Name", fieldname: "name" }],
    primary_action: function() { /* submit */ }
});
```

### 3.6 Sidebar Navigation
Workspace-based navigation with JSON configuration:
```json
{
    "label": "Selling",
    "icon": "fa fa-sales",
    "items": [
        { "type": "doctype", "name": "Quotation", "label": "Quotations" },
        { "type": "report", "name": "sales_order_analysis", "label": "Sales Analytics" }
    ]
}
```

---

## 4. Data Table / List View

### 4.1 List View Rendering
List views are rendered by Frappe's `frappe.listview` module (not in this codebase - part of frappe-framework). The ERPnext doctype JSON files define list view settings.

### 4.2 Sortable/Filterable Features
- Defined via DocType `fields` with `in_list_view: 1`
- Quick search via search box
- Column sorting (click header)
- Pagination with page length options

### 4.3 Bulk Actions
Standard Frappe list view with:
- Checkbox selection
- Bulk rename/delete/submit
- Custom bulk actions defined in doctype

### 4.4 Report Tables
Reports use custom HTML templates with:
```html
<table class="table table-bordered table-condensed">
    <!-- Standard Bootstrap table styling -->
</table>
```

From `erpnext/templates/print_formats/includes/items.html`:
```jinja2
<table class="table table-bordered table-condensed mb-0" style="width: 100%;">
    <thead>
        <tr>
            <th class="text-uppercase" style="text-align:center">Sr</th>
            <th class="text-uppercase">Details</th>
            <!-- More columns -->
        </tr>
    </thead>
    <tbody>
        {% for item in doc.items %}
        <tr>
            <td style="text-align:center">{{ loop.index }}</td>
            <td>{{ item.item_code }}: {{ item.item_name }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
```

---

## 5. Print Templates and Report Layouts

### 5.1 Print Format Structure
Print templates are Jinja2 HTML files in `erpnext/templates/print_formats/`. Example from `sales_invoice_print.html`:

```jinja2
{% macro add_header(...) %}
    <div class="letter-head">{{ letter_head }}</div>
{% endmacro %}

<!-- Page breaks for multi-page printing -->
{% for page in layout %}
<div class="page-break">
    <!-- Header -->
    <div id="header-html" class="hidden-pdf">{{ add_header(...) }}</div>
    
    <!-- Content with Bootstrap grid -->
    <div class="row section-break">
        <div class="col-xs-6">Customer info</div>
        <div class="col-xs-3"></div>
        <div class="col-xs-3">Invoice details</div>
    </div>
    
    <!-- Item table -->
    <table class="table table-bordered table-condensed">
        <!-- ... -->
    </table>
    
    <!-- Footer -->
    <div id="footer-html" class="visible-pdf">
        <p class="text-center small page-number">
            Page <span class="page"></span> of <span class="topage"></span>
        </p>
    </div>
</div>
{% endfor %}
```

### 5.2 Print Styles
Inline `<style>` tags in print templates:
```html
<style>
    .print-format label {
        color: #74808b;
        font-size: 12px;
        margin-bottom: 4px;
    }
    .taxes-section .order-taxes.mt-5 {
        margin-top: 0px !important;
    }
</style>
```

### 5.3 Tax Templates
`erpnext/templates/print_formats/includes/taxes.html` renders tax breakdown:
```jinja2
{% for d in doc.taxes %}
    {% if d.tax_amount %}
    <div class="row">
        <div class="col-xs-8"><div>{{ _(d.description) }}</div></div>
        <div class="col-xs-4" style="text-align: right;">{{ d.get_formatted("tax_amount") }}</div>
    </div>
    {% endif %}
{% endfor %}
```

---

## 6. Responsive Design

### 6.1 Mobile-Friendly Patterns
Bootstrap responsive classes throughout:
- `col-xs-*` - Extra small screens (<768px)
- `col-sm-*` - Small screens (>=768px)
- `hidden-xs` - Hide on mobile
- `visible-xs` - Show only on mobile

From `order.html`:
```html
<span class="d-s-n col-3">  <!-- d-s-n = display small only -->
    {{ _("Quantity") }}
</span>
<span class="d-l-n order-qty">  <!-- d-l-n = display large only -->
    {{ _("Qty ") }}({{ d.get_formatted("qty") }})
</span>
```

### 6.2 Mobile-Specific Views
- POS interface is mobile-responsive
- Order portal pages use responsive grids
- Some pages have simplified mobile views

---

## 7. Animations and Interactions

### 7.1 Loading States
From POS ItemSelector:
```javascript
start_item_loading_animation();
// ... async operations ...
stop_item_loading_animation();
```

Items not found states:
```javascript
this.$items_container.removeClass(this.item_display_class);
this.$items_container.addClass("items-not-found");
```

### 7.2 Form Validation Feedback
```javascript
frappe.validated = false;
frappe.throw(__("Error message"));
frappe.msgprint(__("Validation message"));
```

### 7.3 Page Transitions
No explicit page transition animations - standard HTTP navigation with:
- Form submission with loading indicator
- AJAX calls with `frappe.dom.wait_for_image_load()`
- Skeleton loading states in newer versions

---

## 8. Theming

### 8.1 CSS Variables
Limited use of CSS custom properties. Primary color referenced:
```css
.time-slot.selected {
    color: white;
    background: var(--primary-color);
}
```

### 8.2 Color Scheme
Bootstrap-based with custom overrides:
- **Primary:** Blue tones (`#007bff` or custom)
- **Success:** Green (`#28a745`)
- **Warning:** Orange (`#ffc107`)
- **Danger:** Red (`#dc3545`)
- **Muted:** Gray (`#6c7680`, `#74808b`)

### 8.3 Typography
- System fonts via Bootstrap defaults
- Font sizes: 12px (small), 14px (base), 16px (lg)
- Custom utility classes: `.font-md`, `.text-uppercase`
- Icon fonts (Lucide/Feather in newer versions)

### 8.4 Spacing System
Bootstrap spacing utilities:
- `m-0`, `mt-1`, `mb-2`, `p-0`, `px-3`
- Custom: `.section-break`, `.page-container`

---

## 9. Iconography

### 9.1 Icon Libraries
- **Feather Icons** (in newer versions via CDN)
- **Font Awesome** (older versions)
- Custom CSS icons in some areas

### 9.2 Icon Usage Patterns
From `support/index.html`:
```html
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"
    fill="none" stroke="currentColor" stroke-width="2" 
    stroke-linecap="round" stroke-linejoin="round" class="feather feather-search">
    <circle cx="11" cy="11" r="8"></circle>
    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
</svg>
```

### 9.3 Indicator Icons
Status indicators use color-coded spans:
```html
<span class="indicator-pill whitespace-nowrap green">In Stock</span>
<span class="indicator-pill whitespace-nowrap orange">Low Stock</span>
<span class="indicator-pill whitespace-nowrap red">Out of Stock</span>
```

---

## 10. UX Micro-Patterns

### 10.1 Quick Entry (Type-ahead Create)
Not fully in this codebase (handled by Frappe), but referenced in utility files:
- `item_quick_entry.html` - Quick item creation
- `customer_quick_entry.js` - Quick customer creation
- `supplier_quick_entry.js` - Quick supplier creation

### 10.2 Auto-Save / Drafts
ERPnext automatically saves drafts:
```javascript
frappe.auto_save = true;  // In form setup
```

### 10.3 Dirty Form Detection
Handled by `frappe.ui.form`:
- Prompt before leaving unsaved forms
- `frm.dirty()` to check modified state
- `frm.save()` to save

### 10.4 Undo/Redo
Limited undo capability - relies on server-side audit trail.

### 10.5 Keyboard Shortcuts
From POS component:
```javascript
attach_shortcuts() {
    // Custom keyboard handlers for POS
}
```

Standard Frappe shortcuts:
- `Ctrl+S` - Save
- `Ctrl+Enter` - Submit
- `Esc` - Cancel/Clear

### 10.6 Optimistic UI Updates
Used in POS:
```javascript
// Update UI immediately
render_item_list(items);
// Then sync with server
```

### 10.7 Dashboard Indicators
From `erpnext/utils.js`:
```javascript
frm.dashboard.add_indicator(
    __("Annual Billing: {0}", [format_currency(...)]),
    "blue"
);
frm.dashboard.add_indicator(
    __("Total Unpaid: {0}", [...]),
    company_wise_info[0].total_unpaid ? "orange" : "green"
);
```

---

## 11. Special Interfaces

### 11.1 Point of Sale (POS)
Located in `erpnext/selling/page/point_of_sale/`:

**Components:**
- `pos_item_selector.js` - Item grid with search, filters, images
- `pos_item_cart.js` - Shopping cart component
- `pos_payment.js` - Payment handling
- `pos_past_order_summary.js` - Order history

**Features:**
- Barcode scanning (`onscan.js`)
- Item group filtering
- Real-time inventory indicators (green/orange/red)
- Quick search
- Cart item editing

**DOM Structure:**
```html
<section class="items-selector">
    <div class="filter-section">
        <div class="label">All Items</div>
        <div class="search-field"></div>
        <div class="item-group-field"></div>
    </div>
    <div class="items-container"></div>
</section>
```

### 11.2 Shopping Cart / Customer Portal
From `templates/pages/order.html` and `templates/includes/cart.css`:

```html
<div class="order-items order-item-header mb-1 row text-muted">
    <span class="col-5">{{ _("Item") }}</span>
    <span class="d-s-n col-3">{{ _("Quantity") }}</span>
    <span class="col-2 pl-10">{{ _("Rate") }}</span>
    <span class="col-2 text-right">{{ _("Amount") }}</span>
</div>
```

Features:
- Product images with fallback (abbr if no image)
- Quantity and rate display
- Tax breakdown
- Payment button integration
- Print action
- Dropdown actions menu

### 11.3 Support Portal
From `www/support/index.html`:

```html
<section class="section section-padding-top section-padding-bottom">
    <div class='container'>
        <div class="hero-content">
            <h1 class="hero-title">{{ greeting_title }}</h1>
        </div>
        <div class="search-container">
            <div class="website-search" id="search-container">
                <input type="search" class="form-control" placeholder="Search..." />
            </div>
        </div>
    </div>
</section>
```

### 11.4 Appointment Booking
From `www/book_appointment/`:
- Date/time slot selection
- Customer form
- Available/unavailable slot indicators
- Responsive design

---

## 12. Key Design Patterns Summary

| Pattern | Implementation |
|---------|---------------|
| **Grid System** | Bootstrap 4 `.row` + `.col-*` |
| **Cards** | `.card`, `.card-body`, `.card-md` |
| **Tables** | `.table.table-bordered.table-condensed` |
| **Forms** | Server-rendered by Frappe, client JS validation |
| **Buttons** | `.btn.btn-primary`, `.btn.btn-secondary`, `.btn.btn-sm` |
| **Indicators** | `.indicator`, `.indicator-pill`, `.indicator-*` (color) |
| **Alerts** | `frappe.msgprint()`, `frappe.throw()` |
| **Modals** | `frappe.ui.Dialog`, Bootstrap modals |
| **Navigation** | Workspace JSON config + sidebar |
| **Theming** | CSS overrides + Bootstrap variables |
| **Icons** | Lucide/Feather SVG icons |
| **Print** | Jinja2 templates with inline styles |

---

## 13. Comparison with UltrERP

**Framework:**
- ERPnext: Jinja2 + Vanilla JS + Bootstrap 4
- UltrERP: React 19 + Vite + Tailwind CSS v4 + Radix UI

**Key Differences:**
1. ERPnext uses server-rendered templates; UltrERP uses client-side React
2. ERPnext has no component library; UltrERP uses Radix UI primitives
3. ERPnext styling is Bootstrap + custom CSS; UltrERP uses Tailwind CSS
4. Form handling in ERPnext is Frappe-based; UltrERP uses React Hook Form
5. Tables in ERPnext are HTML; UltrERP uses TanStack Table
6. Charts in ERPnext are Visx/Recharts; ERPnext has no modern charting

---

*Research compiled from ERPnext v15+ codebase at `/reference/erpnext-develop/`*
