# Review: Overlooked Gaps

## Overlooked ERPnext Modules (not in gap analysis)

### 1. Telephony Module (completely missed)
- `erpnext/telephony/doctype/call_log/` — Call logging with telephony call types
- `erpnext/telephony/doctype/voice_call_settings/` — Voice call configuration
- `erpnext/telephony/doctype/incoming_call_settings/` — Incoming call routing
- `erpnext/telephony/doctype/incoming_call_handling_schedule/` — Call schedule
- `erpnext/telephony/doctype/telephony_call_type/` — Call type classification
- **Gap:** No telephony/call center integration in UltrERP

### 2. WhatsApp Integration in CRM (not flagged)
- `erpnext/crm/doctype/lead/lead.json` — has `whatsapp_no` field
- `erpnext/crm/doctype/opportunity/opportunity.json` — has `whatsapp_no` field
- **Gap:** UltrERP has LINE integration but no WhatsApp. WhatsApp Business API is widely used in Taiwan B2B contexts.

### 3. Auto-Repeat / Recurring Documents (not in gap analysis)
- Referenced in `erpnext/hooks.py` and locale files: `auto_email_to_sender`, recurring document generation
- **Gap:** No auto-repeat for recurring invoices/orders in UltrERP

### 4. Shift Management (not in gap analysis)
- `erpnext/assets/doctype/asset_shift_allocation/` — Asset shift allocation
- `erpnext/assets/doctype/asset_shift_factor/` — Shift factor for assets
- **Note:** ERPnext removed standalone HR/Payroll in v14 — leave/expense/payroll are in Frappe core, not ERPnext

### 5. Asset Maintenance Module (not in gap analysis)
- `erpnext/assets/doctype/asset_maintenance/` — Asset maintenance scheduling
- `erpnext/assets/doctype/asset_maintenance_log/` — Maintenance log with calendar view
- `erpnext/assets/doctype/asset_maintenance_task/` — Maintenance tasks
- `erpnext/assets/doctype/asset_maintenance_team/` — Maintenance team members
- **Gap:** No asset maintenance scheduling in UltrERP

### 6. Asset Repair Module (not in gap analysis)
- `erpnext/assets/doctype/asset_repair/` — Repair tracking with status, `repair_cost`
- **Gap:** No asset repair tracking in UltrERP

### 7. Video / Portal Content (not in gap analysis)
- `erpnext/utilities/doctype/video/` — Video doctype for web portal content
- `erpnext/utilities/doctype/video_settings/` — Video settings
- **Gap:** No video content management in UltrERP

### 8. Rename Tool (not in gap analysis)
- `erpnext/utilities/doctype/rename_tool/` — Bulk rename utility for items/customers/suppliers
- **Gap:** No bulk rename tool in UltrERP

### 9. Email Campaign (mentioned in auto_email results)
- `erpnext/crm/doctype/email_campaign/` — Email campaign tracking
- **Gap:** No email campaign management in UltrERP

### 10. Driving License & Vehicle (setup doctypes, partially visible)
- `erpnext/setup/doctype/driver/` — Driver records
- `erpnext/setup/doctype/vehicle/` — Vehicle records with dashboard
- **Gap:** No driver or vehicle fleet management in UltrERP

### 11. Transaction Deletion Record (compliance, missed)
- `erpnext/setup/doctype/transaction_deletion_record_to_delete/` — Compliance audit trail for deletions
- **Gap:** No transaction deletion logging in UltrERP (only general audit_log)

### 12. Terms and Conditions (missed as separate doctype)
- `erpnext/setup/doctype/terms_and_conditions/` — Reusable T&C templates
- **Gap:** No T&C template management in UltrERP

## Overlooked UltrERP Domains (not in gap analysis)

### 1. Legacy Import Domain
- `backend/domains/legacy_import/` — Full legacy data import pipeline
- **Status:** Already implemented. NOT missing — this is an UltrERP strength. CSV import, staging, normalization, mapping, canonical import.

### 2. Intelligence Domain
- `backend/domains/intelligence/` — Analytics/BI layer
- **Status:** Already implemented (ProspectGapTable, AffinityMatrix, RevenueDiagnosisCard, etc.)

### 3. AEO Domain
- `backend/domains/aeo/` — AEO content generation
- **Status:** Already implemented

### 4. LINE Domain
- `backend/domains/line/` — LINE webhook integration
- **Status:** Already implemented. NOT a gap — only messaging integration present.

## New Gaps to Add to Report

### HIGH Priority (newly identified)

| Gap | Evidence | Impact |
|-----|----------|--------|
| **No WhatsApp integration** | ERPnext has `whatsapp_no` on Lead/Opportunity; Taiwan B2B uses WhatsApp Business API | Cannot engage leads via WhatsApp; only LINE available |
| **No Call / Telephony log** | ERPnext `telephony/doctype/call_log/` | No call center integration |
| **No Asset Maintenance scheduling** | ERPnext `asset_maintenance/` + `asset_maintenance_log/` with calendar | Cannot schedule planned maintenance for equipment |
| **No Asset Repair tracking** | ERPnext `asset_repair/` with repair_cost, status | Cannot track equipment repairs |
| **No Video / portal content** | ERPnext `utilities/doctype/video/` | No video content for customer portal |

### MEDIUM Priority (newly identified)

| Gap | Evidence | Impact |
|-----|----------|--------|
| **No auto-repeat / recurring documents** | Referenced in ERPnext `hooks.py` | Cannot auto-generate recurring invoices/orders |
| **No bulk rename tool** | ERPnext `utilities/doctype/rename_tool/` | No utility to rename items/customers in bulk |
| **No email campaign** | ERPnext `crm/doctype/email_campaign/` | No email marketing campaign tracking |
| **No driver/fleet management** | ERPnext `setup/doctype/driver/`, `vehicle/` | Cannot manage delivery fleet drivers and vehicles |
| **No T&C template management** | ERPnext `setup/doctype/terms_and_conditions/` | Cannot reuse T&C across customer/supplier contracts |
| **No transaction deletion audit log** | ERPnext `transaction_deletion_record_to_delete/` | Missing compliance record of deleted transactions (beyond general audit log) |

### Previously noted but status clarification

| Item | Clarification |
|------|---------------|
| Leave Management | NOT in ERPnext — removed in v14. Lives in Frappe HR module, not ERPnext. UltrERP gap analysis correctly notes no HR. |
| Expense Claim | NOT in ERPnext — patch `add_expense_claim_default_account.py` shows it existed but was removed in v14 when HR/Payroll modules were cut. |
| Payroll/PaySlip | NOT in ERPnext — removed in v14 (`patches/v14_0/remove_hr_and_payroll_modules.py`). Lives in Frappe Payroll, not ERPnext. |
| Quality Inspection | Already in gap analysis as MISSING (Priority 1) — correct. |
| WhatsApp/chat | No WhatsApp found; LINE is present — correct. |
| CSV Import | Legacy import domain exists — NOT a gap, it's a strength. |
| Print Designer | Already in gap analysis as MISSING (Priority 2) — correct. |
| Automation (auto-reply) | Approval engine exists (backend) but no scheduled notification/auto-reply — correct gap. |
