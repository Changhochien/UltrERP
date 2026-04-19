import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import CreateInvoicePage from "../../../pages/invoices/CreateInvoicePage";

const mocks = vi.hoisted(() => ({
	listCustomers: vi.fn(),
	createInvoice: vi.fn(),
}));

vi.mock("../../../lib/api/customers", () => ({
	listCustomers: (...args: unknown[]) => mocks.listCustomers(...args),
}));

vi.mock("../../../lib/api/invoices", () => ({
	createInvoice: (...args: unknown[]) => mocks.createInvoice(...args),
}));

afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
	localStorage.clear();
	mocks.listCustomers.mockReset();
	mocks.createInvoice.mockReset();
});

const customersResponse = {
	items: [
		{
			id: "cust-1",
			company_name: "Acme Corp",
			normalized_business_number: "12345678",
			contact_phone: "02-12345678",
			status: "active",
		},
	],
	page: 1,
	page_size: 200,
	total_count: 1,
	total_pages: 1,
};

function mockInvoiceCreateFlow() {
	let createPayload: Record<string, unknown> | null = null;
	mocks.listCustomers.mockResolvedValue(customersResponse);
	mocks.createInvoice.mockImplementation(async (payload: Record<string, unknown>) => {
		createPayload = payload;
		return {
			ok: true,
			data: {
				id: "inv-1",
				invoice_number: "AA00000001",
				invoice_date: "2026-04-03",
				customer_id: "cust-1",
				buyer_type: "b2b",
				buyer_identifier_snapshot: "12345678",
				currency_code: "TWD",
				subtotal_amount: "200.00",
				tax_amount: "10.00",
				total_amount: "210.00",
				status: "issued",
				version: 1,
				voided_at: null,
				void_reason: null,
				created_at: "2026-04-03T00:00:00Z",
				updated_at: "2026-04-03T00:00:00Z",
				lines: [],
			},
		};
	});
	return () => createPayload;
}

async function selectCustomer() {
	const customerCombobox = screen.getAllByRole("combobox")[0];
	fireEvent.click(customerCombobox);

	await waitFor(() => {
		expect(screen.getByText("Acme Corp")).toBeTruthy();
	});

	fireEvent.click(screen.getByText("Acme Corp"));

	await waitFor(() => {
		expect(
			screen.getAllByRole("combobox")[0].textContent,
		).toContain("Acme Corp (12345678)");
	});
}

describe("CreateInvoicePage", () => {
	it("renders preview totals as line values change", async () => {
		mocks.listCustomers.mockResolvedValue(customersResponse);

		render(<MemoryRouter><CreateInvoicePage /></MemoryRouter>);

		await selectCustomer();

		fireEvent.change(screen.getByLabelText(/Description/i), {
			target: { value: "Invoice line" },
		});
		fireEvent.change(screen.getByLabelText(/Quantity/i), {
			target: { value: "2" },
		});
		fireEvent.change(screen.getByLabelText(/Unit Price/i), {
			target: { value: "100" },
		});

		await waitFor(() => {
			const totalsCard = screen.getByTestId("invoice-totals-card");
			expect(within(totalsCard).getByText(/TWD 210\.00/)).toBeTruthy();
		});
	});

	it("submits the create-invoice payload and shows the created state", async () => {
		const readPayload = mockInvoiceCreateFlow();

		render(<MemoryRouter><CreateInvoicePage /></MemoryRouter>);

		await selectCustomer();

		fireEvent.change(screen.getByLabelText(/Description/i), {
			target: { value: "Invoice line" },
		});
		fireEvent.change(screen.getByLabelText(/Quantity/i), {
			target: { value: "2" },
		});
		fireEvent.change(screen.getByLabelText(/Unit Price/i), {
			target: { value: "100" },
		});

		fireEvent.click(screen.getByRole("button", { name: "Create Invoice" }));

		await waitFor(() => {
			expect(screen.getByRole("heading", { level: 1, name: "Invoice Created" })).toBeTruthy();
		});

		const payload = readPayload();
		expect(payload).toMatchObject({
			customer_id: "cust-1",
			buyer_type: "b2b",
			buyer_identifier: "12345678",
			currency_code: "TWD",
		});
		expect(payload?.lines).toEqual([
			{
				product_id: null,
				product_code: null,
				description: "Invoice line",
				quantity: "2",
				unit_price: "100",
				tax_policy_code: "standard",
			},
		]);
	});
});
