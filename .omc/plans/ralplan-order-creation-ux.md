# RALPLAN: Order Creation UX — Searchable Customer & Product Selection

## RALPLAN-DR Summary

### Principles (5)
1. **Mirror proven patterns** — Clone `CustomerCombobox` architecture for `ProductCombobox`; do not invent new UX patterns when established ones exist.
2. **Zero backend changes** — All backend APIs (`listCustomers`, `searchProducts`, `createCustomer`) already support the required functionality; implementation is frontend-only.
3. **Progressive disclosure of complexity** — Stock is shown inline in the dropdown (not in a separate panel), eliminating the need for multi-step lookups.
4. **Inline creation with guardrails** — Customer creation happens inside the combobox popover with backend-supported duplicate detection (HTTP 409 / `createCustomer`); no client-side duplicate checking needed.
5. **Composable, reusable components** — `ProductCombobox` must live in `src/components/products/` and work in any form, not just `OrderForm`.

### Decision Drivers (Top 3)
1. **Existing `CustomerCombobox` UX is the gold standard** — The spec already references it as the pattern to mirror; deviation would introduce inconsistency.
2. **`searchProducts` does NOT return warehouse-specific stock** — `ProductSearchResult.current_stock` is aggregate stock across all warehouses. Per spec ("show stock inline in dropdown"), this aggregate stock is sufficient for the UX.
3. **`createCustomer` has built-in duplicate detection** — HTTP 409 returns `DuplicateInfo` with `existing_customer_id`, `existing_customer_name`, `normalized_business_number`. The inline creation flow must handle this 409 response and surface it as a confirmation prompt.

### Key Type Resolutions

**InvoiceLineEditor / InvoiceDraftLine type mismatch (resolved):**
- `InvoiceDraftLine` (types.ts line 25) has `product_code: string` — a human-readable product code like "WIDGET-001", NOT a UUID. It is MISSING `product_id: string` — this is the field that must be added.
- `InvoiceCreateLinePayload` (types.ts line 6) has BOTH `product_id?: string | null` and `product_code?: string | null`. The backend accepts either field.
- **PRE-REQ (Step 0):** Before wiring `ProductCombobox`, add `product_id: string` to `InvoiceDraftLine` in `src/domain/invoices/types.ts`. Initialize it to `""` in `makeDraftLine()` in `CreateInvoicePage.tsx` (line 36). Add `product_id` to `updateLine` partial merges.
- **Decision:** `ProductCombobox` writes `product_id` (UUID) to the line, not `product_code`. The `product_code` field in `InvoiceDraftLine` is a legacy snapshot field — on product selection, set `product_code: product.code` (the human-readable code from `ProductSearchResult`) AND `product_id` (UUID from `ProductSearchResult.id`). This ensures `InvoiceCreateLinePayload` is correctly populated.
- **Submission fix (Step 5):** `CreateInvoicePage.tsx` lines 163-169 only send `product_code`. The `lines.map()` payload must ALSO include `product_id: line.product_id?.trim() || null`.

**CustomerCreatePayload fields (confirmed):**
```typescript
// src/domain/customers/types.ts line 3
interface CustomerCreatePayload {
  company_name: string;       // required
  business_number: string;    // required
  billing_address: string;    // required
  contact_name: string;       // required
  contact_phone: string;      // required
  contact_email: string;      // optional
  credit_limit: string;      // optional (empty string = no credit limit)
}
```
**IMPORTANT — `credit_limit` is required in `CustomerCreatePayload` but missing from the inline creation form.** The field must be added to the form in Step 4 as an optional `<Input>` (placeholder `"Credit limit (optional)"`), with value `""` meaning no credit limit. If omitted from the API payload, the backend may reject it — always include `credit_limit: createForm.credit_limit` even when empty.

---

## 1. Requirements Summary

Replace UUID-only text inputs in `OrderForm` and `InvoiceLineEditor` with searchable, auto-complete combobox selectors:

