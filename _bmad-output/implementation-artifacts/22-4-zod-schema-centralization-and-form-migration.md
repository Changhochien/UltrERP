# Story 22.4: Zod Schema Centralization and Form Migration

**Status:** done

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

- [x] Task 1: Add the shared schema dependencies and directory structure. (AC: 1)
  - [x] Add `zod` and `@hookform/resolvers` to `package.json`.
  - [x] Create `src/lib/schemas/`.
  - [x] Add the initial schema files for customer, invoice, order, payment, product, supplier, stock-adjustment, and supplier-order domains.
- [x] Task 2: Migrate the existing react-hook-form customer pattern to Zod. (AC: 1, 2)
  - [x] Replace the custom native resolver in `src/components/customers/CustomerForm.tsx` with `zodResolver`.
  - [x] Keep the existing `Field`, `FieldLabel`, and `FieldError` composition intact.
  - [x] Preserve current trimming and Taiwan business-number validation behavior through the shared customer schema.
- [x] Task 3: Migrate the payment forms as one consistent slice. (AC: 3, 4)
  - [x] Create the shared payment schema and inferred form values.
  - [x] Migrate `src/domain/payments/components/RecordPaymentForm.tsx` to `react-hook-form` plus `zodResolver`.
  - [x] Migrate `src/domain/payments/components/RecordUnmatchedPayment.tsx` in the same slice so both payment flows share the same validation conventions, date picker usage, spinner usage, and toast behavior.
- [x] Task 4: Migrate the remaining shipped priority forms in reviewable slices. (AC: 1, 5)
  - [x] Migrate `OrderForm.tsx`, `ProductForm.tsx`, `SupplierForm.tsx`, `StockAdjustmentForm.tsx`, `SupplierOrderForm.tsx`, and the customer quick-create validation path to shared schemas and payload mappers.
  - [x] Preserve the customer-linked intake and confirmation workflow semantics in `OrderForm.tsx`.
  - [x] Land the invoice schema and the remaining form migrations as coherent reviewable slices across the Story 22.4 commit sequence.
- [x] Task 5: Audit backend-contract parity for touched domains. (AC: 5)
  - [x] Compare the touched frontend schema fields against the current backend/API contracts for the touched domains.
  - [x] Fix or document field-shape divergence through shared payload mappers and schema helpers.
- [x] Task 6: Add focused validation coverage. (AC: 1-5)
  - [x] Add tests around the payment forms and additional migrated inventory/customer/order schema slices.
  - [x] Add schema-level coverage for the most error-prone refinements.
  - [x] Preserve regression coverage for customer creation and payment submission behavior.

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

GPT-5.4

### Debug Log References

- `pnpm vitest run src/tests/customers/CustomerForm.test.tsx src/domain/payments/__tests__/RecordPaymentForm.test.tsx src/domain/payments/__tests__/RecordUnmatchedPayment.test.tsx src/tests/schemas/formSchemas.test.ts src/tests/orders/OrderCommissionEntry.test.tsx src/tests/customers/CustomerCombobox.test.tsx src/tests/inventory/ProductForm.test.tsx src/tests/inventory/SupplierForm.test.tsx src/domain/inventory/components/StockAdjustmentForm.test.tsx`

### Completion Notes List

- Introduced shared Zod-backed schema modules for customers, payments, orders, invoices, products, suppliers, stock adjustments, and supplier orders under `src/lib/schemas/`, plus shared form-error collection helpers.
- Migrated `CustomerForm`, payment recording flows, `OrderForm`, `ProductForm`, `SupplierForm`, `StockAdjustmentForm`, `SupplierOrderForm`, and the customer quick-create validation path to use shared schema parsing and contract-preserving payload mappers.
- Preserved existing UX semantics in the touched flows, including Taiwan business-number validation, order commission entry behavior, and customer duplicate-selection handling.
- Refreshed focused regression coverage across customer, payment, order, schema, and inventory form surfaces; the current focused Story 22.4 suite passed with `29/29` tests.

### File List

- `package.json`
- `pnpm-lock.yaml`
- `src/components/customers/CustomerForm.tsx`
- `src/components/customers/CustomerCombobox.tsx`
- `src/domain/payments/components/RecordPaymentForm.tsx`
- `src/domain/payments/components/RecordUnmatchedPayment.tsx`
- `src/domain/orders/components/OrderForm.tsx`
- `src/domain/inventory/components/ProductForm.tsx`
- `src/domain/inventory/components/StockAdjustmentForm.tsx`
- `src/domain/inventory/components/SupplierForm.tsx`
- `src/domain/inventory/components/SupplierOrderForm.tsx`
- `src/lib/collectFormErrorMessages.ts`
- `src/lib/schemas/customer.schema.ts`
- `src/lib/schemas/payment.schema.ts`
- `src/lib/schemas/order.schema.ts`
- `src/lib/schemas/invoice.schema.ts`
- `src/lib/schemas/product.schema.ts`
- `src/lib/schemas/stock-adjustment.schema.ts`
- `src/lib/schemas/supplier.schema.ts`
- `src/lib/schemas/supplier-order.schema.ts`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`
- `backend/domains/orders/mcp.py`
- `src/domain/payments/__tests__/RecordPaymentForm.test.tsx`
- `src/domain/payments/__tests__/RecordUnmatchedPayment.test.tsx`
- `src/tests/customers/CustomerForm.test.tsx`
- `src/tests/customers/CustomerCombobox.test.tsx`
- `src/tests/orders/OrderCommissionEntry.test.tsx`
- `src/tests/inventory/ProductForm.test.tsx`
- `src/tests/inventory/SupplierForm.test.tsx`
- `src/domain/inventory/components/StockAdjustmentForm.test.tsx`
- `src/tests/schemas/formSchemas.test.ts`