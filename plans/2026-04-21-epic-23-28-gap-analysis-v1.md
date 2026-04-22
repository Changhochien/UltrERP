# ERPNext vs Epic 23 & Epic 28 Gap Analysis

**Date:** 2026-04-21
**Phase:** Research & Analysis
**Scope:** CRM, Projects, Support, and Contacts modules

---

## Executive Summary

This gap analysis compares ERPNext's CRM, Projects, Support, and Contacts capabilities against the validated requirements from Epic 23 (CRM Foundation) and Epic 28 (Workforce/Contacts/Service Desk Foundations).

### Key Findings:

| Domain | ERPNext Coverage | Epic Coverage | Gap Status |
|--------|------------------|---------------|------------|
| **CRM - Lead** | Full lifecycle (~50 fields) | Story 23.1 | Drafted, not implemented |
| **CRM - Opportunity** | Full pipeline | Story 23.2 | Drafted, not implemented |
| **CRM - Quotation** | Full lifecycle | Story 23.3 | Drafted, not implemented |
| **CRM - Settings** | Masters + reporting | Story 23.5 | Drafted, not implemented |
| **Projects - Project** | Full module | Epic 28 partial | Not planned |
| **Projects - Timesheet** | Full module | Story 28.3 | Not planned |
| **Projects - Activity Cost** | Full module | Story 28.3 | Not planned |
| **Support - Issue** | Full SLA tracking | Story 28.4 | Not planned |
| **Support - SLA** | Full priority-based | Story 28.4 | Not planned |
| **Support - Warranty** | Claim + Schedule | Story 28.5 | Not planned |
| **Contacts - Person** | Dynamic link model | Story 28.2 | Not planned |
| **HR - Employee** | Full module | Story 28.1 | Not planned |

---

## 1. CRM Analysis (Epic 23 Coverage)

### 1.1 Lead Management

#### ERPNext Capabilities:
| Field Category | ERPNext Fields | Notes |
|----------------|-----------------|-------|
| **Identity** | `salutation`, `first_name`, `middle_name`, `last_name`, `company_name`, `lead_name` | Composite lead_name auto-generated |
| **Status Lifecycle** | `status` with options: Lead, Open, Replied, Opportunity, Quotation, Lost Quotation, Interested, Converted, Do Not Contact | Full progression supported |
| **Owner & Attribution** | `lead_owner`, `qualified_by`, `qualified_on`, `qualification_status` | UTM tracking available |
| **UTM Analytics** | `utm_source`, `utm_medium`, `utm_campaign`, `utm_content` | Full UTM fields |
| **Territory & Segmentation** | `territory`, `market_segment`, `industry`, `type` (Client/Channel Partner/Consultant) | Geographic + segment |
| **Organization** | `no_of_employees`, `annual_revenue`, `company_size` | B2B focused |
| **Contact Methods** | `email_id`, `phone`, `mobile_no`, `whatsapp_no`, `fax`, `website` | Multi-channel |
| **Address** | Inline address: `city`, `state`, `country` | Basic address |
| **Qualification** | `qualification_status`: Unqualified, In Process, Qualified | Explicit qualification flow |
| **Conversion** | Links to `customer` (from existing customer leads) | Lead-to-customer |
| **Deduplication** | `CRM Settings.allow_lead_duplication_based_on_emails` | Optional dedupe |

#### Epic 23 Story 23.1 Requirements:
- [ ] Lead records with status, lead owner, territory, source, UTM attribution
- [ ] Dedupe checks against existing customers and leads
- [ ] Conversion-ready qualification states
- [ ] Lead-to-opportunity and lead-to-customer conversion

#### Gap Assessment:
| Requirement | ERPNext | UltrERP | Status |
|-------------|---------|---------|--------|
| Lead capture with full field set | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| UTM tracking | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Deduplication | ⚠️ Optional setting | ❌ Not implemented | **GAP** |
| Lead qualification | ✅ Full lifecycle | ❌ Not implemented | **MAJOR GAP** |
| Lead conversion | ✅ Full | ❌ Not implemented | **MAJOR GAP** |

