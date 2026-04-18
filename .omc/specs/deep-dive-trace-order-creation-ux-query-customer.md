# Deep Dive Trace: order-creation-ux-query-customer

## Observed Result
Order creation UX requires users to type raw UUIDs for customer and product — no searchable combobox, no autocomplete, no name-based lookup.

## Ranked Hypotheses

| Rank | Hypothesis | Confidence | Evidence Strength | Why it leads |
|------|------------|------------|-------------------|--------------|
| 1 | **UX inconsistency** — `CustomerCombobox` exists but `OrderForm` was never updated; `ProductCombobox` was never built | **High** | Strong | Lane 3 found `CustomerCombobox` is production-ready, noted "for invoice creation," used in `OrderList` filters and `CreateInvoicePage`, but absent from `OrderForm`. No `ProductCombobox` exists anywhere. Invoice creation is also incomplete (no product combobox for line items). |
| 2 | **Code-path** — OrderForm uses plain `<input>` instead of wiring existing components | **High** | Strong | Confirmed: `customerId` is `<Input placeholder="Customer UUID">`, `product_id` is same pattern. `CustomerCombobox` props (`value`/`onChange`) match `OrderForm`'s `customerId`/`setCustomerId` state exactly — wiring would be trivial. `useProductSearch` hook exists but no UI component built from it. |
| 3 | **API/backend gap** | **Low (Disproven)** | — | `listCustomers` accepts `q` param. `searchProducts` exists with full text query. The backend is fully capable. Gap is entirely frontend. |

## Evidence Summary by Hypothesis

### Lane 1 (Code-path)
- `OrderForm` lines 103-110: plain `<Input type="text" placeholder="Customer UUID">`
- `OrderForm` lines 179-186: plain `<Input type="text" placeholder="Product UUID">`
- `CustomerCombobox` has compatible `value`/`onChange` interface — reuse would be trivial
- `useProductSearch` hook exists (`src/domain/inventory/hooks/useProductSearch.ts`) but no popover combobox UI built from it
- `ProductSearch.tsx` is a full-page DataTable — too heavy for inline form use

### Lane 2 (API/backend)
- `listCustomers({ q })` → `GET /api/v1/customers?q=...` — confirmed supported
- `searchProducts(query)` → `GET /api/v1/inventory/products/search?q=...` — confirmed supported
- `checkStock(productId)` → `GET /api/v1/orders/check-stock?product_id=...` — accepts only UUID, no search path
- **Conclusion**: APIs support search; the form simply doesn't call them

### Lane 3 (UX inconsistency)
- `CustomerCombobox` comment: "for invoice creation" — component explicitly designed for this use case
- `CustomerCombobox` used in: `OrderList` filters, `InvoiceList` filters, `CreateInvoicePage` — proven reusable
- `OrderForm` has no comment/TODO suggesting deliberate exclusion — reads as unfinished scaffolding
- `InvoiceLineEditor` (gold-standard creation form) also uses plain `product_code` text input — inconsistency is **system-wide**, not just OrderForm
- No `ProductCombobox` exists anywhere in codebase despite the same UX gap applying to all creation forms

## Evidence Against / Missing Evidence

- **Lane 1**: No evidence of deliberate technical barrier — only unfinished wiring
- **Lane 2**: Strong evidence against — APIs already support search. Fully disproven as a backend problem.
- **Lane 3**: No evidence of intentional exclusion. "For invoice creation" comment is descriptive, not prescriptive.

## Per-Lane Critical Unknowns

- **Lane 1**: Was the product search capability (`useProductSearch`) intentionally deprioritized, or is it simply waiting to be wired into a UI component?
- **Lane 2**: Fully resolved — API is not the bottleneck.
- **Lane 3**: (1) Was `OrderForm` written before `CustomerCombobox` existed? (2) Do `product_id` (orders) and `product_code` (invoices) have different backend semantics that might explain the different UX? (3) Was `ProductCombobox` ever attempted and removed?

## Rebuttal Round

- **Best rebuttal to leader**: "This is just unfinished work, not a UX design problem"
- **Why leader held**: The `CustomerCombobox` comment "for invoice creation" AND its absence from `OrderForm` is a clear pattern gap. The fact that `InvoiceLineEditor` also lacks product search confirms this is systemic — it's not that OrderForm was forgotten, it's that the product side of the combobox pattern was never completed at all.
- **Lane 2 rebuttal**: "The API doesn't support search" — disproven immediately. `listCustomers` and `searchProducts` both exist with `q` params.

## Convergence / Separation Notes
- Lane 1 and Lane 3 **converge**: the code-path gap (no combobox wired) is the mechanism by which the UX inconsistency manifests. The root cause is the same: `ProductCombobox` was never built, and `CustomerCombobox` was not wired into `OrderForm`.
- Lane 2 **separates** cleanly — the API hypothesis is disproven. This is a frontend-only gap.

## Most Likely Explanation
**Incomplete UX pattern**: The `CustomerCombobox` component establishes a proven, production-ready pattern for searchable customer selection in creation forms. This pattern was:
1. Applied to `InvoiceLineEditor` for the customer field (partially — customer uses combobox)
2. Applied to `OrderList`/`InvoiceList` for filtering
3. **Never applied to `OrderForm`** for either customer or product fields
4. **Never extended to products at all** — `ProductCombobox` does not exist

The `product_id` field in `OrderForm` is UUID-only because no `ProductCombobox` was ever built. The `customerId` field is UUID-only because `CustomerCombobox` was not wired in. The stock check path compounds the problem by only accepting full UUIDs (no search fallback).

## Critical Unknown
**Why was `OrderForm` written with raw UUID inputs when `CustomerCombobox` was already established?** This could be a simple ordering issue (OrderForm predates CustomerCombobox) or an oversight. The deeper unknown is whether `ProductCombobox` was ever planned — if not, the entire creation layer will need this component built from scratch.

## Recommended Discriminating Probe
**Check `CreateInvoicePage` product UX** — does invoice creation also require UUID-only product entry? If yes, the problem is system-wide (no `ProductCombobox` anywhere). If no, the problem is specific to `OrderForm`. Confirmed: `InvoiceLineEditor` uses plain `product_code` text input — so this is a **system-wide gap** affecting all creation forms.
