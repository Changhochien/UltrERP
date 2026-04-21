# Story 22.2: DatePicker and DateRangePicker Components

**Status:** done

**Story ID:** 22.2

**Epic:** Epic 22 - UI Foundation System: Toast, DatePicker, Breadcrumb, Form Validation, and TanStackDataTable

---

## Story

As a user entering or filtering by dates,
I want a consistent calendar-based date picker across forms and filter bars,
so that date input behaves predictably across browsers and matches the rest of the UI system.

## Acceptance Criteria

1. Given a date field uses the new DatePicker, when the user opens it, then a locale-aware calendar popover appears and remains usable on desktop and mobile browsers including iOS Safari.
2. Given a user selects a date, when the popover closes, then the trigger displays a locale-formatted value using the existing i18n and date-formatting stack.
3. Given a filter bar currently uses separate native from and to date inputs, when it is migrated, then it renders shared calendar-based date-picker controls that preserve the current filtering behavior, including independent lower and upper bounds where the existing UX depends on them.
4. Given the audited `type="date"` fields in the current codebase are migrated, when the story is complete, then the touched forms and filters no longer rely on native browser date inputs.
5. Given the same slice touches global date and chart token styling, when the story is complete, then `--ring` is aligned to the primary token and the chart token set is expanded to a usable categorical palette.

## Tasks / Subtasks

- [x] Task 1: Add the missing date picker dependencies and components. (AC: 1, 2)
  - [x] Add `react-day-picker` to `package.json` and reuse the existing Base UI popover stack instead of adding a second popover library.
  - [x] Create `src/components/ui/DatePicker.tsx` for single-date selection.
  - [x] Create `src/components/ui/DateRangePicker.tsx` for range selection.
- [x] Task 2: Match the existing field and filter styling. (AC: 1, 2)
  - [x] Render the trigger with the current `Input` and `InputGroup` visual language.
  - [x] Keep keyboard support for open, close, and date selection.
  - [x] Use the existing i18n stack and installed `date-fns` dependency for display formatting.
- [x] Task 3: Replace the audited native date inputs. (AC: 3, 4)
  - [x] Migrate `src/components/filters/DateRangeFilter.tsx` to shared calendar-based controls while preserving the existing independent-bound filter semantics.
  - [x] Migrate the current known date inputs in `RecordPaymentForm.tsx`, `RecordUnmatchedPayment.tsx`, `SupplierOrderForm.tsx`, `CreateInvoicePage.tsx`, `CustomerStatementTab.tsx`, and `AdminPage.tsx`.
  - [x] Re-run a repository search for `type="date"` and replace the targeted Story 22.2 surfaces.
- [x] Task 4: Reconcile the shared tokens touched by this slice. (AC: 5)
  - [x] Update `src/index.css` so `--ring` aligns with the primary tone instead of the current neutral placeholder.
  - [x] Replace the current incomplete chart palette with 10 distinct categorical chart tokens.
  - [x] Keep the existing theme structure intact while updating the token values.
- [x] Task 5: Add focused validation coverage. (AC: 1-5)
  - [x] Add component tests for single-date selection, range selection, and locale formatting.
  - [x] Add focused regression coverage for the migrated filter bar and migrated form flows, including non-UTC default-date behavior.
  - [x] Document the validation actually performed for this slice; a dedicated iOS Safari manual smoke test was not run in this session.

## Dev Notes

### Context

- The repo currently relies on native `type="date"` inputs in multiple user-facing forms and filters.
- `date-fns` is already installed and can support locale formatting.
- No reusable DatePicker or DateRangePicker component exists today.

### Architecture Compliance

- Keep the trigger visually aligned with the existing `Input` and `Field` system.
- Use a popover-based calendar rather than leaving native date input behavior in place.
- Preserve the current filter semantics while consolidating the filter-bar date UX.

### Implementation Guidance

- Primary files:
  - `package.json`
  - `src/components/ui/DatePicker.tsx`
  - `src/components/ui/DateRangePicker.tsx`
  - `src/components/filters/DateRangeFilter.tsx`
  - `src/domain/payments/components/RecordPaymentForm.tsx`
  - `src/domain/payments/components/RecordUnmatchedPayment.tsx`
  - `src/domain/inventory/components/SupplierOrderForm.tsx`
  - `src/pages/invoices/CreateInvoicePage.tsx`
  - `src/components/customers/CustomerStatementTab.tsx`
  - `src/pages/AdminPage.tsx`
  - `src/index.css`
- If extending `src/components/ui/field.tsx` is low-risk in this slice, prefer that over bespoke date-field wrappers.
- Keep calendar behavior accessible and avoid introducing a mobile-only fork.

### Testing Requirements

- Frontend component coverage is required.
- Verify the repository no longer depends on native date inputs in the touched slice.
- Confirm locale formatting for at least English plus one non-English locale already configured in the app.

