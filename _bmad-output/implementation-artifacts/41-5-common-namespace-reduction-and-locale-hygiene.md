# Story 41.5: Common Namespace Reduction and Locale Hygiene

**Status:** in-progress

**Story ID:** 41.5

**Epic:** Epic 41 - Translation Namespace Architecture Hardening

---

## Story

As a frontend developer,
I want the remaining feature trees extracted and `common` reduced to governed shared primitives,
so that the old monolithic translation resource collapses into a small, durable shared layer.

---

## Problem Statement

Even after shell, route, operations, sales, and finance extraction, the translation system will still be incomplete unless the remaining feature trees are moved out and `common` is actively reduced. Without a final cleanup story, the repo could end up with both new namespaces and a legacy `common` file that still owns major feature slices.

## Solution

Extract the remaining domain trees, reduce `common` to shared primitives and shared component text, and tighten locale hygiene checks so the monolithic structure cannot silently return.

This story should:

- move the remaining feature trees into dedicated namespaces
- normalize `settingsPage.*` into the `settings` namespace
- remove major feature-owned trees from `common.json`
- strengthen the namespace hygiene check to guard against regressions

## Acceptance Criteria

1. Given remaining feature text still lives under `common.admin.*`, `common.dashboard.*`, `common.intelligence.*`, `common.settingsPage.*`, and `common.auth.*`, when Story 41.5 lands, then those strings live in dedicated namespaces and the remaining `common` file contains only shared primitives and shared component copy.
2. Given Epic 41 forbids a feature-owned monolith, when Story 41.5 completes, then `public/locales/*/common.json` no longer contains major feature trees.
3. Given final validation runs, when Story 41.5 completes, then build, lint, focused frontend tests, and locale hygiene checks all pass, and the namespace inventory matches between English and Traditional Chinese.

## Tasks / Subtasks

- [ ] Task 1: Extract the remaining feature trees into dedicated namespaces. (AC: 1)
  - [ ] Add `admin.json`, `dashboard.json`, `intelligence.json`, `settings.json`, and `auth.json` for both locales.
  - [ ] Move the corresponding trees out of `common.json`.
  - [ ] Normalize `settingsPage.*` into `settings` namespace-local keys.
- [ ] Task 2: Migrate remaining consumers to feature namespaces. (AC: 1)
  - [ ] Update dashboard, settings, admin, intelligence, and auth-facing pages and components.
  - [ ] Keep shell, routes, and common responsibilities separated.
- [ ] Task 3: Reduce `common` to governed shared primitives. (AC: 2)
  - [ ] Keep only shared actions, status text, validation, shared component copy, and shared widget text in `common`.
  - [ ] Remove feature-owned trees from `public/locales/en/common.json` and `public/locales/zh-Hant/common.json`.
- [ ] Task 4: Finalize namespace hygiene enforcement and validate the epic. (AC: 3)
  - [ ] Tighten the parity or hygiene check so major feature trees under `common` fail validation.
  - [ ] Run focused frontend tests, lint, and build.
  - [ ] Perform a final search-based audit to confirm the new namespace model is the active structure.

## Dev Notes

### Context

- The final story is where the monolithic `common` resource actually collapses into a governed shared layer.
- `settingsPage` is the one verified section whose namespace should be normalized during extraction rather than preserved as a final namespace name.

### Architecture Compliance

- `common` should remain small and stable after this story.
- Do not leave duplicate feature trees in both `common` and their new namespace files.
- Keep route and shell text out of feature namespaces.

### Suggested File Targets

- `src/pages/dashboard/**`
- `src/pages/settings/**`
- `src/pages/AdminPage.tsx`
- `src/pages/IntelligencePage.tsx`
- `src/pages/LoginPage.tsx`
- `src/domain/intelligence/**`
- `src/domain/dashboard/**`
- `public/locales/en/admin.json`
- `public/locales/zh-Hant/admin.json`
- `public/locales/en/dashboard.json`
- `public/locales/zh-Hant/dashboard.json`
- `public/locales/en/intelligence.json`
- `public/locales/zh-Hant/intelligence.json`
- `public/locales/en/settings.json`
- `public/locales/zh-Hant/settings.json`
- `public/locales/en/auth.json`
- `public/locales/zh-Hant/auth.json`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`

## References

- `../planning-artifacts/epic-41.md`
- `src/pages/settings/SettingsPage.tsx`
- `src/pages/AdminPage.tsx`
- `src/pages/IntelligencePage.tsx`
- `src/pages/LoginPage.tsx`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- 2026-04-26 review-fix pass: reopened the final hardening story because the rollout still needs a temporary legacy-`common` compatibility bridge and repo-wide frontend validation is blocked by unrelated pre-existing issues.

### Completion Notes List

- 2026-04-26: Strengthened locale hygiene to enforce leaf-key parity plus the repo's single-brace interpolation contract.
- 2026-04-26: Normalized placeholder syntax across locale JSON files and backfilled missing peer keys so `en` and `zh-Hant` inventories stay aligned.
- 2026-04-26: Added shared `common` primitives needed by surviving shared consumers while the runtime compatibility bridge covers remaining legacy feature lookups.
- 2026-04-26: Reopened final hardening because repo-wide `pnpm lint` and `pnpm build` still fail in unrelated pre-existing files and the runtime compatibility bridge is still required.

### Validation

- `pnpm check:locale-parity`
- `pnpm exec vitest run src/tests/locale-parity.test.ts src/tests/invoices/InvoicePrintSheet.test.tsx src/tests/ui/DatePicker.test.tsx`
- `pnpm lint` currently fails in unrelated pre-existing test/config files outside the Epic 41 slice
- `pnpm build` currently fails on unrelated pre-existing frontend TypeScript issues outside the touched files

### File List

- `_bmad-output/implementation-artifacts/41-5-common-namespace-reduction-and-locale-hygiene.md`
- `src/lib/i18n-resource-utils.ts`
- `src/tests/locale-parity.test.ts`
- `scripts/check-locale-parity.ts`
- `src/pages/settings/`
- `src/pages/AdminPage.tsx`
- `src/pages/IntelligencePage.tsx`
- `src/pages/LoginPage.tsx`
- `src/domain/dashboard/`
- `src/domain/intelligence/`
- `public/locales/en/admin.json`
- `public/locales/zh-Hant/admin.json`
- `public/locales/en/dashboard.json`
- `public/locales/zh-Hant/dashboard.json`
- `public/locales/en/intelligence.json`
- `public/locales/zh-Hant/intelligence.json`
- `public/locales/en/settings.json`
- `public/locales/zh-Hant/settings.json`
- `public/locales/en/auth.json`
- `public/locales/zh-Hant/auth.json`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`