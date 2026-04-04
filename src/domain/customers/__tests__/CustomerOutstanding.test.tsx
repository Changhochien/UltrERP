import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { CustomerOutstanding } from "../components/CustomerOutstanding";

afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
});

const summaryResponse = {
	total_outstanding: "1200.00",
	overdue_count: 1,
	overdue_amount: "500.00",
	invoice_count: 3,
	currency_code: "TWD",
};

describe("CustomerOutstanding", () => {
	it("renders outstanding summary card", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () => summaryResponse,
		} as Response);

		render(<CustomerOutstanding customerId="cust-1" />);

		await waitFor(() => {
			expect(screen.getByTestId("customer-outstanding")).toBeTruthy();
		});

		expect(screen.getByText("Outstanding Balance")).toBeTruthy();
		expect(screen.getByText(/TWD 1200\.00/)).toBeTruthy();
		expect(screen.getByText("3")).toBeTruthy(); // invoice count
	});

	it("shows overdue details when present", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () => summaryResponse,
		} as Response);

		render(<CustomerOutstanding customerId="cust-1" />);

		await waitFor(() => {
			expect(screen.getByText(/Overdue/)).toBeTruthy();
		});

		expect(screen.getByText(/500\.00/)).toBeTruthy();
	});

	it("surfaces backend detail for mixed-currency summaries", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: false,
			json: async () => ({
				detail: "Customer outstanding summary is unavailable for mixed-currency receivables.",
			}),
		} as Response);

		render(<CustomerOutstanding customerId="cust-1" />);

		await waitFor(() => {
			expect(screen.getByText(/mixed-currency receivables/)).toBeTruthy();
		});
	});

	it("renders nothing when no summary", async () => {
		vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("fail"));

		render(<CustomerOutstanding customerId="cust-1" />);

		await waitFor(() => {
			expect(screen.getByText(/Error:/)).toBeTruthy();
		});
	});
});