#### Story 23.1 Implementation Status: **DRAFTED - NOT IMPLEMENTED**

---

### 1.2 Opportunity Pipeline

#### ERPNext Capabilities:
| Feature | ERPNext Fields | Notes |
|---------|----------------|-------|
| **Dynamic Party Link** | `opportunity_from` (DocType) + `party_name` (Dynamic Link) | Supports Lead, Customer, Prospect |
| **Sales Stage** | `sales_stage` (Link to Sales Stage) + `probability` (%) | Stage-based pipeline |
| **Commercial** | `currency`, `opportunity_amount`, `base_opportunity_amount`, `conversion_rate` | Multi-currency ready |
| **Timeline** | `expected_closing`, `transaction_date`, `first_response_time` | Forecasting fields |
| **Status** | Open, Quotation, Converted, Lost, Replied, Closed | Full state machine |
| **Contact** | `contact_person`, `contact_email`, `contact_mobile`, `phone`, `whatsapp` | Contact linkage |
| **Address** | `customer_address`, `address_display` | Full address |
| **Organization** | `industry`, `market_segment`, `annual_revenue`, `no_of_employees` | B2B context |
| **Lost Reasons** | `lost_reasons` (multi-select), `order_lost_reason` (detailed), `competitors` | Win/loss analysis |
| **Items** | `items` (Opportunity Item table) | Product context |
| **UTM** | `utm_source`, `utm_medium`, `utm_campaign`, `utm_content` | Attribution |
| **Assignment** | `opportunity_owner` | Owner tracking |

#### Epic 23 Story 23.2 Requirements:
- [ ] Opportunity records linked to lead, prospect, or customer
- [ ] Sales stage, probability, expected close, currency, amount
- [ ] Status: Open, Replied, Quoted, Converted, Lost, Closed
- [ ] Loss handling with reasons and competitors
- [ ] Quotation handoff preparation

#### Gap Assessment:
| Requirement | ERPNext | UltrERP | Status |
|-------------|---------|---------|--------|
| Dynamic party linking | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Stage-based pipeline | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Probability forecasting | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Loss tracking | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Quotation handoff | ✅ Full | ❌ Not implemented | **MAJOR GAP** |

#### Story 23.2 Implementation Status: **DRAFTED - NOT IMPLEMENTED**

---

### 1.3 Quotations/Proposals

#### ERPNext Capabilities (from research):
| Feature | ERPNext | Notes |
|---------|---------|-------|
| **Party Link** | `quotation_to` (Dynamic Link) | Customer/Lead/Prospect |
| **Items** | Full item table with qty, rate, discount | Commercial lines |
| **Taxes** | Tax calculation and templates | Taiwan-compliant |
| **Validity** | `valid_till` date tracking | Expiry management |
| **Status** | Draft, Open, Replied, Partially Ordered, Ordered, Lost, Cancelled, Expired | Full state machine |
| **Auto-repeat** | Scheduled recurring quotations | Automation |
| **Lost Reasons** | `lost_reasons`, `competitors` | Loss analysis |
| **Conversion** | `make_sales_order` | Direct to order |

#### Epic 23 Story 23.3 Requirements:
- [ ] Quotation records with validity, items, taxes, notes
- [ ] Status: Draft, Open, Replied, Ordered, Lost, Cancelled, Expired
- [ ] Revision workflow (explicit, not silent overwrite)
- [ ] Quotation-to-order conversion

#### Gap Assessment:
| Requirement | ERPNext | UltrERP | Status |
|-------------|---------|---------|--------|
| Full quotation lifecycle | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Item/tax management | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Validity tracking | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Order conversion | ✅ Full | ❌ Not implemented | **MAJOR GAP** |

#### Story 23.3 Implementation Status: **DRAFTED - NOT IMPLEMENTED**

---

### 1.4 Customer/Contact Management

