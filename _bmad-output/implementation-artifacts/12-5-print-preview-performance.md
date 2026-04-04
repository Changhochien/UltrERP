# Story 12.5: Print Preview Performance

Status: ready-for-dev

## Story

As a finance clerk,
I want invoice print preview to open in under 1 second,
So that I can verify layout quickly before printing.

## Acceptance Criteria

**AC1:** Preview surface opens within budget  
**Given** an invoice exists and is print-ready  
**When** I open print preview  
**Then** the preview surface renders in under 1 second on target hardware  
**And** the timing excludes the OS print dialog and any PDF-export startup cost

**AC2:** Shared renderer remains the single source of truth  
**Given** preview and printing both exist  
**When** this story lands  
**Then** both paths still use the same invoice print renderer  
**And** the story does not introduce a second preview-only layout template

**AC3:** Large invoices remain usable  
**Given** an invoice has a realistic large line-item payload  
**When** I open preview  
**Then** the UI remains responsive enough to review the document immediately  
**And** the preview controls do not visibly jank while mounting

## Tasks / Subtasks

- [ ] **Task 1: Add a real baseline measurement for preview-open time** (AC1)
  - [ ] Instrument the preview-open path with browser performance marks or equivalent timing hooks
  - [ ] Measure from user action to preview-ready state, not to `window.print()`
  - [ ] Record the exact metric definition in code comments or implementation notes so future measurements stay comparable

- [ ] **Task 2: Optimize the existing preview path instead of rebuilding it** (AC1, AC2, AC3)
  - [ ] Start from `src/components/invoices/print/InvoicePrintPreviewModal.tsx`
  - [ ] Keep `src/components/invoices/print/InvoicePrintSheet.tsx` as the rendering source of truth
  - [ ] Reduce avoidable work on preview open: repeated derived-data assembly, unnecessary remount churn, or layout thrash
  - [ ] If code-splitting or prefetch is introduced, make sure it still improves the measured open-to-preview time rather than only moving the work elsewhere

- [ ] **Task 3: Precompute print payload where it actually helps** (AC1, AC3)
  - [ ] Reuse or extend `src/lib/print/invoices.ts` for print-readiness and payload-preparation work
  - [ ] Avoid doing expensive data shaping repeatedly during modal mount if it can be derived earlier from stable invoice data
  - [ ] Keep the optimization localized to the print flow; do not leak preview-only concerns into unrelated invoice screens

- [ ] **Task 4: Add focused validation for large preview fixtures** (AC1, AC3)
  - [ ] Add a component test or fixture-driven render check for a representative large invoice
  - [ ] Add a manual performance validation recipe using realistic invoice data and documented target hardware
  - [ ] Explicitly exclude the native print dialog from the timing contract

## Dev Notes

### Repo Reality

- A real preview modal already exists in `src/components/invoices/print/InvoicePrintPreviewModal.tsx`.
- Shared print helpers already exist in `src/lib/print/invoices.ts`.
- The preview surface is therefore an optimization target, not a greenfield feature.

### Critical Warnings

- Do **not** rebuild print preview from scratch. Optimize the current surface.
- Do **not** fork the renderer. `InvoicePrintSheet` must remain the single source of layout truth.
- The PRD performance budget explicitly excludes the OS print dialog and PDF pipeline startup. Measure only what the product actually controls.
- Story 2.2 remains blocked on the approved stationery reference asset. This story should improve render speed without changing the stationery contract or layout coordinates.

### Implementation Direction

- First measure, then optimize.
- Likely wins are in render-path cleanup and payload preparation, not in inventing a second rendering system.
- If the preview is dynamically imported, prefetch or warm it early enough that the user-perceived open time still improves.

### Validation Follow-up

- The current print-preview path is already real: `InvoicePrintPreviewModal.tsx` renders `InvoicePrintSheet.tsx`, and `window.print()` is invoked separately. Measure from user action to preview-ready state, not to the native print dialog.
- Use explicit `performance.mark()` / `performance.measure()` hooks so the sub-1-second budget has a stable definition before any optimization work starts.
- `InvoicePrintSheet.tsx` already keeps `formatDate()` and `formatAmount()` at module scope, so do not spend this story on that micro-refactor. Focus on render frequency, derived-data churn, and bundle-loading cost instead.
- Keep the shared renderer intact. If you add memoization, code-splitting, or prefetching, prove they improve user-visible preview-open time instead of only moving work elsewhere.

### References

- `_bmad-output/planning-artifacts/epics.md` - Epic 12 / Story 12.5
- `_bmad-output/planning-artifacts/prd.md` - FR46 / print preview and performance NFR
- `src/components/invoices/print/InvoicePrintPreviewModal.tsx` - current preview surface
- `src/components/invoices/print/InvoicePrintSheet.tsx` - shared renderer to preserve
- `src/lib/print/invoices.ts` - current print helper entry points
- `_bmad-output/implementation-artifacts/2-2-print-invoice.md` - existing print-preview story context

## Dev Agent Record

### Agent Model Used

GitHub Copilot (GPT-5.4)

### Completion Notes List

- Story 12.5 was framed as a performance-optimization story because the preview already exists in production code.
- The timing contract explicitly excludes the native print dialog, matching the PRD wording.
- Renderer drift is prevented by keeping the shared print sheet as the single source of truth.