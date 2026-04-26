# Epic 41: Translation Namespace Architecture Hardening

## Epic Goal

Reorganize the frontend translation system from one oversized `common` namespace into feature-scoped namespaces with a governed shared layer, so localization scales without forcing unrelated domains to share one translation file.

## Business Value

- Translation work becomes cheaper to review because domain owners can edit one feature file instead of scrolling through a 3,500-line catch-all resource.
- Frontend copy drift drops because route labels, navigation labels, and page descriptions get one canonical home instead of being maintained in parallel.
- Initial locale payload stays lean because `i18next` can keep loading namespaces on demand rather than front-loading every feature into one file.
- Adding future locales becomes safer because parity checks can reason about namespace inventories per feature instead of one monolithic JSON blob.

## Current State Summary

- `src/i18n.ts` currently initializes only the `common` namespace and loads resources from `/locales/{lng}/{ns}.json`.
- `public/locales/en/common.json` is approximately 3,663 lines with about 2,989 leaf keys, while `public/locales/zh-Hant/common.json` is approximately 3,532 lines with about 2,868 leaf keys.
- The file-level `common` namespace currently contains unrelated sections for inventory, CRM, procurement, orders, dashboard, settings, intelligence, admin, and auth.
- The codebase already expresses feature ownership through `keyPrefix` usage such as `inventory.productDetail`, `inventory.productGrid`, `intelligence.affinity`, and `customer.detail.outstanding`, but every slice still resolves through `useTranslation("common")`.
- `src/lib/navigation.tsx` keeps route-oriented labels under `nav.*` while page metadata lives under `routes.*`; there are 25 shared key stems and 22 currently resolve to identical values in both locales.
- `src/tests/helpers/i18n.ts` only seeds the `common` namespace today, which bakes the monolithic resource shape into the test harness.

## Architecture Decision

### Core Decision

Adopt feature-scoped namespaces that mirror the frontend architecture while preserving semantic keys and the existing interpolation behavior.

1. Keep semantic translation keys; do not switch to content-as-key or opaque generated IDs.
2. Split locale files by namespace, not by one giant nested object inside `common`.
3. Keep `common` reserved for truly shared UI primitives and shared component copy.
4. Introduce a dedicated `routes` namespace as the canonical source of page labels and page descriptions.
5. Introduce a dedicated `shell` namespace for app chrome such as sidebar group headers, section headers, menu labels, and workspace shell text.
6. Move feature strings into feature namespaces and drop the duplicated feature root inside each namespace.
7. Preserve the repo's single-brace interpolation contract (`{value}`) and current language detection behavior.

### Namespace Target

The target runtime namespace set for both locales is:

- `common`
- `shell`
- `routes`
- `auth`
- `dashboard`
- `admin`
- `intelligence`
- `crm`
- `customer`
- `inventory`
- `orders`
- `procurement`
- `purchase`
- `invoice`
- `payments`
- `settings`

### Target Resource Shape

The new structure should align the namespace with the owning feature and keep nesting local to that feature.

Examples:

- `public/locales/{lng}/inventory.json`
  - `productGrid.*`
  - `productDetail.*`
  - `transfersPage.*`
- `public/locales/{lng}/crm.json`
  - `leadForm.*`
  - `opportunityDetail.*`
  - `quotationList.*`
- `public/locales/{lng}/routes.json`
  - `dashboard.label`
  - `dashboard.description`
  - `inventoryTransfers.label`
- `public/locales/{lng}/shell.json`
  - `app.tagline`
  - `nav.home`
  - `nav.reports`
  - `navMenu.logOut`

### Canonical Label Policy

- `routes.*.label` is the canonical label for route destinations and breadcrumb/page-title surfaces.
- Sidebar item labels should reuse `routes.*.label` when the sidebar label and route label are intentionally the same.
- A shell-specific short label should exist only when the navigation label is intentionally shorter than the route label. The currently verified short-label exceptions are `belowReorderReport`, `inventoryCategories`, and `inventoryValuation`.
- `common` should not become a dumping ground for feature-specific button text merely because the English copy happens to match in multiple contexts.

### Guardrails

- Do not introduce a new locale or translation management platform in this epic.
- Do not rewrite product copy except where a canonical label decision is required to remove duplication.
- Do not change backend behavior, API contracts, or route structure in this epic.
- Do not preserve feature prefixes inside feature namespaces if the namespace already provides that context.
- Keep migrations incremental so each story can validate one behavioral slice before expanding.

## Scope

- Enable multi-namespace loading in the frontend runtime and test harness.
- Split the current locale resources into dedicated namespace files for both English and Traditional Chinese.
- Migrate route, shell, and feature consumers to the new namespaces.
- Remove redundant route/navigation label duplication where a canonical route label is sufficient.
- Add locale parity and namespace hygiene checks so future changes cannot quietly regress to a monolithic `common` file.

## Non-Goals

- Adding Simplified Chinese or any third locale.
- Introducing `locize`, a TMS, or save-missing workflows.
- Migrating to the i18next selector API in this epic.
- Rewriting every copy string for tone or terminology.
- Localizing backend validation or server-generated messages.

## Validation Strategy

- Use focused frontend tests for each migrated slice rather than one all-or-nothing migration.
- Add a locale parity and namespace inventory check early in the epic so later stories can reuse it.
- Keep build and lint validation at the end of each story that changes translation imports or resource files.
- Use a final search-based hygiene pass to prove feature-owned keys no longer live under `public/locales/*/common.json`.