#### ERPNext Capabilities:
| Feature | ERPNext | Notes |
|---------|---------|-------|
| **Customer** | Full record with receivable accounts, credit limits, payment terms | Per-company settings |
| **Customer Group** | Tree structure with defaults | Hierarchy |
| **Territory** | Geographic tree structure | Sales territories |
| **Contact** | Dynamic link pattern: links to Customer, Supplier, Lead, Opportunity | Shared contacts |
| **Address** | Separate Address doctype with Dynamic Link | Per-party addresses |
| **Contact Person** | Links via Dynamic Links | Multiple contacts per party |

#### Epic 28 Story 28.2 Requirements:
- [ ] Standalone contact records with phone, email, role
- [ ] Dynamic relationships across business records
- [ ] Multiple contacts per party
- [ ] Historical context preservation

#### Gap Assessment:
| Requirement | ERPNext | UltrERP | Status |
|-------------|---------|---------|--------|
| Shared contact CRUD | ✅ Full | ❌ Embedded fields only | **MAJOR GAP** |
| Contact-address separation | ✅ Full | ❌ Single billing_address field | **MAJOR GAP** |
| Multiple contacts | ✅ Full | ❌ Single contact_name | **MAJOR GAP** |
| Dynamic linking | ✅ Full | ❌ Not implemented | **MAJOR GAP** |

#### Story 28.2 Implementation Status: **NOT PLANNED**

---

### 1.5 CRM Settings & Reporting

#### ERPNext Capabilities:
| Setting | ERPNext | Notes |
|---------|---------|-------|
| **CRM Settings** | `auto_creation_of_contact`, `close_opportunity_after_days`, `allow_lead_duplication`, `default_valid_till` | Configuration |
| **Sales Stages** | Customizable pipeline stages | Flexibility |
| **Campaigns** | Email campaign tracking | Marketing |
| **Dashboard** | CRM-specific dashboards | Analytics |
| **Reports** | Pipeline reports, lost reasons, conversion rates | Insights |

#### Epic 23 Story 23.5 Requirements:
- [ ] Sales stages, territory, customer group setup
- [ ] Pipeline views for leads, opportunities, quotations
- [ ] Lost reasons and segment filters
- [ ] UTM attribution reporting

#### Gap Assessment:
| Requirement | ERPNext | UltrERP | Status |
|-------------|---------|---------|--------|
| CRM setup masters | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Pipeline reporting | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Territory management | ✅ Full | ⚠️ Basic territory exists | **PARTIAL GAP** |

#### Story 23.5 Implementation Status: **DRAFTED - NOT IMPLEMENTED**

---

## 2. Projects Analysis (Epic 28 Partial Coverage)

### 2.1 Project Module

#### ERPNext Capabilities:
| Feature | ERPNext | Notes |
|---------|---------|-------|
| **Project** | Full project with costing and billing | Status: Open, Completed, Cancelled |
| **Tasks** | Tree structure with dependencies | Status: Open, Working, Pending Review, Overdue, Completed, Template, Cancelled |
| **Timeline** | Expected/actual start/end dates | Gantt support |
| **Costing** | `estimated_costing`, `total_costing_amount`, `total_purchase_cost` | Budget tracking |
| **Billing** | `total_sales_amount`, `total_billed_amount`, `total_billable_amount` | Revenue tracking |
| **Customer Link** | `customer`, `sales_order` linkage | Account context |
| **Progress** | `percent_complete` with multiple methods (Manual, Task Completion, Task Progress, Task Weight) | Flexible tracking |
| **Users** | `users` table for access control | Team collaboration |
| **Department** | `department` linkage | Organizational |

#### Epic 28 Coverage:
Epic 28 does NOT explicitly cover Projects. Projects are mentioned as non-goals:
> "Deep project-management parity" is a Non-Goal for Epic 28.

#### Gap Assessment:
| Requirement | ERPNext | UltrERP | Status |
|-------------|---------|---------|--------|
| Project CRUD | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Task management | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Project costing | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Gantt chart | ✅ Full | ❌ Not implemented | **MAJOR GAP** |

#### Recommendation: **DEFER TO FUTURE EPIC** (not in Epic 23/28 scope)

---

### 2.2 Timesheets (Story 28.3)

