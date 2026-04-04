/** Payments API helpers. */

import { apiFetch } from "../apiFetch";
import type {
	PaymentCreate,
	PaymentCreateUnmatched,
	Payment,
	PaymentListResponse,
	ReconciliationResult,
} from "../../domain/payments/types";

export interface PaymentApiError {
	detail: Array<{ field: string; message: string }> | string;
}

export async function createPayment(
	data: PaymentCreate,
): Promise<
	| { ok: true; data: Payment }
	| { ok: false; errors: Array<{ field: string; message: string }> }
> {
	let resp: Response;
	try {
		resp = await apiFetch("/api/v1/payments", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(data),
		});
	} catch {
		return { ok: false, errors: [{ field: "", message: "Unable to reach the server. Please try again." }] };
	}

	if (resp.ok) {
		const payment: Payment = await resp.json();
		return { ok: true, data: payment };
	}

	const body: PaymentApiError = await resp.json().catch(() => ({ detail: "Unknown error" }));
	if (typeof body.detail === "string") {
		return { ok: false, errors: [{ field: "", message: body.detail }] };
	}
	return { ok: false, errors: body.detail ?? [] };
}

export async function createUnmatchedPayment(
	data: PaymentCreateUnmatched,
): Promise<
	| { ok: true; data: Payment }
	| { ok: false; errors: Array<{ field: string; message: string }> }
> {
	let resp: Response;
	try {
		resp = await apiFetch("/api/v1/payments/unmatched", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(data),
		});
	} catch {
		return { ok: false, errors: [{ field: "", message: "Unable to reach the server. Please try again." }] };
	}

	if (resp.ok) {
		const payment: Payment = await resp.json();
		return { ok: true, data: payment };
	}

	const body: PaymentApiError = await resp.json().catch(() => ({ detail: "Unknown error" }));
	if (typeof body.detail === "string") {
		return { ok: false, errors: [{ field: "", message: body.detail }] };
	}
	return { ok: false, errors: body.detail ?? [] };
}

export async function fetchPayments(params?: {
	invoice_id?: string;
	customer_id?: string;
	page?: number;
	page_size?: number;
}): Promise<PaymentListResponse> {
	const qs = new URLSearchParams();
	if (params?.invoice_id) qs.set("invoice_id", params.invoice_id);
	if (params?.customer_id) qs.set("customer_id", params.customer_id);
	if (params?.page) qs.set("page", String(params.page));
	if (params?.page_size) qs.set("page_size", String(params.page_size));
	const qsStr = qs.toString();
	const url = `/api/v1/payments${qsStr ? `?${qsStr}` : ""}`;
	const resp = await apiFetch(url);
	if (!resp.ok) throw new Error("Failed to fetch payments");
	return resp.json();
}

export async function fetchPaymentsByInvoice(invoiceId: string): Promise<PaymentListResponse> {
	return fetchPayments({ invoice_id: invoiceId });
}

export async function runReconciliation(): Promise<ReconciliationResult> {
	const resp = await apiFetch("/api/v1/payments/reconcile", { method: "POST" });
	if (!resp.ok) throw new Error("Failed to run reconciliation");
	return resp.json();
}

export async function confirmMatch(
	paymentId: string,
): Promise<
	| { ok: true; data: Payment }
	| { ok: false; errors: Array<{ field: string; message: string }> }
> {
	let resp: Response;
	try {
		resp = await apiFetch(`/api/v1/payments/${paymentId}/confirm-match`, { method: "POST" });
	} catch {
		return { ok: false, errors: [{ field: "", message: "Unable to reach the server. Please try again." }] };
	}
	if (resp.ok) {
		const payment: Payment = await resp.json();
		return { ok: true, data: payment };
	}
	const body: PaymentApiError = await resp.json().catch(() => ({ detail: "Unknown error" }));
	if (typeof body.detail === "string") {
		return { ok: false, errors: [{ field: "", message: body.detail }] };
	}
	return { ok: false, errors: body.detail ?? [] };
}

export async function manualMatch(
	paymentId: string,
	invoiceId: string,
): Promise<
	| { ok: true; data: Payment }
	| { ok: false; errors: Array<{ field: string; message: string }> }
> {
	let resp: Response;
	try {
		resp = await apiFetch(`/api/v1/payments/${paymentId}/manual-match`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ invoice_id: invoiceId }),
		});
	} catch {
		return { ok: false, errors: [{ field: "", message: "Unable to reach the server. Please try again." }] };
	}
	if (resp.ok) {
		const payment: Payment = await resp.json();
		return { ok: true, data: payment };
	}
	const body: PaymentApiError = await resp.json().catch(() => ({ detail: "Unknown error" }));
	if (typeof body.detail === "string") {
		return { ok: false, errors: [{ field: "", message: body.detail }] };
	}
	return { ok: false, errors: body.detail ?? [] };
}
