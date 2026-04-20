# Story 22.4: Zod Schema Centralization and Form Migration

**Status:** ready-for-dev

**Story ID:** 22.4

**Epic:** Epic 22 - UI Foundation System: Toast, DatePicker, Breadcrumb, Form Validation, and TanStackDataTable

---

## Story

As a developer and operator working across UltrERP forms,
I want shared Zod-backed frontend schemas and a consistent react-hook-form pattern,
so that validation rules stay aligned with backend contracts and the same UX rules apply across forms.

## Acceptance Criteria

1. Given the frontend schema layer exists, when a domain form needs validation, then it can import a shared Zod schema from `src/lib/schemas/`.
2. Given `CustomerForm` already uses `react-hook-form`, when this story is implemented, then it switches from the current custom resolver to `zodResolver` without regressing its existing field UX.
3. Given either payment-recording form is submitted with invalid data, when the user clicks submit, then inline field errors appear and no API call is made.
4. Given either payment-recording form succeeds or fails, when the server responds, then the form uses the new validation stack together with toast feedback and consistent loading behavior.
5. Given a backend Pydantic schema changes for a touched domain, when the frontend schema is updated, then the field names and contract shape remain aligned rather than drifting.

## Tasks / Subtasks

- [ ] Task 1: Add the shared schema dependencies and directory structure. (AC: 1)
  - [ ] Add `zod` and `@hookform/resolvers` to `package.json`.
  - [ ] Create `src/lib/schemas/`.
  - [ ] Add the initial schema files for customer, invoice, order, payment, product, and supplier domains.
- [ ] Task 2: Migrate the existing react-hook-form customer pattern to Zod. (AC: 1, 2)
  - [ ] Replace the custom native resolver in `src/components/customers/CustomerForm.tsx` with `zodResolver`.
  - [ ] Keep the existing `Field`, `FieldLabel`, and `FieldError` composition intact.
  - [ ] Preserve current trimming and Taiwan business-number validation behavior while deciding whether the checksum stays in schema refinement or in a dedicated validation helper.
- [ ] Task 3: Migrate the payment forms as one consistent slice. (AC: 3, 4)
  - [ ] Create the shared payment schema and inferred form values.
  - [ ] Migrate `src/domain/payments/components/RecordPaymentForm.tsx` to `react-hook-form` plus `zodResolver`.
  - [ ] Migrate `src/domain/payments/components/RecordUnmatchedPayment.tsx` in the same slice so both payment flows share the same validation conventions, date picker usage, spinner usage, and toast behavior.
- [ ] Task 4: Migrate the remaining priority forms in repo order. (AC: 1, 5)
  - [ ] Prioritize `OrderForm.tsx`, `ProductForm.tsx`, `SupplierForm.tsx`, `StockAdjustmentForm.tsx`, `SupplierOrderForm.tsx`, `CreateInvoicePage.tsx`, `EditCustomerDialog.tsx`, `CustomerCombobox` quick-create, and `ProductCombobox` quick-create.
  - [ ] When migrating `OrderForm.tsx`, preserve the customer-linked intake and confirmation workflow semantics already defined by Epic 21.2.
  - [ ] Land these migrations in reviewable slices if necessary, but keep the schema layer coherent.
- [ ] Task 5: Audit backend-contract parity for touched domains. (AC: 5)
  - [ ] Compare the touched frontend schema fields against `backend/domains/*/schemas.py`.
  - [ ] Fix or document any field-name divergence immediately because the API contract is the source of truth.
- [ ] Task 6: Add focused validation coverage. (AC: 1-5)
  - [ ] Add tests around the payment forms and at least one other migrated form.
  - [ ] Add schema-level coverage for the most error-prone refinements.
  - [ ] Preserve existing regression coverage for customer creation and payment submission behavior.

## Dev Notes

### Context

- `react-hook-form` is already installed.
- `CustomerForm` already uses `react-hook-form`, but it still relies on a custom native resolver.
- Most other forms in the repo still use raw `useState` patterns today.
- The revised Epic 22 scope explicitly requires matched and unmatched payment forms to be migrated together.

### Architecture Compliance

- Keep shared schema files under `src/lib/schemas/` rather than scattering them across domains.
- Reuse the existing `Field` compound component pattern for inline errors and labels.
- Treat backend Pydantic field names as the contract source of truth.

### Implementation Guidance

- Primary files:
  - `package.json`
  - `src/lib/schemas/*.schema.ts`
  - `src/components/customers/CustomerForm.tsx`
  - `src/domain/payments/components/RecordPaymentForm.tsx`
  - `src/domain/payments/components/RecordUnmatchedPayment.tsx`
  - the remaining forms listed in the task section
  - `backend/domains/*/schemas.py` for touched domains
- If a form-specific validation helper already exists and is still useful, keep it only if the schema can call it cleanly instead of duplicating business rules.
- Use the toast system and spinner introduced in other Epic 22 stories rather than inventing custom submission feedback.
- Treat `OrderForm.tsx` as a form-architecture migration, not as the place to redefine order-domain behavior already owned by Epic 21.

### Testing Requirements

- Frontend form tests plus any targeted backend-contract verification are required.
- Preserve existing customer validation behavior while switching the resolver implementation.
- Ensure both payment forms reject invalid submissions before hitting the API.

### References

- `package.json`
- `src/components/customers/CustomerForm.tsx`
- `src/domain/payments/components/RecordPaymentForm.tsx`
- `src/domain/payments/components/RecordUnmatchedPayment.tsx`
- `src/domain/orders/components/OrderForm.tsx`
- `src/domain/inventory/components/ProductForm.tsx`
- `src/domain/inventory/components/SupplierForm.tsx`
- `src/domain/inventory/components/StockAdjustmentForm.tsx`
- `src/domain/inventory/components/SupplierOrderForm.tsx`
- `src/pages/invoices/CreateInvoicePage.tsx`
- `src/components/customers/EditCustomerDialog.tsx`
- `src/components/customers/CustomerCombobox.tsx`
- `src/components/products/ProductCombobox.tsx`
- `backend/domains/customers/schemas.py`
- `backend/domains/payments/schemas.py`
- `backend/domains/orders/schemas.py`
- `backend/domains/inventory/schemas.py`
- `backend/domains/invoices/schemas.py`

## Dev Agent Record

### Agent Model Used

Record the implementation model and version here.

### Debug Log References

Record focused frontend and backend validation commands here.

### Completion Notes List

Summarize the shared schema layer, the migrated forms, and any field-name parity decisions here once implementation is done.

### File List

- `package.json`
- `src/lib/schemas/*.schema.ts`
- touched frontend form files
- any shared form utilities introduced for the migration
- focused frontend tests for migrated forms