- **New `ProductCombobox` component** at `src/components/products/ProductCombobox.tsx` — mirrors `CustomerCombobox` architecture: `Popover` + `Command` pattern, debounced server-side search, shows name + code + SKU + inline stock (aggregate).
- **`OrderForm`** — Replace customer UUID input with `CustomerCombobox` (already exists); replace product UUID inputs with `ProductCombobox`; auto-populate `description` from selected product's `name`.
- **`InvoiceLineEditor`** — Replace `product_code` plain text input with `ProductCombobox`; auto-populate `description` from `ProductSearchResult.name`.
- **`CustomerCombobox` inline creation** — Add "Create new customer" option when no results match; inline creation panel with required fields from `CustomerCreatePayload`; duplicate detection via `createCustomer` HTTP 409 response; 409 confirmation UX via `window.confirm` using duplicate customer name.

---

## 2. Implementation Steps

### Step 0 (Pre-requisite): Add `product_id` to `InvoiceDraftLine` and `makeDraftLine`

**File:** `src/domain/invoices/types.ts`

**After line 30** (`tax_policy_code: InvoiceTaxPolicyCode`), add:
```typescript
product_id: string;
```

**File:** `src/pages/invoices/CreateInvoicePage.tsx`

**Line 43** — Add `product_id: ""` to `makeDraftLine`:
```typescript
function makeDraftLine(id: number): DraftLine {
  return {
    id,
    product_code: "",
    product_id: "",    // <— ADD
    description: "",
    quantity: "1",
    unit_price: "0",
    tax_policy_code: "standard",
  };
}
```

**Line 134** — Ensure `updateLine` merges `product_id` from partial updates:
```typescript
// Already works — the `...next` spread merges all InvoiceDraftLine fields including product_id
```

**Line 163–169** — Add `product_id` to the submission payload:
```typescript
lines: lines.map((line) => ({
  product_id: line.product_id?.trim() || null,  // <— ADD
  product_code: line.product_code.trim() || null,
  description: line.description.trim(),
  quantity: line.quantity,
  unit_price: line.unit_price,
  tax_policy_code: line.tax_policy_code,
})),
```

### Step 1: Create `src/components/products/` directory and `ProductCombobox.tsx`

**File:** `src/components/products/ProductCombobox.tsx` — **NEW**

Architecture mirrors `CustomerCombobox` (`src/components/customers/CustomerCombobox.tsx` lines 1–221) with these differences:

- **API call:** Use `searchProducts(query, { limit: 50 })` directly from `src/lib/api/inventory.ts` (NOT the `useProductSearch` hook). See `inventory.ts` lines 22–45 for the API signature.
- **Debounce:** 300ms, same pattern as `CustomerCombobox` line 94.
- **Abort:** `useRef<AbortController>` same pattern as `CustomerCombobox` line 49.
- **Results display:** Each `CommandItem` shows:
  ```
  {product.name}
  {product.code} · {product.current_stock > 0 ? `${product.current_stock} avail` : "Out of stock"}
  ```
  Note: `ProductSearchResult` (types.ts line 70) does NOT have a `sku` field — only `id`, `code`, `name`, `category`, `status`, `current_stock`, `relevance`. Do NOT display `SKU:` until verified to exist. `ProductSearchResult.current_stock` is aggregate stock across all warehouses. Use this directly. No separate stock fetch needed.
- **Client-side filter:** Filter by `name`, `code` (matching on `product.code`).
- **Props interface:**
  ```typescript
  interface ProductComboboxProps {
    value: string;                             // selected product_id (UUID)
    onChange: (productId: string) => void;
    /** Fires immediately before onChange when a product is selected, with the full search result. */
    onProductSelected?: (product: ProductSearchResult) => void;
    onClear?: () => void;
    placeholder?: string;
    disabled?: boolean;
  }
  ```
  Note: `value` is a UUID (the `id` field of `ProductSearchResult`), not the human-readable `product.code`.
- **Trigger button:** Shows selected product's name+code or placeholder, with a `Search` icon (same icon path as `CustomerCombobox` line 180).
- **Selected product fetch (if not in results):** If `value` is set but the product is not in the loaded results list, fetch it via `fetchProductDetail` (`inventory.ts` lines 49–67). The result shape is `{ ok: true; data: ProductDetail } | { ok: false; error: string }` — handle the `.ok` branch to get `ProductDetail`, ignore or log the `.error` branch. Add the fetched product to local state so the trigger button can display it. See `useProductDetail.ts` lines 16–21 for the exact handling pattern.
- **`onProductSelected` firing:** In `handleSelect`, fire `onProductSelected(product)` immediately before `onChange(product.id)`.

