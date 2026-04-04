# UltrERP Print Preview Performance

## Scope

Story 12.5 optimizes the invoice print preview open path without forking the renderer. The preview shell is opened from invoice detail, but `src/components/invoices/print/InvoicePrintSheet.tsx` remains the single layout source for preview, print, and downstream PDF reuse.

Instrumentation and preview preparation live in `src/lib/print/invoices.ts`. The invoice-detail open path lives in `src/domain/invoices/components/InvoiceDetail.tsx`. The preview shell itself lives in `src/components/invoices/print/InvoicePrintPreviewModal.tsx`.

## Timing Contract

- Measure only the user-controlled path from preview-button click to preview-ready render.
- Use the `ultrerp:invoice-print-preview-open` User Timing measure emitted by the frontend.
- The `ready` point is the first preview-ready animation frame after the modal mounts.
- Exclude `window.print()`, the native print dialog, and any PDF-export startup work from the budget.

## Large Fixture

- Use a realistic invoice with at least 100 line items.
- Keep the shared renderer path intact: the preview must still render `InvoicePrintSheet.tsx` instead of a preview-only template.
- Verify both first item and last item content are visible so the fixture exercises the full list surface rather than a truncated sample.

## Manual Validation

### Target hardware record

Record the machine used for the measurement run before claiming the budget is met.

- OS:
- CPU:
- RAM:
- Browser or webview build:
- Build mode: `pnpm build` plus deployed preview, or `pnpm dev`

### Preparation

1. Start the frontend with a build representative of the claim being made.
2. Open an invoice detail page for a print-ready invoice with at least 100 line items.
3. Open DevTools and clear existing User Timing entries.
4. Confirm the invoice detail page shows the `Print Preview` action and that no native print dialog is already open.

### Measurement run

1. Click `Print Preview`.
2. Wait until the preview surface is visibly ready for review.
3. In DevTools, inspect `performance.getEntriesByName("ultrerp:invoice-print-preview-open")` or the Performance panel User Timing entries.
4. Record the latest measure duration in milliseconds.
5. Repeat at least 5 times on the same invoice after a full page reload for the first run and warm-cache runs afterward.

### Pass criteria

1. The latest `ultrerp:invoice-print-preview-open` duration is under 1000 ms on the recorded target hardware.
2. The preview opens without visible control jank while mounting.
3. The shared renderer content matches the same field set used by print and PDF pathways.
4. The native print dialog is not included in the recorded duration.

## Notes

- The preview shell is lazy-loaded, but the chunk is prefetched from invoice detail so the user-perceived open path improves rather than just shifting work later.
- Customer print data is prepared before modal mount so preview-open timing is not dominated by avoidable payload shaping during the dialog render.
- If future work changes the open path, keep the same measure name and timing boundary so Story 12.5 comparisons stay meaningful.