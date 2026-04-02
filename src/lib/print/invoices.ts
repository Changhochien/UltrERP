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

/** Default seller info — will be replaced by tenant config */
export const DEFAULT_SELLER: SellerInfo = {
	name: "UltrERP",
	address: "",
	phone: "",
	fax: "",
};

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
