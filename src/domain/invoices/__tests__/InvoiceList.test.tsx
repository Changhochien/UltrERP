import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { InvoiceList } from "../components/InvoiceList";
import { ToastProvider } from "../../../providers/ToastProvider";

afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
});

const invoiceListResponse = {
	items: [
		{
			id: "inv-1",
			invoice_number: "AA00000001",
			invoice_date: "2026-04-01",
			customer_id: "cust-1",
			currency_code: "TWD",
			total_amount: "1000.00",
			status: "issued",
			created_at: "2026-04-01T00:00:00Z",
			amount_paid: "300.00",
			outstanding_balance: "700.00",
			payment_status: "partial",
			due_date: "2026-05-01",
			days_overdue: 0,
		},
		{
			id: "inv-2",
			invoice_number: "AA00000002",
			invoice_date: "2026-02-01",
			customer_id: "cust-2",
			currency_code: "TWD",
			total_amount: "500.00",
			status: "issued",
			created_at: "2026-02-01T00:00:00Z",
			amount_paid: "0",
			outstanding_balance: "500.00",
			payment_status: "overdue",
			due_date: "2026-03-03",
			days_overdue: 30,
		},
	],
	total: 2,
	page: 1,
	page_size: 20,
};

function renderInvoiceList() {
	return render(
		<ToastProvider>
			<MemoryRouter>
				<InvoiceList onSelect={() => {}} />
			</MemoryRouter>
		</ToastProvider>,
	);
}

describe("InvoiceList", () => {
	it("renders payment columns", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () => invoiceListResponse,
		} as Response);

		renderInvoiceList();

		await waitFor(() => {
			expect(screen.getByText("AA00000001")).toBeTruthy();
		});

		// Check column headers exist
		expect(screen.getByText(/Outstanding/)).toBeTruthy();
		// "Paid" header exists (among others like status option)
		const paidElements = screen.getAllByText("Paid");
		expect(paidElements.length).toBeGreaterThanOrEqual(1);

		// Check amounts rendered
		expect(screen.getByText(/300\.00/)).toBeTruthy();
		expect(screen.getByText(/700\.00/)).toBeTruthy();
	});

	it("highlights overdue rows", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () => invoiceListResponse,
		} as Response);

		renderInvoiceList();

		await waitFor(() => {
			expect(screen.getByText("AA00000002")).toBeTruthy();
		});

		// Overdue badge + status label both render
		const overdueSpans = screen.getAllByText("Overdue");
		expect(overdueSpans.length).toBeGreaterThanOrEqual(1);
	});

	it("renders payment status filter", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () => invoiceListResponse,
		} as Response);

		renderInvoiceList();

		await waitFor(() => {
			expect(screen.getByLabelText("Status:")).toBeTruthy();
		});
	});

	it("shows error on fetch failure", async () => {
		vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Network error"));

		renderInvoiceList();

		await waitFor(() => {
			expect(screen.getByRole("alert")).toBeTruthy();
		});
	});
});