#### ERPNext Capabilities:
| Feature | ERPNext | Notes |
|---------|---------|-------|
| **Timesheet** | Full time tracking | Status: Draft, Submitted, Partially Billed, Billed, Payslip, Completed |
| **Employee Link** | `employee`, `department`, `user` | Staff context |
| **Time Logs** | Per-project/task hours | Detailed entry |
| **Activity Types** | `activity_type` per entry | Categorization |
| **Billing** | `total_billable_hours`, `total_billed_hours`, `total_billable_amount`, `total_costing_amount` | Revenue tracking |
| **Project Link** | `parent_project` | Project context |
| **Customer Link** | `customer` | Account context |
| **Sales Invoice** | `sales_invoice` linkage | Billing integration |

#### Story 28.3 Requirements:
- [ ] Activity types, costing-ready metadata
- [ ] Timesheet entry workflows
- [ ] Link to projects, issues, service work
- [ ] Approval and billing hooks

#### Gap Assessment:
| Requirement | ERPNext | UltrERP | Status |
|-------------|---------|---------|--------|
| Timesheet CRUD | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Activity types | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Project linking | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Billing integration | ✅ Full | ❌ Not implemented | **MAJOR GAP** |

#### Story 28.3 Implementation Status: **NOT PLANNED**

---

### 2.3 Activity Cost

#### ERPNext Capabilities:
| Feature | ERPNext | Notes |
|---------|---------|-------|
| **Activity Type** | Name, costing_rate, billing_rate | Per-activity rates |
| **Activity Cost** | Per employee + activity_type rates | Staff cost matrix |
| **Project Template** | Predefined tasks with dependencies | Project blueprints |

#### Gap Assessment:
| Requirement | ERPNext | UltrERP | Status |
|-------------|---------|---------|--------|
| Activity types | ✅ Full | ❌ Not implemented | **GAP** |
| Activity costing | ✅ Full | ❌ Not implemented | **GAP** |
| Project templates | ✅ Full | ❌ Not implemented | **GAP** |

#### Recommendation: **INCLUDE IN STORY 28.3** (bundled with timesheets)

---

## 3. Support/Service Analysis (Epic 28 Partial Coverage)

### 3.1 Issue Tracking (Story 28.4)

#### ERPNext Capabilities:
| Feature | ERPNext | Notes |
|---------|---------|-------|
| **Issue** | Full ticket tracking | Status: Open, Replied, On Hold, Resolved, Closed |
| **Subject** | `subject` (required) | Issue title |
| **Customer** | `customer`, `customer_name` | Account context |
| **Raised By** | `raised_by` (email) | Reporter |
| **Priority** | `priority` (Link to Issue Priority) | Triage |
| **Issue Type** | `issue_type` (Link to Issue Type) | Categorization |
| **Description** | `description` (Text Editor) | Full details |
| **Contact** | `contact` (Link to Contact) | Contact linkage |
| **Lead** | `lead` (Link to Lead) | Prospect context |
| **Project** | `project` (Link to Project) | Project context |
| **Company** | `company` | Multi-company |
| **Via Portal** | `via_customer_portal` | Self-service |
| **SLA Fields** | `service_level_agreement`, `response_by`, `sla_resolution_by`, `agreement_status` | SLA tracking |
| **Response** | `first_response_time`, `first_responded_on`, `avg_response_time` | Response metrics |
| **Resolution** | `resolution_details`, `resolution_time`, `user_resolution_time` | Resolution metrics |
| **Hold Tracking** | `on_hold_since`, `total_hold_time` | Pause handling |
| **Split Issue** | `split_issue()` method | Thread management |
| **Auto-close** | Scheduler for replied tickets | SLA compliance |

#### Story 28.4 Requirements:
- [ ] Issue records with status, priority, assignment
- [ ] Response/resolution timing
- [ ] SLA policies by priority
- [ ] Escalation and overdue visibility

#### Gap Assessment:
| Requirement | ERPNext | UltrERP | Status |
|-------------|---------|---------|--------|
| Issue CRUD | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Priority/Type | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Customer/Contact link | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| SLA tracking | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Response metrics | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Split issue | ✅ Full | ❌ Not implemented | **GAP** |

