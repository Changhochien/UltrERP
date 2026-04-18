import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import CreateInvoicePage from "../../../pages/invoices/CreateInvoicePage";

afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
	localStorage.clear();
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
	vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
		const url = typeof input === "string" ? input : input.toString();
		if (url.includes("/api/v1/customers")) {
			return {
				ok: true,
				json: async () => customersResponse,
			} as Response;
		}
		if (url === "/api/v1/invoices") {
			createPayload = JSON.parse(String(init?.body));
			return {
				ok: true,
				json: async () => ({
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
				}),
			} as Response;
		}
		throw new Error(`Unexpected fetch: ${url}`);
	});
	return () => createPayload;
}

describe("CreateInvoicePage", () => {
	it("renders preview totals as line values change", async () => {
		vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
			const url = typeof input === "string" ? input : input.toString();
			if (url.includes("/api/v1/customers")) {
				return {
					ok: true,
					json: async () => customersResponse,
				} as Response;
			}
			throw new Error(`Unexpected fetch: ${url}`);
		});

		render(<MemoryRouter><CreateInvoicePage /></MemoryRouter>);

		await waitFor(() => {
			expect(screen.getByText("Acme Corp (12345678)")).toBeTruthy();
		});

		fireEvent.change(screen.getByLabelText("Description"), {
			target: { value: "Invoice line" },
		});
		fireEvent.change(screen.getByLabelText("Quantity"), {
			target: { value: "2" },
		});
		fireEvent.change(screen.getByLabelText("Unit Price"), {
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

		await waitFor(() => {
			expect(screen.getByText("Acme Corp (12345678)")).toBeTruthy();
		});

		fireEvent.change(screen.getByLabelText("Customer"), {
			target: { value: "cust-1" },
		});
		fireEvent.change(screen.getByLabelText("Description"), {
			target: { value: "Invoice line" },
		});
		fireEvent.change(screen.getByLabelText("Quantity"), {
			target: { value: "2" },
		});
		fireEvent.change(screen.getByLabelText("Unit Price"), {
			target: { value: "100" },
		});

		fireEvent.click(screen.getByRole("button", { name: "Create Invoice" }));

		await waitFor(() => {
			expect(screen.getByText("Invoice Created")).toBeTruthy();
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
				product_code: null,
				description: "Invoice line",
				quantity: "2",
				unit_price: "100",
				tax_policy_code: "standard",
			},
		]);
	});
});