## Dependency and Phase Order

1. Story 41.1 establishes multi-namespace runtime support, test support, and parity guardrails.
2. Story 41.2 extracts route and shell text, then removes safe navigation duplication.
3. Story 41.3 migrates operations-heavy domains with the largest translation surface area.
4. Story 41.4 migrates the sales and finance domains.
5. Story 41.5 migrates the remaining domains, reduces `common` to shared primitives, and finalizes hygiene enforcement.

---

## Story 41.1: Multi-Namespace i18n Scaffolding

As a frontend developer,
I want runtime and test support for multiple i18n namespaces,
so that translation extraction can proceed without breaking the current app shell or test harness.

**Acceptance Criteria:**

1. Given the runtime currently initializes only `common`, when Story 41.1 lands, then `src/i18n.ts` supports loading `common`, `shell`, `routes`, and feature namespaces from `/locales/{lng}/{ns}.json` while preserving supported languages and single-brace interpolation.
2. Given the test helper currently seeds only `common`, when Story 41.1 lands, then `src/tests/helpers/i18n.ts` can register multiple namespaces for English and keep the current interpolation semantics intact.
3. Given later stories need safe migration guardrails, when a parity or hygiene check runs, then missing locale namespace files or mismatched namespace inventories between `en` and `zh-Hant` are surfaced before merge.

---

## Story 41.2: Shell and Route Translation Extraction

As a frontend developer,
I want app shell text and route metadata extracted into dedicated namespaces,
so that navigation, breadcrumbs, and page metadata stop depending on duplicated keys inside `common`.

**Acceptance Criteria:**

1. Given route labels and descriptions currently live under `common.routes.*`, when Story 41.2 lands, then they live in `routes.json` for both locales and route consumers resolve them from the `routes` namespace.
2. Given the sidebar currently duplicates many route labels under `nav.*`, when Story 41.2 lands, then route destinations reuse canonical `routes.*.label` values unless an explicit short-label exception is documented.
3. Given app chrome text is not page metadata, when Story 41.2 lands, then sidebar group headers, section headers, nav menu labels, language/theme labels, and app shell text live in `shell.json` or governed shared copy.
4. Given focused navigation and breadcrumb tests run, when Story 41.2 completes, then rendered English and Traditional Chinese labels remain unchanged except for documented short-label exceptions.

---

## Story 41.3: Operations Namespace Migration

As a frontend developer,
I want operations-heavy translation trees moved into their own namespaces,
so that inventory and procurement work can evolve without reopening the same global file.

**Acceptance Criteria:**

1. Given operations text currently lives under `common.inventory.*`, `common.procurement.*`, and `common.purchase.*`, when Story 41.3 lands, then those strings live in dedicated `inventory`, `procurement`, and `purchase` namespaces for both locales.
2. Given current consumers use `useTranslation("common", { keyPrefix: "inventory..." })` or equivalent, when Story 41.3 lands, then those consumers resolve through feature namespaces with simplified local key prefixes and no raw-key regressions.
3. Given focused operations tests run, when Story 41.3 completes, then inventory, procurement, and purchase surfaces keep their current rendered behavior and locale parity.

---

## Story 41.4: Sales and Finance Namespace Migration

As a frontend developer,
I want the sales and finance translation trees moved into dedicated namespaces,
so that customer, order, invoice, payment, and CRM workflows stop sharing one file-level namespace.

**Acceptance Criteria:**

1. Given the sales and finance copy currently lives under `common.crm.*`, `common.customer.*`, `common.orders.*`, `common.invoice.*`, and `common.payments.*`, when Story 41.4 lands, then those strings live in dedicated namespaces for both locales.
2. Given the affected pages and hooks currently read from `common`, when Story 41.4 lands, then they resolve feature copy through their owning namespace while still using `common` only for truly shared UI primitives.
3. Given focused sales and finance tests run, when Story 41.4 completes, then route labels, table text, form messages, and empty states keep current behavior in both locales.

---

## Story 41.5: Common Namespace Reduction and Locale Hygiene

As a frontend developer,
I want the remaining feature trees extracted and `common` reduced to governed shared primitives,
so that the old monolithic translation resource collapses into a small, durable shared layer.

**Acceptance Criteria:**

1. Given remaining feature text still lives under `common.admin.*`, `common.dashboard.*`, `common.intelligence.*`, `common.settingsPage.*`, and `common.auth.*`, when Story 41.5 lands, then those strings live in dedicated namespaces and the remaining `common` file contains only shared primitives and shared component copy.
2. Given the epic target forbids a feature-owned monolith, when Story 41.5 completes, then `public/locales/*/common.json` no longer contains major feature trees.
3. Given final validation runs, when Epic 41 completes, then build, lint, focused frontend tests, and locale hygiene checks all pass, and the namespace inventory matches between English and Traditional Chinese.

## References

- `src/i18n.ts`
- `src/tests/helpers/i18n.ts`
- `src/lib/navigation.tsx`
- `src/components/AppNavigation.tsx`
- `src/components/LanguageSwitcher.tsx`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`
- `src/pages/InventoryPage.tsx`
- `src/pages/procurement/CreateRFQPage.tsx`
- `src/pages/crm/LeadListPage.tsx`
- `src/pages/orders/OrdersPage.tsx`
- `src/pages/settings/SettingsPage.tsx`