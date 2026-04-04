/**
 * Invoice print helper — reusable entry point for preview and print actions.
 *
 * Uses the same InvoicePrintSheet renderer for both paths so layout
 * drift between preview and paper cannot occur.
 */

import type {
	InvoiceResponse,
	PrintCustomerInfo,
	SellerInfo,
} from "../../domain/invoices/types";
import type { CustomerResponse } from "../../domain/customers/types";

type InvoicePrintPreviewModalModule = typeof import("../../components/invoices/print/InvoicePrintPreviewModal");

let invoicePrintPreviewModalPromise: Promise<InvoicePrintPreviewModalModule> | null = null;

export const INVOICE_PRINT_PREVIEW_OPEN_MEASURE = "ultrerp:invoice-print-preview-open";

export interface InvoicePrintPreviewContext {
	customer: PrintCustomerInfo;
	seller: SellerInfo;
}

export interface InvoicePrintPreviewMeasurement {
	measureName: string;
	startMarkName: string;
	readyMarkName: string;
}

/** Default seller info — will be replaced by tenant config */
export const DEFAULT_SELLER: SellerInfo = {
	name: "UltrERP",
	address: "",
	phone: "",
	fax: "",
};

function supportsUserTiming(): boolean {
	return typeof performance !== "undefined"
		&& typeof performance.mark === "function"
		&& typeof performance.measure === "function";
}

export function loadInvoicePrintPreviewModal(): Promise<InvoicePrintPreviewModalModule> {
	invoicePrintPreviewModalPromise ??= import("../../components/invoices/print/InvoicePrintPreviewModal")
		.catch((error) => {
			invoicePrintPreviewModalPromise = null;
			throw error;
		});
	return invoicePrintPreviewModalPromise;
}

export function prefetchInvoicePrintPreviewModal(): void {
	void loadInvoicePrintPreviewModal();
}

/**
 * Build PrintCustomerInfo from whatever customer fields are available.
 * In a full implementation this fetches from the customer API; for now
 * it takes inline data.
 */
export function buildPrintCustomer(data: {
	company_name: string;
	billing_address: string;
	contact_name: string;
	contact_phone: string;
	contact_fax?: string;
	shipping_address?: string;
}): PrintCustomerInfo {
	return {
		company_name: data.company_name,
		billing_address: data.billing_address,
		contact_name: data.contact_name,
		contact_phone: data.contact_phone,
		contact_fax: data.contact_fax,
		shipping_address: data.shipping_address,
	};
}

export function buildInvoicePrintPreviewContext(
	customer: Pick<
		CustomerResponse,
		"company_name" | "billing_address" | "contact_name" | "contact_phone"
	>,
	seller: SellerInfo = DEFAULT_SELLER,
): InvoicePrintPreviewContext {
	return {
		customer: buildPrintCustomer(customer),
		seller,
	};
}

/**
 * Measure only the user-controlled preview-open path: click to first preview-ready frame.
 * This intentionally excludes `window.print()` and any native print-dialog startup cost.
 */
export function startInvoicePrintPreviewMeasurement(input: {
	invoiceId: string;
	lineCount: number;
}): InvoicePrintPreviewMeasurement | null {
	if (!supportsUserTiming()) {
		return null;
	}

	const token = `${input.invoiceId}:${input.lineCount}:${performance.now().toFixed(3)}`;
	const startMarkName = `${INVOICE_PRINT_PREVIEW_OPEN_MEASURE}:start:${token}`;
	const readyMarkName = `${INVOICE_PRINT_PREVIEW_OPEN_MEASURE}:ready:${token}`;

	performance.clearMeasures(INVOICE_PRINT_PREVIEW_OPEN_MEASURE);
	performance.mark(startMarkName);

	return {
		measureName: INVOICE_PRINT_PREVIEW_OPEN_MEASURE,
		startMarkName,
		readyMarkName,
	};
}

export function clearInvoicePrintPreviewMeasurement(
	measurement: InvoicePrintPreviewMeasurement | null,
): void {
	if (!measurement || !supportsUserTiming()) {
		return;
	}

	performance.clearMarks(measurement.startMarkName);
	performance.clearMarks(measurement.readyMarkName);
}

export function finishInvoicePrintPreviewMeasurement(
	measurement: InvoicePrintPreviewMeasurement | null,
): number | null {
	if (!measurement || !supportsUserTiming()) {
		return null;
	}

	performance.mark(measurement.readyMarkName);
	const previewMeasure = performance.measure(
		measurement.measureName,
		measurement.startMarkName,
		measurement.readyMarkName,
	);
	performance.clearMarks(measurement.startMarkName);
	performance.clearMarks(measurement.readyMarkName);
	return previewMeasure.duration;
}

/**
 * Validate that an invoice has the minimum data needed for print.
 * Returns an error string, or null if valid.
 */
export function validatePrintReady(invoice: InvoiceResponse): string | null {
	if (invoice.status === "voided") {
		return "Cannot print a voided invoice.";
	}
	if (!invoice.lines || invoice.lines.length === 0) {
		return "Invoice has no line items.";
	}
	if (!invoice.invoice_number) {
		return "Invoice number is missing.";
	}
	return null;
}
