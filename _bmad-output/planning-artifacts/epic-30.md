# Epic 30: Customer Operations and Omnichannel Engagement

## Epic Goal

Extend UltrERP beyond core back-office transactions into customer-facing commerce and engagement flows: portal access, POS, loyalty, recurring documents, and omnichannel outreach built on top of the CRM, order, and finance foundations.

## Business Value

- Customers gain self-service visibility and faster interaction paths.
- Retail and cash-sale scenarios gain a dedicated POS flow.
- Sales and success teams can retain and re-engage customers with loyalty and recurring-document programs.
- WhatsApp, telephony, and email engagement stop living outside the ERP workflow.

## Scope

**Backend:**
- Customer portal access and document feeds.
- POS invoice and cash-sale workflows.
- Loyalty, recurring-document, and blanket-agreement-ready commercial models.
- Omnichannel engagement records for WhatsApp, telephony, and email campaigns.

**Frontend:**
- Portal-ready views and customer communication history.
- POS interface optimized for high-speed order entry.
- Engagement workbench fed by Epic 23 CRM data and Epic 28 contacts.

**Data Model:**
- Portal-access roles and document visibility rules.
- POS payment and session context.
- Loyalty balances, recurring-document schedules, and engagement logs.

## Non-Goals

- Replacing LINE integrations already in place.
- Full call-center workforce scheduling.
- Marketing-automation parity with dedicated campaign suites.
- Re-architecting the order or invoice core semantics owned by earlier epics.

## Technical Approach

- Build all customer-facing channels on top of stable CRM, order, contact, and finance records.
- Keep portal and engagement data linked to the same party and contact identities created earlier in the roadmap.
- Treat POS as a fast-path commercial document flow, not a second order system.
- Add recurring automation only where document semantics are already stable.

## Key Constraints

- Epic 23 and Epic 28 are hard prerequisites for meaningful omnichannel engagement.
- Loyalty and recurring documents should not land before finance and order semantics are stable.
- LINE remains a supported channel; new channels extend it rather than replace it.

## Dependency and Phase Order

1. Portal and POS should build on stable customer, order, and payment foundations.
2. Loyalty and recurring documents should build on stable finance and commercial defaults.
3. Omnichannel engagement should use CRM and shared contacts rather than ad hoc phone or email fields.

---

## Story 30.1: Customer Portal and Self-Service Documents

- Add customer-facing access to relevant orders, invoices, payments, and service issues.
- Keep document visibility scoped by customer and contact permissions.
- Surface portal-ready attachments, messages, and status history.

**Acceptance Criteria:**

- Given a customer contact logs in, only that party's permitted documents are visible.
- Given an order, invoice, or issue changes status, the portal reflects it consistently.
- Given a service request or document needs follow-up, the portal provides the right next action.

## Story 30.2: POS and Cash-Sale Operations

- Add a POS-oriented selling surface for rapid item selection, payment capture, and receipt output.
- Keep POS transactions aligned with the same customer, product, tax, and inventory rules used elsewhere.
- Support barcode-friendly entry and session controls.

**Acceptance Criteria:**

- Given a cashier opens a session, items can be sold and paid without using the full order workflow.
- Given stock-controlled items are sold through POS, inventory remains consistent.
- Given finance audits cash sales, the source session and payment details are traceable.

## Story 30.3: Loyalty and Retention Programs

- Add loyalty program definitions, point earning or redemption rules, and customer balances.
- Keep loyalty effects visible on relevant sales documents.
- Preserve auditability of loyalty accrual and usage.

**Acceptance Criteria:**

- Given a loyalty program is active, qualifying sales can earn or redeem points.
- Given a customer views their account, the current loyalty position is understandable.
- Given finance or support reviews a transaction, loyalty impacts remain visible.

## Story 30.4: Recurring Documents and Commercial Agreements

- Add recurring-document schedules and blanket-agreement-ready references for repetitive commercial work.
- Support safe review and generation of recurring invoices or orders.
- Keep recurrence explicit rather than hidden in scheduler-only automation.

**Acceptance Criteria:**

- Given a recurring template exists, the system can generate the next document on schedule with clear lineage.
- Given a recurring schedule changes, future generations respect the new rule without mutating history.
- Given a long-term commercial agreement exists, the generated documents retain the agreement reference.

## Story 30.5: Omnichannel Engagement Workbench

- Start with a delivery-feasibility spike for WhatsApp Business API, telephony provider, and campaign-delivery dependencies.
- Add WhatsApp, telephony call-log, and email-campaign engagement records tied to CRM parties and shared contacts.
- Keep outreach history visible alongside CRM and customer records.
- Support follow-up workflows without requiring external spreadsheets or standalone tools.

**Acceptance Criteria:**

- Given implementation begins, provider auth, limits, and cost assumptions are documented before channel-specific delivery is enabled.
- Given a sales or service user contacts a party over WhatsApp, phone, or email, the interaction is logged against the correct record.
- Given a manager reviews outreach, engagement history is visible across channels in one place.
- Given CRM data changes, engagement history keeps stable party and contact linkage.