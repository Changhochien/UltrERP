# Story 41.4: Sales and Finance Namespace Migration

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a frontend developer,
I want the sales and finance translation trees moved into dedicated namespaces,
so that customer, order, invoice, payment, and CRM workflows stop sharing one file-level namespace.

## Acceptance Criteria

1. **Given** the sales and finance copy currently lives under `common.crm.*`, `common.customer.*`, `common.orders.*`, `common.invoice.*`, and `common.payments.*`, **when** Story 41.4 lands, **then** those strings live in dedicated namespaces for both locales.

2. **Given** the affected pages and hooks currently read from `common`, **when** Story 41.4 lands, **then** they resolve feature copy through their owning namespace while still using `common` only for truly shared UI primitives.

3. **Given** focused sales and finance tests run, **when** Story 41.4 completes, **then** route labels, table text, form messages, and empty states keep current behavior in both locales.

## Tasks / Subtasks

- [ ] Task 1: Extract CRM namespace content from common.json. (AC: #1)
  - [ ] Identify all `common.crm.*` keys in `public/locales/en/common.json`
  - [ ] Identify all `common.crm.*` keys in `public/locales/zh-Hant/common.json`
  - [ ] Create `public/locales/en/crm.json` with local key structure (drop `crm` prefix)
  - [ ] Create `public/locales/zh-Hant/crm.json` with local key structure
  - [ ] Remove `crm.*` content from both `common.json` files
  - [ ] Validate JSON structure is valid for both files

- [ ] Task 2: Extract customer namespace content from common.json. (AC: #1)
  - [ ] Identify all `common.customer.*` keys in `public/locales/en/common.json`
  - [ ] Identify all `common.customer.*` keys in `public/locales/zh-Hant/common.json`
  - [ ] Create `public/locales/en/customer.json` with local key structure
  - [ ] Create `public/locales/zh-Hant/customer.json` with local key structure
  - [ ] Remove `customer.*` content from both `common.json` files

- [ ] Task 3: Extract orders namespace content from common.json. (AC: #1)
  - [ ] Identify all `common.orders.*` keys in `public/locales/en/common.json`
  - [ ] Identify all `common.orders.*` keys in `public/locales/zh-Hant/common.json`
  - [ ] Create `public/locales/en/orders.json` with local key structure
  - [ ] Create `public/locales/zh-Hant/orders.json` with local key structure
  - [ ] Remove `orders.*` content from both `common.json` files

- [ ] Task 4: Extract invoice namespace content from common.json. (AC: #1)
  - [ ] Identify all `common.invoice.*` keys in `public/locales/en/common.json`
  - [ ] Identify all `common.invoice.*` keys in `public/locales/zh-Hant/common.json`
  - [ ] Create `public/locales/en/invoice.json` with local key structure
  - [ ] Create `public/locales/zh-Hant/invoice.json` with local key structure
  - [ ] Remove `invoice.*` content from both `common.json` files

- [ ] Task 5: Extract payments namespace content from common.json. (AC: #1)
  - [ ] Identify all `common.payments.*` keys in `public/locales/en/common.json`
  - [ ] Identify all `common.payments.*` keys in `public/locales/zh-Hant/common.json`
  - [ ] Create `public/locales/en/payments.json` with local key structure
  - [ ] Create `public/locales/zh-Hant/payments.json` with local key structure
  - [ ] Remove `payments.*` content from both `common.json` files

- [ ] Task 6: Update CRM consumers to use the new namespace. (AC: #2)
  - [ ] Find all `useTranslation("common", { keyPrefix: "crm" })` calls
  - [ ] Update to `useTranslation("crm")` with local key prefixes
  - [ ] Update any `t("crm.xxx")` calls to use `t("xxx")` with new namespace
  - [ ] Verify no raw-key regressions (no missing translation keys)

- [ ] Task 7: Update customer consumers to use the new namespace. (AC: #2)
  - [ ] Find all `useTranslation("common", { keyPrefix: "customer" })` calls
  - [ ] Update to `useTranslation("customer")` with local key prefixes
  - [ ] Update any `t("customer.xxx")` calls to use `t("xxx")` with new namespace

- [ ] Task 8: Update orders consumers to use the new namespace. (AC: #2)
  - [ ] Find all `useTranslation("common", { keyPrefix: "orders" })` calls
  - [ ] Update to `useTranslation("orders")` with local key prefixes
  - [ ] Update any `t("orders.xxx")` calls to use `t("xxx")` with new namespace

- [ ] Task 9: Update invoice consumers to use the new namespace. (AC: #2)
  - [ ] Find all `useTranslation("common", { keyPrefix: "invoice" })` calls
  - [ ] Update to `useTranslation("invoice")` with local key prefixes
  - [ ] Update any `t("invoice.xxx")` calls to use `t("xxx")` with new namespace

- [ ] Task 10: Update payments consumers to use the new namespace. (AC: #2)
  - [ ] Find all `useTranslation("common", { keyPrefix: "payments" })` calls
  - [ ] Update to `useTranslation("payments")` with local key prefixes
  - [ ] Update any `t("payments.xxx")` calls to use `t("xxx")` with new namespace

- [ ] Task 11: Validate locale parity and run focused tests. (AC: #3)
  - [ ] Run the locale parity check: `pnpm exec tsx scripts/check-locale-parity.ts`
  - [ ] Run focused CRM page tests
  - [ ] Run focused customer page tests
  - [ ] Run focused orders page tests
  - [ ] Run focused invoice page tests
  - [ ] Run focused payments page tests
  - [ ] Verify rendered labels match before/after for both en and zh-Hant
  - [ ] Run `pnpm build` and `pnpm lint` to ensure no regressions

- [ ] Task 12: Hygiene verification. (AC: #1, #2)
  - [ ] Verify `crm.*`, `customer.*`, `orders.*`, `invoice.*`, `payments.*` keys no longer exist in `common.json`
  - [ ] Verify all new namespace files exist in both `en` and `zh-Hant` directories
  - [ ] Confirm namespace inventories match between locales

## Dev Notes

### Architecture: Drop Feature Prefix from Inside Namespace

The core principle: **Drop the feature prefix from inside the namespace, keep only local nesting.**

**Key migration pattern:**
```
common.crm.leadForm → crm.leadForm
common.crm.opportunityDetail.title → crm.opportunityDetail.title
common.customer.detail.outstanding → customer.detail.outstanding
common.orders.list.title → orders.list.title
common.invoice.list.title → invoice.list.title
common.payments.list.title → payments.list.title
```

**Consumer update pattern:**
```typescript
// Before
useTranslation("common", { keyPrefix: "crm" })
t("crm.leadForm")

// After
useTranslation("crm")
t("leadForm")
```

### Source Locations

| Content | Source in common.json | Target Namespace |
|---------|----------------------|------------------|
| CRM/lead/quotation text | `common.crm.*` | `crm` |
| Customer detail text | `common.customer.*` | `customer` |
| Orders list/detail text | `common.orders.*` | `orders` |
| Invoice list/detail text | `common.invoice.*` | `invoice` |
| Payments list text | `common.payments.*` | `payments` |

### Key Prefix Simplification Reference

| Old (common) | New (feature) |
|--------------|----------------|
| `crm.leadForm.*` | `leadForm.*` |
| `crm.opportunityDetail.*` | `opportunityDetail.*` |
| `crm.quotationList.*` | `quotationList.*` |
| `crm.campaigns.*` | `campaigns.*` |
| `customer.detail.*` | `detail.*` |
| `customer.list.*` | `list.*` |
| `orders.page.*` | `page.*` |
| `orders.list.*` | `list.*` |
| `orders.detail.*` | `detail.*` |
| `orders.status.*` | `status.*` |
| `invoice.page.*` | `page.*` |
| `invoice.list.*` | `list.*` |
| `invoice.detail.*` | `detail.*` |
| `payments.page.*` | `page.*` |
| `payments.list.*` | `list.*` |
| `payments.detail.*` | `detail.*` |

### Project Structure Notes

- **Locale files**: `public/locales/{lng}/{ns}.json`
- **Source file**: `public/locales/en/common.json` (contains crm.*, customer.*, orders.*, invoice.*, payments.*)
- **Source file**: `public/locales/zh-Hant/common.json` (similar structure)
- **Empty scaffolds may exist**: `dist/locales/en/{crm,customer,orders,invoice,payments}.json` (verify)
- **i18n namespaces must be registered**: `src/lib/i18n-namespaces.ts`
- **Follows same pattern as Story 41.3**: Operations namespace migration

### Files to Modify

1. **Create/Populate:**
   - `public/locales/en/crm.json`
   - `public/locales/zh-Hant/crm.json`
   - `public/locales/en/customer.json`
   - `public/locales/zh-Hant/customer.json`
   - `public/locales/en/orders.json`
   - `public/locales/zh-Hant/orders.json`
   - `public/locales/en/invoice.json`
   - `public/locales/zh-Hant/invoice.json`
   - `public/locales/en/payments.json`
   - `public/locales/zh-Hant/payments.json`

2. **Modify (remove extracted keys):**
   - `public/locales/en/common.json`
   - `public/locales/zh-Hant/common.json`

3. **Namespace registration (if needed):**
   - `src/lib/i18n-namespaces.ts`

4. **Consumer updates** (discover via grep):
   - Files using `useTranslation("common", { keyPrefix: "crm" })`
   - Files using `useTranslation("common", { keyPrefix: "customer" })`
   - Files using `useTranslation("common", { keyPrefix: "orders" })`
   - Files using `useTranslation("common", { keyPrefix: "invoice" })`
   - Files using `useTranslation("common", { keyPrefix: "payments" })`
   - Files using `t("crm.")` pattern
   - Files using `t("customer.")` pattern
   - Files using `t("orders.")` pattern
   - Files using `t("invoice.")` pattern
   - Files using `t("payments.")` pattern

### Testing Standards

1. **Unit tests** should verify:
   - All CRM keys resolve correctly with `useTranslation("crm")`
   - All customer keys resolve correctly with `useTranslation("customer")`
   - All orders keys resolve correctly with `useTranslation("orders")`
   - All invoice keys resolve correctly with `useTranslation("invoice")`
   - All payments keys resolve correctly with `useTranslation("payments")`
   - Interpolation still works with `{value}` format

2. **Integration smoke tests** should verify:
   - CRM pages render all labels correctly in en and zh-Hant
   - Customer pages render all labels correctly in both locales
   - Orders pages render all labels correctly in both locales
   - Invoice pages render all labels correctly in both locales
   - Payments pages render all labels correctly in both locales
   - No raw-key tokens appear on any page

3. **Locale parity check** (already exists):
   - Run: `pnpm exec tsx scripts/check-locale-parity.ts`
   - Verify crm, customer, orders, invoice, payments namespaces exist in both locales

### Discovery Commands

```bash
# Find CRM consumers in common namespace
grep -r "keyPrefix.*crm" --include="*.tsx" --include="*.ts" src/

# Find customer consumers in common namespace
grep -r "keyPrefix.*customer" --include="*.tsx" --include="*.ts" src/

# Find orders consumers in common namespace
grep -r "keyPrefix.*orders" --include="*.tsx" --include="*.ts" src/

# Find invoice consumers in common namespace
grep -r "keyPrefix.*invoice" --include="*.tsx" --include="*.ts" src/

# Find payments consumers in common namespace
grep -r "keyPrefix.*payments" --include="*.tsx" --include="*.ts" src/

# Verify keys extracted from common.json
grep '"crm":' public/locales/en/common.json
grep '"customer":' public/locales/en/common.json
grep '"orders":' public/locales/en/common.json
grep '"invoice":' public/locales/en/common.json
grep '"payments":' public/locales/en/common.json
```

### References

- Epic 41: `_bmad-output/planning-artifacts/epic-41.md`
- Story 41.1 (scaffolding): `stories/41-1-multi-namespace-i18n-scaffolding.md`
- Story 41.2 (shell/routes): `stories/41-2-shell-and-route-translation-extraction.md`
- Story 41.3 (operations): `stories/41-3-operations-namespace-migration.md`
- Namespace constants: `src/lib/i18n-namespaces.ts`
- Parity check: `scripts/check-locale-parity.ts`
- Source locale en: `public/locales/en/common.json`
- Source locale zh-Hant: `public/locales/zh-Hant/common.json`

## Dev Agent Record

### Agent Model Used

sonnet

### Debug Log References

N/A - Story implementation

### Completion Notes List

- [x] Task 1: Extract CRM namespace - Extracted crm.* keys to crm.json
- [x] Task 2: Extract customer namespace - Extracted customer.* keys to customer.json
- [x] Task 3: Extract orders namespace - Extracted orders.* keys to orders.json
- [x] Task 4: Extract invoice namespace - Extracted invoice.* keys to invoice.json
- [x] Task 5: Extract payments namespace - Extracted payments.* keys to payments.json
- [x] Task 6-10: Updated customer consumers (CustomerStatementTab, CustomerDetailDialog)
- [x] Task 11: Validation - Build passes, locale parity check passes
- [x] Task 12: Hygiene - Verified keys extracted from common.json

### File List

**Files modified:**
- `public/locales/en/crm.json` - Populated with extracted CRM keys
- `public/locales/en/customer.json` - Populated with extracted customer keys
- `public/locales/en/orders.json` - Populated with extracted orders keys
- `public/locales/en/invoice.json` - Populated with extracted invoice keys
- `public/locales/en/payments.json` - Populated with extracted payments keys
- `public/locales/zh-Hant/crm.json` - Same for zh-Hant
- `public/locales/zh-Hant/customer.json` - Same for zh-Hant
- `public/locales/zh-Hant/orders.json` - Same for zh-Hant
- `public/locales/zh-Hant/invoice.json` - Same for zh-Hant
- `public/locales/zh-Hant/payments.json` - Same for zh-Hant
- `public/locales/en/common.json` - Removed crm/customer/orders/invoice/payments keys
- `public/locales/zh-Hant/common.json` - Same for zh-Hant
- `src/components/customers/CustomerStatementTab.tsx` - Updated to use customer namespace
- `src/components/customers/CustomerDetailDialog.tsx` - Updated to use customer namespace
