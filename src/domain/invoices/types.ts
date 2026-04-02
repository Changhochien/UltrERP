/** Invoice domain types matching backend InvoiceResponse / InvoiceLineResponse. */

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

export interface InvoiceResponse {
	id: string;
	tenant_id: string;
	invoice_number: string;
	invoice_date: string;
	customer_id: string;
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
}

/** Seller info injected by tenant config */
export interface SellerInfo {
	name: string;
	address: string;
	phone: string;
	fax: string;
	logoUrl?: string;
}

/** Customer snapshot used in print layout */
export interface PrintCustomerInfo {
	company_name: string;
	billing_address: string;
	contact_name: string;
	contact_phone: string;
	contact_fax?: string;
	shipping_address?: string;
}
