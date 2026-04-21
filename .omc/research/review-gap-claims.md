# Gap Claims Validation Report

**Reviewer:** review-gaps agent
**Date:** 2026-04-20
**Sources checked:** ERPnext v14/v15 source at `/reference/erpnext-develop/`, UltrERP backend at `/backend/domains/`

---

## Validated Claims (high confidence)

### CRM/Sales

- **Opportunity `party_name` Dynamic Link**: CONFIRMED. Actual `opportunity.json` line 126-134 shows `party_name` with `fieldtype: "Dynamic Link"` and `options: "opportunity_from"`. The gap analysis correctly identified this.

- **Opportunity statuses**: CONFIRMED as "Open/Quotation/Converted/Lost/Replied/Closed" — matches actual `opportunity.json` line 177.

- **Quotation `quotation_to` Dynamic Link**: CONFIRMED. Actual `quotation.json` lines 166-187 show `quotation_to` as `Link` to `DocType` and `party_name` as `Dynamic Link` with `options: "quotation_to"`.

- **Quotation statuses**: CONFIRMED as "Draft/Open/Replied/Partially Ordered/Ordered/Lost/Cancelled/Expired" — matches `quotation.json` line 854.

- **Quotation has auto_repeat**: CONFIRMED. `quotation.json` has `allow_auto_repeat: 1` and `auto_repeat` field.

- **Lead has UTM fields**: CONFIRMED. `lead.json` lines 507-533 show `utm_source`, `utm_medium`, `utm_campaign`, `utm_content` under `utm_analytics_section`.

- **Lead statuses**: CONFIRMED as "Lead/Open/Replied/Opportunity/Quotation/Lost Quotation/Interested/Converted/Do Not Contact" — matches `lead.json` line 151.

### Manufacturing

- **BOM has `bom_operations` table**: CONFIRMED. `bom.json` lines 280-287 show `operations` field with `options: "BOM Operation"`.

- **BOM has `bom_materials` table**: CONFIRMED. `bom.json` lines 294-303 show `items` field with `options: "BOM Item"`.

- **Work Order has operations routing**: CONFIRMED. `work_order.json` lines 346-366 show `operations_section` with `operations` table (`Work Order Operation`).

- **Work Order status machine**: CONFIRMED as "Draft/Submitted/Not Started/In Process/Stock Reserved/Stock Partially Reserved/Completed/Stopped/Closed/Cancelled" — matches `work_order.json` line 119.

### Accounting

- **Journal Entry voucher types**: CONFIRMED. `journal_entry.json` lines 102-108 show 18 voucher types including Bank Entry, Cash Entry, Credit Note, Debit Note, Contra Entry, Exchange Rate Revaluation, Deferred Revenue, etc.

- **accounts_controller.py is large**: CONFIRMED. File is 4,496 lines — a very large base class indeed.

### UltrERP Cross-checks

- **No GL Entry domain**: CONFIRMED. No `backend/domains/gl` or similar exists. The gap analysis correctly identifies this gap.

- **No commission tracking on Order**: CONFIRMED. `backend/domains/orders/schemas.py` has no `commission_rate`, `sales_team`, `total_commission`, or `amount_eligible_for_commission` fields. Order schema is limited to payment_terms_code, lines, pricing.

- **Invoice payment_status field DOES exist**: PARTIALLY CORRECTED below.

---

## Claims That Need Correction

### Lead field count (85 fields)

**Gap analysis claim:** "erpnext/crm/doctype/lead/lead.json — 85 fields including UTM, qualification_status..."

**Actual:** The JSON `fields` array has approximately 50 actual data fields. The remainder are Column Break, Section Break, and Tab Break UI layout elements (~17 of those). A conservative count of actual data-carrying fields is ~50, not 85. The ~85 figure may include label/options/metadata from oldfieldname/oldfieldtype pairs, or may be from a different version.

**Fix:** Revise to "~50 fields (excluding layout elements)" or "roughly 50 data fields".

---

### Purchase Order JSON not found

**Gap analysis claim:** References `erpnext/buying/doctype/purchase_order/purchase_order.json` as evidence for PO field counts and `received_qty`, `po_detail` fields.

**Actual:** That file does NOT exist in the reference checkout. The PO statuses claim is also uncorroborated — the statuses shown ("Draft/On Hold/To Receive and Bill/To Bill/To Receive/Completed/Cancelled/Closed/Delivered") were likely pulled from ERPnext documentation, not the actual JSON.

