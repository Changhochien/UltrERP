# Epic 25: Multi-Currency, Payment Terms, and Commercial Defaults

## Epic Goal

Add currency-aware commercial foundations and reusable payment-term configuration across sales, purchasing, invoices, and payments without blocking on full dual-currency GL parity.

## Business Value

- International pricing and procurement stop assuming one base currency.
- Payment terms move from hard-coded enums toward reusable business policy.
- Customers and suppliers gain consistent commercial defaults across domains.
- Epic 26 can build finance automation on top of stable currency and term semantics.

## Scope

**Backend:**
- Currency and exchange-rate masters.
- Transaction-level currency fields and conversion-rate handling for orders, quotations, POs, invoices, and payments.
- Payment Terms Template and schedule support.

**Frontend:**
- Currency-aware form inputs, summaries, and display formatting.
- Commercial profile defaults on customer and supplier screens.
- Template-driven payment-term selection in order, quote, and procurement flows.

**Data Model:**
- Currency code, exchange rate, and base-amount fields where needed.
- Payment-term templates with installment schedules and discount windows.
- Customer and supplier commercial defaults for currency, payment terms, and credit-policy-like settings.

## Non-Goals

- Dual-currency GL entries or unrealized gain/loss posting.
- Full finance-book and accounting-dimension parity.
- Regional tax packs.
- Replacing existing order payment-term behavior before compatibility shims exist.

## Technical Approach

- Treat this epic as Phase 1 multi-currency: fields, exchange rates, conversion math, and display behavior only.
- Preserve backwards compatibility for existing base-currency records.
- Replace enum-only payment terms with template-backed defaults while keeping existing order workflows readable.
- Centralize rounding and conversion utilities instead of duplicating them across domains.

## Key Constraints

- The validated report is explicit: Phase 1 multi-currency stays medium effort only by avoiding dual-currency GL automation.
- Existing payment-status and payment-term behavior should be extended, not reinterpreted as missing.
- Shared form work should consume Epic 22 schema and UI primitives.

## Dependency and Phase Order

1. Land currency masters before transaction-level currency fields.
2. Land payment-term templates before replacing enum-only selection in major flows.
3. Feed Epic 26 from these stable currency and term foundations.

---

## Story 25.1: Currency and Exchange-Rate Masters

- Add currency definitions and exchange-rate maintenance.
- Support effective-date lookups and base-currency fallbacks.
- Make exchange-rate resolution reusable across domains.

**Acceptance Criteria:**

- Given a transaction is authored in a foreign currency, the system resolves an effective conversion rate.
- Given no custom rate exists, the user sees a controlled fallback or validation error.
- Given finance updates rates, later transactions use the new effective values without mutating historical rows.

## Story 25.2: Currency-Aware Commercial Documents

- Add currency and conversion-rate fields to quotations, orders, purchase orders, invoices, and payments.
- Store both transaction-facing amounts and normalized base amounts where needed for reporting.
- Keep existing single-currency records fully readable.

**Acceptance Criteria:**

- Given a quotation or PO is created in a non-base currency, totals display in both transaction and base views.
- Given an existing base-currency document is opened, nothing regresses.
- Given downstream reports aggregate values, documented base-amount fields are available.

## Story 25.3: Payment Terms Template Builder and Schedule Handling

- Add reusable payment-term templates with installment schedules, due-date rules, and optional early-payment discounts.
- Replace hard-coded selection where appropriate with template-backed defaults and a compatibility shim for existing enum-coded records.
- Preserve compatibility with existing simple terms during migration.

**Acceptance Criteria:**

- Given finance defines a new term template, sales and procurement users can select it on new documents.
- Given a legacy NET_30 style term is used, existing records remain readable and new records can still map through a documented compatibility path.
- Given a payment schedule is generated, due dates and portions remain explicit.

## Story 25.4: Customer and Supplier Commercial Profiles

- Add default currency, payment terms, and credit/commercial settings to customer and supplier records.
- Apply those defaults when creating quotes, orders, POs, and invoices.
- Keep manual override explicit and auditable.

**Acceptance Criteria:**

- Given a customer has a preferred currency and payment template, new quotes and orders inherit them.
- Given a supplier has procurement defaults, new POs inherit them.
- Given a user overrides a default, the effective value is still visible and traceable.

## Story 25.5: FX Rounding, Display, and Audit Safeguards

- Centralize money formatting, rounding, and conversion rules.
- Expose transaction-to-base conversion details in user-facing and audit views.
- Prevent silent drift between line totals, summaries, and converted amounts.

**Acceptance Criteria:**

- Given a document total is recalculated, displayed and stored converted amounts remain consistent.
- Given finance audits a foreign-currency document, the applied rate and rounding policy are visible.
- Given a conversion mismatch occurs, the system surfaces a deterministic validation failure instead of silently adjusting totals.