# UI/UX Gap Claims — Validation vs Source

**Reviewer:** review-ui agent
**Date:** 2026-04-20
**Source checked:** UltrERP main branch, actual source files

---

## Confirmed P0 Gaps

1. **Toast Notification System — MISSING**
   - `src/components/ui/` directory exists with 26 components. No `toast.tsx` or equivalent.
   - No `useToast` hook, no Toast provider in the component tree.
   - All user feedback is currently silent (no confirmation on form submit, no API error display at the global level).
   - **VERIFIED.**

2. **RecordPaymentForm — Uses raw useState, NOT react-hook-form**
   - `src/domain/payments/components/RecordPaymentForm.tsx` uses `useState` for all fields (amount, method, paymentDate, referenceNumber, notes).
   - Manual inline validation (`isValid` computed manually), no Zod schema.
   - Contrast: `CustomerForm.tsx` uses `react-hook-form` with a native resolver pattern.
   - **VERIFIED — gap is real and inconsistent within the same app.**

3. **Zod — NOT installed**
   - `package.json`: no `zod` dependency.
   - No `zodResolver` usage anywhere in `src/`.
   - Validation in CustomerForm uses a native resolver pattern (non-Zod).
   - Claim that Zod should be added is **VERIFIED** as a genuine gap.

4. **Breadcrumbs — MISSING**
   - Grep across entire `src/` for `breadcrumb`/`Breadcrumb` returns **zero matches**.
   - No Breadcrumb component in `src/components/ui/`.
   - No breadcrumb logic in any page component.
   - **VERIFIED.**

5. **`src/lib/schemas/` — Does NOT exist**
   - No centralized validation schemas directory.
   - Schemas are inlined in form components (e.g., CustomerForm has validation inline).
   - **VERIFIED.**

6. **`src/hooks/useForm.ts` — Does NOT exist**
   - No centralized form hook.
   - Forms are built per-component using `react-hook-form` directly.
   - **VERIFIED** (claim is accurate — no centralized form hook exists).

---

## Confirmed P1 Gaps

7. **AlertFeed CSS — Uses raw CSS classes, NOT Tailwind**
   - `src/domain/inventory/components/AlertFeed.tsx` uses raw CSS class names: `.alert-sidebar`, `.alert-item`, `.alert-sidebar-header`, `.alert-sidebar-title`, `.alert-filters`, `.alert-filter-btn`, `.alert-list`, `.alert-empty`, `.alert-empty-text`, `.alert-icon`, `.alert-body`, `.alert-product`, `.alert-desc`, `.alert-footer`, `.alert-meta`, `.alert-ack-btn`, `.alert-count-badge`.
   - These are defined in `inventory.css`, not in Tailwind.
   - **VERIFIED** — confirmed raw CSS usage inconsistent with the Tailwind-first approach.

8. **CommandBar CSS — Uses raw CSS classes, NOT Tailwind**
   - `src/domain/inventory/components/CommandBar.tsx` uses raw CSS class names: `.command-bar`, `.command-search`, `.command-actions`, `.drawer-action-btn`, `.command-shortcut`.
   - These are defined in `inventory.css`.
   - **VERIFIED** — confirmed raw CSS usage.

---

## Disputed Claims (gap exists but described differently)

9. **DatePicker — Claimed missing, actually partially exists in utilities**
   - `src/lib/time.ts` and dashboard components reference date formatting utilities.
   - However, there is NO `DatePicker` component in `src/components/ui/`.
   - The codebase uses native `<input type="date">` inputs throughout.
   - **Partially disputed**: Gap is real (no calendar picker component), but there ARE date utilities in `src/lib/time.ts` — not a total void.

10. **Command palette — Component exists but not wired globally**
    - `src/components/ui/command.tsx` exists (cmdk-based `Command` component).
    - However, it is NOT wired globally — no keyboard listener, no global ⌘K activation.
    - Claimed as "missing" — actually "exists but not implemented globally" is more precise.
    - **Disputed framing, gap is real** (global palette is not functional).

---

## False Positives

None found. All claimed gaps are real or partially real.

---

## New UI Gaps Found in Source

1. **`src/components/ui/` has no `toast` — but also has no `sonner`** (another common Radix-based toast library). The gap is complete silence on notifications.

2. **AlertFeed and CommandBar share `inventory.css`** — these are the two raw-CSS components flagged in P1, but they may be the only two in the codebase using this pattern. A full audit of `src/` for raw CSS class usage (vs `cn()`) was not done in this review, but only these two were called out in the gap analysis.

3. **`src/components/ui/command.tsx` exists but has no global keyboard shortcut wiring** — any global ⌘K implementation would need to wrap the app in a Command provider or attach a keyboard listener at the app root.

4. **No centralized icon system** — icons are imported individually from `lucide-react` throughout. No `Icon` wrapper component.

5. **No form error summary component** — RecordPaymentForm shows errors via `SurfaceMessage`, but there's no generic `FormErrorSummary` component for form-level validation errors.

---

## Summary

| Claim | Status |
|-------|--------|
| Toast missing (P0) | CONFIRMED |
| RecordPaymentForm uses useState not react-hook-form (P0) | CONFIRMED |
| Zod not installed (P0) | CONFIRMED |
| Breadcrumbs missing (P0) | CONFIRMED |
| DatePicker missing (P1) | CONFIRMED (with nuance — date utils exist) |
| Global command palette not wired (P1) | CONFIRMED (component exists) |
| AlertFeed uses raw CSS (P1) | CONFIRMED |
| CommandBar uses raw CSS (P1) | CONFIRMED |
| src/lib/schemas/ missing | CONFIRMED |
| src/hooks/useForm.ts missing | CONFIRMED |
| Command component exists | TRUE (disputes "missing" framing) |

**Bottom line:** The gap analysis is well-supported. All P0 and P1 claims are accurate. The only disputed item is the command palette framing — the component exists, it just isn't wired globally.