#### Story 28.4 Implementation Status: **NOT PLANNED**

---

### 3.2 Service Level Agreement (SLA)

#### ERPNext Capabilities:
| Feature | ERPNext | Notes |
|---------|---------|-------|
| **SLA Definition** | Per-document-type SLA | Applied to Issue |
| **Priority-based** | `priorities` table with response/resolution times | Per-priority SLA |
| **Working Hours** | `support_and_resolution` table (Service Day) | Business hours |
| **Holiday List** | `holiday_list` link | Non-working days |
| **Pause Conditions** | `pause_sla_on` table | Status-based pause |
| **Fulfilled Status** | `sla_fulfilled_on` table | Resolution status mapping |
| **Entity Linking** | `entity_type` + `entity` (Dynamic Link) | Customer/Customer Group/Territory |
| **Default SLA** | `default_service_level_agreement` flag | Fallback |
| **Conditions** | Python expression for dynamic assignment | Advanced rules |

#### Gap Assessment:
| Requirement | ERPNext | UltrERP | Status |
|-------------|---------|---------|--------|
| SLA creation | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Priority-based times | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Working hours | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Holiday handling | ✅ Full | ⚠️ Basic list exists | **PARTIAL GAP** |
| Status pause | ✅ Full | ❌ Not implemented | **GAP** |

#### Recommendation: **INCLUDE IN STORY 28.4** (bundled with Issue)

---

### 3.3 Help Article / Knowledge Base

#### ERPNext Capabilities:
ERPNext v14+ has moved Help Article to Frappe's core (Knowledge Base). From research:
- `support_search_source` for integrating search
- No dedicated Help Article doctype in Support module

#### Gap Assessment:
| Requirement | ERPNext | UltrERP | Status |
|-------------|---------|---------|--------|
| Knowledge base | ⚠️ Moved to Frappe core | ❌ Not implemented | **GAP** |
| Help articles | ⚠️ Via Frappe Knowledge Base | ❌ Not implemented | **DEFER** |

#### Recommendation: **DEFER** (depends on Frappe Knowledge Base integration)

---

### 3.4 Maintenance Schedule

#### ERPNext Capabilities:
| Feature | ERPNext | Notes |
|---------|---------|-------|
| **Maintenance Schedule** | Planned maintenance visits | Serial no + item mapping |
| **Maintenance Visit** | Actual maintenance records | Service documentation |
| **Warranty Claim** | Warranty tracking | `warranty_amc_status` |

#### Story 28.5 Requirements:
- [ ] Warranty-claim-ready linkage (customer, product, serial)
- [ ] Service context for field operations
- [ ] Compatible with Epic 31 asset lifecycle

#### Gap Assessment:
| Requirement | ERPNext | UltrERP | Status |
|-------------|---------|---------|--------|
| Maintenance schedules | ✅ Full | ❌ Not implemented | **GAP** |
| Warranty claims | ✅ Full | ❌ Not implemented | **GAP** |
| Serial/item linking | ✅ Full | ❌ Not implemented | **GAP** |

#### Story 28.5 Implementation Status: **NOT PLANNED**

---

### 3.5 Customer Portal for Issues

#### ERPNext Capabilities:
| Feature | ERPNext | Notes |
|---------|---------|-------|
| **Portal Access** | Issues visible to linked Contact | `has_website_permission` |
| **Self-service** | Raise issues via portal | Via Customer Portal |
| **Email Integration** | `make_issue_from_communication` | Email-to-ticket |

#### Epic 28 Note:
> "Service flows should integrate with Epic 30 portal work rather than compete with it."

#### Gap Assessment:
| Requirement | ERPNext | UltrERP | Status |
|-------------|---------|---------|--------|
| Portal issue viewing | ✅ Full | ❌ Not implemented | **DEFER TO EPIC 30** |
| Portal issue creation | ✅ Full | ❌ Not implemented | **DEFER TO EPIC 30** |
| Email-to-ticket | ✅ Full | ❌ Not implemented | **DEFER TO EPIC 30** |

