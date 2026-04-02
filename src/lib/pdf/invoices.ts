/**
 * Invoice PDF export — calls the backend endpoint and triggers download.
 *
 * The backend generates the PDF using the same HTML/CSS layout as
 * InvoicePrintSheet.tsx, ensuring consistent output between print and PDF.
 */

const API_BASE = "/api/v1/invoices";

export interface PdfExportResult {
	ok: true;
	filename: string;
}

export interface PdfExportError {
	ok: false;
	status: number;
	message: string;
}

/**
 * Request a PDF from the backend and trigger a browser download.
 */
export async function exportInvoicePdf(
	invoiceId: string,
): Promise<PdfExportResult | PdfExportError> {
	const res = await fetch(`${API_BASE}/${invoiceId}/pdf`);

	if (!res.ok) {
		const body = await res.json().catch(() => ({ detail: "PDF export failed" }));
		return {
			ok: false,
			status: res.status,
			message: body.detail ?? body.errors?.[0]?.message ?? "PDF export failed",
		};
	}

	// Extract filename from Content-Disposition header
	const disposition = res.headers.get("Content-Disposition") ?? "";
	const match = disposition.match(/filename="?([^"]+)"?/);
	const filename = match?.[1] ?? `invoice-${invoiceId}.pdf`;

	// Trigger browser download
	const blob = await res.blob();
	const url = URL.createObjectURL(blob);
	const a = document.createElement("a");
	a.href = url;
	a.download = filename;
	document.body.appendChild(a);
	a.click();
	document.body.removeChild(a);
	URL.revokeObjectURL(url);

	return { ok: true, filename };
}
