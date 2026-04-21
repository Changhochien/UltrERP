# Roadmap Feasibility Review

**Reviewer:** review-roadmap agent
**Date:** 2026-04-20
**Sources:** ERPnext-Research-Report.md (Section 6), gap-analysis.md, actual ERPnext source files

---

## Phase 1 Effort Corrections

### 1. Lead/Opportunity/Quotation — Should be MEDIUM, not HIGH

**Roadmap claim:** High effort — "requires new domain (CRM) with state machines, Dynamic Links, whitelist methods, UTM tracking"

**Actual field counts:**
- **Lead:** ~35-40 real data fields (many JSON entries are Section Break, Column Break, Tab Break, or HTML layout elements — not actual fields). The report claimed 85 fields; actual data-carrying fields are fewer. Core fields: status (Select), lead_name, company_name, email_id, phone, mobile_no, territory (Link), lead_owner (Link), qualification_status, qualified_by, annual_revenue, no_of_employees, industry, market_segment, UTM fields (utm_source, utm_medium, utm_campaign, utm_content), with corresponding HTML sections for address and contact.
- **Opportunity:** ~40 real data fields. Key fields: opportunity_from (Dynamic Link), party_name (Dynamic Link), status, sales_stage, probability, expected_closing, currency, conversion_rate, opportunity_amount, base_opportunity_amount, items table, contact info, UTM fields.
- **Quotation:** (confirmed exists at `erpnext/selling/doctype/quotation/quotation.json`)

**Correction:** The effort should be **MEDIUM**, not HIGH. The field counts are manageable, and neither Lead nor Opportunity has complex financial GL integration. The real complexity is the new CRM domain pattern (state machines, Dynamic Links, conversion workflows), but this is comparable to the effort of building the existing Order domain. The report's "85 fields" claim for Lead overstates the actual data fields significantly once layout elements are excluded.

**However:** Quotation adds complexity because it requires a `make_sales_order` conversion and tax/pricing engine integration with the existing Order domain. That said, it still does NOT require GL first.

---

### 2. Purchase Order — Should be HIGH, not Medium

**Roadmap claim:** Medium effort — "new domain with standard transaction patterns"

**Actual:** ERPnext Purchase Order JSON has ~97 field_order entries and ~100+ field definitions spanning supplier, items (Purchase Order Item table), currency/conversion_rate, taxes, payment schedule, advance allocation, subcontracting (supplied_items), drop-ship, inter-company, project/cost center, accounting dimensions, auto-repeat, and extensive address/contact sections. It is submittable (creates stock and GL entries on submit).

**gap-analysis.md Priority Matrix correctly lists PO as High effort.** The roadmap misclassifies it as Medium.

**Verification:** `wc -l purchase_order.json` = 1390 lines. The gap-analysis P0 table also says "Purchase Order: High."

---

### 3. Multi-Currency — Correct as Medium BUT understated dependency

**Roadmap claim:** Medium effort — "requires currency field on transactions, exchange rate lookup, conversion calculation"

**Actual:** `accounts_controller.py` contains 181 occurrences of "currency" or "conversion_rate" references. This is deeply integrated throughout the accounting controller, not just two fields.

**Correction:** The effort classification as Medium is defensible for the **UI layer** (adding currency + conversion_rate fields to transaction forms). However, the roadmap understates that **multi-currency GL entries require GL to exist first**. The report says "GL entries in both transaction and company currency" — this is Phase 2 GL work, not Phase 1. A minimally viable Phase 1 multi-currency could add the fields and do currency conversion math without actually writing dual-currency GL entries, deferring that to Phase 2.

**Recommendation:** Split multi-currency into:
- Phase 1 (Medium): currency + conversion_rate fields, exchange rate lookup, display conversion — no GL changes
- Phase 2 (Medium-High): dual-currency GL entries, unrealized gain/loss on payment

---

## Dependency Analysis

### Does Lead/Opportunity require GL first?

**No.** Lead and Opportunity are pre-financial documents. They track prospective customers and potential deals, but they do not create GL entries. A Lead converted to a Customer creates a Customer record; an Opportunity converted to a Quotation creates a Quotation; neither triggers accounting. GL is needed when a Quotation becomes a Sales Order that is invoiced — which is the existing Order → Invoice flow that already exists in UltrERP.

**Verified:** ERPnext Lead and Opportunity DocTypes have no `is_submittable` flag and no GL-related code in their field schemas.

### Does Purchase Order require anything from existing inventory domain?

**Partially.** PO's `schedule_date`, `set_warehouse`, and items table (with `received_qty`) interact with inventory, but:
- UltrERP already has a **Products** domain with warehouse support
- The PO receiving (GRN/Purchase Receipt) would need the `received_qty` bin update, which requires the inventory **Bin** model — which UltrERP has (part of existing inventory domain)
- PO does NOT require BOM or Work Order first

**Actual dependency:** PO is blocked by having Suppliers (existing in UltrERP inventory domain), Products (existing), and Warehouses (existing). It is largely independent.

### Does Quotation require Lead/Opportunity first?

**Yes, in terms of full pipeline flow.** However, a minimal Quotation implementation (standalone, linked directly to Customer) could be built independently. The `quotation_to` Dynamic Link would link to Customer/Lead/Prospect.

---

## Phase 2/3 Corrections

### BOM — Minimally Viable vs. Full Implementation

**Roadmap claim:** High effort — BOM has 775 lines JSON, Work Order has 745 lines

