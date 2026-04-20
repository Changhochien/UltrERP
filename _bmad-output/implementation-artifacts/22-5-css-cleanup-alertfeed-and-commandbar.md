# Story 22.5: CSS Cleanup - AlertFeed and CommandBar

**Status:** ready-for-dev

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

- [ ] Task 1: Audit current component and stylesheet ownership. (AC: 1-3)
  - [ ] Review `src/domain/inventory/components/AlertFeed.tsx`, `src/domain/inventory/components/CommandBar.tsx`, and `src/domain/inventory/inventory.css`.
  - [ ] Confirm exactly which selectors belong to these two components before removing anything.
- [ ] Task 2: Convert AlertFeed styling to the shared class system. (AC: 1)
  - [ ] Replace the raw component-specific CSS dependency with utility classes and existing design tokens.
  - [ ] Preserve current layout, spacing, hover, unread, and emphasis behavior.
- [ ] Task 3: Convert CommandBar styling to the shared class system. (AC: 2)
  - [ ] Replace the raw component-specific CSS dependency with utility classes and existing design tokens.
  - [ ] Preserve current structure for the search input, results list, and action affordances.
- [ ] Task 4: Remove or relocate only the unused stylesheet rules. (AC: 3)
  - [ ] Delete the now-unused selectors for AlertFeed and CommandBar from `inventory.css`.
  - [ ] Leave drawer, timeline, warehouse-card, or other still-active rules alone unless they are also touched by this story.
  - [ ] If a truly shared rule still belongs in CSS, move it deliberately rather than deleting it blindly.
- [ ] Task 5: Add focused regression coverage. (AC: 1-3)
  - [ ] Add focused rendering tests or lightweight visual assertions for the touched components.
  - [ ] Verify the inventory workspace still renders correctly after the stylesheet cleanup.

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

Record the implementation model and version here.

### Debug Log References

Record focused frontend validation commands and any visual verification here.

### Completion Notes List

Summarize the selectors removed, the utility-class conversion, and any remaining inventory.css follow-up here once implementation is done.

### File List

- `src/domain/inventory/components/AlertFeed.tsx`
- `src/domain/inventory/components/CommandBar.tsx`
- `src/domain/inventory/inventory.css`
- any focused frontend tests added for the touched components