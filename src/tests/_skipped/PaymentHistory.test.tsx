import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import PaymentHistory from "../components/PaymentHistory";

afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
});

describe("PaymentHistory", () => {
	it("shows loading state", () => {
		vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
		render(<PaymentHistory invoiceId="inv-1" />);
		expect(screen.getByText(/Loading payments/)).toBeTruthy();
	});

	it("shows no payments message when empty", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () => ({
				items: [],
				total: 0,
				page: 1,
				page_size: 20,
			}),
		} as Response);

		render(<PaymentHistory invoiceId="inv-1" />);
		await waitFor(() => {
			expect(screen.getByText("No payments recorded.")).toBeTruthy();
		});
	});

	it("displays payment list", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () => ({
				items: [
					{
						id: "p1",
						payment_ref: "PAY-20260401-0001",
						amount: "500.00",
						payment_method: "BANK_TRANSFER",
						payment_date: "2026-04-01",
						invoice_id: "inv-1",
						customer_id: "c1",
						created_by: "system",
						created_at: "2026-04-01T00:00:00Z",
					},
				],
				total: 1,
				page: 1,
				page_size: 20,
			}),
		} as Response);

		render(<PaymentHistory invoiceId="inv-1" />);
		await waitFor(() => {
			expect(screen.getByText("PAY-20260401-0001")).toBeTruthy();
			expect(screen.getByText("500.00")).toBeTruthy();
			expect(screen.getByText("BANK_TRANSFER")).toBeTruthy();
		});
	});

	it("shows error on fetch failure", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: false,
			status: 500,
		} as Response);

		render(<PaymentHistory invoiceId="inv-1" />);
		await waitFor(() => {
			expect(screen.getByText(/Error:/)).toBeTruthy();
		});
	});
});