**Actual BOM complexity:**
- BOM materials table (item, qty, rate, source_warehouse, operation)
- BOM operations table (operation, workstation, time)
- Multi-level BOM recursion (`use_multi_level_bom`)
- Scrap warehouse
- Work Order: production_item, bom_no, qty, operations routing, required_items, reserve_stock, transfer_material_against

**Minimally viable BOM (Phase 2, Medium effort):**
- BOM with flat materials list (no operations)
- Work Order that consumes materials and produces FG (simple transfer, no scheduling)
- No Job Cards, no operations routing, no multi-level BOM
- No production planning

**Full ERPnext-style BOM/Work Order:** Confirmed HIGH effort. The report correctly notes this.

### GL — Minimally Viable

**Roadmap claim:** High effort — requires account model, GL entry creation, report engine

**Minimally viable GL (Medium effort):**
- Account model with tree (parent_account, lft, rgt) and types (Asset, Liability, Income, Expense, Equity)
- GL Entry DocType: account, party_type/party, debit, credit, company
- Manual Journal Entry (no auto-GL from transactions yet)
- Basic P&L report (sum income minus expenses per account)
- **No** dimensions, no fiscal year, no cost center filtering

**Why this is Medium not High:** The complex part is auto-generating GL from existing transactions (Sales Invoice → GL Entry on submit). A manual-only GL with Journal Entry is relatively straightforward and provides real accounting value immediately. Auto-GL from transactions is the hard part that could be phased.

**Full GL with auto-entry from all transactions:** Confirmed HIGH effort — requires modifying every transaction's submit/cancel handlers.

---

## Quick Win Opportunities (P2/P3 items that are actually easy)

1. **Sales Commission Tracking (gap-analysis: Low effort)**
   - Add `sales_team` child table to Order: sales_person, allocated_percentage, commission_rate
   - Add `total_commission` computed field
   - Commission report per salesperson
   - This is genuinely LOW effort — just fields on the existing Order domain

2. **Customer Group + Territory trees (gap-analysis: Low effort)**
   - Tree-structured master data with parent/child
   - Add to Customer: `customer_group` (Link), `territory` (Link)
   - These are setup doctypes, not transaction doctypes — much simpler than domains with submit/cancel logic

3. **UTM Analytics on existing Order domain (gap-analysis: Low)**
   - Add utm_source, utm_medium, utm_campaign, utm_content fields to Order
   - Already mentioned in roadmap for Lead/Opportunity/Quotation but equally easy on Order directly
   - No state machine, no conversion logic

4. **Payment Terms Template builder (gap-analysis: Low)**
   - UltrERP already has payment terms enum (NET_30, NET_60, COD)
   - Upgrade to a proper Template doctype with due date installments
   - Standard simple doctype, no transaction integration required

5. **Item Barcode support (gap-analysis: Medium)**
   - Add `barcode` field to Products domain
   - Add `Item Barcode` child table (item, barcode, barcode_type)
   - BarcodeScanner utility exists in ERPnext — could be ported
   - No GL impact, no submit logic changes

---

## ERPnext Reference Corrections

### File path corrections

All referenced paths in the roadmap **exist and are correct:**
- `erpnext/crm/doctype/lead/lead.json` — **VERIFIED EXISTS**
- `erpnext/crm/doctype/opportunity/opportunity.json` — **VERIFIED EXISTS**
- `erpnext/buying/doctype/purchase_order/purchase_order.json` — **VERIFIED EXISTS** (1390 lines)
- `erpnext/controllers/selling_controller.py` — **VERIFIED EXISTS** (1095 lines)
- `erpnext/controllers/accounts_controller.py` — **VERIFIED EXISTS** (4496 lines)
- `erpnext/manufacturing/doctype/bom/bom.json` — **VERIFIED EXISTS** (775 lines)
- `erpnext/manufacturing/doctype/work_order/work_order.json` — **VERIFIED EXISTS** (745 lines)
- `erpnext/selling/doctype/quotation/quotation.json` — **VERIFIED EXISTS**

### selling_controller.py size

1095 lines. This is a meaningful base class used by Quotation, Sales Order, Delivery Note. Any CRM/Selling implementation that follows ERPnext patterns would need to reference or replicate some of this logic. The roadmap correctly identifies this as a reference file.

### accounts_controller.py size

4496 lines. Massive. This is the core of all accounting in ERPnext. It handles GL entry creation, currency validation, tax calculation, payment schedule, outstanding management, advance allocation, and cancellation with reverse entries. The roadmap's "High effort" for GL is strongly supported by this file's size and complexity.

---

## Summary of Corrections

| Item | Roadmap Classification | Actual Classification | Reason |
|------|----------------------|---------------------|--------|
| Lead + Opportunity + Quotation | HIGH | MEDIUM | Field counts manageable; no GL dependency; new domain but comparable to Order domain effort |
| Purchase Order | MEDIUM | HIGH | 100+ field submittable DocType; gap-analysis P0 table correctly says HIGH |
| Multi-Currency (Phase 1) | MEDIUM | MEDIUM (correct) but understates GL dependency | Fields + conversion math only in Phase 1; dual-currency GL is Phase 2 |
| BOM/Work Order | HIGH | HIGH (confirmed) | 775 and 745 line DocTypes; minimally viable reduces but full implementation is genuinely high |
| GL | HIGH | MEDIUM (minimally viable) / HIGH (full) | Manual-only GL + Chart of Accounts is medium; auto-GL from all transactions is high |
| Commission Tracking | (Phase 2, not classified) | LOW | Just fields on existing Order domain |
| Customer Group/Territory | (Phase 2, Medium) | LOW | Setup doctypes, tree structure only |
| UTM on Order | (Phase 1 CRM, not standalone) | LOW | Easy standalone addition |
