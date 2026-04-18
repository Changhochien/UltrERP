# Order Creation UX — Searchable Customer & Product Selection

## Goal

Replace UUID-only text inputs in order creation (and all other creation forms) with searchable, auto-complete combobox selectors for customer and product fields, matching the UX standard already established by `CustomerCombobox`.

---

## Trace Findings

**Root cause (confirmed):** The codebase has a proven UX pattern (`CustomerCombobox`) for searchable customer selection, but:
1. `OrderForm` was never wired to use it — customer field is a raw UUID text input
2. `ProductCombobox` does not exist — no searchable product picker exists anywhere in the system
3. Backend APIs (`listCustomers` with `q` param, `searchProducts`) fully support search — the gap is entirely frontend

**System-wide scope confirmed:** `InvoiceLineEditor` also lacks product selection UX. The gap affects all creation forms, not just orders.

---

## ProductCombobox Component

### Location
`src/components/products/ProductCombobox.tsx` — new reusable component, mirrors `CustomerCombobox` architecture.

### Props interface (target)
```typescript
interface ProductComboboxProps {
  value: string;           // selected product_id
  onChange: (productId: string) => void;
  onClear?: () => void;
  placeholder?: string;
  disabled?: boolean;
}
```

### UX Behavior
- **Trigger**: shows selected product's name/code or placeholder when empty
- **Popover**: opens on click with `Command` pattern (same as `CustomerCombobox`)
- **Search**: debounced 300ms server-side query via `searchProducts(query)`, client-side filter by `name` + `code` + `sku`
- **Results**: show product name, code, SKU, and **inline stock status** (available qty or "Out of stock")
- **Stock shown inline**: each dropdown item shows available quantity — no separate stock check needed
- **Loading state**: spinner during search
- **Empty state**: "No products found" with optional "Create new product" action

---

## CustomerCombobox Integration (OrderForm)

### Change: `src/domain/orders/components/OrderForm.tsx`

Replace the plain `<Input placeholder="Customer UUID">` with `<CustomerCombobox>`:
- Props: `value={customerId}`, `onChange={setCustomerId}`, `onClear={() => setCustomerId("")}`
- Remove `customerId` plain text input
- Wire `onCustomersLoaded` to pre-fill any cached customer list

---

## ProductCombobox Integration (OrderForm)

### Change: `src/domain/orders/components/OrderForm.tsx`

Replace the line item `<Input placeholder="Product UUID">` with `<ProductCombobox>`:
- Props: `value={line.product_id}`, `onChange={(id) => updateLine(idx, { product_id: id })}`
- On selection: auto-populate `description` field from selected product's name
- Remove the `useStockCheck` UUID-length gate — stock is shown inline in dropdown
- After selection: display selected product's name, code, SKU in a read-only info row

---

## Invoice Creation Fix

### Change: `src/domain/invoice/components/InvoiceLineEditor.tsx` (or wherever `product_code` is entered)

Apply the same `ProductCombobox` replacement for the product line item field:
- Replace plain `product_code` text input with `ProductCombobox`
- Auto-populate description on product selection

---

## Inline Customer Creation

### UX Flow
1. User types in `CustomerCombobox` search — results shown
2. If no match: dropdown shows "No customer found — Create new?"
3. Clicking "Create new" opens an inline creation panel (within the same popover or a small modal)
4. **Duplicate prevention**: before creating, check if a customer with same name or business number already exists — warn if so, require confirmation
5. On success: auto-select the newly created customer

### API needed
- If `createCustomer` API does not exist, it may need to be built. Check `src/lib/api/customers.ts`.

---

## System-Wide Audit

Before or during implementation, audit all creation/entry forms for UUID-only inputs:
- [ ] `OrderForm` — customer (UUID → `CustomerCombobox`), product (UUID → `ProductCombobox`)
- [ ] `InvoiceLineEditor` / `CreateInvoicePage` — customer (already uses `CustomerCombobox` ✓), product (plain `product_code` → `ProductCombobox`)
- [ ] Any other creation forms: quote, purchase order, supplier invoice, etc.
- [ ] `CustomerCombobox` usage: audit all current placements (`OrderList`, `InvoiceList`) — confirm consistent behavior

---

## Non-Goals
- No backend API changes required (APIs already support search)
- No change to stock check endpoint semantics
- OrderForm line item structure (`lines[]` array) unchanged — only the product picker UI changes

## Constraints
- `ProductCombobox` must be a **reusable shared component** in `src/components/products/`
- Must match `CustomerCombobox` UX patterns (debounce, popover, Command pattern)
- Frontend-only implementation unless a new `createCustomer` API call is needed

---

## Acceptance Criteria

1. **Customer field** in `OrderForm`: searchable dropdown showing company name + business number, no UUID entry required
2. **Product field** in `OrderForm` line items: searchable dropdown showing name + code + SKU + inline stock, no UUID entry required
3. **Invoice creation**: same UX for customer and product fields
4. **ProductCombobox** is reusable: drop-in component usable in any form
5. **Inline customer creation**: "Create new" option in combobox with duplicate detection
6. **No regression**: existing `OrderForm` validation, submission payload, and `checkStock` flow work unchanged (stock is now shown inline in dropdown; the API call path can be preserved for confirmation-time checks)
7. **All creation forms** audited and updated

---

## Technical Context

### Key files
| File | Change |
|------|--------|
| `src/components/customers/CustomerCombobox.tsx` | Reference pattern |
| `src/components/products/ProductCombobox.tsx` | **New** — reusable combobox |
| `src/domain/orders/components/OrderForm.tsx` | Wire `CustomerCombobox` + `ProductCombobox` |
| `src/domain/invoice/components/InvoiceLineEditor.tsx` | Wire `ProductCombobox` |
| `src/lib/api/inventory.ts` | `searchProducts` — already exists |
| `src/lib/api/customers.ts` | `listCustomers` with `q` — already exists |
| `src/domain/inventory/hooks/useProductSearch.ts` | Reference for debounce/search pattern |

### `useProductSearch` hook (existing)
```typescript
// src/domain/inventory/hooks/useProductSearch.ts
// Already wraps searchProducts with debounce, abort, pagination
// ProductCombobox should use this hook or mirror its pattern
```

### API shapes (already exist)
- `GET /api/v1/customers?q={query}` → `{ customers: [...], total }`
- `GET /api/v1/inventory/products/search?q={query}` → `{ products: [...], total }`
- `POST /api/v1/customers` → may need to check if exists for inline creation

---

## Ontology

| Entity | Current state | Target state |
|--------|-------------|-------------|
| `OrderForm.customerId` | Raw UUID string | Customer object via `CustomerCombobox` |
| `OrderForm.lines[].product_id` | Raw UUID string | Product object via `ProductCombobox` |
| `ProductCombobox` | **Does not exist** | New reusable component |
| `InvoiceLineEditor.product` | Plain text `product_code` | `ProductCombobox` selection |
| `CustomerCombobox` | Exists, used in list filters | Reused in creation forms |

---

## Interview Transcript

- **Scope**: Full system fix — OrderForm, InvoiceLineEditor, all creation forms
- **Product search UX**: Name + code + SKU, inline stock in dropdown
- **Auto-load**: Details load automatically on selection (pricing, stock)
- **Architecture**: New reusable `ProductCombobox` in `src/components/products/`, mirroring `CustomerCombobox`
- **Inline creation**: Add new customer from form with duplicate detection/confirm
- **Constraints**: No constraints — full redesign OK, frontend only (backend APIs sufficient)
