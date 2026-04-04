import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { InvoiceDetail } from "../components/InvoiceDetail";

afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
});

const invoiceResponse = {
	id: "inv-1",
	invoice_number: "AA00000001",
	invoice_date: "2026-04-01",
	customer_id: "cust-1",
	customer_name: "Acme Corp",
	currency_code: "TWD",
	subtotal_amount: "800.00",
	tax_amount: "200.00",
	total_amount: "1000.00",
	status: "issued",
	lines: [],
	amount_paid: "600.00",
	outstanding_balance: "400.00",
	payment_status: "partial",
	due_date: "2026-05-01",
	days_overdue: 0,
};

const paymentHistoryResponse = { items: [], total: 0, page: 1, page_size: 20 };

describe("InvoiceDetail", () => {
	it("renders payment summary section", async () => {
		vi.spyOn(globalThis, "fetch")
			.mockResolvedValueOnce({
				ok: true,
				json: async () => invoiceResponse,
			} as Response)
			.mockResolvedValueOnce({
				ok: true,
				json: async () => paymentHistoryResponse,
			} as Response);

		render(<InvoiceDetail invoiceId="inv-1" onBack={() => {}} />);

		await waitFor(() => {
			expect(screen.getByTestId("payment-summary")).toBeTruthy();
		});

		expect(screen.getByText("Payment Summary")).toBeTruthy();
		expect(screen.getByText(/600\.00/)).toBeTruthy(); // amount paid
		expect(screen.getByText(/400\.00/)).toBeTruthy(); // outstanding
		expect(screen.getByText("Partial")).toBeTruthy(); // status label
	});

	it("shows days overdue when overdue", async () => {
		const overdue = {
			...invoiceResponse,
			payment_status: "overdue",
			days_overdue: 15,
		};

		vi.spyOn(globalThis, "fetch")
			.mockResolvedValueOnce({
				ok: true,
				json: async () => overdue,
			} as Response)
			.mockResolvedValueOnce({
				ok: true,
				json: async () => paymentHistoryResponse,
			} as Response);

		render(<InvoiceDetail invoiceId="inv-1" onBack={() => {}} />);

		await waitFor(() => {
			expect(screen.getByText("15")).toBeTruthy();
		});

		expect(screen.getByText("Days Overdue")).toBeTruthy();
	});

	it("renders error state", async () => {
		vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("fail"));

		render(<InvoiceDetail invoiceId="inv-1" onBack={() => {}} />);

		await waitFor(() => {
			expect(screen.getByText(/Error:/)).toBeTruthy();
		});
	});

	it("surfaces non-404 invoice detail errors from the backend", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
			ok: false,
			status: 503,
			json: async () => ({ detail: "Invoice service unavailable" }),
		} as Response);

		render(<InvoiceDetail invoiceId="inv-1" onBack={() => {}} />);

		await waitFor(() => {
			expect(screen.getByText("Error: Invoice service unavailable")).toBeTruthy();
		});
	});

	it("renders eGUI status and server-derived deadline when available", async () => {
		vi.spyOn(globalThis, "fetch")
			.mockResolvedValueOnce({
				ok: true,
				json: async () => ({
					...invoiceResponse,
					egui_submission: {
						status: "PENDING",
						mode: "mock",
						fia_reference: null,
						retry_count: 0,
						deadline_at: "2026-04-03T12:00:00Z",
						deadline_label: "48-hour submission window",
						is_overdue: false,
						last_synced_at: "2026-04-01T13:00:00Z",
						last_error_message: null,
						updated_at: "2026-04-01T13:00:00Z",
					},
				}),
			} as Response)
			.mockResolvedValueOnce({
				ok: true,
				json: async () => paymentHistoryResponse,
			} as Response);

		render(<InvoiceDetail invoiceId="inv-1" onBack={() => {}} />);

		await waitFor(() => {
			expect(screen.getByTestId("egui-status")).toBeTruthy();
		});

		expect(screen.getByText("eGUI Status")).toBeTruthy();
		expect(screen.getByText("PENDING")).toBeTruthy();
		expect(screen.getByText("48-hour submission window")).toBeTruthy();
	});

	it("refreshes eGUI status without reloading the page", async () => {
		const fetchSpy = vi.spyOn(globalThis, "fetch")
			.mockResolvedValueOnce({
				ok: true,
				json: async () => ({
					...invoiceResponse,
					egui_submission: {
						status: "PENDING",
						mode: "mock",
						fia_reference: null,
						retry_count: 0,
						deadline_at: "2026-04-03T12:00:00Z",
						deadline_label: "48-hour submission window",
						is_overdue: false,
						last_synced_at: "2026-04-01T13:00:00Z",
						last_error_message: null,
						updated_at: "2026-04-01T13:00:00Z",
					},
				}),
			} as Response)
			.mockResolvedValueOnce({
				ok: true,
				json: async () => paymentHistoryResponse,
			} as Response)
			.mockResolvedValueOnce({
				ok: true,
				json: async () => ({
					status: "QUEUED",
					mode: "mock",
					fia_reference: null,
					retry_count: 0,
					deadline_at: "2026-04-03T12:00:00Z",
					deadline_label: "48-hour submission window",
					is_overdue: false,
					last_synced_at: "2026-04-01T14:00:00Z",
					last_error_message: null,
					updated_at: "2026-04-01T14:00:00Z",
				}),
			} as Response);

		render(<InvoiceDetail invoiceId="inv-1" onBack={() => {}} />);

		await waitFor(() => {
			expect(screen.getByText("PENDING")).toBeTruthy();
		});

		fireEvent.click(screen.getByRole("button", { name: "Refresh eGUI status" }));

		await waitFor(() => {
			expect(screen.getByText("QUEUED")).toBeTruthy();
		});

		expect(fetchSpy).toHaveBeenCalledTimes(3);
	});

	it("keeps the invoice detail visible when eGUI refresh fails", async () => {
		vi.spyOn(globalThis, "fetch")
			.mockResolvedValueOnce({
				ok: true,
				json: async () => ({
					...invoiceResponse,
					egui_submission: {
						status: "PENDING",
						mode: "mock",
						fia_reference: null,
						retry_count: 0,
						deadline_at: "2026-04-03T12:00:00Z",
						deadline_label: "48-hour submission window",
						is_overdue: false,
						last_synced_at: "2026-04-01T13:00:00Z",
						last_error_message: null,
						updated_at: "2026-04-01T13:00:00Z",
					},
				}),
			} as Response)
			.mockResolvedValueOnce({
				ok: true,
				json: async () => paymentHistoryResponse,
			} as Response)
			.mockResolvedValueOnce({
				ok: false,
				json: async () => ({ detail: "Live refresh unavailable" }),
			} as Response);

		render(<InvoiceDetail invoiceId="inv-1" onBack={() => {}} />);

		await waitFor(() => {
			expect(screen.getByText("PENDING")).toBeTruthy();
		});

		fireEvent.click(screen.getByRole("button", { name: "Refresh eGUI status" }));

		await waitFor(() => {
			expect(screen.getByTestId("egui-refresh-error")).toBeTruthy();
		});

		expect(screen.getByRole("heading", { name: "Invoice AA00000001" })).toBeTruthy();
		expect(screen.getByText("PENDING")).toBeTruthy();
	});

	it("hides the eGUI surface when tracking is disabled", async () => {
		vi.spyOn(globalThis, "fetch")
			.mockResolvedValueOnce({
				ok: true,
				json: async () => invoiceResponse,
			} as Response)
			.mockResolvedValueOnce({
				ok: true,
				json: async () => paymentHistoryResponse,
			} as Response);

		render(<InvoiceDetail invoiceId="inv-1" onBack={() => {}} />);

		await waitFor(() => {
			expect(screen.getByTestId("payment-summary")).toBeTruthy();
		});

		expect(screen.queryByText("eGUI Status")).toBeNull();
		expect(screen.queryByRole("button", { name: "Refresh eGUI status" })).toBeNull();
	});
});
