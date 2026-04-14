import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { InvoiceDetail } from "../components/InvoiceDetail";
import { INVOICE_PRINT_PREVIEW_OPEN_MEASURE } from "../../../lib/print/invoices";

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
const customerResponse = {
	id: "cust-1",
	tenant_id: "tenant-1",
	company_name: "Acme Corp",
	normalized_business_number: "12345678",
	billing_address: "台北市信義區信義路五段7號",
	contact_name: "王大明",
	contact_phone: "0912-345-678",
	contact_email: "ap@example.com",
	credit_limit: "100000",
	status: "active",
	version: 1,
	created_at: "2026-04-01T00:00:00Z",
	updated_at: "2026-04-01T00:00:00Z",
};

function jsonResponse(body: unknown, status = 200): Response {
	return {
		ok: status >= 200 && status < 300,
		status,
		json: async () => body,
	} as Response;
}

function mockInvoiceDetailRequests(options?: {
	invoice?: Record<string, unknown>;
	refreshBody?: unknown;
	refreshStatus?: number;
	customer?: Record<string, unknown> | null;
	customerFailureCount?: number;
}) {
	let remainingCustomerFailures = options?.customerFailureCount ?? 0;
	const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
		const url = typeof input === "string"
			? input
			: input instanceof URL
				? input.toString()
				: input.url;

		if (url.includes("/api/v1/invoices/inv-1/egui/refresh")) {
			return jsonResponse(
				options?.refreshBody ?? { detail: "Live refresh unavailable" },
				options?.refreshStatus ?? 503,
			);
		}

		if (url.includes("/api/v1/invoices/inv-1")) {
			return jsonResponse(options?.invoice ?? invoiceResponse);
		}

		if (url.includes("/api/v1/payments?invoice_id=inv-1")) {
			return jsonResponse(paymentHistoryResponse);
		}

		if (url.includes("/api/v1/customers/cust-1")) {
			if (remainingCustomerFailures > 0) {
				remainingCustomerFailures -= 1;
				throw new Error("Customer service unavailable");
			}

			if (options?.customer === null) {
				return jsonResponse({ detail: "Customer not found" }, 404);
			}

			return jsonResponse(options?.customer ?? customerResponse);
		}

		throw new Error(`Unexpected fetch URL: ${url}`);
	});

	return fetchSpy;
}

