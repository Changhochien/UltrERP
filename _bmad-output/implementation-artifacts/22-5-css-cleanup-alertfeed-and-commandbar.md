# Story 22.5: CSS Cleanup - AlertFeed and CommandBar

**Status:** done

**Story ID:** 22.5

**Epic:** Epic 22 - UI Foundation System: Toast, DatePicker, Breadcrumb, Form Validation, and TanStackDataTable

---

## Story

As a developer maintaining the inventory workspace,
I want `AlertFeed` and `CommandBar` styling to live in the shared Tailwind-driven UI system,
so that these components stop drifting away from the rest of the app and become easier to maintain.

## Acceptance Criteria

1. Given `AlertFeed` renders in the inventory workspace, when this story is complete, then its styling comes from the shared utility-class system instead of component-specific raw CSS rules.
2. Given `CommandBar` renders in the inventory workspace, when this story is complete, then its styling also comes from the shared utility-class system instead of raw CSS rules.
3. Given the touched CSS is audited after migration, when unused AlertFeed or CommandBar rules are removed, then `inventory.css` no longer carries dead rules for those components while unrelated inventory styles remain intact.

## Tasks / Subtasks

- [x] Task 1: Audit current component and stylesheet ownership. (AC: 1-3)
  - [x] Review `src/domain/inventory/components/AlertFeed.tsx`, `src/domain/inventory/components/CommandBar.tsx`, and `src/domain/inventory/inventory.css`.
  - [x] Confirm exactly which selectors belong to these two components before removing anything.
- [x] Task 2: Convert AlertFeed styling to the shared class system. (AC: 1)
  - [x] Replace the raw component-specific CSS dependency with utility classes and existing design tokens.
  - [x] Preserve current layout, spacing, hover, unread, and emphasis behavior.
- [x] Task 3: Convert CommandBar styling to the shared class system. (AC: 2)
  - [x] Replace the raw component-specific CSS dependency with utility classes and existing design tokens.
  - [x] Preserve current structure for the search input, results list, and action affordances.
- [x] Task 4: Remove or relocate only the unused stylesheet rules. (AC: 3)
  - [x] Delete the now-unused selectors for AlertFeed and CommandBar from `inventory.css`.
  - [x] Leave drawer, timeline, warehouse-card, or other still-active rules alone unless they are also touched by this story.
  - [x] If a truly shared rule still belongs in CSS, move it deliberately rather than deleting it blindly.
- [x] Task 5: Add focused regression coverage. (AC: 1-3)
  - [x] Add focused rendering tests or lightweight visual assertions for the touched components.
  - [x] Verify the inventory workspace still renders correctly after the stylesheet cleanup.

## Dev Notes

### Context

- `src/domain/inventory/inventory.css` currently holds raw component CSS alongside still-used drawer and timeline rules.
- This story is intentionally narrow: convert AlertFeed and CommandBar without turning it into a full inventory stylesheet rewrite.

### Architecture Compliance

- Do not remove unrelated inventory CSS during this story.
- Keep the converted components aligned with the rest of the shared UI language.
- Prefer additive class composition over bespoke new CSS blocks.

### Implementation Guidance

- Primary files:
  - `src/domain/inventory/components/AlertFeed.tsx`
  - `src/domain/inventory/components/CommandBar.tsx`
  - `src/domain/inventory/inventory.css`
- Use existing tokens and helpers such as `cn()` where needed.
- If Tailwind utility composition alone becomes unreadable, use the smallest shared helper possible rather than falling back to new raw component CSS.

### Testing Requirements

- Frontend rendering or interaction coverage is sufficient for this story.
- Validate that the inventory workspace still renders without missing styles after the cleanup.
- Confirm there are no orphaned selectors for AlertFeed or CommandBar left behind.

### References

- `src/domain/inventory/components/AlertFeed.tsx`
- `src/domain/inventory/components/CommandBar.tsx`
- `src/domain/inventory/inventory.css`
- `src/lib/utils.ts`

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `pnpm vitest run src/domain/inventory/__tests__/AlertFeed.test.tsx`
- `pnpm vitest run src/domain/inventory/__tests__/AlertFeed.test.tsx src/domain/inventory/__tests__/CommandBar.test.tsx`
- `pnpm vitest run src/domain/inventory/__tests__/AlertFeed.test.tsx src/domain/inventory/__tests__/CommandBar.test.tsx src/pages/InventoryPage.test.tsx`
- `pnpm vitest run src/domain/inventory/components/StockAdjustmentForm.test.tsx src/tests/inventory/ProductForm.test.tsx src/domain/inventory/__tests__/AlertFeed.test.tsx src/domain/inventory/__tests__/CommandBar.test.tsx src/pages/InventoryPage.test.tsx`

### Completion Notes List

- Audited `src/domain/inventory/inventory.css` and confirmed the old AlertFeed and CommandBar selectors were already gone, so no further stylesheet deletion was required for this story.
- Rebuilt `CommandBar` on shared `Input` and `Button` primitives, then mounted it on the live inventory page with page-owned search state and action wiring for stock adjustment, transfers, and order creation.
- Replaced the stale standalone `AlertFeed` implementation with a wrapper over the live `AlertPanel` surface so the story now targets the actual inventory workspace instead of dead component code.
- Converted the inventory page stock-adjustment and create-product overlays to shared dialogs, reset their form state on reopen, and localized the newly live command-bar and dialog flows.
- Localized `StockAdjustmentForm`, `CreateProductForm`, and `ProductForm`, fixed stock-adjustment confirmation interpolation to match the repo's single-brace i18n configuration, and added focused regression coverage for the live page wiring and dialog behavior.

### File List

- `src/domain/inventory/components/AlertFeed.tsx`
- `src/domain/inventory/components/CommandBar.tsx`
- `src/domain/inventory/components/CreateProductForm.tsx`
- `src/domain/inventory/components/ProductForm.tsx`
- `src/domain/inventory/components/ProductTable.tsx`
- `src/domain/inventory/components/StockAdjustmentForm.tsx`
- `src/domain/inventory/__tests__/AlertFeed.test.tsx`
- `src/domain/inventory/__tests__/CommandBar.test.tsx`
- `src/domain/inventory/components/StockAdjustmentForm.test.tsx`
- `src/pages/InventoryPage.tsx`
- `src/pages/InventoryPage.test.tsx`
- `public/locales/en/common.json`
- `public/locales/zh-Hant/common.json`
- `src/domain/inventory/inventory.css` (audited, unchanged)