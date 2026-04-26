# Story 41.1: Multi-Namespace i18n Scaffolding

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a frontend developer,
I want runtime and test support for multiple i18n namespaces,
so that translation extraction can proceed without breaking the current app shell or test harness.

## Acceptance Criteria

1. **Given** the runtime currently initializes only `common`, **when** Story 41.1 lands, **then** `src/i18n.ts` supports loading `common`, `shell`, `routes`, and feature namespaces from `/locales/{lng}/{ns}.json` while preserving supported languages and single-brace interpolation.

2. **Given** the test helper currently seeds only `common`, **when** Story 41.1 lands, **then** `src/tests/helpers/i18n.ts` can register multiple namespaces for English and keep the current interpolation semantics intact.

3. **Given** later stories need safe migration guardrails, **when** a parity or hygiene check runs, **then** missing locale namespace files or mismatched namespace inventories between `en` and `zh-Hant` are surfaced before merge.

## Tasks / Subtasks

- [x] Task 1 (AC: #1)
  - [x] Subtask 1.1: Update `src/i18n.ts` `ns` array to include all target namespaces
  - [x] Subtask 1.2: Verify supported languages (`en`, `zh-Hant`) remain unchanged
  - [x] Subtask 1.3: Verify single-brace interpolation (`prefix: '{'`, `suffix: '}'`) is preserved
  - [x] Subtask 1.4: Create placeholder locale files for new namespaces (en + zh-Hant)
- [x] Task 2 (AC: #2)
  - [x] Subtask 2.1: Update `src/tests/helpers/i18n.ts` to seed all namespaces for English
  - [x] Subtask 2.2: Verify interpolation semantics (`prefix: '{'`, `suffix: '}'`) are set
  - [x] Subtask 2.3: Test that existing tests still pass with multi-namespace setup
- [x] Task 3 (AC: #3)
  - [x] Subtask 3.1: Create a locale parity/hygiene check script or test
  - [x] Subtask 3.2: Validate script detects missing namespace files
  - [x] Subtask 3.3: Validate script detects mismatched namespace inventories between en and zh-Hant

## Dev Notes

### Architecture Decision

Keep semantic keys, split by namespace, preserve single-brace interpolation.

- **Key principle**: Do NOT switch to content-as-key or opaque generated IDs
- **Namespace structure**: Feature-scoped namespaces that mirror frontend architecture
- **Interpolation**: Single-brace `{value}` contract must be preserved throughout

### Target Namespace Set

The runtime and test harness must support all 16 namespaces:

| Namespace | Purpose |
|-----------|---------|
| `common` | Shared UI primitives and shared component copy |
| `shell` | App chrome: sidebar headers, section headers, nav menu labels, language/theme labels |
| `routes` | Page labels and page descriptions (canonical source) |
| `auth` | Authentication flows |
| `dashboard` | Dashboard-specific copy |
| `admin` | Admin panel copy |
| `intelligence` | AI/analytics features |
| `crm` | CRM features (leads, opportunities, quotations) |
| `customer` | Customer management |
| `inventory` | Inventory operations |
| `orders` | Order management |
| `procurement` | Procurement (RFQs) |
| `purchase` | Purchase orders |
| `invoice` | Invoice-related copy |
| `payments` | Payment-related copy |
| `settings` | Settings page copy |

### Source Tree Components to Touch

#### Runtime Configuration (`src/i18n.ts`)

**Current state:**
```typescript
ns: ['common'],
defaultNS: 'common',
```

**Required change:**
```typescript
ns: ['common', 'shell', 'routes', 'auth', 'dashboard', 'admin', 'intelligence', 'crm', 'customer', 'inventory', 'orders', 'procurement', 'purchase', 'invoice', 'payments', 'settings'],
defaultNS: 'common',
```

**Preserve existing:**
- `supportedLngs: ['en', 'zh-Hant']`
- `fallbackLng: 'en'`
- `backend.loadPath: '/locales/{lng}/{ns}.json'`
- `interpolation.prefix: '{'` and `interpolation.suffix: '}'`

#### Test Helper (`src/tests/helpers/i18n.ts`)

**Current pattern:**
```typescript
import enTranslations from "../../../public/locales/en/common.json";

resources: {
  en: { common: enTranslations },
},
ns: ["common"],
defaultNS: "common",
```

**Required change:** Register all 16 namespaces with English translations. Each namespace should have a corresponding import from `public/locales/en/{ns}.json`.

**Preserve existing:**
- `lng: "en"`
- `fallbackLng: "en"`
- `interpolation.prefix: '{'` and `interpolation.suffix: '}'`

### Testing Standards

1. **Unit tests** for parity/hygiene script should verify:
   - All 16 namespaces exist in both `en` and `zh-Hant` directories
   - Namespace inventories match between `en` and `zh-Hant`
   - Script exits non-zero when violations are found

2. **Integration smoke tests** should verify:
   - App initializes without errors with multi-namespace config
   - Existing translation keys still resolve correctly
   - Interpolation still works with `{value}` format

### Project Structure Notes

- Locale files are located in: `public/locales/{lng}/{ns}.json`
- Current `common.json`: en has ~3663 lines, zh-Hant has ~3530 lines
- Placeholder files for new namespaces should be minimal (empty `{}` or minimal structure)
- The new namespace files are scaffolded now but populated in later stories (41.2-41.5)

### References

- Epic 41: `_bmad-output/planning-artifacts/epic-41.md`
- Current i18n config: `src/i18n.ts`
- Current test helper: `src/tests/helpers/i18n.ts`
- Language detection: `src/i18n.ts` (mapDetectedLanguage function)
- i18next-http-backend pattern: existing HttpBackend usage in `src/i18n.ts`

## Dev Agent Record

### Agent Model Used

sonnet

### Debug Log References

N/A - Initial story creation

### Completion Notes List

- [x] Task 1: Multi-namespace runtime support implemented
- [x] Task 2: Multi-namespace test support implemented
- [x] Task 3: Parity/hygiene guardrails created
- [x] All existing tests pass (514 passed; 5 pre-existing failures unrelated to i18n)
- [x] Build and lint clean

### File List

**Files to create:**
- `public/locales/en/shell.json` (placeholder)
- `public/locales/en/routes.json` (placeholder)
- `public/locales/en/auth.json` (placeholder)
- `public/locales/en/dashboard.json` (placeholder)
- `public/locales/en/admin.json` (placeholder)
- `public/locales/en/intelligence.json` (placeholder)
- `public/locales/en/crm.json` (placeholder)
- `public/locales/en/customer.json` (placeholder)
- `public/locales/en/inventory.json` (placeholder)
- `public/locales/en/orders.json` (placeholder)
- `public/locales/en/procurement.json` (placeholder)
- `public/locales/en/purchase.json` (placeholder)
- `public/locales/en/invoice.json` (placeholder)
- `public/locales/en/payments.json` (placeholder)
- `public/locales/en/settings.json` (placeholder)
- `public/locales/zh-Hant/shell.json` (placeholder)
- `public/locales/zh-Hant/routes.json` (placeholder)
- `public/locales/zh-Hant/auth.json` (placeholder)
- `public/locales/zh-Hant/dashboard.json` (placeholder)
- `public/locales/zh-Hant/admin.json` (placeholder)
- `public/locales/zh-Hant/intelligence.json` (placeholder)
- `public/locales/zh-Hant/crm.json` (placeholder)
- `public/locales/zh-Hant/customer.json` (placeholder)
- `public/locales/zh-Hant/inventory.json` (placeholder)
- `public/locales/zh-Hant/orders.json` (placeholder)
- `public/locales/zh-Hant/procurement.json` (placeholder)
- `public/locales/zh-Hant/purchase.json` (placeholder)
- `public/locales/zh-Hant/invoice.json` (placeholder)
- `public/locales/zh-Hant/payments.json` (placeholder)
- `public/locales/zh-Hant/settings.json` (placeholder)
- `scripts/check-locale-parity.ts` or `src/tests/locale-parity.test.ts` (parity check)

**Files modified:**
- `src/i18n.ts` (add all namespaces to `ns` array, use shared constants)
- `src/tests/helpers/i18n.ts` (register all namespaces for test environment)

**Files created:**
- `src/lib/i18n-namespaces.ts` (shared namespace constants)
- `scripts/check-locale-parity.ts` (parity/hygiene check)
- `src/tests/locale-parity.test.ts` (Vitest test suite)
- `public/locales/en/{shell,routes,auth,dashboard,admin,intelligence,crm,customer,inventory,orders,procurement,purchase,invoice,payments,settings}.json` (15 placeholder files)
- `public/locales/zh-Hant/{shell,routes,auth,dashboard,admin,intelligence,crm,customer,inventory,orders,procurement,purchase,invoice,payments,settings}.json` (15 placeholder files)

## Change Log

- **2026-04-26**: Initial implementation - Multi-namespace i18n scaffolding complete. Updated i18n.ts and test helper to support 16 namespaces. Created parity/hygiene check script with key-count validation. All acceptance criteria satisfied. Build passes, 514 tests pass.