#### Recommendation: **DEFER TO EPIC 30** (portal work)

---

## 4. Contacts/Addresses Analysis (Epic 28 Coverage)

### 4.1 Contact-Address Separation

#### ERPNext Pattern:
```
Customer (Party)
  ├── Address (Dynamic Link via party)
  │     ├── address_line1, address_line2
  │     ├── city, state, pincode
  │     ├── country
  │     └── address_type: Billing, Shipping, Office, Warehouse
  └── Contact (Dynamic Link via party)
        ├── first_name, last_name
        ├── email_id, phone, mobile
        ├── designation, department
        └── is_primary_contact
```

#### Current UltrERP Pattern:
```
Customer
  ├── company_name
  ├── billing_address (single text field)
  ├── contact_name (single field)
  ├── contact_phone
  └── contact_email
```

#### Gap Assessment:
| Requirement | ERPNext | UltrERP | Status |
|-------------|---------|---------|--------|
| Separate Address record | ✅ Full | ❌ Single text field | **MAJOR GAP** |
| Multiple addresses | ✅ Full | ❌ Single address | **MAJOR GAP** |
| Address types | ✅ Full | ❌ Not implemented | **MAJOR GAP** |
| Separate Contact record | ✅ Full | ❌ Embedded fields | **MAJOR GAP** |
| Multiple contacts | ✅ Full | ❌ Single contact | **MAJOR GAP** |
| Contact roles | ✅ Full | ❌ Not implemented | **MAJOR GAP** |

#### Story 28.2 Implementation Status: **NOT PLANNED**

---

### 4.2 Multiple Contacts Per Party

#### ERPNext Capabilities:
| Feature | ERPNext | Notes |
|---------|---------|-------|
| **Contact Person Table** | `get_contacts()` on Customer | Multiple per party |
| **Primary Contact** | `is_primary` flag | Default selection |
| **Dynamic Links** | Contact linked via `Dynamic Link` doctype | Flexible |

#### Gap Assessment:
| Requirement | ERPNext | UltrERP | Status |
|-------------|---------|---------|--------|
| Multiple contacts | ✅ Full | ❌ Single contact | **MAJOR GAP** |
| Contact designation | ✅ Full | ❌ Not implemented | **GAP** |
| Primary contact | ✅ Full | ❌ Not implemented | **GAP** |

---

### 4.3 Customer Groups & Territories

#### ERPNext Capabilities:
| Feature | ERPNext | Notes |
|---------|---------|-------|
| **Customer Group** | Tree structure with `parent_customer_group` | Hierarchy |
| **Defaults** | `default_price_list`, `default_payment_terms` per group | Auto-population |
| **Territory** | Tree structure for geographic segmentation | Sales routing |
| **Group-based SLA** | SLA can target Customer Group | Service rules |

#### Current UltrERP Status:
- Customer Group: ⚠️ Basic exists (mentioned in Epic 23.5)
- Territory: ⚠️ Basic exists (mentioned in Epic 23.5)

#### Gap Assessment:
| Requirement | ERPNext | UltrERP | Status |
|-------------|---------|---------|--------|
| Customer Group tree | ✅ Full | ⚠️ Basic | **PARTIAL GAP** |
| Territory tree | ✅ Full | ⚠️ Basic | **PARTIAL GAP** |
| Group defaults | ✅ Full | ❌ Not implemented | **GAP** |

#### Recommendation: **INCLUDE IN STORY 23.5** (CRM setup masters)

---

## 5. Taiwan-Specific CRM Enhancements

### 5.1 Epic 9 LINE Integration (Already Planned)

| Story | Status | Coverage |
|-------|--------|----------|
| Story 9.1: LINE Notification on New Order | Implemented | ✅ Staff receive LINE notifications |
| Story 9.2: LINE BOT Order Submission | Implemented | ✅ Customers submit orders via LINE |
| Story 9.3: LINE Order Confirmation | Implemented | ✅ Order confirmation sent via LINE |

### 5.2 Additional Taiwan-Specific CRM Opportunities

#### Missing Integrations:

