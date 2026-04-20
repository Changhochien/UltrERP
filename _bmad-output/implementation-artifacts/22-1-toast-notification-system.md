# Story 22.1: Toast Notification System

**Status:** ready-for-dev

**Story ID:** 22.1

**Epic:** Epic 22 - UI Foundation System: Toast, DatePicker, Breadcrumb, Form Validation, and TanStackDataTable

---

## Story

As an operator performing create, update, confirm, receive, and reconcile actions,
I want clear transient success and failure feedback,
so that important mutations never complete silently while persistent page states remain visible inline.

## Acceptance Criteria

1. Given the app root is wrapped with a ToastProvider, when a supported mutation succeeds, then a success toast appears in the bottom-right corner with a title and optional description and auto-dismisses after 5 seconds by default.
2. Given the app root is wrapped with a ToastProvider, when a supported mutation fails, then an error toast appears with the relevant server or fallback message.
3. Given a page-level load failure, empty state, or blocking inline warning is rendered, when the page displays that state, then the message remains inline via `SurfaceMessage` instead of being downgraded to a transient toast.
4. Given multiple mutations fire in quick succession, when toasts are emitted rapidly, then they stack without overlapping and only the newest 5 remain visible.
5. Given toast content is rendered, when assistive technologies read the page, then the toast uses accessible live-region semantics and remains dismissible by mouse and keyboard.

## Tasks / Subtasks

- [ ] Task 1: Add the toast infrastructure. (AC: 1, 2, 4, 5)
  - [ ] Add `@radix-ui/react-toast` to `package.json`.
  - [ ] Create `src/components/ui/Toast.tsx` as the Radix wrapper with UltrERP variants, stacking, portal rendering, and dismissal controls.
  - [ ] Create `src/providers/ToastProvider.tsx` and a new `src/hooks/useToast.ts` hook.
  - [ ] Reuse the already-installed `framer-motion` package for enter and exit animation.
- [ ] Task 2: Wire the provider at the app root. (AC: 1, 2)
  - [ ] Insert `ToastProvider` into the existing root tree in `src/App.tsx` without disturbing `AuthProvider`, `ThemeProvider`, `AuthGate`, or `SidebarProvider` behavior.
  - [ ] Ensure every routed page can call `useToast()` safely after the provider is mounted.
- [ ] Task 3: Define the API and message boundary. (AC: 2, 3, 5)
  - [ ] Implement `toast`, `success`, `error`, `warning`, and `info` helpers from `useToast()`.
  - [ ] Map toast variants to the current token system: success, destructive, warning, and info.
  - [ ] Audit current `SurfaceMessage` usage and document the boundary between transient mutation feedback and persistent inline state in the story implementation notes.
- [ ] Task 4: Apply the first integration slice to high-value mutations. (AC: 1, 2, 3)
  - [ ] Add toast callbacks to the highest-impact mutation paths first: order confirmation, customer create or update, invoice creation, and both payment-recording flows.
  - [ ] Keep persistent fetch errors and blocking warnings inline.
  - [ ] Avoid introducing a new global mutation abstraction unless the touched hooks already share one.
- [ ] Task 5: Add focused test coverage. (AC: 1-5)
  - [ ] Add component tests for provider wiring, variant rendering, stack limits, and manual dismissal.
  - [ ] Add focused integration coverage for at least one success path and one failure path.
  - [ ] Validate keyboard and assistive-technology behavior on the rendered toast viewport.

## Dev Notes

### Context

- There is currently no toast system in the repo.
- `SurfaceMessage` already exists in `src/components/layout/PageLayout.tsx` and should remain the persistent inline-state pattern.
- `src/App.tsx` currently composes the root providers and is the correct place to insert a toast provider.

### Architecture Compliance

- Do not replace every inline error with a toast. That would regress UX for blocking or persistent states.
- Keep the implementation additive. Introduce toast infrastructure without refactoring unrelated layout or auth wiring.
- Prefer targeted `onSuccess` and `onError` integration in touched hooks over inventing a new cross-app event bus.

### Implementation Guidance

- Primary files:
  - `src/App.tsx`
  - `src/components/ui/Toast.tsx`
  - `src/providers/ToastProvider.tsx`
  - `src/hooks/useToast.ts`
  - `src/components/layout/PageLayout.tsx`
  - touched mutation hooks under `src/domain/**/hooks/`
- Variant styling should align with existing design tokens rather than introducing a separate visual system.
- Default toast duration should be configurable per call, with 5000ms as the default.

### Testing Requirements

- Frontend tests are the priority for this story.
- Add at least one integration test proving a hooked mutation produces toast output on success and failure.
- Preserve the current inline `SurfaceMessage` behavior in existing pages after toast integration.

### References

- `src/App.tsx`
- `src/components/layout/PageLayout.tsx`
- `src/domain/orders/hooks/useOrders.ts`
- `src/domain/payments/components/RecordPaymentForm.tsx`
- `src/domain/payments/components/RecordUnmatchedPayment.tsx`
- `package.json`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

Record the implementation model and version here.

### Debug Log References

Record focused frontend test commands and any validation artifacts here.

### Completion Notes List

Summarize the provider wiring, the message-boundary decisions, and the touched mutation hooks here once implementation is done.

### File List

- `package.json`
- `src/App.tsx`
- `src/components/ui/Toast.tsx`
- `src/providers/ToastProvider.tsx`
- `src/hooks/useToast.ts`
- touched mutation hooks under `src/domain/**/hooks/`
- any focused frontend tests added for toast behavior