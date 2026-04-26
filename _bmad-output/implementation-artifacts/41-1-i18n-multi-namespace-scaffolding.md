# Story 41.1: Multi-Namespace i18n Scaffolding

**Status:** completed

**Story ID:** 41.1

**Epic:** Epic 41 - Translation Namespace Architecture Hardening

---

## Story

As a frontend developer,
I want the runtime and test harness to support multiple i18n namespaces,
so that translation extraction can proceed without breaking the current app surface.

---

## Problem Statement

The frontend currently routes all translated copy through the `common` namespace even though the app is already organized by feature. `src/i18n.ts` initializes only `common`, `src/tests/helpers/i18n.ts` only seeds `common`, and the locale files under `public/locales/*/common.json` have grown into multi-thousand-line resources. Without a namespace-capable foundation, every later migration would have to mix runtime changes, test harness changes, and feature extraction in the same story.

## Solution

Establish namespace-aware runtime and test scaffolding first, without moving the large feature trees yet.

This story should:

- preserve the existing `/locales/{lng}/{ns}.json` loading contract
- preserve supported languages and single-brace interpolation
- create the namespace inventory for both locales
- add a parity or hygiene check that later stories can reuse

The goal is to make later extraction stories mechanical rather than architectural.

## Acceptance Criteria

1. Given the runtime currently initializes only `common`, when Story 41.1 lands, then `src/i18n.ts` supports loading `common`, `shell`, `routes`, and feature namespaces from `/locales/{lng}/{ns}.json` while preserving supported languages, language detection, and single-brace interpolation.
2. Given the test helper currently seeds only `common`, when Story 41.1 lands, then `src/tests/helpers/i18n.ts` can register multiple namespaces for English and keep the same interpolation semantics.
3. Given later stories need migration guardrails, when a parity or hygiene check runs, then missing locale namespace files or mismatched namespace inventories between `en` and `zh-Hant` are surfaced before merge.
4. Given this story is foundational only, when it completes, then no user-facing copy changes are required beyond namespace plumbing and test support.

## Tasks / Subtasks

- [ ] Task 1: Expand runtime namespace support in `src/i18n.ts`. (AC: 1)
  - [ ] Keep `common` as the default namespace.
  - [ ] Register `shell`, `routes`, and the planned feature namespaces so `react-i18next` can load them on demand.
  - [ ] Preserve `supportedLngs`, fallback behavior, detection order, and single-brace interpolation.
- [ ] Task 2: Create namespace scaffolding for both locales. (AC: 1, 3)
  - [ ] Add the target namespace files under `public/locales/en/`.
  - [ ] Add the matching target namespace files under `public/locales/zh-Hant/`.
  - [ ] Ensure the namespace inventory matches between languages before feature extraction begins.
- [ ] Task 3: Update the shared test harness for namespace-aware translation loading. (AC: 2)
  - [ ] Update `src/tests/helpers/i18n.ts` to load multiple namespaces.
  - [ ] Update shared test utilities or mocks that assume `common` is the only namespace, but do not broaden the change into feature migrations.
- [ ] Task 4: Add a locale parity and namespace hygiene check. (AC: 3)
  - [ ] Add a script or focused test that compares namespace inventories between `en` and `zh-Hant`.
  - [ ] Fail the check when a required namespace file is missing.
  - [ ] Make the check easy to rerun in later stories.

## Dev Notes

### Context

- `src/i18n.ts` already uses `i18next-http-backend`, `i18next-browser-languagedetector`, and `initReactI18next`.
- `src/tests/helpers/i18n.ts` currently imports only `public/locales/en/common.json`.
- The repo uses single-brace interpolation (`{value}`), not the default `{{value}}`.

### Architecture Compliance

- Do not move large feature trees in this story.
- Do not change route consumers yet unless a minimal smoke path is needed to prove namespace loading works.
- Prefer one reusable parity or hygiene check over ad hoc manual comparisons.

### Suggested File Targets

- `src/i18n.ts`
- `src/tests/helpers/i18n.ts`
- `public/locales/en/`
- `public/locales/zh-Hant/`
- `package.json` or `scripts/` if a new validation command is introduced

### Validation Commands

- `cd /Users/changtom/Downloads/UltrERP && pnpm build`
- `cd /Users/changtom/Downloads/UltrERP && pnpm lint`

## References

- `../planning-artifacts/epic-41.md`
- `src/i18n.ts`
- `src/tests/helpers/i18n.ts`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- 2026-04-26 review-fix pass: corrected `zh-Hant` language detection, restored legacy `common` compatibility for remaining consumers, and tightened locale parity coverage.

### Completion Notes List

- 2026-04-26: Implemented shared namespace constants plus 16-namespace runtime and test scaffolding.
- 2026-04-26: Fixed browser language detection so Traditional Chinese resolves to `zh-Hant` instead of falling back to English.
- 2026-04-26: Added legacy `common` compatibility layering and placeholder normalization so remaining `useTranslation("common")` consumers stay stable during the migration.
- 2026-04-26: Upgraded locale hygiene from namespace-inventory checks to leaf-key parity and single-brace interpolation validation.

### Validation

- `pnpm check:locale-parity`
- `pnpm exec vitest run src/tests/locale-parity.test.ts src/tests/invoices/InvoicePrintSheet.test.tsx src/tests/ui/DatePicker.test.tsx`
- VS Code diagnostics: no editor errors in touched i18n/runtime/test files

### File List

- `_bmad-output/implementation-artifacts/41-1-i18n-multi-namespace-scaffolding.md`
- `src/lib/i18n-resource-utils.ts`
- `src/i18n.ts`
- `src/tests/helpers/i18n.ts`
- `src/tests/locale-parity.test.ts`
- `scripts/check-locale-parity.ts`
- `public/locales/en/`
- `public/locales/zh-Hant/`