/** Invoice domain types matching backend InvoiceResponse / InvoiceLineResponse. */

export type InvoiceBuyerType = "b2b" | "b2c";
export type InvoiceTaxPolicyCode = "standard" | "zero" | "exempt" | "special";

export interface InvoiceCreateLinePayload {
	product_id?: string | null;
	product_code?: string | null;
	description: string;
	quantity: string;
	unit_price: string;
	tax_policy_code: InvoiceTaxPolicyCode;
}

export interface InvoiceCreatePayload {
	customer_id: string;
	buyer_type: InvoiceBuyerType;
	buyer_identifier?: string | null;
	invoice_date?: string;
	currency_code: string;
	order_id?: string | null;
	lines: InvoiceCreateLinePayload[];
}

export interface InvoiceDraftLine {
	product_code: string;
	description: string;
	quantity: string;
	unit_price: string;
	tax_policy_code: InvoiceTaxPolicyCode;
}

export interface InvoiceTaxPolicyOption {
	code: InvoiceTaxPolicyCode;
	labelKey: string;
	taxType: number;
	taxRate: number;
}

export const INVOICE_TAX_POLICY_OPTIONS: InvoiceTaxPolicyOption[] = [
	{ code: "standard", labelKey: "invoice.taxPolicy.standard", taxType: 1, taxRate: 0.05 },
	{ code: "zero", labelKey: "invoice.taxPolicy.zero", taxType: 2, taxRate: 0 },
	{ code: "exempt", labelKey: "invoice.taxPolicy.exempt", taxType: 3, taxRate: 0 },
	{ code: "special", labelKey: "invoice.taxPolicy.special", taxType: 4, taxRate: 0.1 },
];

export interface SellerInfo {
	name: string;
	address: string;
	phone: string;
	fax: string;
	logoUrl?: string;
}

export interface PrintCustomerInfo {
	company_name: string;
	billing_address: string;
	contact_name: string;
	contact_phone: string;
	shipping_address?: string;
	contact_fax?: string;
}

export interface InvoiceLineResponse {
	id: string;
	product_id: string | null;
	product_code_snapshot: string | null;
	description: string;
	quantity: string;
	unit_price: string;
	subtotal_amount: string;
	tax_type: number;
	tax_rate: string;
	tax_amount: string;
	total_amount: string;
	zero_tax_rate_reason: string | null;
}

export type InvoiceEguiStatus =
	| "PENDING"
	| "QUEUED"
	| "SENT"
	| "ACKED"
	| "FAILED"
	| "RETRYING"
	| "DEAD_LETTER";

export interface InvoiceEguiSubmission {
	status: InvoiceEguiStatus;
	mode: "mock" | "live";
	fia_reference?: string | null;
	retry_count: number;
	deadline_at: string;
	deadline_label: string;
	is_overdue: boolean;
	last_synced_at?: string | null;
	last_error_message?: string | null;
	updated_at: string;
}

export interface InvoiceResponse {
	id: string;
	invoice_number: string;
	invoice_date: string;
	customer_id: string;
	order_id?: string | null;
	buyer_type: string;
	buyer_identifier_snapshot: string;
	currency_code: string;
	subtotal_amount: string;
	tax_amount: string;
	total_amount: string;
	status: string;
	version: number;
	voided_at: string | null;
	void_reason: string | null;
	created_at: string;
	updated_at: string;
	lines: InvoiceLineResponse[];
	// Payment summary fields (computed, optional)
	amount_paid?: string | null;
	outstanding_balance?: string | null;
	payment_status?: string | null;
	due_date?: string | null;
	days_overdue?: number | null;
	egui_submission?: InvoiceEguiSubmission | null;
}

export interface InvoiceListItem {
	id: string;
	invoice_number: string;
	invoice_date: string;
	customer_id: string;
	order_id?: string | null;
	currency_code: string;
	total_amount: string;
	status: string;
	created_at: string;
	amount_paid: string;
	outstanding_balance: string;
	payment_status: string;
	due_date: string | null;
	days_overdue: number;
}

export interface InvoiceListResponse {
	items: InvoiceListItem[];
	total: number;
	page: number;
	page_size: number;
}

export interface CustomerOutstandingSummary {
	total_outstanding: string;
	overdue_count: number;
	overdue_amount: string;
	invoice_count: number;
	currency_code: string;
}
