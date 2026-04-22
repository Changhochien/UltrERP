# Epic 23: CRM Foundation and Quotation Pipeline

## Epic Goal

Close the validated pre-sale gap by giving UltrERP a lead, opportunity, and quotation pipeline that hands off cleanly into the existing customer and order workflows instead of forcing sales teams to jump straight from customer master data to confirmed orders.

## Business Value

- Sales can track prospects before they become customers.
- Opportunities and quotations become first-class commercial records instead of offline spreadsheets.
- Epic 21 gains a clean quotation-to-order integration point without inheriting CRM scope.
- UTM and sales-stage data can drive attribution and pipeline reporting.

## Scope

**Backend:**
- New CRM domain covering Lead, Opportunity, Quotation, Sales Stage, and supporting CRM settings/masters.
- Dynamic-party selection patterns for linking quotations and opportunities to leads, prospects, or customers.
- Conversion flows from lead to opportunity, quotation, customer, and order handoff.

**Frontend:**
- CRM workspace with list, detail, and funnel views for leads, opportunities, and quotations.
- Quotation authoring and revision workflow using Epic 22 form primitives.
- Shared customer and order handoff views that preserve Epic 21 order semantics.

**Data Model:**
- Lead attribution, qualification, territory, and communication fields.
- Opportunity probability, expected close date, amount, and stage fields.
- Quotation validity, lost reasons, pricing, taxes, and status history.

## Non-Goals

- Full ERPnext sales-controller parity on day one.
- Finance-side GL posting or revenue recognition.
- Replacing Epic 21 order confirmation semantics.
- Marketing automation beyond the minimum CRM data needed for later engagement epics.

## Technical Approach

- Treat Lead, Opportunity, and Quotation as pre-financial documents with independent state machines.
- Reuse existing customer, product, and tax foundations where possible rather than cloning order logic.
- Keep quotation-to-order conversion additive: the order domain stays authoritative once the order exists.
- Start quotations in the existing base-currency model and let Epic 25 add cross-currency behavior without changing the CRM write model.
- Start with direct, explicit conversion flows instead of a generalized document-mapper abstraction.

## Key Constraints

- The roadmap correction stands: this is medium effort, not high, and it should not wait for GL.
- CRM must consume Epic 22 toast, breadcrumb, date, and Zod primitives rather than inventing new local patterns.
- Contact capture may start CRM-local, but the model must be compatible with Epic 28 shared contacts.

## Dependency and Phase Order

1. Land the shared Epic 22 UI blockers first.
2. Implement Lead and Opportunity before Quotation-to-Order conversion.
3. Keep Epic 21 integration at the handoff boundary only.
4. Let later engagement work in Epic 30 extend these CRM records instead of redefining them.

---

## Story 23.1: Lead Capture, Deduplication, and Qualification

- Add lead records with status, lead owner, territory, source, and UTM attribution fields.
- Support dedupe checks against existing customers and previously captured leads.
- Allow conversion-ready qualification states without forcing customer creation too early.

**Acceptance Criteria:**

- Given a new prospect is entered, the system stores lead status, source, and attribution cleanly.
- Given a duplicate business identity or contact is detected, the UI surfaces merge or reuse guidance.
- Given a lead advances, the system can convert it to an opportunity or customer without data loss.

## Story 23.2: Opportunity Pipeline and Dynamic Party Linking

- Add opportunity records linked to either a lead, prospect, or customer.
- Track sales stage, probability, expected close, currency, and estimated amount.
- Preserve history for lost, closed, replied, and converted outcomes.

**Acceptance Criteria:**

- Given a user creates an opportunity from a lead, the linked party remains traceable.
- Given a probability or stage changes, list and dashboard views reflect the updated pipeline state.
- Given an opportunity is lost or converted, reporting remains historically accurate.

## Story 23.3: Quotation Authoring and Lifecycle

- Add quotation records with validity date, item lines, taxes, notes, and lost-reason tracking.
- Include quotation auto-repeat hooks and scheduling metadata for recurring commercial offers.
- Support quotation states such as draft, open, replied, ordered, lost, cancelled, and expired.
- Make quotation revisions explicit rather than silently overwriting commercial offers.

**Acceptance Criteria:**