### Step 2: Wire `CustomerCombobox` into `OrderForm`

**File:** `src/domain/orders/components/OrderForm.tsx`

**Lines 99–111** — Replace the customer `Input` (plain UUID text input):
```tsx
// REPLACE lines 99-111:
<label className="space-y-2">
  <span>{t("orders.form.customerId")}</span>
  <Input id="ord-customer" type="text" required value={customerId}
    onChange={(e) => setCustomerId(e.target.value)} placeholder="Customer UUID" />
</label>

// WITH:
<label className="space-y-2">
  <span>{t("orders.form.customerId")}</span>
  <CustomerCombobox
    value={customerId}
    onChange={setCustomerId}
    onClear={() => setCustomerId("")}
    placeholder={t("orders.form.customerPlaceholder") ?? "Search customer by name or BAN…"}
  />
</label>
```

**Add import at top of file:**
```tsx
import { CustomerCombobox } from "../../../components/customers/CustomerCombobox";
```

### Step 3: Wire `ProductCombobox` into `OrderForm` line items + remove `useStockCheck`

**File:** `src/domain/orders/components/OrderForm.tsx`

**Remove the entire `useStockCheck` hook and its usage.** With `ProductCombobox` providing inline stock in the dropdown, the separate stock-check panel column is redundant. The hook is not used elsewhere and should be removed in the same PR:

1. **Remove the import:** `import { useStockCheck } from "../hooks/useStockCheck";`
2. **Remove `useStockCheck` call** (around line 40): `const { checkProductStock, stockData } = useStockCheck();`
3. **Remove `checkProductStock` calls** in the `useEffect` (lines 40–46) that calls `checkProductStock` for each product.
4. **Remove the stock data display** (lines 246–262) that renders `stockData[pid]` in the table.
5. **Remove the `productIdKey` dependency** (around line 35) that concatenates product IDs for the effect.

**After removing `useStockCheck`, wire `ProductCombobox` into the line item table:**

**Lines 178–186** — Replace the product `Input` (plain UUID text input) in the line item table:
```tsx
// REPLACE lines 178-186:
<TableCell>
  <Input type="text" required value={line.product_id}
    onChange={(e) => updateLine(idx, { product_id: e.target.value })}
    placeholder="Product UUID" aria-label={`Line ${idx + 1} product`} />
</TableCell>

// WITH:
<TableCell>
  <ProductCombobox
    value={line.product_id ?? ""}
    onChange={(productId) => updateLine(idx, { product_id: productId })}
    onProductSelected={(product) => updateLine(idx, { description: product.name })}
    placeholder="Search product…"
    disabled={false}
  />
</TableCell>
```

**Auto-populate description:** When `ProductCombobox` fires `onProductSelected`, the `OrderForm` also sets `description` to `product.name` (the `ProductSearchResult.name` field). The `onProductSelected` callback is designed precisely for this use case.

**Add import at top of file:**
```tsx
import { ProductCombobox } from "../../../components/products/ProductCombobox";
```

### Step 4: Add inline customer creation to `CustomerCombobox`

**File:** `src/components/customers/CustomerCombobox.tsx`

**After line 193** (`CommandEmpty` rendering), add a "Create new customer" `CommandItem` when query is non-empty and no results match:

```tsx
{/* After CommandEmpty, before closing <> */}
{filtered.length === 0 && query.trim().length > 0 && (
  <CommandGroup>
    <CommandItem
      onSelect={() => {
        setShowCreatePanel(true);
      }}
    >
      <div className="flex items-center gap-2">
        <span>Create new customer</span>
      </div>
    </CommandItem>
  </CommandGroup>
)}
```

**Add state:** `const [showCreatePanel, setShowCreatePanel] = useState(false);` after line 45.

**Add inline creation panel:** Inside the `PopoverContent`, below the `CommandList`, conditionally render a compact form when `showCreatePanel` is true:

```tsx
{showCreatePanel && (
  <div className="border-t p-3 space-y-3">
    <p className="text-sm font-medium text-foreground">Create new customer</p>
    <div className="space-y-2">
      <Input
        placeholder="Company name *"
        value={createForm.company_name}
        onChange={(e) => setCreateForm((f) => ({ ...f, company_name: e.target.value }))}
      />
      <Input
        placeholder="Business number *"
        value={createForm.business_number}
        onChange={(e) => setCreateForm((f) => ({ ...f, business_number: e.target.value }))}
      />
      <Input
        placeholder="Contact phone *"
        value={createForm.contact_phone}
        onChange={(e) => setCreateForm((f) => ({ ...f, contact_phone: e.target.value }))}
      />
      <Input
        placeholder="Billing address"
        value={createForm.billing_address}
        onChange={(e) => setCreateForm((f) => ({ ...f, billing_address: e.target.value }))}
      />
      <Input
        placeholder="Contact name"
        value={createForm.contact_name}
        onChange={(e) => setCreateForm((f) => ({ ...f, contact_name: e.target.value }))}
      />
      <Input
        placeholder="Contact email"
        value={createForm.contact_email}
        onChange={(e) => setCreateForm((f) => ({ ...f, contact_email: e.target.value }))}
      />
      <Input
        placeholder="Credit limit (optional)"
        value={createForm.credit_limit}
        onChange={(e) => setCreateForm((f) => ({ ...f, credit_limit: e.target.value }))}
      />
    </div>
    {createError && (
      <p className="text-xs text-destructive">{createError}</p>
    )}
    <div className="flex gap-2">
      <Button
        size="sm"
        onClick={handleCreateSubmit}
        disabled={!createForm.company_name.trim() || !createForm.business_number.trim() || !createForm.contact_phone.trim()}
      >
        Create
      </Button>
      <Button size="sm" variant="outline" onClick={() => setShowCreatePanel(false)}>
        Cancel
      </Button>
    </div>
  </div>
)}
```

**Add `createForm` state and `handleCreateSubmit`:** Use `useState` for the form fields. On submit, construct the payload explicitly:

```typescript
const payload = {
  company_name: createForm.company_name,
  business_number: createForm.business_number,
  contact_phone: createForm.contact_phone,
  billing_address: createForm.billing_address,
  contact_name: createForm.contact_name,
  contact_email: createForm.contact_email,
  credit_limit: createForm.credit_limit,  // empty string = no credit limit
};
const result = await createCustomer(payload);
```

Then handle results:
1. `result.ok === true`: call `onChange(result.data.id)`, close popover, reset `createForm`.
2. `result.duplicate`: call `window.confirm(\`A customer with business number "${result.duplicate.normalized_business_number}" already exists: "${result.duplicate.existing_customer_name}". Use existing customer?\`)` — if confirmed, call `onChange(result.duplicate.existing_customer_id)`, close popover.
3. `result.errors`: display the first error message in an inline error paragraph (`text-xs text-destructive`).

**Field rationale:** `company_name`, `business_number`, and `contact_phone` are marked `required` in `CustomerCreatePayload`. The other four (`billing_address`, `contact_name`, `contact_email`, `credit_limit`) are optional but included for a usable creation flow. `credit_limit` is always included in the payload — an empty string means no credit limit.

**Import `createCustomer`:** Add to import at line 6:
```tsx
import { listCustomers, createCustomer } from "../../lib/api/customers";
```

### Step 5: Wire `ProductCombobox` into `InvoiceLineEditor`

**File:** `src/components/invoices/InvoiceLineEditor.tsx`

**Lines 59–71** — Replace the product code `Input`:
```tsx
// REPLACE lines 59-71:
<div className="space-y-1.5">
  <label htmlFor={`line-${index}-product-code`} className="text-sm font-medium">
    {t("invoice.lineEditor.productCode")}
  </label>
  <Input id={`line-${index}-product-code`} type="text" value={line.product_code}
    onChange={(event) => onChange({ ...line, product_code: event.target.value })}
    placeholder="Optional" />
</div>

// WITH:
<div className="space-y-1.5">
  <label className="text-sm font-medium">
    {t("invoice.lineEditor.productCode")}
  </label>
  <ProductCombobox
    value={line.product_id ?? ""}
    onChange={(productId) => onChange({ ...line, product_id: productId, product_code: line.product_code })}
    onProductSelected={(product) =>
      onChange({ ...line, product_id: product.id, product_code: product.code, description: product.name })
    }
    placeholder="Search product…"
  />
</div>
```

