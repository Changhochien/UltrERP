# Story 2.2: Preview and Print on Approved Stationery

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a finance clerk,
I want to preview and print invoices to pre-printed stationery,
so that the printed invoice matches our established A4/A5 format exactly.

## Acceptance Criteria

1. Given an existing invoice with persisted totals and line items, when the clerk opens print preview, then the preview renders the invoice using the approved pre-printed stationery layout and shows the exact fields that will be printed.
2. Given the approved stationery layout is loaded, when the print preview opens, then the preview surface renders in under 1 second on target hardware, excluding OS print-dialog startup time.
3. Given the preview matches the approved layout, when the clerk confirms print, then the system prints the invoice correctly against the pre-printed stationery without shifting totals or key identifiers outside the position tolerances defined in `docs/invoices/stationery-spec.md`.
4. Given the stationery contract still has open gaps or the required reference asset is missing, when print preview is opened, then the system does not silently invent a layout and instead blocks completion with an explicit implementation/configuration error.

## Tasks / Subtasks

- [ ] Task 1: Encode the approved stationery layout as a source-controlled contract (AC: 1, 4)
  - [ ] Complete `docs/invoices/stationery-spec.md` with the approved field map, page size, print area, margins, coordinate/spacing notes, and acceptance tolerances derived from the business-approved stationery sample.
  - [ ] Add the required companion reference asset as `docs/invoices/stationery-reference.png` or `docs/invoices/stationery-reference.pdf`.
  - [ ] If the business-approved sample is not yet digitized, stop implementation at this task, keep the story blocked, and surface the missing asset explicitly rather than guessing the layout.
- [ ] Task 2: Build a reusable print renderer from the invoice snapshot contract (AC: 1, 2)
  - [ ] Create `src/components/invoices/print/InvoicePrintSheet.tsx` for the printable markup.
  - [ ] Create `src/components/invoices/print/invoice-print.css` with print-specific styles and page sizing.
  - [ ] Ensure the renderer consumes persisted invoice data from Story 2.1, not editable form state.
- [ ] Task 3: Implement preview and print actions in the finance UI (AC: 1, 2, 3)
  - [ ] Create a preview surface such as `src/components/invoices/print/InvoicePrintPreviewModal.tsx`.
  - [ ] Add a print action helper such as `src/lib/print/invoices.ts` that reuses the same renderer for both preview and print.
  - [ ] Wire preview/print entry points into the invoice detail or invoice confirmation UI without introducing PDF export logic in this story.
- [ ] Task 4: Add performance and regression tests for print layout (AC: 2, 3, 4)
  - [ ] Add frontend tests to verify the preview renders the expected invoice fields and totals.
  - [ ] Add a lightweight performance assertion or profiling harness for preview render time where feasible.
  - [ ] Add a developer-facing checklist for manual alignment verification against the approved stationery sample.

## Dev Notes

### Story Context

- Story 2.2 depends on Story 2.1 producing a stable persisted invoice snapshot.
- Story 2.2 should also consume the shared totals-validation gate from Story 2.4 before allowing preview or print actions.
- Story 2.6 must reuse the same visual layout contract and renderer rather than creating a second invoice rendering path.
- Epic 12.5 reinforces the same preview performance target and should not redefine this story's print renderer.
- `docs/invoices/stationery-spec.md` now exists as the blocker contract, but the approved reference asset is still missing.

### Dependency Sequencing

- This story stays blocked until the approved stationery reference asset is committed.
- Once unblocked, implement Story 2.2 after Story 2.1 and Story 2.4 so the renderer uses persisted invoice snapshots and the shared validation gate.
- Story 2.6 must not proceed ahead of this story.

### Scope Guardrails

- Do not implement PDF export here. That belongs to Story 2.6 and should reuse this story's renderer.
- Do not invent page geometry, field coordinates, or spacing from memory. The approved business stationery sample is the source of truth.
- Do not create a canvas-only or image-only print path that cannot be reused by preview and PDF export.
- Do not broaden this story into invoice creation or invoice editing; it operates on existing invoices only.

### Technical Requirements

- Use a single layout definition for preview and print so print fidelity issues are solved once.
- Prefer semantic HTML plus print CSS over absolute-positioned bitmap screenshots unless the approved stationery sample proves a fully positioned layout is required.
- Keep render inputs immutable and sourced from persisted invoice data, including invoice number, customer identity, line items, subtotal, tax, and grand total.
- If Tauri-specific native printing introduces instability, use the browser/webview print path first and keep the abstraction localized in `src/lib/print/`.

### Architecture Compliance

- Frontend work stays under `src/components/invoices/`, `src/pages/invoices/`, and `src/lib/print/`.
- No backend API redesign is needed if the existing invoice detail/read model already exposes required print data; add only the minimum read contract extension needed.
- Keep all routes versioned and consistent with the Epic 1 frontend/backend structure.

### Performance and UX Requirements

- Preview surface must render in under 1 second on target hardware, excluding OS print-dialog and PDF-pipeline startup.
- The preview should make layout drift obvious before paper is wasted; the clerk must be able to visually confirm field placement before printing.
- Manual verification must use the position tolerances documented in `docs/invoices/stationery-spec.md`.
- If the layout asset is unavailable, fail loudly in development and testing rather than rendering an approximate output.

### Testing Requirements

- Add component tests for preview rendering using representative invoice data.
- Add a manual verification checklist comparing output with the approved physical or PDF sample.
- If automated visual regression tooling exists later, this story should be ready to adopt it by having a stable print component and reference asset.

### Project Structure Notes

- Suggested files:
  - `docs/invoices/stationery-spec.md`
  - `src/components/invoices/print/InvoicePrintSheet.tsx`
  - `src/components/invoices/print/InvoicePrintPreviewModal.tsx`
  - `src/components/invoices/print/invoice-print.css`
  - `src/lib/print/invoices.ts`
- Reuse invoice domain types from `src/domain/invoices/types.ts` introduced in Story 2.1.

### Risks / Open Questions

- The repository now contains `docs/invoices/stationery-spec.md`, but the approved reference asset is still missing. That remains the main blocker for true pixel-accurate implementation.
- A4/A5 is called out in product artifacts, but exact dimensions, margins, and field anchors are not yet encoded in the repo.
- Story 2.6 must be forced to reuse this story's renderer to avoid layout drift between print and PDF.

### References

- `_bmad-output/epics.md` — Story 2.2 acceptance criteria and related print/PDF stories.
- `_bmad-output/planning-artifacts/prd.md` — Journey 2, print fidelity, and A4/A5 workflow notes.
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md` — approved stack and invoice-first build order.
- `research/ui-ux/02-wireframes/02-invoice-creation.md` — invoice entry context; note that it does not yet solve print layout.

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `/Users/hcchang/Library/Application Support/Code - Insiders/User/workspaceStorage/4320abfca0ca1465bc6bebe187407283/GitHub.copilot-chat/debug-logs/e9fed657-b634-4e14-91d2-303118396630`

### Completion Notes List

- Story updated to use the new stationery contract but remains blocked pending the approved reference asset.
- Preview and print are intentionally constrained to one reusable rendering path.
- PDF generation is deferred to Story 2.6 but must reuse this story's layout contract.

### File List

- `docs/invoices/stationery-spec.md`
- `docs/invoices/stationery-reference.png` or `docs/invoices/stationery-reference.pdf`
- `src/components/invoices/print/InvoicePrintSheet.tsx`
- `src/components/invoices/print/InvoicePrintPreviewModal.tsx`
- `src/components/invoices/print/invoice-print.css`
- `src/lib/print/invoices.ts`
