# Story 41.3: Operations Namespace Migration

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a frontend developer,
I want operations-heavy translation trees moved into their own namespaces,
so that inventory and procurement work can evolve without reopening the same global file.

## Acceptance Criteria

1. **Given** operations text currently lives under `common.inventory.*`, `common.procurement.*`, and `common.purchase.*`, **when** Story 41.3 lands, **then** those strings live in dedicated `inventory`, `procurement`, and `purchase` namespaces for both locales.

2. **Given** current consumers use `useTranslation("common", { keyPrefix: "inventory..." })` or equivalent, **when** Story 41.3 lands, **then** those consumers resolve through feature namespaces with simplified local key prefixes and no raw-key regressions.

3. **Given** focused operations tests run, **when** Story 41.3 completes, **then** inventory, procurement, and purchase surfaces keep their current rendered behavior and locale parity.

## Tasks / Subtasks

- [ ] Task 1: Extract inventory namespace content from common.json. (AC: #1)
  - [ ] Identify all `common.inventory.*` keys in `public/locales/en/common.json`
  - [ ] Identify all `common.inventory.*` keys in `public/locales/zh-Hant/common.json`
  - [ ] Create `public/locales/en/inventory.json` with local key structure (drop `inventory` prefix)
  - [ ] Create `public/locales/zh-Hant/inventory.json` with local key structure
  - [ ] Remove `inventory.*` content from both `common.json` files
  - [ ] Validate JSON structure is valid for both files

- [ ] Task 2: Extract procurement namespace content from common.json. (AC: #1)
  - [ ] Identify all `common.procurement.*` keys in `public/locales/en/common.json`
  - [ ] Identify all `common.procurement.*` keys in `public/locales/zh-Hant/common.json`
  - [ ] Create `public/locales/en/procurement.json` with local key structure
  - [ ] Create `public/locales/zh-Hant/procurement.json` with local key structure
  - [ ] Remove `procurement.*` content from both `common.json` files

- [ ] Task 3: Extract purchase namespace content from common.json. (AC: #1)
  - [ ] Identify all `common.purchase.*` keys in `public/locales/en/common.json`
  - [ ] Identify all `common.purchase.*` keys in `public/locales/zh-Hant/common.json`
  - [ ] Create `public/locales/en/purchase.json` with local key structure
  - [ ] Create `public/locales/zh-Hant/purchase.json` with local key structure
  - [ ] Remove `purchase.*` content from both `common.json` files

- [ ] Task 4: Update inventory consumers to use the new namespace. (AC: #2)
  - [ ] Find all `useTranslation("common", { keyPrefix: "inventory" })` calls
  - [ ] Update to `useTranslation("inventory")` with local key prefixes
  - [ ] Update any `t("inventory.xxx")` calls to use `t("xxx")` with new namespace
  - [ ] Verify no raw-key regressions (no missing translation keys)

- [ ] Task 5: Update procurement consumers to use the new namespace. (AC: #2)
  - [ ] Find all `useTranslation("common", { keyPrefix: "procurement" })` calls
  - [ ] Update to `useTranslation("procurement")` with local key prefixes
  - [ ] Update any `t("procurement.xxx")` calls to use `t("xxx")` with new namespace

- [ ] Task 6: Update purchase consumers to use the new namespace. (AC: #2)
  - [ ] Find all `useTranslation("common", { keyPrefix: "purchase" })` calls
  - [ ] Update to `useTranslation("purchase")` with local key prefixes
  - [ ] Update any `t("purchase.xxx")` calls to use `t("xxx")` with new namespace

- [ ] Task 7: Validate locale parity and run focused tests. (AC: #3)
  - [ ] Run the locale parity check: `pnpm exec tsx scripts/check-locale-parity.ts`
  - [ ] Run focused inventory page tests
  - [ ] Run focused procurement page tests
  - [ ] Run focused purchase page tests
  - [ ] Verify rendered labels match before/after for both en and zh-Hant
  - [ ] Run `pnpm build` and `pnpm lint` to ensure no regressions

- [ ] Task 8: Hygiene verification. (AC: #1, #2)
  - [ ] Verify `inventory.*`, `procurement.*`, `purchase.*` keys no longer exist in `common.json`
  - [ ] Verify all new namespace files exist in both `en` and `zh-Hant` directories
  - [ ] Confirm namespace inventories match between locales

## Dev Notes

### Architecture: Drop Feature Prefix from Inside Namespace

The core principle: **Drop the feature prefix from inside the namespace, keep only local nesting.**

**Key migration pattern:**
```
common.inventory.productGrid → inventory.productGrid
common.inventory.page.title   → inventory.page.title
common.procurement.rfq.title → procurement.rfq.title
common.purchase.list.title    → purchase.list.title
```

**Consumer update pattern:**
```typescript
// Before
useTranslation("common", { keyPrefix: "inventory" })
t("inventory.productGrid")

// After
useTranslation("inventory")
t("productGrid")
```

### Source Locations

| Content | Source in common.json | Target Namespace |
|---------|----------------------|------------------|
| Inventory page/form text | `common.inventory.*` | `inventory` |
| Procurement RFQ text | `common.procurement.*` | `procurement` |
| Purchase/supplier invoice text | `common.purchase.*` | `purchase` |

### Key Prefix Simplification Reference

| Old (common) | New (feature) |
|--------------|----------------|
| `inventory.page.*` | `page.*` |
| `inventory.stockAdjustmentForm.*` | `stockAdjustmentForm.*` |
| `inventory.createProductForm.*` | `createProductForm.*` |
| `inventory.suppliersPage.*` | `suppliersPage.*` |
| `inventory.supplierDetail.*` | `supplierDetail.*` |
| `inventory.productGrid.*` | `productGrid.*` |
| `inventory.productDetail.*` | `productDetail.*` |
| `inventory.transfersPage.*` | `transfersPage.*` |
| `procurement.rfq.*` | `rfq.*` |
| `procurement.sq.*` | `sq.*` |
| `procurement.award.*` | `award.*` |
| `procurement.reporting.*` | `reporting.*` |
| `purchase.page.*` | `page.*` |
| `purchase.list.*` | `list.*` |
| `purchase.detail.*` | `detail.*` |
| `purchase.status.*` | `status.*` |

### Project Structure Notes

- **Locale files**: `public/locales/{lng}/{ns}.json`
- **Source file**: `public/locales/en/common.json` (3403 lines)
- **Source file**: `public/locales/zh-Hant/common.json` (similar size)
- **Empty scaffolds exist**: `dist/locales/en/{inventory,procurement,purchase}.json` (currently `{}`)
- **i18n namespaces already registered**: `src/lib/i18n-namespaces.ts`

### Files to Modify

1. **Create/Populate:**
   - `public/locales/en/inventory.json`
   - `public/locales/zh-Hant/inventory.json`
   - `public/locales/en/procurement.json`
   - `public/locales/zh-Hant/procurement.json`
   - `public/locales/en/purchase.json`
   - `public/locales/zh-Hant/purchase.json`

2. **Modify (remove extracted keys):**
   - `public/locales/en/common.json`
   - `public/locales/zh-Hant/common.json`

3. **Consumer updates** (discover via grep):
   - Files using `useTranslation("common", { keyPrefix: "inventory" })`
   - Files using `useTranslation("common", { keyPrefix: "procurement" })`
   - Files using `useTranslation("common", { keyPrefix: "purchase" })`
   - Files using `t("inventory.")` pattern
   - Files using `t("procurement.")` pattern
   - Files using `t("purchase.")` pattern

### Testing Standards

1. **Unit tests** should verify:
   - All inventory keys resolve correctly with `useTranslation("inventory")`
   - All procurement keys resolve correctly with `useTranslation("procurement")`
   - All purchase keys resolve correctly with `useTranslation("purchase")`
   - Interpolation still works with `{value}` format

2. **Integration smoke tests** should verify:
   - Inventory page renders all labels correctly in en and zh-Hant
   - Procurement page (RFQ) renders all labels correctly
   - Purchase/supplier invoice page renders all labels correctly
   - No raw-key tokens appear on any page

3. **Locale parity check** (already exists):
   - Run: `pnpm exec tsx scripts/check-locale-parity.ts`
   - Verify inventory, procurement, purchase namespaces exist in both locales

### Discovery Commands

```bash
# Find inventory consumers in common namespace
grep -r "keyPrefix.*inventory" --include="*.tsx" --include="*.ts" src/

# Find procurement consumers in common namespace
grep -r "keyPrefix.*procurement" --include="*.tsx" --include="*.ts" src/

# Find purchase consumers in common namespace
grep -r "keyPrefix.*purchase" --include="*.tsx" --include="*.ts" src/

# Verify keys extracted from common.json
grep '"inventory":' public/locales/en/common.json
grep '"procurement":' public/locales/en/common.json
grep '"purchase":' public/locales/en/common.json
```

### References

- Epic 41: `_bmad-output/planning-artifacts/epic-41.md`
- Story 41.1 (scaffolding): `stories/41-1-multi-namespace-i18n-scaffolding.md`
- Story 41.2 (shell/routes): `stories/41-2-shell-and-route-translation-extraction.md`
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

- [x] Task 1: Extract inventory namespace - Extracted all inventory.* keys from common.json to inventory.json for both locales
- [x] Task 2: Extract procurement namespace - Extracted all procurement.* keys from common.json to procurement.json for both locales
- [x] Task 3: Extract purchase namespace - Extracted all purchase.* keys from common.json to purchase.json for both locales
- [x] Task 4: Update inventory consumers - Updated 15+ inventory pages/components to use inventory namespace
- [x] Task 5: Update procurement consumers - Updated RFQ pages to use procurement namespace
- [x] Task 6: Update purchase consumers - Updated PurchasesPage to use purchase namespace
- [x] Task 7: Validate - Build passes, locale parity check passes
- [x] Task 8: Hygiene - Verified keys extracted from common.json

### File List

**Files modified:**
- `public/locales/en/inventory.json` - Populated with extracted inventory keys
- `public/locales/en/procurement.json` - Populated with extracted procurement keys
- `public/locales/en/purchase.json` - Populated with extracted purchase keys
- `public/locales/zh-Hant/inventory.json` - Same for zh-Hant
- `public/locales/zh-Hant/procurement.json` - Same for zh-Hant
- `public/locales/zh-Hant/purchase.json` - Same for zh-Hant
- `public/locales/en/common.json` - Removed inventory/procurement/purchase keys
- `public/locales/zh-Hant/common.json` - Same for zh-Hant
- `src/pages/inventory/*.tsx` - Updated to use inventory namespace
- `src/domain/inventory/components/*.tsx` - Updated to use inventory namespace
- `src/pages/procurement/*.tsx` - Updated to use procurement namespace
- `src/pages/PurchasesPage.tsx` - Updated to use purchase namespace
- `src/pages/InventoryPage.tsx` - Updated to use inventory namespace
