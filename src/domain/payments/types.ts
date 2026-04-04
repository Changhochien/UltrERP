/** Payments domain types for API payloads and responses. */

export type PaymentMethod = "CASH" | "BANK_TRANSFER" | "CHECK" | "CREDIT_CARD" | "OTHER";

export interface PaymentCreate {
	invoice_id: string;
	amount: string;
	payment_method: PaymentMethod;
	payment_date?: string;
	reference_number?: string;
	notes?: string;
}

export interface PaymentCreateUnmatched {
	customer_id: string;
	amount: string;
	payment_method: PaymentMethod;
	payment_date?: string;
	reference_number?: string;
	notes?: string;
}

export interface Payment {
	id: string;
	invoice_id: string | null;
	customer_id: string;
	payment_ref: string;
	amount: string;
	payment_method: string;
	payment_date: string;
	reference_number: string | null;
	notes: string | null;
	created_by: string;
	created_at: string;
	updated_at: string;
	match_status: string;
	match_type: string | null;
	matched_at: string | null;
	suggested_invoice_id: string | null;
}

export interface PaymentListItem {
	id: string;
	payment_ref: string;
	amount: string;
	payment_method: string;
	payment_date: string;
	invoice_id: string | null;
	customer_id: string;
	created_by: string;
	created_at: string;
	match_status: string;
	match_type: string | null;
}

export interface PaymentListResponse {
	items: PaymentListItem[];
	total: number;
	page: number;
	page_size: number;
}

export interface ReconciliationResultItem {
	payment_id: string;
	payment_ref: string;
	match_status: string;
	match_type: string | null;
	invoice_number: string | null;
	suggested_invoice_number: string | null;
}

export interface ReconciliationResult {
	matched_count: number;
	suggested_count: number;
	unmatched_count: number;
	details: ReconciliationResultItem[];
}