| Enhancement | Description | Priority |
|-------------|-------------|----------|
| **LINE Messaging for CRM** | Send lead/opportunity notifications via LINE | Medium |
| **LINE Contact Linking** | Link LINE user ID to Contact record | Medium |
| **WhatsApp Business** | B2B Taiwan also uses WhatsApp | Medium |
| **Taiwan Business Number** | Already validated in Customer | ✅ Implemented |
| **Traditional Chinese UI** | Full zh-Hant translation | Partial |
| **Taiwan Tax Integration** | eGUI for invoices | ✅ Implemented |

#### Gap Assessment:
| Requirement | ERPNext | UltrERP | Status |
|-------------|---------|---------|--------|
| LINE CRM notifications | ❌ Not in ERPNext | ⚠️ Order-level exists | **CUSTOM GAP** |
| LINE Contact linking | ❌ Not in ERPNext | ❌ Not implemented | **CUSTOM GAP** |
| WhatsApp integration | ✅ `whatsapp_no` field | ❌ Not implemented | **GAP** |
| Traditional Chinese | ❌ ERPNext has zh-TW locale | ⚠️ Partial | **PARTIAL** |

#### Recommendations:
1. **Add LINE CRM notification stories** to notify sales staff of new leads/opportunities via LINE
2. **Add LINE ID field to Contact** for customer LINE linking
3. **Add WhatsApp Business API** for international B2B customers
4. **Enhance Traditional Chinese** translations for CRM terminology

---

## 6. Implementation Recommendations

### 6.1 Epic 23 - Priority Order

| Story | Effort | Priority | Status | Recommendation |
|-------|--------|----------|--------|----------------|
| Story 23.1: Lead Capture | Medium | **P0** | Drafted | **Implement immediately** |
| Story 23.2: Opportunity Pipeline | Medium | **P0** | Drafted | **Implement after 23.1** |
| Story 23.3: Quotation Lifecycle | Medium | P1 | Drafted | **Implement after 23.2** |
| Story 23.4: Quotation-to-Order | Low | P1 | Drafted | **Implement with 23.3** |
| Story 23.5: CRM Setup Masters | Low | P2 | Drafted | **Implement with 23.1** |

### 6.2 Epic 28 - Priority Order

| Story | Effort | Priority | Status | Recommendation |
|-------|--------|----------|--------|----------------|
| Story 28.1: Employee & Org Structure | Medium | P1 | Not planned | **Plan for Phase 2** |
| Story 28.2: Shared Contact CRUD | Medium | **P0** | Not planned | **Plan for Phase 2** |
| Story 28.3: Activity Types & Timesheets | Medium | P1 | Not planned | **Plan for Phase 2** |
| Story 28.4: Issue Tracking & SLA | Medium | P1 | Not planned | **Plan for Phase 3** |
| Story 28.5: Warranty & Service Handoff | Low | P2 | Not planned | **Plan for Phase 3** |

### 6.3 New Taiwan-Specific Stories

| Story | Effort | Priority | Recommendation |
|-------|--------|----------|----------------|
| **LINE CRM Notifications** | Low | Medium | Add to Epic 23 or Epic 30 |
| **LINE Contact Linking** | Medium | Medium | Add to Epic 28 Story 28.2 |
| **WhatsApp Business Integration** | Medium | Low | Defer to future |

---

## 7. Summary: Gap Coverage Matrix

### Epic 23 Coverage

| Requirement | ERPNext | UltrERP | Gap |
|-------------|---------|---------|-----|
| Lead Management | ✅ Full | ❌ None | **MAJOR GAP** |
| Opportunity Pipeline | ✅ Full | ❌ None | **MAJOR GAP** |
| Quotations | ✅ Full | ❌ None | **MAJOR GAP** |
| Customer Management | ✅ Full | ⚠️ Basic | **PARTIAL GAP** |
| CRM Settings | ✅ Full | ❌ None | **MAJOR GAP** |
| UTM Tracking | ✅ Full | ❌ None | **MAJOR GAP** |
| Deduplication | ✅ Full | ❌ None | **GAP** |
| Lead Qualification | ✅ Full | ❌ None | **MAJOR GAP** |

