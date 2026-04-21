# ERPnext CRM & Sales Module - Detailed Research

## Table of Contents
1. [CRM Module](#crm-module)
2. [Selling Module](#selling-module)
3. [Shared Controllers](#shared-controllers)
4. [Integration Patterns](#integration-patterns)

---

## CRM Module

### Directory: `erpnext/crm/doctype/`

| Doctype | Purpose |
|---------|---------|
| Lead | Initial prospect contact |
| Opportunity | Potential sales deal |
| Quotation | (also in Selling) |
| CRM Note | Notes attached to CRM docs |
| CRM Settings | Single-doc settings |
| Prospect | Company-level prospect tracking |
| Campaign | Marketing campaigns |
| Contract | Service contracts |
| Appointment | Booking/scheduling |
| SMS Center | SMS sending configuration |
| Sales Stage | Pipeline stages |
| Opportunity Type | Types of opportunities |
| Market Segment | Segmentation |
| Industry Type | Industry classification |
| Competitor | Competitor tracking |

---

## 1. Lead

**File:** `erpnext/crm/doctype/lead/lead.json`

### Fields

| Field | Type | Label | Options / Notes |
|-------|------|-------|----------------|
| naming_series | Select | Series | `CRM-LEAD-.YYYY.-` |
| lead_name | Data | Full Name | read_only, computed |
| first_name | Data | First Name | mandatory if no company_name |
| middle_name | Data | Middle Name | |
| last_name | Data | Last Name | |
| salutation | Link | Salutation | options: Salutation |
| gender | Link | Gender | options: Gender |
| company_name | Data | Organization Name | in_list_view, mandatory if no first_name |
| email_id | Data | Email | options: Email |
| mobile_no | Data | Mobile No | options: Phone |
| phone | Data | Phone | options: Phone |
| phone_ext | Data | Phone Ext. | |
| whatsapp_no | Data | WhatsApp | options: Phone |
| fax | Data | Fax | |
| website | Data | Website | |
| lead_owner | Link | Lead Owner | default: `__user`, options: User |
| status | Select | Status | **Lead, Open, Replied, Opportunity, Quotation, Lost Quotation, Interested, Converted, Do Not Contact** |
| type | Select | Lead Type | options: (blank), Client, Channel Partner, Consultant |
| request_type | Select | Request Type | (blank), Product Enquiry, Request for Information, Suggestions, Other |
| market_segment | Link | Market Segment | options: Market Segment |
| industry | Link | Industry | options: Industry Type |
| annual_revenue | Currency | Annual Revenue | |
| no_of_employees | Select | No of Employees | 1-10, 11-50, 51-200, 201-500, 501-1000, 1000+ |
| territory | Link | Territory | options: Territory, in_list_view |
| qualification_status | Select | Qualification Status | Unqualified, In Process, Qualified |
| qualified_by | Link | Qualified By | options: User |
| qualified_on | Date | Qualified on | |
| company | Link | Company | options: Company |
| customer | Link | From Customer | shown if source=='Existing Customer' |
| image | Attach Image | Image | hidden |
| language | Link | Print Language | options: Language |
| title | Data | Title | hidden, read_only |
| disabled | Check | Disabled | default: 0 |
| unsubscribed | Check | Unsubscribed | default: 0 |
| blog_subscriber | Check | Blog Subscriber | default: 0 |
| notes | Table | Notes | options: CRM Note |
| utm_source | Link | Source | options: UTM Source |
| utm_medium | Link | Medium | options: UTM Medium |
| utm_campaign | Link | Campaign | options: UTM Campaign |
| utm_content | Data | Content | |
| city | Data | City | |
| state | Data | State/Province | |
| country | Link | Country | options: Country |

### State Machine

Lead statuses: `Lead` (default) → `Open` → `Replied` → `Opportunity` → `Quotation` → `Converted`
Alternative: `Lead` → `Lost Quotation`, `Interested`, `Do Not Contact`

### Permissions

| Role | Permlevel | Create | Read | Write | Delete | Email | Print | Report | Import | Export | Share |
|------|-----------|--------|------|-------|--------|-------|-------|--------|--------|-------|-------|
| Sales User | 0 | Yes | Yes | Yes | No | Yes | Yes | Yes | No | No | Yes |
| Sales Manager | 0 | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| System Manager | 0 | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Desk User | 1 | No | Yes | No | No | No | No | Yes | No | No | No |
| Sales Manager | 1 | No | Yes | No | No | No | No | Yes | No | No | No |
| Sales User | 1 | No | Yes | No | No | No | No | Yes | No | No | No |

### Key Controller Logic (`lead.py`)

- **onload:** Sets `is_customer` flag if lead has been converted; loads address/contact; fetches linked prospects
- **before_insert:** Auto-creates Contact if `auto_creation_of_contact` is enabled in CRM Settings
- **after_insert:** Links to contact
- **on_trash:** Clears lead field in Issues, deletes contact/address links, removes from prospects
- **validate:** Sets full_name, lead_name, title, status; checks email uniqueness (unless duplication allowed)
- **on_update:** Updates linked prospects
- **set_lead_name:** If no first/last name, uses company_name; if neither, uses email prefix

### Whitelist Methods

- `make_customer` / `_make_customer` - Converts lead to customer via get_mapped_doc
- `make_opportunity` - Creates opportunity from lead
- `make_quotation` - Creates quotation from lead
- `get_lead_details` - Returns party details + tax info
- `make_lead_from_communication` - Creates lead from email
- `add_lead_to_prospect` - Links lead to prospect

---

## 2. Opportunity

**File:** `erpnext/crm/doctype/opportunity/opportunity.json`

### Fields

| Field | Type | Label | Key Notes |
|-------|------|-------|-----------|
| naming_series | Select | Series | `CRM-OPP-.YYYY.-` |
| opportunity_from | Link | Opportunity From | **reqd**, options: DocType |
| party_name | Dynamic Link | Party | reqd, dynamically points to Customer/Lead/Prospect |
| customer_name | Data | Customer Name | hidden, read_only |
| title | Data | Title | hidden |
| opportunity_type | Link | Opportunity Type | options: Opportunity Type |
| status | Select | Status | **Open, Quotation, Converted, Lost, Replied, Closed** |
| opportunity_owner | Link | Opportunity Owner | options: User |
| sales_stage | Link | Sales Stage | default: Prospecting, options: Sales Stage |
| probability | Percent | Probability (%) | default: 100 |
| expected_closing | Date | Expected Closing Date | |
| currency | Link | Currency | options: Currency |
| opportunity_amount | Currency | Opportunity Amount | |
| conversion_rate | Float | Exchange Rate | |
| base_opportunity_amount | Currency | Company Currency | read_only |
| transaction_date | Date | Opportunity Date | default: Today, reqd |
| company | Link | Company | reqd |
| items | Table | Items | options: Opportunity Item |
| contact_person | Link | Contact Person | options: Contact |
| contact_email | Data | Contact Email | options: Email |
| contact_mobile | Data | Contact Mobile | options: Phone |
| job_title | Data | Job Title | |
| customer_address | Link | Customer / Lead Address | options: Address |
| address_display | Text Editor | Address | read_only |
| territory | Link | Territory | options: Territory |
| customer_group | Link | Customer Group | shown if opportunity_from==Customer |
| industry | Link | Industry | options: Industry Type |
| market_segment | Link | Market Segment | options: Market Segment |
| website | Data | Website | |
| lost_reasons | Table MultiSelect | Lost Reasons | shown if status==Lost, options: Opportunity Lost Reason Detail |
| order_lost_reason | Small Text | Detailed Reason | read_only, shown if status==Lost |
| competitors | Table MultiSelect | Competitors | read_only, shown if status==Lost |
| first_response_time | Duration | First Response Time | read_only |
| amended_from | Link | Amended From | options: Opportunity |
| notes | Table | Notes | options: CRM Note |
| utm_source | Link | Source | options: UTM Source |
| utm_medium | Link | Medium | options: UTM Medium |
| utm_campaign | Link | Campaign | options: UTM Campaign |
| utm_content | Data | Content | |

### State Machine

Opportunity statuses: `Open` → `Quotation` → `Converted`
Alternative: `Open` → `Replied` → `Closed` (auto-closed after N days per CRM Settings)
Alternative: `Open` → `Lost`

### Permissions

| Role | Create | Read | Write | Delete | Email | Print | Report | Import | Export | Share | Submit |
|------|--------|------|-------|--------|-------|-------|--------|--------|-------|-------|--------|-------|
| Sales User | Yes | Yes | Yes | Yes | Yes | Yes | Yes | No | No | Yes | No |
| Sales Manager | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | No |

### Key Controller Logic (`opportunity.py`)

- **onload:** Loads address/contact for the referenced party (Lead/Customer/Prospect)
- **after_insert:** Updates Lead status, links open tasks/events, carries forward communications
- **validate:** Sets opportunity_type (default: Sales), validates items, validates UOM/qty integers, sets exchange rate, calculates totals
- **on_update:** Updates linked Prospect with opportunity values
- **declare_enquiry_lost:** Sets status to Lost with reasons and competitors (blocked if active quotation exists)
- **make_quotation:** Maps to Quotation, copies items, sets taxes
- **make_customer:** Maps to Customer
- **make_request_for_quotation:** Maps to RFQ
- **make_supplier_quotation:** Maps to Supplier Quotation

### Auto-close Logic

Daily cron job `auto_close_opportunity` sets status=`Closed` for opportunities where `status=Replied` and modified > N days (default 15, configurable in CRM Settings).

---

## 3. CRM Settings

**File:** `erpnext/crm/doctype/crm_settings/crm_settings.json` (Single Doc)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| campaign_naming_by | Select | Campaign Name/Naming Series | |
| allow_lead_duplication_based_on_emails | Check | 0 | Allow duplicate leads with same email |
| auto_creation_of_contact | Check | 1 | Auto-create contact when lead is created |
| close_opportunity_after_days | Int | 15 | Days before auto-closing replied opportunities |
| default_valid_till | Data | (blank) | Default quotation validity in days |
| carry_forward_communication_and_comments | Check | 0 | Copy communications from Lead→Opportunity→Quotation |
| update_timestamp_on_new_communication | Check | 0 | Update modified timestamp on new communication |

**Accessible by:** System Manager, Sales Manager, Sales Master Manager

---

## 4. Prospect

**File:** `erpnext/crm/doctype/prospect/prospect.json`

Represents a company-level prospect that can contain multiple leads and opportunities.

| Field | Type | Key Notes |
|-------|------|-----------|
| company_name | Data | |
| no_of_employees | Select | 1-10 through 1000+ |
| market_segment | Link | options: Market Segment |
| industry | Link | options: Industry Type |
| annual_revenue | Currency | |
| prospect_owner | Link | User |
| company | Link | Company |
| territory | Link | Territory |
| leads | Table | Prospect Lead (lead, lead_name, email, mobile_no, lead_owner, status) |
| opportunities | Table | Prospect Opportunity (opportunity, amount, stage, deal_owner, probability, expected_closing, currency, contact_person) |
| notes | Table | CRM Note |

---

## 5. Contract

**File:** `erpnext/crm/doctype/contract/contract.json`

Service contract doctype.

| Field | Type | Key Notes |
|-------|------|-----------|
| contract_type | Link | Contract Type |
| party_type | Select | Customer/Supplier |
| party_name | Dynamic Link | |
| contract_status | Select | Draft, Active, Inactive, Terminated |
| start_date | Date | |
| end_date | Date | |
| fulfilled_by | Link | Contract Fulfilment CheckTemplate |
| fulfilment_terms | Table | Contract Fulfilment Terms |
| contract_details | Text Editor | |

---

## Selling Module

### Directory: `erpnext/selling/doctype/`

| Doctype | Purpose |
|---------|---------|
| Customer | Buyer of goods/services |
| Customer Group | Classification grouping |
| Territory | Geographic region |
| Sales Partner | Channel partners who earn commission |
| Sales Team | Sales person allocation table |
| Commission Rate | Partner commission structure |
| Quotation | Sales/price quotation |
| Sales Order | Customer purchase order |
| Delivery Note | Goods delivery record |
| Sales Invoice | Billing document |
| Product Bundle | Kit/combination item |
| Installation Note | Post-delivery installation |
| Selling Settings | Single-doc configuration |

---

## 6. Customer

**File:** `erpnext/selling/doctype/customer/customer.json`

### Fields

| Field | Type | Label | Key Notes |
|-------|------|-------|-----------|
| naming_series | Select | Series | `CUST-.YYYY.-` |
| customer_name | Data | Customer Name | reqd, in_global_search |
| customer_type | Select | Customer Type | **Company, Individual, Partnership**, reqd, default: Company |
| gender | Link | Gender | shown if type==Individual |
| image | Attach Image | Image | hidden |
| customer_group | Link | Customer Group | in_list_view, reqd, link_filter: is_group=0 |
| territory | Link | Territory | in_list_view |
| default_currency | Link | Billing Currency | in_list_view |
| default_price_list | Link | Default Price List | options: Price List |
| account_manager | Link | Account Manager | options: User |
| lead_name | Link | Lead | no_copy, read_only |
| opportunity_name | Link | Opportunity | no_copy, read_only |
| prospect_name | Link | Prospect | no_copy, read_only |
| website | Data | Website | |
| language | Link | Print Language | options: Language |
| tax_id | Data | Tax ID | |
| tax_category | Link | Tax Category | options: Tax Category |
| tax_withholding_category | Link | Tax Withholding Category | |
| tax_withholding_group | Link | Tax Withholding Group | |
| default_bank_account | Link | Default Company Bank Account | options: Bank Account |
| customer_primary_address | Link | Customer Primary Address | options: Address |
| customer_primary_contact | Link | Customer Primary Contact | options: Contact |
| primary_address | Text Editor | Primary Address | read_only |
| mobile_no | Read Only | Mobile No | fetch from contact |
| email_id | Read Only | Email Id | fetch from contact |
| first_name | Read Only | First Name | hidden, fetch from contact |
| last_name | Read Only | Last Name | hidden, fetch from contact |
| accounts | Table | Accounts | options: Party Account |
| payment_terms | Link | Default Payment Terms Template | options: Payment Terms Template |
| credit_limits | Table | Credit Limit | options: Customer Credit Limit |
| so_required | Check | Allow Sales Invoice Creation Without Sales Order | default: 0 |
| dn_required | Check | Allow Sales Invoice Creation Without Delivery Note | default: 0 |
| disabled | Check | Disabled | default: 0 |
| is_frozen | Check | Is Frozen | default: 0 |
| is_internal_customer | Check | Is Internal Customer | default: 0 |
| represents_company | Link | Represents Company | shown if is_internal_customer |
| companies | Table | Allowed To Transact With | shown if is_internal_customer, options: Allowed To Transact With |
| loyalty_program | Link | Loyalty Program | options: Loyalty Program |
| loyalty_program_tier | Data | Loyalty Program Tier | read_only |
| default_sales_partner | Link | Sales Partner | |
| default_commission_rate | Float | Commission Rate | |
| sales_team | Table | Sales Team | options: Sales Team |
| portal_users | Table | Customer Portal Users | options: Portal User |
| supplier_numbers | Table | Supplier Numbers | options: Supplier Number At Customer |
| market_segment | Link | Market Segment | options: Market Segment |
| industry | Link | Industry | options: Industry Type |
| customer_details | Text | Customer Details | |
| customer_pos_id | Data | Customer POS ID | read_only |

### Permissions

| Role | Create | Read | Write | Delete | Email | Print | Report | Import | Export | Share |
|------|--------|------|-------|--------|-------|-------|--------|--------|-------|-------|
| Sales User | Yes | Yes | Yes | No | Yes | Yes | Yes | No | No | Yes |
| Sales Manager | No | Yes | No | No | Yes | Yes | Yes | No | No | No |
| Sales Master Manager | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Stock User | No | Yes | No | No | Yes | Yes | Yes | No | No | No |
| Stock Manager | No | Yes | No | No | Yes | Yes | Yes | No | No | No |
| Accounts User | No | Yes | No | No | Yes | Yes | Yes | No | No | No |
| Accounts Manager | No | Yes | No | No | Yes | Yes | Yes | No | No | No |

---

## 7. Customer Group

**File:** `erpnext/selling/doctype/customer_group/customer_group.json`

| Field | Type | Key Notes |
|-------|------|-----------|
| parent_customer_group | Link | Parent Group | |
| customer_group_name | Data | Customer Group Name | |
| default_price_list | Link | Default Price List | |
| payment_terms | Link | Default Payment Terms Template | |
| credit_limits | Table | Credit Limit | options: Customer Credit Limit |
| is_group | Check | Is Group | default: 0 |

---

## 8. Territory

**File:** `erpnext/selling/doctype/territory/territory.json`

| Field | Type | Key Notes |
|-------|------|-----------|
| parent_territory | Link | Parent Territory | |
| territory_name | Data | Territory Name | |
| territory_manager | Link | Territory Manager | User |

---

## 9. Sales Partner

Represents channel partners who sell products and earn commission.

| Field | Type | Key Notes |
|-------|------|-----------|
| partner_name | Data | Partner Name | |
| partner_type | Link | Sales Partner Type | |
| commission_rate | Float | Commission Rate | |
| referral_code | Data | Referral Code | |
| customers | Table | Customers (link to Customer) | |
| territories | Table | Territories (link to Territory) | |

---

## 10. Sales Partner Type

| Field | Type |
|-------|------|
| name | Data |

---

## 11. Sales Team (Child Table)

**File:** `erpnext/selling/doctype/sales_team/sales_team.json`

| Field | Type |
|-------|------|
| sales_person | Link, options: Sales Person |
| allocated_percentage | Float |
| commission_rate | Float |
| allocated_amount | Currency |
| incentives | Currency |

---

## 12. Quotation

**File:** `erpnext/selling/doctype/quotation/quotation.json`

### Fields (Key)

| Field | Type | Label | Key Notes |
|-------|------|-------|-----------|
| naming_series | Select | Series | `SAL-QTN-.YYYY.-` |
| quotation_to | Link | Quotation To | reqd, default: Customer, options: DocType |
| party_name | Dynamic Link | Party | reqd, dynamic based on quotation_to |
| customer_name | Data | Customer Name | hidden, read_only |
| transaction_date | Date | Date | default: Today, reqd |
| valid_till | Date | Valid Till | |
| order_type | Select | Order Type | Sales, Maintenance, Shopping Cart, reqd, default: Sales |
| company | Link | Company | reqd |
| currency | Link | Currency | reqd |
| conversion_rate | Float | Exchange Rate | reqd |
| selling_price_list | Link | Price List | reqd |
| items | Table | Items | options: Quotation Item, reqd |
| taxes_and_charges | Link | Sales Taxes and Charges Template | |
| taxes | Table | Sales Taxes and Charges | |
| grand_total | Currency | Grand Total | read_only |
| net_total | Currency | Net Total | read_only |
| total_qty | Float | Total Quantity | read_only |
| contact_person | Link | Contact Person | options: Contact |
| customer_address | Link | Customer Address | options: Address |
| shipping_address_name | Link | Shipping Address | options: Address |
| payment_terms_template | Link | Payment Terms Template | |
| payment_schedule | Table | Payment Schedule | |
| tc_name | Link | Terms | options: Terms and Conditions |
| terms | Text Editor | Term Details | |
| letter_head | Link | Letter Head | allow_on_submit |
| status | Select | Status | **Draft, Open, Replied, Partially Ordered, Ordered, Lost, Cancelled, Expired** |
| lost_reasons | Table MultiSelect | Lost Reasons | shown if status==Lost, options: Quotation Lost Reason Detail |
| order_lost_reason | Small Text | Detailed Reason | shown if status==Lost |
| competitors | Table MultiSelect | Competitors | options: Competitor Detail |
| opportunity | Link | Opportunity | |
| referral_sales_partner | Link | Referral Sales Partner | options: Sales Partner |
| auto_repeat | Link | Auto Repeat | |
| amended_from | Link | Amended From | options: Quotation |
| incoterm | Link | Incoterm | |
| named_place | Data | Named Place | |
| coupon_code | Link | Coupon Code | |
| utm_source | Link | Source | options: UTM Source |
| utm_medium | Link | Medium | options: UTM Medium |
| utm_campaign | Link | Campaign | options: UTM Campaign |
| utm_content | Data | Content | |
| packed_items | Table | Bundle Items | options: Packed Item |
| pricing_rules | Table | Pricing Rule Detail | read_only |

### State Machine

Quotation statuses: `Draft` → `Open` → `Replied` → `Partially Ordered` / `Ordered`
Alternative: `Draft` → `Expired` (cron job sets expired if valid_till passed and no SO)
Alternative: `Open`/`Replied` → `Lost` (via declare_enquiry_lost)
Alternative: `Draft` → `Cancelled`

### Permissions

| Role | Submit | Amend | Cancel |
|------|--------|-------|--------|
| Sales User | Yes | No | No |
| Sales Manager | Yes | Yes | Yes |
| Maintenance Manager | Yes | Yes | Yes |
| Maintenance User | Yes | Yes | Yes |

### Key Controller Logic (`quotation.py`)

- **validate:** Sets status, validates uom integers, validates valid_till, sets customer_name, makes packing list
- **before_submit:** Sets has_alternative_item flag
- **on_submit:** Validates approving authority, updates opportunity to "Quotation" status, updates lead
- **on_cancel:** Clears lost_reasons, updates opportunity back to "Open", updates lead
- **declare_enquiry_lost:** Sets status=Lost with reasons and competitors (blocked if SO already created)
- **get_ordered_status:** Returns Open/Partially Ordered/Ordered based on mapped SO items
- **make_sales_order:** Maps quotation to sales order, respecting alternative items
- **make_sales_invoice:** Maps quotation to sales invoice

---

## 13. Sales Order

**File:** `erpnext/selling/doctype/sales_order/sales_order.json`

### Fields (Key)

| Field | Type | Label | Key Notes |
|-------|------|-------|-----------|
| naming_series | Select | Series | `SAL-ORD-.YYYY.-` |
| customer | Link | Customer | reqd, in_global_search |
| customer_name | Data | Customer Name | fetch from customer.customer_name, read_only |
| order_type | Select | Order Type | Sales, Maintenance, Shopping Cart, reqd, default: Sales |
| transaction_date | Date | Date | default: Today, reqd |
| delivery_date | Date | Delivery Date | allow_on_submit, in_list_view |
| company | Link | Company | reqd |
| currency | Link | Currency | reqd |
| conversion_rate | Float | Exchange Rate | reqd |
| selling_price_list | Link | Price List | reqd |
| items | Table | Items | options: Sales Order Item, reqd |
| taxes_and_charges | Link | Sales Taxes and Charges Template | |
| taxes | Table | Sales Taxes and Charges | |
| grand_total | Currency | Grand Total | read_only |
| total_qty | Float | Total Quantity | read_only |
| net_total | Currency | Net Total | read_only |
| contact_person | Link | Contact Person | options: Contact |
| customer_address | Link | Customer Address | options: Address |
| shipping_address_name | Link | Shipping Address | options: Address |
| billing_address_column | Section | Billing Address | |
| shipping_address_column | Section | Shipping Address | |
| payment_terms_template | Link | Payment Terms Template | |
| payment_schedule | Table | Payment Schedule | |
| tc_name | Link | Terms | options: Terms and Conditions |
| terms | Text Editor | Terms and Conditions | |
| status | Select | Status | **Draft, On Hold, To Pay, To Deliver and Bill, To Bill, To Deliver, Completed, Cancelled, Closed** |
| delivery_status | Select | Delivery Status | Not Delivered, Fully Delivered, Partly Delivered, Closed, Not Applicable |
| billing_status | Select | Billing Status | Not Billed, Fully Billed, Partly Billed, Closed |
| per_delivered | Percent | % Delivered | read_only |
| per_billed | Percent | % Amount Billed | read_only |
| per_picked | Percent | % Picked | read_only |
| advance_payment_status | Select | Advance Payment Status | Not Requested, Requested, Partially Paid, Fully Paid |
| po_no | Data | Customer's Purchase Order | allow_on_submit |
| po_date | Date | Customer's Purchase Order Date | allow_on_submit |
| tax_id | Data | Tax Id | read_only |
| project | Link | Project | |
| sales_partner | Link | Sales Partner | |
| commission_rate | Float | Commission Rate | |
| total_commission | Currency | Total Commission | |
| amount_eligible_for_commission | Currency | Amount Eligible for Commission | read_only |
| sales_team | Table | Sales Team | options: Sales Team |
| is_internal_customer | Check | Is Internal Customer | read_only |
| represents_company | Link | Represents Company | read_only |
| reserve_stock | Check | Reserve Stock | shown if docstatus in [0,1] and not subcontracted |
| is_subcontracted | Check | Is Subcontracted | |
| auto_repeat | Link | Auto Repeat | |
| inter_company_order_reference | Link | Inter Company Order Reference | options: Purchase Order |
| letter_head | Link | Letter Head | allow_on_submit |
| set_warehouse | Link | Set Source Warehouse | |
| skip_delivery_note | Check | Skip Delivery Note | shown if order_type==Maintenance |
| amended_from | Link | Amended From | options: Sales Order |
| incoterm | Link | Incoterm | |
| named_place | Data | Named Place | |
| coupon_code | Link | Coupon Code | |
| packed_items | Table | Packed Items | options: Packed Item |
| pricing_rules | Table | Pricing Rule Detail | read_only |
| cost_center | Link | Cost Center | |

### State Machine

Sales Order statuses: `Draft` → `On Hold` / `To Deliver and Bill` / `To Bill` / `To Deliver` / `To Pay` → `Completed`
Alternative: `Draft` → `Cancelled`
Alternative: Any status (except Cancelled) → `Closed`
`On Hold` → can be reopened to previous status

### Permissions

| Role | Submit | Amend | Cancel |
|------|--------|-------|--------|
| Sales User | Yes | No | No |
| Sales Manager | Yes | Yes | Yes |
| Maintenance User | Yes | Yes | Yes |

### Key Controller Logic (`sales_order.py`)

- **validate:** Validates delivery_date vs transaction_date, PO number uniqueness, project-customer match, warehouse for stock items, drop ship supplier, blanket orders, inter-company rules, pricing rules
- **on_submit:** Validates credit limit, updates reserved qty, validates approving authority, updates project, updates quotation status
- **on_cancel:** Checks linked invoice docstatus, updates reserved qty, updates project, unlinks inter-company docs
- **on_update_after_submit:** Calculates commission and contribution
- **before_update_after_submit:** Validates PO and drop ship
- **check_credit_limit:** Validates against customer's credit limit (can be bypassed per Company in Customer Credit Limit table)
- **update_reserved_qty:** Updates bin reserved_qty for all items/warehouses
- **create_stock_reservation_entries:** Creates Stock Reservation Entries if reserve_stock enabled
- **update_delivery_status:** Updates per_delivered from Purchase Orders (for drop shipped items)
- **make_delivery_note:** Maps to Delivery Note with partial qty support
- **make_sales_invoice:** Maps to Sales Invoice with partial billing support
- **make_material_request:** Creates Material Request from SO items
- **make_project:** Creates Project from SO
- **make_purchase_order:** Creates Purchase Order per supplier for drop ship items
- **make_pick_list:** Creates Pick List for warehouse picking
- **make_work_orders:** Creates Work Orders for subcontracted items
- **make_production_plan:** Creates Production Plan from SO
- **make_maintenance_schedule:** Creates Maintenance Schedule
- **make_maintenance_visit:** Creates Maintenance Visit
- **close_or_unclose_sales_orders:** Bulk close/unclose via `update_status`

### Status Indicators

- Draft: red
- On Hold: orange
- To Deliver and Bill / To Bill / To Deliver: orange
- Completed: green
- Cancelled: red

---

## 14. Selling Settings

**File:** `erpnext/selling/doctype/selling_settings/selling_settings.json` (Single Doc)

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| cust_master_name | Select | Customer Name | Customer Naming By: Customer Name, Naming Series, Auto Name |
| customer_group | Link | (none) | Default Customer Group |
| territory | Link | (none) | Default Territory |
| selling_price_list | Link | (none) | Default Price List |
| so_required | Select | No | Is Sales Order Required for Sales Invoice & Delivery Note Creation? (No/Yes) |
| dn_required | Select | No | Is Delivery Note Required for Sales Invoice Creation? (No/Yes) |
| sales_update_frequency | Select | Daily | Monthly, Each Transaction, Daily |
| maintain_same_sales_rate | Check | 0 | Maintain Same Rate Throughout Sales Cycle |
| maintain_same_rate_action | Select | Stop | Stop/Warn when rate changes |
| role_to_override_stop_action | Link | (none) | Role Allowed to Override Stop Action |
| editable_price_list_rate | Check | 0 | Allow User to Edit Price List Rate in Transactions |
| allow_multiple_items | Check | 0 | Allow Item to be Added Multiple Times in a Transaction |
| allow_against_multiple_purchase_orders | Check | 0 | Allow Multiple Sales Orders Against a Customer's Purchase Order |
| validate_selling_price | Check | 0 | Validate Selling Price for Item Against Purchase Rate or Valuation Rate |
| hide_tax_id | Check | 0 | Hide Customer's Tax ID from Sales Transactions |
| enable_discount_accounting | Check | 0 | Enable Discount Accounting for Selling |
| allow_sales_order_creation_for_expired_quotation | Check | 0 | Allow Sales Order Creation For Expired Quotation |
| dont_reserve_sales_order_qty_on_sales_return | Check | 0 | Don't Reserve Sales Order Qty on Sales Return |
| allow_negative_rates_for_items | Check | 0 | Allow Negative rates for Items |
| blanket_order_allowance | Float | (none) | Blanket Order Allowance (%) |
| allow_zero_qty_in_sales_order | Check | 0 | Allow Sales Order with Zero Quantity |
| allow_zero_qty_in_quotation | Check | 0 | Allow Quotation with Zero Quantity |
| enable_utm | Check | 0 | Enable UTM in CRM documents |
| fallback_to_default_price_list | Check | 0 | Use Prices from Default Price List as Fallback |
| editable_bundle_item_rates | Check | 0 | Calculate Product Bundle Price based on Child Items' Rates |
| enable_tracking_sales_commissions | Check | 0 | Enable tracking sales commissions |
| allow_delivery_of_overproduced_qty | Check | 0 | Allow Delivery of Overproduced Qty (subcontracting) |
| deliver_secondary_items | Check | 0 | Deliver Secondary Items with Finished Goods |
| set_zero_rate_for_expired_batch | Check | 0 | Set Incoming Rate as Zero for Expired Batch |
| use_legacy_js_reactivity | Check | 0 | Use Legacy (Client side) Reactivity |

**Accessible by:** System Manager, Sales Manager

---

## Shared Controllers

### `erpnext/controllers/selling_controller.py`

Base controller for all selling documents (Quotation, Sales Order, Delivery Note, Sales Invoice).

**Key Methods:**

| Method | Description |
|--------|-------------|
| `set_missing_values` | Calls set_missing_lead_customer_details, set_price_list_and_item_details, set_company_contact_person |
| `set_missing_lead_customer_details` | Fetches party details from Customer (via _get_party_details) or Lead (via get_lead_details), sets taxes |
| `set_price_list_and_item_details` | Sets price list currency, calls set_missing_item_details |
| `set_customer_address` | Renders and sets address_display fields via render_address |
| `validate_max_discount` | Validates item discount against item's max_discount |
| `validate_selling_price` | Ensures selling rate >= last_purchase_rate and >= valuation_rate (configurable) |
| `set_qty_as_per_stock_uom` | Sets stock_qty = qty * conversion_factor |
| `validate_auto_repeat_subscription_dates` | Validates subscription dates |
| `set_serial_and_batch_bundle` | Creates serial/batch bundles for items |
| `validate_for_duplicate_items` | Prevents same item multiple times (unless allow_multiple_items setting) |
| `validate_target_warehouse` | Ensures target_warehouse != warehouse |
| `set_po_nos` | Collects PO numbers from linked Sales Orders / Delivery Notes |
| `set_gross_profit` | Calculates gross profit on item rows |
| `calculate_commission` | Computes commission based on commission_rate and amount_eligible_for_commission |
| `calculate_contribution` | Distributes commission among sales team based on allocated_percentage |
| `validate_sales_team` | Validates sales persons are enabled |
| `get_already_delivered_qty` | Returns delivered qty from DN and SI against SO item |
| `update_reserved_qty` | Updates bin reserved_qty |
| `get_item_list` | Returns flattened item list including packed items |
| `has_product_bundle` | Checks if item is a product bundle |
| `update_stock_ledger` | Creates SLE entries for stock transactions |
| `get_sle_for_source_warehouse` | Builds source warehouse SLE |
| `get_sle_for_target_warehouse` | Builds target warehouse SLE |
| `set_incoming_rate` | Sets incoming rate for delivery/return based on valuation |
| `update_stock_reservation_entries` | Updates SRE delivered qty on DN/SI submit/cancel |
| `check_sales_order_on_hold_or_close` | Prevents delivery/invoice if SO is On Hold or Closed |

---

## Integration Patterns

### Document Flow

```
Lead → Opportunity → Quotation → Sales Order → Delivery Note → Sales Invoice
         ↘              ↗
          Prospect
```

### Cross-Doc References

| From | To | Link Fields |
|------|----|-------------|
| Opportunity | Lead/Customer/Prospect | opportunity_from, party_name |
| Quotation | Lead/Customer/Prospect | quotation_to, party_name |
| Quotation | Opportunity | opportunity, prevdoc_docname (on items) |
| Sales Order | Quotation | prevdoc_docname (on items) |
| Sales Order | Customer | customer |
| Sales Order Item | Sales Order | sales_order, so_detail |
| Delivery Note | Sales Order | against_sales_order, so_detail |
| Delivery Note Item | Sales Order Item | so_detail, dn_detail |
| Sales Invoice | Sales Order | sales_order, so_detail |
| Sales Invoice Item | Sales Order Item | so_detail |

### UTM Analytics

UTM fields present on: Lead, Opportunity, Quotation, Sales Order
Fields: utm_source (UTM Source), utm_medium (UTM Medium), utm_campaign (UTM Campaign), utm_content
Enabled via `enable_utm` in Selling Settings.

### Common Child Tables in Selling

| Parent | Child Table | Purpose |
|--------|-------------|---------|
| Opportunity | Opportunity Item | Line items in opportunity |
| Quotation | Quotation Item | Line items in quotation |
| Quotation | Sales Taxes and Charges | Tax lines |
| Quotation Item | Packed Item | Bundle contents |
| Sales Order | Sales Order Item | Line items |
| Sales Order | Sales Taxes and Charges | Tax lines |
| Sales Order Item | Packed Item | Bundle contents |
| Sales Order | Sales Team | Commission allocation |
| Customer | Party Account | Company-specific receivable account |
| Customer | Customer Credit Limit | Per-company credit limits |
| Customer | Sales Team | Default sales team |
| Customer | Supplier Number At Customer | Customer's supplier numbers |

### Commission Tracking

Commission is tracked at the Sales Order level:
1. `amount_eligible_for_commission` = sum of item `base_net_amount` where `grant_commission=1`
2. `commission_rate` from sales_partner or Customer's default
3. `total_commission` = amount_eligible_for_commission * commission_rate / 100
4. `sales_team` table distributes commission via `allocated_percentage` and `commission_rate`
5. Enabled via `enable_tracking_sales_commissions` in Selling Settings

### Party Account

Customer can have per-company receivable accounts via the `accounts` (Party Account) child table. Default fetched from Company.

### Credit Limit

Per-company credit limits defined in Customer's `credit_limits` table. Each row has:
- company
- credit_limit
- bypass_credit_limit_check

Check triggered on Sales Order submit via `check_credit_limit`.

---

## Key Observations for UltrERP Implementation

1. **Lead is not linked to Customer directly** - conversion creates a NEW Customer from lead fields (company_name or first+last name). Existing Customer link is only for lead source tracking.

2. **Opportunity uses Dynamic Link** for party_name - can point to Customer, Lead, or Prospect doctypes.

3. **Quotation is quotation_to-centric** - can be addressed to Customer, Lead, Prospect, or CRM Deal. The `quotation_to` field uses DocType as options.

4. **Sales Order requires Delivery Date** for Sales order_type - validated in controller. Maintenance orders can skip via `skip_delivery_note`.

5. **Pricing in Selling Controller** - `set_price_list_and_item_details` is the main entry point; it calls `set_price_list_currency` and `set_missing_item_details`.

6. **Commission calculation** happens in both SellingController (basic) and SalesOrder (full with contribution distribution).

7. **Stock reservation** is integrated at Sales Order level via `reserve_stock` flag and Stock Reservation Entries.

8. **Multi-company support** - Customer can transact with multiple companies; Territory and Customer Group are company-agnostic master data.

9. **CRM Settings** controls whether Contact is auto-created when Lead is created.

10. **State transitions** are largely implicit (status field changes driven by user action + document submission) rather than enforced via Workflow doctype.
