# Story 2.6: Export PDF from Shared Invoice Renderer

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a finance clerk,
I want to export an invoice to PDF,
so that I can email it to customers or save for records.

## Acceptance Criteria

1. Given an invoice exists and passes totals validation, when the clerk clicks `Export to PDF`, then the system generates a PDF through the backend-assisted headless-browser path defined in architecture, using the same approved print renderer and stationery layout as Story 2.2.
2. Given the PDF is generated successfully, when export completes, then the PDF is saved or downloaded to the user's device through the supported desktop/web flow.
3. Given the approved stationery reference asset or print contract is incomplete, when export is requested, then the system blocks completion with an explicit configuration error instead of producing an inferred PDF layout.

## Tasks / Subtasks

- [ ] Task 1: Define a single-source invoice rendering path for print and PDF (AC: 1)
  - [ ] Reuse the print renderer and stationery contract from Story 2.2.
  - [ ] Ensure PDF export consumes the same invoice snapshot and totals validation gate as print.
  - [ ] Do not create a second independent invoice layout definition for PDF.
- [ ] Task 2: Implement the PDF export adapter (AC: 1, 2, 3)
  - [ ] Add a PDF export module such as `src/lib/pdf/invoices.ts` plus minimal backend support such as `backend/domains/invoices/pdf.py` or an equivalent internal rendering adapter.
  - [ ] Render the shared invoice HTML/CSS through a backend-assisted headless browser path; do not rely on Tauri-native print-to-PDF or a second jsPDF/canvas layout.
  - [ ] Integrate file-save behavior with the supported platform APIs.
- [ ] Task 3: Add export entry points to the finance UI (AC: 1, 2)
  - [ ] Add an export action on the invoice detail/preview surface.
  - [ ] Block export when totals validation fails and surface the existing discrepancy messaging.
  - [ ] Provide clear success/failure feedback after save completes.
- [ ] Task 4: Add PDF export tests (AC: 1, 2, 3)
  - [ ] Add tests verifying the PDF export path uses the same render contract as print.
  - [ ] Add a smoke/integration test confirming a file artifact is produced and named predictably.
  - [ ] Add a failure-path test confirming export is blocked when the stationery contract remains incomplete.

## Dev Notes

### Story Context

- Story 2.6 depends directly on Story 2.2 for the stationery layout contract and on Story 2.4 for totals validation.
- PDF export is a distribution/output concern; it must not mutate invoice data or bypass immutability rules.
- If Story 2.5 later stores PDF artifacts too, it should archive the output of this story rather than regenerating a second PDF layout.
- Because Tauri does not provide a prescribed native print-to-PDF path for this architecture, PDF export follows the backend-assisted rendering approach documented upstream.

### Dependency Sequencing

- This story stays blocked until Story 2.2 is unblocked and complete.
- Implement Story 2.6 only after Story 2.2 and Story 2.4 so it reuses the approved renderer and shared validation gate.
- Do not let PDF export become a workaround for the blocked print-layout contract.

### Scope Guardrails

- Do not create a second invoice layout implementation just for PDF.
- Do not bypass the print layout specification or totals validation.
- Do not broaden this story into email delivery, attachment workflows, or archival policies.

### Technical Requirements

- PDF generation must reuse the approved print renderer and stylesheet from Story 2.2.
- PDF export should operate on persisted invoice data only.
- Backend-assisted rendering must stay minimal and layout-reuse-driven rather than introducing a second templating system.
- Do not treat Tauri-native print-to-PDF as the primary implementation path for this story.

### Architecture Compliance

- Frontend-driven invoice export logic belongs under `src/lib/pdf/` and `src/components/invoices/`.
- Any backend assistive code must remain inside the existing FastAPI modular-monolith layout and should not introduce a separate rendering service.
- The invoice aggregate remains the source of truth; PDF generation is a representation layer only.

### Testing Requirements

- Verify export is blocked when validation fails.
- Verify generated PDF naming is predictable and tied to invoice identity.
- Verify the render path is shared with print to reduce regression risk.

### Project Structure Notes

- Suggested files:
  - `backend/domains/invoices/pdf.py`
  - `src/lib/pdf/invoices.ts`
  - `src/components/invoices/InvoiceExportButton.tsx`
  - `src/components/invoices/print/InvoicePrintSheet.tsx` (reused)
  - `backend/tests/integration/test_invoice_pdf.py`
  - `src/tests/invoices/export-pdf.test.tsx`

### Risks / Open Questions

- The repo still lacks a committed stationery reference asset, so exact PDF fidelity remains blocked on Story 2.2 completing that contract.
- The platform-level PDF mechanism is now prescribed as a backend-assisted headless-browser path; implementation should not reopen that decision unless architecture changes.

### References

- `_bmad-output/epics.md` — Story 2.6 acceptance criteria.
- `_bmad-output/planning-artifacts/prd.md` — print/file-system integration requirements.
- `docs/superpowers/specs/2026-03-30-erp-architecture-design-v2.md` — approved application stack and invoice-first sequencing.
- `_bmad-output/implementation-artifacts/2-2-print-invoice.md` — print renderer and stationery contract prerequisites.
- `_bmad-output/implementation-artifacts/2-4-invoice-totals-validation.md` — validation gate prerequisite.

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Debug Log References

- `/Users/hcchang/Library/Application Support/Code - Insiders/User/workspaceStorage/4320abfca0ca1465bc6bebe187407283/GitHub.copilot-chat/debug-logs/e9fed657-b634-4e14-91d2-303118396630`

### Completion Notes List

- Story updated to require the backend-assisted shared-renderer PDF path.
- The story remains blocked until Story 2.2 receives the approved stationery reference asset.

### File List

- `backend/domains/invoices/pdf.py`
- `src/lib/pdf/invoices.ts`
- `src/components/invoices/InvoiceExportButton.tsx`
- `backend/tests/integration/test_invoice_pdf.py`
- `src/tests/invoices/export-pdf.test.tsx`