- Given a quotation is authored, the customer or lead target is explicit and valid-till is tracked.
- Given a quotation is configured to recur, the schedule metadata is stored without bypassing review or approval controls.
- Given a quotation expires or is lost, the reason and final state remain reportable.
- Given a quotation is reopened or revised, prior commercial context is still visible.

## Story 23.4: Quotation-to-Order Conversion and Commercial Handoff

- Convert accepted quotations into the existing order intake flow without bypassing Epic 21 behavior.
- Carry forward party, lines, taxes, notes, and relevant payment-term defaults.
- Preserve quotation lineage on the resulting order for reporting and audit.

**Acceptance Criteria:**

- Given an accepted quotation, a user can create a pending order without rekeying the commercial data.
- Given the converted order is later confirmed, Epic 21 invoice and stock-reservation semantics still apply.
- Given a quotation is partially converted, the remaining commercial state stays explicit.

## Story 23.5: CRM Setup Masters and Pipeline Reporting

- Add sales stages, territory, customer group, and basic CRM settings.
- Provide pipeline views for open leads, active opportunities, open quotations, lost reasons, and segment filters.
- Expose explicit UTM attribution fields and reporting hooks for later engagement and analytics epics.

**Acceptance Criteria:**

- Given CRM setup records are configured, new records use them consistently.
- Given a sales manager filters the pipeline, open work and drop-off reasons are visible by stage, territory, or customer group.
- Given a lead or opportunity is captured from an attributed source, UTM source, medium, campaign, and content remain reportable.
- Given Epic 30 later adds outreach channels, the CRM records already expose stable party and attribution fields.

## Story 23.6: UTM Tracking and Marketing Attribution

- Add comprehensive UTM parameter capture on all lead and opportunity sources.
- Store utm_source, utm_medium, utm_campaign, utm_content, and utm_term fields on lead records.
- Propagate UTM data through opportunity creation to quotation and order handoff.
- Provide attribution reporting: lead source analysis, conversion by channel, campaign ROI.
- Support first-touch and multi-touch attribution models.

**Acceptance Criteria:**

- Given a lead originates from a marketing campaign URL with UTM parameters, the system captures all five standard UTM fields.
- Given an opportunity is created from a lead, UTM attribution data follows through to the opportunity record.
- Given a sales manager reviews the marketing attribution report, conversion rates by source, medium, and campaign are visible.
- Given a quotation converts to an order, the original UTM attribution remains traceable for revenue attribution.
- Given a lead has multiple interactions across channels, the system can track the full attribution journey.

## Story 23.7: Lead Conversion and Customer Handoff

- Implement complete lead-to-customer conversion workflow with all related records.
- Convert lead to customer with address and contact data migration.
- Create opportunity from lead with qualification data preservation.
- Generate quotation from lead or opportunity with party linkage.
- Track conversion metrics: conversion rate, time-to-conversion, conversion source.
- Support partial conversion (convert to customer only, or to opportunity only).

**Acceptance Criteria:**

- Given a lead is qualified, the system can convert it to a customer without data re-entry.
- Given a lead is converted, all linked contacts, addresses, and communications migrate to the customer record.
- Given an opportunity is created during conversion, historical lead data remains visible.
- Given a lead conversion fails partially, the system preserves successful conversions and surfaces errors.
- Given sales leadership reviews conversion metrics, time-to-conversion and conversion source are reportable.
- Given a lead is converted, the original lead record remains for historical reference with converted status.

## Story 23.8: CRM Reporting and Pipeline Analytics

- Add CRM dashboard with key sales metrics: pipeline value, win rate, conversion rate, average deal size.
- Provide pipeline funnel visualization: leads by stage, conversion drop-off points.
- Build win/loss analysis reports with loss reason categorization.
- Add sales rep performance tracking: assigned leads, opportunities owned, closed revenue.
- Support forecast reporting: expected close by period based on stage probabilities.
- Enable period-over-period comparison for trend analysis.

**Acceptance Criteria:**

- Given a sales manager opens the CRM dashboard, pipeline value, win rate, and conversion rate display prominently.
- Given a pipeline funnel view is requested, the system shows lead volume at each stage with conversion percentages.
- Given a win/loss report is generated, loss reasons are categorized and ranked by frequency.
- Given a sales rep performance report is run, individual metrics for assigned leads, opportunities, and revenue are visible.
- Given a forecast report is generated, expected revenue by period reflects stage probability weighting.
- Given period comparisons are requested, trends in pipeline, win rate, and revenue are visualized.
