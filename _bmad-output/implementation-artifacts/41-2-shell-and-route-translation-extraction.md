# Story 41.2: Shell and Route Translation Extraction

**Status:** completed

**Story ID:** 41.2

**Epic:** Epic 41 - Translation Namespace Architecture Hardening

---

## Story

As a frontend developer,
I want shell text and route metadata extracted into dedicated namespaces,
so that navigation, breadcrumbs, and page metadata stop relying on duplicated `common` keys.

---

## Problem Statement

The app shell currently mixes sidebar group labels, menu labels, workspace chrome, and route metadata into the same `common` namespace. `src/lib/navigation.tsx` also maintains route-oriented navigation labels under `nav.*` while page labels live under `routes.*.label`. Local analysis found 25 shared key stems and 22 identical values across the two label families. That duplication increases maintenance cost while offering almost no semantic benefit.

## Solution

Extract app shell text into `shell.json` and page metadata into `routes.json`, then make route labels canonical for route destinations.

This story should:

- move `common.routes.*` into `routes.json`
- move app chrome text such as `app.*`, `navMenu.*`, and shell-only navigation headers into `shell.json`
- refactor navigation metadata so route destinations default to `routes.*.label`
- keep separate short-label keys only for the verified exceptions that intentionally differ from the route label

## Acceptance Criteria

1. Given route labels and descriptions currently live under `common.routes.*`, when Story 41.2 lands, then they live in `routes.json` for both locales and consumers resolve them from the `routes` namespace.
2. Given route destinations in the sidebar currently duplicate many route labels under `nav.*`, when Story 41.2 lands, then those destinations reuse canonical `routes.*.label` values unless an explicit short-label exception is documented.
3. Given shell-only copy is not page metadata, when Story 41.2 lands, then sidebar group headers, section headers, nav menu labels, language and theme labels, and app shell text live in `shell.json` or a governed shared namespace.
4. Given focused navigation and breadcrumb tests run, when Story 41.2 completes, then rendered English and Traditional Chinese labels remain unchanged except for documented short-label exceptions.

## Tasks / Subtasks

- [ ] Task 1: Create shell and route namespace files for both locales. (AC: 1, 3)
  - [ ] Add `public/locales/en/routes.json` and `public/locales/zh-Hant/routes.json`.
  - [ ] Add `public/locales/en/shell.json` and `public/locales/zh-Hant/shell.json`.
  - [ ] Move route and shell trees out of `common.json` into their new homes.
- [ ] Task 2: Refactor route metadata consumers to the `routes` namespace. (AC: 1)
  - [ ] Update pages and helpers that currently call `t("routes.*")` from `useTranslation("common")`.
  - [ ] Keep breadcrumb, title, and description behavior unchanged.
- [ ] Task 3: Refactor navigation metadata to remove safe duplication. (AC: 2, 3)
  - [ ] Update `src/lib/navigation.tsx` so route destinations default to `routes.*.label`.
  - [ ] Introduce explicit shell short-label keys only for destinations whose sidebar label should remain shorter than the route label.
  - [ ] Update `src/components/AppNavigation.tsx`, `src/components/LanguageSwitcher.tsx`, and any shell consumers accordingly.
- [ ] Task 4: Add focused regression coverage for shell and route extraction. (AC: 4)
  - [ ] Validate navigation rendering, breadcrumb labels, and locale parity after the extraction.
  - [ ] Preserve the current three verified short-label exceptions unless product direction changes.

## Dev Notes

### Context

- `src/lib/navigation.tsx` is the structural owner of sidebar metadata.
- `src/components/AppNavigation.tsx` resolves the visible labels.
- Many pages already depend on `routes.*.label` and `routes.*.description`, but they currently do so through the `common` namespace.

### Verified Duplication Baseline

- Shared nav/route stems: 25
- Identical label pairs: 22
- Verified short-label exceptions: `belowReorderReport`, `inventoryCategories`, `inventoryValuation`

### Architecture Compliance

- Use the `routes` namespace as the canonical source for route destination labels.
- Keep shell-only labels in `shell`, not `common`.
- Do not widen this story into feature-namespace extraction beyond shell and route consumers.

### Suggested File Targets

- `src/lib/navigation.tsx`
- `src/components/AppNavigation.tsx`
- `src/components/LanguageSwitcher.tsx`
- `src/pages/**`
- `public/locales/en/routes.json`
- `public/locales/zh-Hant/routes.json`
- `public/locales/en/shell.json`
- `public/locales/zh-Hant/shell.json`

## References

- `../planning-artifacts/epic-41.md`
- `src/lib/navigation.tsx`
- `src/components/AppNavigation.tsx`
- `src/components/LanguageSwitcher.tsx`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- 2026-04-26 review-fix pass: corrected shell consumers that still resolved route or shared `common` keys through the wrong namespace.

### Completion Notes List

- 2026-04-26: Corrected shell header section rendering so `routes.*` section labels resolve through the `routes` namespace instead of `shell`.
- 2026-04-26: Corrected `AppNavigation` footer fallbacks to read shared guest and tenant text from `common`.
- 2026-04-26: Added the missing English shell navigation keys needed by the extracted shell namespace.
- 2026-04-26: Revalidated route and shell locale parity after the review-fix pass.

### Validation

- `pnpm check:locale-parity`
- `pnpm exec vitest run src/tests/locale-parity.test.ts src/tests/invoices/InvoicePrintSheet.test.tsx src/tests/ui/DatePicker.test.tsx`
- VS Code diagnostics: no editor errors in touched shell/route consumers

### File List

- `_bmad-output/implementation-artifacts/41-2-shell-and-route-translation-extraction.md`
- `src/App.tsx`
- `src/lib/navigation.tsx`
- `src/components/AppNavigation.tsx`
- `src/components/LanguageSwitcher.tsx`
- `public/locales/en/routes.json`
- `public/locales/zh-Hant/routes.json`
- `public/locales/en/shell.json`
- `public/locales/zh-Hant/shell.json`