describe("InvoiceDetail", () => {
	it("renders payment summary section", async () => {
		mockInvoiceDetailRequests();

		render(<MemoryRouter><InvoiceDetail invoiceId="inv-1" onBack={() => {}} /></MemoryRouter>);

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

		mockInvoiceDetailRequests({ invoice: overdue });

		render(<MemoryRouter><InvoiceDetail invoiceId="inv-1" onBack={() => {}} /></MemoryRouter>);

		await waitFor(() => {
			expect(screen.getByText("15")).toBeTruthy();
		});

		expect(screen.getByText("Days Overdue")).toBeTruthy();
	});

	it("renders error state", async () => {
		vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("fail"));

		render(<MemoryRouter><InvoiceDetail invoiceId="inv-1" onBack={() => {}} /></MemoryRouter>);

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

		render(<MemoryRouter><InvoiceDetail invoiceId="inv-1" onBack={() => {}} /></MemoryRouter>);

		await waitFor(() => {
			expect(screen.getByText("Error: Invoice service unavailable")).toBeTruthy();
		});
	});

	it("renders eGUI status and server-derived deadline when available", async () => {
		mockInvoiceDetailRequests({
			invoice: {
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
			},
		});

		render(<MemoryRouter><InvoiceDetail invoiceId="inv-1" onBack={() => {}} /></MemoryRouter>);

		await waitFor(() => {
			expect(screen.getByTestId("egui-status")).toBeTruthy();
		});

		expect(screen.getByText("eGUI Status")).toBeTruthy();
		expect(screen.getByText("PENDING")).toBeTruthy();
		expect(screen.getByText("48-hour submission window")).toBeTruthy();
	});

	it("refreshes eGUI status without reloading the page", async () => {
		const fetchSpy = mockInvoiceDetailRequests({
			invoice: {
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
			},
			refreshStatus: 200,
			refreshBody: {
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
			},
		});

		render(<MemoryRouter><InvoiceDetail invoiceId="inv-1" onBack={() => {}} /></MemoryRouter>);

		await waitFor(() => {
			expect(screen.getByText("PENDING")).toBeTruthy();
		});

		fireEvent.click(screen.getByRole("button", { name: "Refresh eGUI status" }));

		await waitFor(() => {
			expect(screen.getByText("QUEUED")).toBeTruthy();
		});

		expect(fetchSpy).toHaveBeenCalledTimes(4);
	});

	it("keeps the invoice detail visible when eGUI refresh fails", async () => {
		mockInvoiceDetailRequests({
			invoice: {
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
			},
		});

		render(<MemoryRouter><InvoiceDetail invoiceId="inv-1" onBack={() => {}} /></MemoryRouter>);

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
		mockInvoiceDetailRequests();

		render(<MemoryRouter><InvoiceDetail invoiceId="inv-1" onBack={() => {}} /></MemoryRouter>);

		await waitFor(() => {
			expect(screen.getByTestId("payment-summary")).toBeTruthy();
		});

		expect(screen.queryByText("eGUI Status")).toBeNull();
		expect(screen.queryByRole("button", { name: "Refresh eGUI status" })).toBeNull();
	});

	it("opens print preview and records a preview-ready measure", async () => {
		const largeInvoice = {
			...invoiceResponse,
			lines: [
				{
					id: "line-1",
					product_id: null,
					product_code_snapshot: "W-001",
					description: "Widget A",
					quantity: "10",
					unit_price: "100",
					subtotal_amount: "1000",
					tax_type: 1,
					tax_rate: "0.05",
					tax_amount: "50",
					total_amount: "1050",
					zero_tax_rate_reason: null,
				},
			],
		};

		mockInvoiceDetailRequests({ invoice: largeInvoice });
		const markSpy = vi.spyOn(window.performance, "mark").mockImplementation(
			() => ({ duration: 0, entryType: "mark", name: "preview", startTime: 0 } as PerformanceMark),
		);
		const measureSpy = vi.spyOn(window.performance, "measure").mockImplementation(
			() => ({ duration: 120 } as PerformanceMeasure),
		);

		render(<MemoryRouter><InvoiceDetail invoiceId="inv-1" onBack={() => {}} /></MemoryRouter>);

		const previewButton = await screen.findByRole("button", { name: "Print Preview" });
		await waitFor(() => {
			expect(previewButton).not.toHaveProperty("disabled", true);
		});

		fireEvent.click(previewButton);

		await waitFor(() => {
			expect(screen.getByRole("dialog", { name: "Invoice print preview" })).toBeTruthy();
		});

		await waitFor(() => {
			expect(measureSpy).toHaveBeenCalledWith(
				INVOICE_PRINT_PREVIEW_OPEN_MEASURE,
				expect.stringContaining(`${INVOICE_PRINT_PREVIEW_OPEN_MEASURE}:start:`),
				expect.stringContaining(`${INVOICE_PRINT_PREVIEW_OPEN_MEASURE}:ready:`),
			);
		});

		expect(markSpy).toHaveBeenCalled();
	});

	it("allows retrying preview preparation after a transient customer preload failure", async () => {
		mockInvoiceDetailRequests({
			invoice: {
				...invoiceResponse,
				lines: [
					{
						id: "line-1",
						product_id: null,
						product_code_snapshot: "W-001",
						description: "Widget A",
						quantity: "10",
						unit_price: "100",
						subtotal_amount: "1000",
						tax_type: 1,
						tax_rate: "0.05",
						tax_amount: "50",
						total_amount: "1050",
						zero_tax_rate_reason: null,
					},
				],
			},
			customerFailureCount: 1,
		});

		render(<MemoryRouter><InvoiceDetail invoiceId="inv-1" onBack={() => {}} /></MemoryRouter>);

		const retryButton = await screen.findByRole("button", { name: "Retry Preview" });
		expect(screen.getByTestId("print-preview-error").textContent).toContain("Unable to prepare print preview.");

		fireEvent.click(retryButton);

		await waitFor(() => {
			expect(screen.getByRole("dialog", { name: "Invoice print preview" })).toBeTruthy();
		});
	});
});