### References

- `package.json`
- `src/components/ui/field.tsx`
- `src/components/ui/input.tsx`
- `src/components/filters/DateRangeFilter.tsx`
- `src/domain/payments/components/RecordPaymentForm.tsx`
- `src/domain/payments/components/RecordUnmatchedPayment.tsx`
- `src/domain/inventory/components/SupplierOrderForm.tsx`
- `src/pages/invoices/CreateInvoicePage.tsx`
- `src/components/customers/CustomerStatementTab.tsx`
- `src/pages/AdminPage.tsx`
- `src/index.css`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `TZ=America/Los_Angeles pnpm vitest run src/tests/ui/DatePicker.test.tsx src/tests/filters/DateRangeFilter.test.tsx src/tests/payments/RecordPaymentForm.test.tsx src/tests/payments/RecordUnmatchedPayment.test.tsx src/tests/inventory/SupplierOrderForm.test.tsx src/pages/invoices/CreateInvoicePage.test.tsx src/pages/AdminPage.test.tsx src/tests/customers/CustomerStatementTab.test.tsx`
- `pnpm eslint src/lib/time.ts src/components/ui/date-picker-utils.ts src/components/ui/DatePicker.tsx src/components/ui/DateRangePicker.tsx src/components/filters/DateRangeFilter.tsx src/domain/payments/components/RecordPaymentForm.tsx src/domain/payments/components/RecordUnmatchedPayment.tsx src/domain/inventory/components/SupplierOrderForm.tsx src/pages/invoices/CreateInvoicePage.tsx src/components/customers/CustomerStatementTab.tsx src/pages/AdminPage.tsx src/tests/ui/DatePicker.test.tsx src/tests/filters/DateRangeFilter.test.tsx src/tests/payments/RecordPaymentForm.test.tsx src/tests/payments/RecordUnmatchedPayment.test.tsx src/tests/inventory/SupplierOrderForm.test.tsx src/pages/invoices/CreateInvoicePage.test.tsx src/pages/AdminPage.test.tsx src/tests/customers/CustomerStatementTab.test.tsx`
- `TZ=America/Los_Angeles pnpm vitest run src/pages/AdminPage.test.tsx`
- `pnpm eslint src/pages/AdminPage.tsx`

### Completion Notes List

- Reused the existing Base UI popover and input stack, added `react-day-picker`, and introduced shared `DatePicker` and `DateRangePicker` components plus `date-picker-utils` helpers for locale-aware formatting and local-calendar serialization.
- Migrated the audited Story 22.2 native date inputs in payment, unmatched payment, supplier order, invoice creation, customer statement, and admin audit flows; filter-style surfaces that depended on independent lower and upper bounds were kept as paired single-date pickers instead of being forced into one range-selection interaction.
- Fixed date-only correctness at the UI boundary by parsing calendar strings locally, updated `appTodayISO()` to honor `Asia/Taipei`, and removed UTC-slicing defaults from Admin and CustomerStatement flows.
- Localized picker placeholder and clear affordances in English and `zh-Hant`, aligned `--ring` to the primary tone, and expanded the chart token palette to a usable categorical set.
- Added focused regression coverage for picker locale formatting, filter semantics, payment and unmatched-payment submission dates, supplier-order and invoice default dates, admin audit defaults, and customer-statement date rendering under a west-of-UTC timezone.
- Final Story 22.2 review returned no blocking issues; the remaining noted risk is that a dedicated manual iOS Safari smoke test was not run in this session.

### File List

- `package.json`
- `pnpm-lock.yaml`
- `src/lib/time.ts`
- `src/components/ui/date-picker-utils.ts`
- `src/components/ui/DatePicker.tsx`
- `src/components/ui/DateRangePicker.tsx`
- `src/components/filters/DateRangeFilter.tsx`
- `src/domain/payments/components/RecordPaymentForm.tsx`
- `src/domain/payments/components/RecordUnmatchedPayment.tsx`
- `src/domain/inventory/components/SupplierOrderForm.tsx`
- `src/pages/invoices/CreateInvoicePage.tsx`
- `src/components/customers/CustomerStatementTab.tsx`
- `src/pages/AdminPage.tsx`
- `src/index.css`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`
- `src/tests/ui/DatePicker.test.tsx`
- `src/tests/filters/DateRangeFilter.test.tsx`
- `src/tests/payments/RecordPaymentForm.test.tsx`
- `src/tests/payments/RecordUnmatchedPayment.test.tsx`
- `src/tests/inventory/SupplierOrderForm.test.tsx`
- `src/pages/invoices/CreateInvoicePage.test.tsx`
- `src/pages/AdminPage.test.tsx`
- `src/tests/customers/CustomerStatementTab.test.tsx`