**Fix:** Note that `purchase_order.json` was not in the reference checkout. The PO description in gap-analysis may be based on secondary sources. Verify against ERPnext repo directly if PO detail is needed.

---

### Purchase Receipt JSON not found

**Gap analysis claim:** "erpnext/buying/doctype/purchase_receipt/purchase_receipt.json — linked to PO via `po_detail`"

**Actual:** This file does NOT exist in the reference checkout at the expected path. The PR linking claim is standard ERPnext behavior but cannot be confirmed from the JSON file directly.

**Fix:** Note that `purchase_receipt.json` was not in the reference checkout.

---

## False Positives (claimed missing but actually exist)

### Invoice partial payment tracking

**Gap analysis claim:** "Invoice really have no partial payment" (invoices domain has no partial payment recording from invoice UI)

**Actual:** The `payment_status` field in the Invoice domain already has `"partial"` as a valid computed value. In `backend/domains/invoices/service.py:1038`, `_compute_payment_status()` returns `"partial"` when sum of payments is greater than 0 but less than total. The invoice service already computes partial payment status.

**Nuance:** The claim "no partial payment" is technically two separate claims:
1. "No UI to record a partial payment FROM the invoice screen" → TRUE (no `Record Partial Payment` button or modal)
2. "No partial payment status tracking" → FALSE (the system already tracks and returns "partial" status)

The gap analysis is partially right but the statement is imprecise. What UltrERP lacks is the UI/action to record a partial payment against an invoice, NOT the computation of partial payment status.

**Fix:** Clarify: "No UI to record/create partial payments from invoice screen, but payment_status=partial is already computed."

---

## False Negatives (claimed missing but actually partially implemented)

### Payment Terms codes on Order

**Gap analysis claim:** "Order domain really have no commission tracking" — correctly identified as missing.

But the same claim row also says "no payment terms template" — this is INCORRECTLY flagged. The Order schema has `PaymentTermsCode` enum (NET_30, NET_60, COD) and `payment_terms_code` + `payment_terms_days` fields. Payment terms ARE implemented.

**Fix:** Remove payment terms from the "missing" column for Orders. Payment terms codes exist; what doesn't exist is a customizable Payment Terms Template builder (which IS correctly listed as MISSING in Accounting section).

---

## New Information Discovered

### BOM is_submittable = true

`bom.json` has `"is_submittable": 1` — BOMs can be submitted in ERPnext, which means they have a workflow state (Draft → Submitted). This was not highlighted in the gap analysis but is relevant for UltrERP BOM implementation planning.

### Work Order operation routing options

The Work Order's `transfer_material_against` field (line 356-359) can be set to either "Work Order" or "Job Card". This means ERPnext supports two modes of manufacturing material transfer:
- Against the Work Order itself (simple mode)
- Against Job Cards (detailed operation-level mode)

This distinction matters for UltrERP's manufacturing gap assessment.

### BOM quality inspection integration

`bom.json` has `inspection_required` Check field and `quality_inspection_template` Link field. BOMs can require QI before materials are accepted — this links BOM to the Quality Inspection system.

### Journal Entry supports TDS/tax withholding

`journal_entry.json` has `apply_tds` Check and `tax_withholding_category`/`tax_withholding_entries` fields — manual journal entries can have TDS applied. This is a nuance not covered in the gap analysis.

### accounts_controller.py size significance

At 4,496 lines, this is not a "base controller" in the lightweight sense. It handles GL entry creation, outstanding calculation, advance allocation, validation of party accounts, currency, taxes, payment schedule, due date, and pricing rules. Any UltrERP accounting implementation will need to address this complexity incrementally — it cannot be replaced with a single equivalent.

---

## Summary

| Claim Type | Count | Notes |
|---|---|---|
| **Validated correct** | 12 | Dynamic Links, statuses, UTM, BOM operations, JE voucher types |
| **Needs correction** | 3 | Lead field count (~50 not 85), PO JSON not in ref, PR JSON not in ref |
| **False positive** | 1 | Invoice partial payment status already computed |
| **False negative** | 1 | Order payment terms codes already exist |
| **New discovery** | 4 | BOM is_submittable, WO Job Card routing, BOM QI integration, JE TDS, accts_controller size |