**Wiring rationale:** `InvoiceDraftLine` stores `product_code` as a human-readable snapshot code (e.g., "WIDGET-001"). `ProductSearchResult` has both `id` (UUID) and `code` (human-readable). When a product is selected via `onProductSelected`:
- `product_id` is set to `product.id` (UUID, required by `InvoiceCreateLinePayload`)
- `product_code` is set to `product.code` (human-readable snapshot, preserves display)
- `description` is set to `product.name` (auto-fill from product name)

`onChange` is also called to sync `product_id` in case `onProductSelected` is not provided.

**Add import at top of file:**
```tsx
import { ProductCombobox } from "../products/ProductCombobox";
```

### Step 6: System-wide audit — check for other creation forms

Audit and update these forms (if they exist) for UUID-only inputs:
- Quote creation form
- Purchase order form
- Supplier invoice form

Use grep to find remaining `placeholder=".*UUID"` patterns:
```bash
grep -rn "placeholder.*UUID" src/ --include="*.tsx"
```

For each match, evaluate whether it should use `CustomerCombobox` or `ProductCombobox`.

---

## 3. Acceptance Criteria

| # | Criterion | How to test |
|---|-----------|-------------|
| AC1 | `OrderForm` customer field: typing in `CustomerCombobox` triggers debounced search, dropdown shows company name + business number, selecting sets `customerId` state | Manual: open OrderForm, click customer field, type — verify dropdown appears with results |
| AC2 | `OrderForm` product field: typing in `ProductCombobox` triggers debounced search, dropdown shows name + code + SKU + inline aggregate stock ("N avail" or "Out of stock"), selecting sets `line.product_id` | Manual: add line item, click product field, type — verify dropdown shows product with aggregate stock |
| AC3 | `ProductCombobox` fires `onProductSelected` when a product is selected, providing `ProductSearchResult` with `name`, `id`, `code` | Manual: select a product in OrderForm — verify `onProductSelected` fires and `description` auto-fills with product name |
| AC4 | `InvoiceLineEditor` uses `ProductCombobox` instead of plain text input; selecting a product auto-populates `product_id`, `product_code`, and `description` | Manual: open invoice creation, add a line — verify product field is a searchable combobox; select a product and verify description auto-fills |
| AC5 | `CustomerCombobox` "Create new" option appears when no search results match | Manual: search for a non-existent customer name — verify "Create new customer" option appears |
| AC6 | Customer duplicate detection: creating a customer with duplicate business number returns 409 and shows `window.confirm` prompt with existing customer name | Manual: try to create a customer with an existing business number — verify native confirm dialog appears with duplicate customer name |
| AC7 | `ProductCombobox` is a reusable component in `src/components/products/` | Import it in both `OrderForm` and `InvoiceLineEditor` — should work without modification |
| AC8 | No regression: `OrderForm` submission payload contains valid `customer_id` (UUID string) and `lines[].product_id` (UUID string) | Manual: fill form via comboboxes and submit — verify payload in network tab |
| AC9 | All creation forms audited for UUID inputs | Run grep command and verify no raw UUID inputs remain in creation forms |
| AC10 | `useStockCheck` is fully removed from `OrderForm` — no dead code remains | Verify `useStockCheck` does not appear in `OrderForm.tsx` after changes |

---

## 4. ADR — Architecture Decisions