### Epic 28 Coverage

| Requirement | ERPNext | UltrERP | Gap |
|-------------|---------|---------|-----|
| Employee Records | ✅ Full | ❌ None | **MAJOR GAP** |
| Department/Designation | ✅ Full | ❌ None | **MAJOR GAP** |
| Shared Contact CRUD | ✅ Full | ❌ None | **MAJOR GAP** |
| Multiple Contacts/Party | ✅ Full | ❌ None | **MAJOR GAP** |
| Contact-Address Separation | ✅ Full | ❌ None | **MAJOR GAP** |
| Timesheets | ✅ Full | ❌ None | **MAJOR GAP** |
| Activity Types | ✅ Full | ❌ None | **GAP** |
| Issue Tracking | ✅ Full | ❌ None | **MAJOR GAP** |
| SLA Management | ✅ Full | ❌ None | **MAJOR GAP** |
| Maintenance Schedule | ✅ Full | ❌ None | **GAP** |
| Customer Portal Issues | ✅ Full | ❌ None | **DEFER TO EPIC 30** |

---

## 8. Immediate Action Items

### For Epic 23 (CRM Foundation):

- [ ] **23.1.1**: Create Lead domain model with full field set
- [ ] **23.1.2**: Implement lead lifecycle state machine
- [ ] **23.1.3**: Add dedupe check against customers and leads
- [ ] **23.1.4**: Build lead conversion to opportunity/customer
- [ ] **23.1.5**: Create lead UI workspace and forms
- [ ] **23.2.1**: Create Opportunity domain model with dynamic party link
- [ ] **23.2.2**: Implement opportunity pipeline state machine
- [ ] **23.2.3**: Add loss tracking and competitor capture
- [ ] **23.2.4**: Build opportunity-to-quotation handoff
- [ ] **23.2.5**: Create opportunity UI workspace and pipeline views
- [ ] **23.3.1**: Create Quotation domain model
- [ ] **23.3.2**: Implement quotation lifecycle with revision support
- [ ] **23.3.3**: Add quotation-to-order conversion
- [ ] **23.3.4**: Create quotation UI workspace
- [ ] **23.5.1**: Create CRM setup masters (Sales Stage, Market Segment, etc.)
- [ ] **23.5.2**: Build CRM pipeline dashboards and reports

### For Epic 28 (Future Planning):

- [ ] **28.1.1**: Create Employee, Department, Designation models
- [ ] **28.2.1**: Create shared Contact doctype with dynamic linking
- [ ] **28.2.2**: Create Address doctype with address types
- [ ] **28.2.3**: Migrate embedded contact fields to shared contacts
- [ ] **28.3.1**: Create Activity Type and Activity Cost models
- [ ] **28.3.2**: Create Timesheet model with time logs
- [ ] **28.4.1**: Create Issue doctype with SLA fields
- [ ] **28.4.2**: Create Service Level Agreement doctype
- [ ] **28.5.1**: Create Maintenance Schedule and Warranty Claim models

### Taiwan-Specific Enhancements:

- [ ] **Add LINE CRM notification story** to Epic 23 or Epic 30
- [ ] **Add LINE ID field to Contact** for LINE user linking
- [ ] **Evaluate WhatsApp Business API** integration

---

## 9. References

- Epic 23 Planning: `_bmad-output/planning-artifacts/epic-23.md`
- Epic 28 Planning: `_bmad-output/planning-artifacts/epic-28.md`
- Story 23.1 Implementation: `_bmad-output/implementation-artifacts/23-1-lead-capture-deduplication-and-qualification.md`
- Story 23.2 Implementation: `_bmad-output/implementation-artifacts/23-2-opportunity-pipeline-and-dynamic-party-linking.md`
- ERPnext Validated Research: `ERPnext-Validated-Research-Report.md`
- ERPNext CRM Reference: `reference/erpnext-develop/erpnext/crm/`
- ERPNext Projects Reference: `reference/erpnext-develop/erpnext/projects/`
- ERPNext Support Reference: `reference/erpnext-develop/erpnext/support/`
