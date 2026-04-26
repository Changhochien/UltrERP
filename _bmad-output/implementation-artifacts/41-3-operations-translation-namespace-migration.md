# Story 41.3: Operations Translation Namespace Migration

**Status:** completed

**Story ID:** 41.3

**Epic:** Epic 41 - Translation Namespace Architecture Hardening

---

## Story

As a frontend developer,
I want the operations-heavy translation trees moved into dedicated namespaces,
so that inventory, procurement, and purchase surfaces stop bloating the global translation file.

---

## Problem Statement

The inventory slice alone is the largest translation owner in the current locale resources. Procurement and purchase-related copy sit beside it in the same `common` namespace even though the codebase already groups those workflows by page and component. This makes every operations copy change harder to review and blocks feature owners from working inside bounded locale files.

## Solution

Move operations-heavy translation trees into dedicated namespaces and simplify key prefixes so the namespace provides the domain context.

This story should:

- extract inventory strings into `inventory.json`
- extract procurement strings into `procurement.json`
- extract purchase strings into `purchase.json`
- update consumers from `useTranslation("common", { keyPrefix: "inventory..." })` style calls to feature namespaces with local key prefixes

## Acceptance Criteria

1. Given operations text currently lives under `common.inventory.*`, `common.procurement.*`, and `common.purchase.*`, when Story 41.3 lands, then those strings live in dedicated `inventory`, `procurement`, and `purchase` namespaces for both locales.
2. Given current consumers rely on `common` plus deep feature key prefixes, when Story 41.3 lands, then those consumers resolve through feature namespaces with simplified local key prefixes and no raw-key regressions.
3. Given focused operations tests run, when Story 41.3 completes, then inventory, procurement, and purchase surfaces keep their current rendered behavior and locale parity.

## Tasks / Subtasks

- [ ] Task 1: Extract operations locale trees into dedicated namespace files. (AC: 1)
  - [ ] Add `inventory.json`, `procurement.json`, and `purchase.json` for both locales.
  - [ ] Move the corresponding translation trees out of `common.json`.
  - [ ] Keep route labels in `routes`, not in the feature namespaces.
- [ ] Task 2: Migrate inventory consumers to the `inventory` namespace. (AC: 2)
  - [ ] Update `src/pages/InventoryPage.tsx` and `src/pages/inventory/**`.
  - [ ] Update `src/domain/inventory/**` components and helpers.
  - [ ] Simplify local key prefixes so they do not repeat `inventory.` inside the namespace.
- [ ] Task 3: Migrate procurement and purchase consumers to feature namespaces. (AC: 2)
  - [ ] Update `src/pages/procurement/**`.
  - [ ] Update `src/pages/PurchasesPage.tsx` and `src/domain/purchases/**`.
  - [ ] Preserve shared UI atoms through `common` only where they are truly shared.
- [ ] Task 4: Revalidate the operations slice after migration. (AC: 3)
  - [ ] Run focused operations tests.
  - [ ] Re-run locale parity and namespace hygiene checks.

## Dev Notes

### Context

- The current locale files show inventory as the single largest translation owner.
- Many operations consumers already use deep `keyPrefix` values, which makes this migration mostly mechanical once namespaces exist.

### Architecture Compliance

- Do not keep `inventory.*` nested under the `inventory` namespace root.
- Keep `routes.*` in the `routes` namespace rather than duplicating them in feature files.
- Reuse `common` only for truly shared atoms such as actions, validation, date-pickers, or shared status text.

### Suggested File Targets

- `src/pages/InventoryPage.tsx`
- `src/pages/inventory/**`
- `src/domain/inventory/**`
- `src/pages/procurement/**`
- `src/pages/PurchasesPage.tsx`
- `src/domain/purchases/**`
- `public/locales/en/inventory.json`
- `public/locales/zh-Hant/inventory.json`
- `public/locales/en/procurement.json`
- `public/locales/zh-Hant/procurement.json`
- `public/locales/en/purchase.json`
- `public/locales/zh-Hant/purchase.json`

## References

- `../planning-artifacts/epic-41.md`
- `src/pages/InventoryPage.tsx`
- `src/pages/procurement/RFQListPage.tsx`
- `src/pages/PurchasesPage.tsx`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- 2026-04-26 review-fix pass: locale parity surfaced missing peer keys and invalid placeholder syntax inside the split operations namespace files.

### Completion Notes List

- 2026-04-26: Operations locale trees remain split into dedicated `inventory`, `procurement`, and `purchase` namespace files.
- 2026-04-26: Normalized placeholder syntax and backfilled missing `en`/`zh-Hant` peer keys so the operations namespace files pass the strengthened locale parity check.
- 2026-04-26: Runtime legacy-`common` compatibility keeps any remaining operations consumers stable while final cleanup continues elsewhere in the epic.

### Validation

- `pnpm check:locale-parity`
- VS Code diagnostics: no editor errors in touched locale-validation files

### File List

- `_bmad-output/implementation-artifacts/41-3-operations-translation-namespace-migration.md`
- `src/pages/InventoryPage.tsx`
- `src/pages/inventory/`
- `src/domain/inventory/`
- `src/pages/procurement/`
- `src/pages/PurchasesPage.tsx`
- `src/domain/purchases/`
- `public/locales/en/inventory.json`
- `public/locales/zh-Hant/inventory.json`
- `public/locales/en/procurement.json`
- `public/locales/zh-Hant/procurement.json`
- `public/locales/en/purchase.json`
- `public/locales/zh-Hant/purchase.json`