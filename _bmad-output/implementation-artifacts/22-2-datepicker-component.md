# Story 22.2: DatePicker and DateRangePicker Components

**Status:** ready-for-dev

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
3. Given a filter bar currently uses separate native from and to date inputs, when it is migrated, then it renders a single DateRangePicker experience that preserves the current filtering behavior.
4. Given the audited `type="date"` fields in the current codebase are migrated, when the story is complete, then the touched forms and filters no longer rely on native browser date inputs.
5. Given the same slice touches global date and chart token styling, when the story is complete, then `--ring` is aligned to the primary token and the chart token set is expanded to a usable categorical palette.

## Tasks / Subtasks

- [ ] Task 1: Add the missing date picker dependencies and components. (AC: 1, 2)
  - [ ] Add `react-day-picker` and `@radix-ui/react-popover` to `package.json`.
  - [ ] Create `src/components/ui/DatePicker.tsx` for single-date selection.
  - [ ] Create `src/components/ui/DateRangePicker.tsx` for range selection.
- [ ] Task 2: Match the existing field and filter styling. (AC: 1, 2)
  - [ ] Render the trigger with the current `Input` and `InputGroup` visual language.
  - [ ] Keep keyboard support for open, close, and date selection.
  - [ ] Use the existing i18n stack and installed `date-fns` dependency for display formatting.
- [ ] Task 3: Replace the audited native date inputs. (AC: 3, 4)
  - [ ] Migrate `src/components/filters/DateRangeFilter.tsx` to `DateRangePicker`.
  - [ ] Migrate the current known date inputs in `RecordPaymentForm.tsx`, `RecordUnmatchedPayment.tsx`, `SupplierOrderForm.tsx`, `CreateInvoicePage.tsx`, `CustomerStatementTab.tsx`, and `AdminPage.tsx`.
  - [ ] Re-run a repository search for `type="date"` and either replace the remaining hits or document why a specific one is intentionally deferred.
- [ ] Task 4: Reconcile the shared tokens touched by this slice. (AC: 5)
  - [ ] Update `src/index.css` so `--ring` aligns with the primary tone instead of the current neutral placeholder.
  - [ ] Replace the current incomplete chart palette with 10 distinct categorical chart tokens.
  - [ ] Keep the existing theme structure intact while updating the token values.
- [ ] Task 5: Add focused validation coverage. (AC: 1-5)
  - [ ] Add component tests for single-date selection, range selection, and locale formatting.
  - [ ] Add focused regression coverage for the migrated filter bar and one migrated form.
  - [ ] Validate iOS Safari behavior manually or document the exact browser smoke test performed.

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

Record the implementation model and version here.

### Debug Log References

Record focused frontend test commands and any browser smoke tests here.

### Completion Notes List

Summarize the component API, the migrated fields, and the token updates here once implementation is done.

### File List

- `package.json`
- `src/components/ui/DatePicker.tsx`
- `src/components/ui/DateRangePicker.tsx`
- `src/components/filters/DateRangeFilter.tsx`
- any migrated date-field consumers
- `src/index.css`
- any focused frontend tests added for date picker behavior