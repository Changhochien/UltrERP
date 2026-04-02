/**
 * InvoiceExportButton — triggers PDF export via the backend endpoint.
 *
 * Validates print-readiness before calling the API.
 */

import { useState } from "react";
import type { InvoiceResponse } from "../../domain/invoices/types";
import { validatePrintReady } from "../../lib/print/invoices";
import { exportInvoicePdf } from "../../lib/pdf/invoices";

interface InvoiceExportButtonProps {
	invoice: InvoiceResponse;
}

export default function InvoiceExportButton({
	invoice,
}: InvoiceExportButtonProps) {
	const [busy, setBusy] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const validationError = validatePrintReady(invoice);

	async function handleExport() {
		setError(null);
		setBusy(true);
		try {
			const result = await exportInvoicePdf(invoice.id);
			if (!result.ok) {
				setError(result.message);
			}
		} catch {
			setError("PDF export failed — network error.");
		} finally {
			setBusy(false);
		}
	}

	return (
		<div className="invoice-export">
			<button
				type="button"
				onClick={handleExport}
				disabled={busy || validationError !== null}
				title={validationError ?? "Export to PDF"}
			>
				{busy ? "匯出中…" : "Export PDF"}
			</button>
			{error && <span className="invoice-export-error">{error}</span>}
		</div>
	);
}
