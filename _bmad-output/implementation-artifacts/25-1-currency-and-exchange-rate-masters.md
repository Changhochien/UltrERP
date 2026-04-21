# Story 25.1: Currency and Exchange-Rate Masters

Status: drafted

## Story

As a finance or commercial operations user,
I want first-class currency definitions and effective-dated exchange rates,
so that sales, procurement, invoicing, and payments can resolve consistent conversion rates without mutating historical records.

## Problem Statement

UltrERP already stores `currency_code` on several transactional records and imports default currency metadata into `app_settings`, but there is no reusable currency master or effective-dated exchange-rate service. Epic 25 requires a shared foundation for transaction currency fields, conversion math, and display formatting. Without that master layer, each domain would improvise rate lookup, fallback behavior, and decimal precision independently.

## Solution

Add a currency-foundation slice that:

- turns supported currencies into first-class master data with symbol, precision, and active-state metadata
- stores effective-dated exchange rates against the tenant base currency or supported currency pairs
- exposes a reusable exchange-rate resolution service for later stories in quotations, orders, POs, invoices, and payments
- preserves historical transaction behavior by snapshotting the applied rate at document creation time rather than mutating old rows when new rates are added

This story should create the currency and rate foundation, not add full dual-currency GL entries or exchange-rate revaluation.

## Acceptance Criteria

1. Given finance maintains supported currencies, when currency masters are viewed or edited, then code, symbol, decimal precision, active state, and base-currency designation are stored in a dedicated reusable model.
2. Given a transaction is authored in a non-base currency, when the system resolves an exchange rate, then it can find the effective rate by date through a reusable lookup service.
3. Given no custom rate exists for a foreign-currency transaction, when the lookup runs, then the user sees a deterministic fallback path such as base-currency identity, configured default, or explicit validation error rather than silent guessing.
4. Given finance adds a new exchange rate today, when historical documents are viewed later, then the old documents keep their previously applied rate snapshots and are not recomputed silently.
5. Given this story is implemented, when the touched code is reviewed, then no dual-currency GL posting, unrealized gain or loss booking, or exchange-rate revaluation workflow is implemented in this foundation slice.

## Tasks / Subtasks

- [ ] Task 1: Add currency and exchange-rate master models. (AC: 1-4)
  - [ ] Create a tenant-scoped currency master with code, symbol, decimal precision, active flag, and a single base-currency designation per tenant.
  - [ ] Create a tenant-scoped exchange-rate master with `source_currency_code`, `target_currency_code`, `effective_date`, and a decimal rate value with sufficient precision for FX conversion.
  - [ ] Preserve compatibility with existing `app_settings` currency metadata and legacy currency import seeds during rollout, using `currency.default` as the initial base-currency seed until the master layer is authoritative.
- [ ] Task 2: Implement reusable exchange-rate resolution services. (AC: 2-4)
  - [ ] Add a shared service that resolves the effective rate for a requested date and currency pair.
  - [ ] Define deterministic fallback behavior in this order: same-currency identity rate, latest active exact currency pair on or before the requested date, documented configured fallback for that pair if present, else validation error.
  - [ ] Reject inactive currencies and unsupported currency pairs deterministically rather than inferring inverse or triangulated rates silently.
  - [ ] Return enough metadata for later stories to snapshot the applied rate, source rule, and effective date on transactional documents.
- [ ] Task 3: Build currency and exchange-rate maintenance surfaces. (AC: 1-3)
  - [ ] Add finance-facing CRUD or maintenance flows for currencies and exchange rates.
  - [ ] Surface base-currency designation, active flags, and rate-effective dates clearly.
  - [ ] Reuse Epic 22 shared table, form, breadcrumb, and feedback patterns.
- [ ] Task 4: Add rollout compatibility and documentation seams. (AC: 1-4)
  - [ ] Map existing `currency.default` and per-currency symbol or decimal settings into the new master layer or a compatibility view.
  - [ ] Keep `app_settings` as a compatibility fallback during rollout, but document that the new tenant-scoped currency master becomes the authoritative source once seeded.
  - [ ] Keep existing `currency_code` fields on invoices, supplier invoices, and supplier payments readable without migration breakage.
  - [ ] Defer adding new currency fields to orders and other commercial documents to Story 25.2.
  - [ ] Document how later document stories should snapshot applied conversion rates rather than recomputing them on read.
- [ ] Task 5: Add focused tests and validation. (AC: 1-5)
  - [ ] Add backend tests for effective-date lookup, base-currency fallback, missing-rate validation, inactive-currency handling, and historical immutability.
  - [ ] Add frontend tests for finance maintenance flows and validation feedback.
  - [ ] Validate that no GL revaluation or posting automation lands in this story.

## Dev Notes

### Context

- The validated roadmap is explicit that Phase 1 multi-currency stays medium effort only by avoiding dual-currency GL automation.
- Legacy import already seeds `currency.default` plus symbol and decimal settings into `app_settings`.
- Several current models already carry `currency_code`, but there is no common exchange-rate source of truth yet.

### Architecture Compliance

- Treat this story as the shared currency foundation for Epic 25, not a finance-posting feature.
- Preserve backward compatibility for existing base-currency records and current `currency_code` fields.
- Centralize rate lookup and currency metadata so later document stories do not reimplement conversion logic.
- Snapshot applied rates on transaction creation in later stories; do not recompute historical documents from current rates.

### Implementation Guidance

- Likely backend files:
  - `backend/domains/settings/models.py` or a dedicated commercial-foundations domain for currency masters
  - new exchange-rate models and schemas in the same domain
  - shared services used by orders, invoices, purchases, and payments
  - migrations under `migrations/versions/`
- Likely frontend files:
  - finance or settings-facing master-data screens under `src/domain/`
  - shared API clients for currency and exchange-rate maintenance
- If the existing `app_settings` data remains the canonical seed source during rollout, expose a migration or sync path rather than duplicating divergent defaults.
- Base currency should always resolve at rate `1` for same-currency conversions.
- Exchange-rate storage should use explicit source and target currency codes plus a high-precision decimal rate, for example a `Numeric` scale suitable for FX rather than a low-precision float.
- Story 25.1 owns master-data precision and lookup semantics; Story 25.5 owns cross-document rounding, formatting, and audit presentation rules.

### Testing Requirements

- Backend tests should cover tenant isolation, effective-date lookup ordering, same-currency identity resolution, and historical rate immutability.
- Frontend tests should cover validation around duplicate effective dates or invalid currency pairs.
- If new translation keys are added, locale files should stay synchronized.

### References

- `../planning-artifacts/epic-25.md`
- `ERPnext-Validated-Research-Report.md`
- `.omc/research/review-roadmap.md`
- `.omc/research/review-gap-claims.md`
- `.omc/research/gap-analysis.md`
- `backend/domains/legacy_import/currency.py`
- `backend/domains/settings/models.py`
- `backend/common/models/order.py`
- `backend/domains/invoices/models.py`
- `backend/common/models/supplier_invoice.py`
- `backend/common/models/supplier_payment.py`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- Story draft only; implementation and validation commands not run yet.

### Completion Notes List

- 2026-04-21: Drafted Story 25.1 from Epic 25, the validated multi-currency research, and the current currency-setting and `currency_code` seams so later commercial documents can share one exchange-rate source of truth.

### File List

- `_bmad-output/implementation-artifacts/25-1-currency-and-exchange-rate-masters.md`