| Decision | Drivers | Alternatives Considered | Why Chosen | Consequences |
|-----------|---------|------------------------|------------|--------------|
| **ProductCombobox calls `searchProducts` directly, not `useProductSearch`** | Lightweight single-shot lookups; hook exposes pagination/sort state irrelevant to combobox | Reuse `useProductSearch` hook | Hook's page state would leak into combobox API; direct call mirrors `CustomerCombobox` exactly | Debounce/abort logic duplicated — acceptable since the patterns are stable |
| **Remove `useStockCheck` entirely, not keep as fallback** | `ProductCombobox` shows inline aggregate stock in dropdown; separate stock check column is redundant | Keep `useStockCheck` as fallback for direct UUID entry | If users bypass `ProductCombobox` (e.g., via API), stock check still fires — but `ProductCombobox` always emits valid UUIDs, making fallback unnecessary | No rollback path for aggregate-vs-warehouse-specific stock — if warehouse-specific stock needed later, add `warehouseId` prop to `ProductCombobox` |
| **`product_id` (UUID) is the canonical foreign key for invoice lines; `product_code` is a snapshot** | `InvoiceCreateLinePayload` accepts both; `InvoiceDraftLine` used `product_code` only | Use `product_code` as canonical key | `product_id` is the proper foreign key; `product_code` is human-readable display text | `InvoiceDraftLine` type must be updated to include `product_id`; `CreateInvoicePage` submission mapper updated to send both fields |
| **Inline customer creation via panel inside `CustomerCombobox` popover, not modal** | Preserves search context; user doesn't lose query; same popover stays open | Modal dialog (breaks context), separate page (too heavy) | Matches spec language; lower friction than modal; `window.confirm` for duplicate confirmation is native and blocking | Panel state adds ~60 lines to `CustomerCombobox`; native `confirm` dialog is ugly but functional |

---

## 5. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `InvoiceDraftLine.product_code` is a human-readable code, not a UUID, causing confusion with `ProductCombobox.value` (which uses UUID `product.id`) | Low | Low | The `ProductCombobox` `value` prop and `onChange` both use `product.id` (UUID). `product_code` is populated separately via `onProductSelected`. Clear in the component API. |
| `ProductSearchResult.current_stock` is aggregate stock (all warehouses), not warehouse-specific | High | Low | Accept aggregate stock as sufficient per spec ("show stock inline in dropdown"). If warehouse-specific stock is required later, add `warehouseId` prop to `ProductCombobox` and pass to `searchProducts`. |
| `CustomerCombobox` inline creation panel makes the popover too tall | Medium | Low | The popover has a fixed `w-[24rem]` width; the creation panel can scroll internally if needed. The panel uses compact `<Input>` components with `placeholder` labels, minimizing height. |
| `window.confirm` for 409 duplicate detection is a native browser dialog | Low | Low | Acceptable for this UX. Native confirm is blocking and clear. If a custom inline confirmation is preferred later, this can be extracted to a dialog component in a follow-up. |
| `InvoiceCreateLinePayload` accepts both `product_id` and `product_code` — using both may confuse backend | Low | Low | Both fields are explicitly in the backend type. `product_id` is the foreign key; `product_code` is a snapshot. Using both is correct and matches how `InvoiceLineResponse` stores data. |

---

## 6. Verification Steps

### Step 1: Verify `ProductCombobox` renders and searches
- Open browser devtools
- Create a temporary test page that renders `<ProductCombobox value="" onChange={console.log} onProductSelected={console.log} />`
- Type a product query — verify network tab shows `/api/v1/inventory/products/search?q=...` calls
- Verify dropdown renders with name, code, SKU, and aggregate stock

### Step 2: Verify `CustomerCombobox` inline creation
- Open `OrderForm` in browser
- Search for a customer that does not exist
- Verify "Create new customer" option appears
- Click it — verify inline form renders inside popover with all 6 fields
- Submit with duplicate business number — verify `window.confirm` dialog appears with the existing customer name

### Step 3: Verify `OrderForm` submission payload
- Fill `OrderForm` using `CustomerCombobox` and `ProductCombobox` (not typing UUIDs)
- Submit and inspect the network request payload
- Verify `customer_id` and each `lines[].product_id` are valid UUID strings

### Step 4: Verify `InvoiceLineEditor` integration
- Navigate to invoice creation
- Add a line item
- Verify the product field shows a searchable combobox
- Select a product — verify `description` auto-fills with product name
- Verify `product_code` (the human-readable code) is populated in the line

### Step 5: Verify `useStockCheck` removal
- Open `OrderForm.tsx` and confirm `useStockCheck` is no longer imported or used
- Confirm no stock data display remains in the line item table

### Step 6: Grep for remaining UUID inputs
```bash
grep -rn 'placeholder=".*UUID"' src/ --include="*.tsx"
```
Expected: No matches in creation forms (`OrderForm`, `InvoiceLineEditor`, quote/purchase order forms).
