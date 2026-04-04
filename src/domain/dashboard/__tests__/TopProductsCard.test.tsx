import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { TopProductsCard } from "../components/TopProductsCard";

afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
});

const topProductsResponse = {
	period: "day",
	start_date: "2026-06-01",
	end_date: "2026-06-01",
	items: [
		{ product_id: "p1", product_name: "Widget A", quantity_sold: "100", revenue: "50000.00" },
		{ product_id: "p2", product_name: "Widget B", quantity_sold: "80", revenue: "40000.00" },
		{ product_id: "p3", product_name: "Widget C", quantity_sold: "50", revenue: "25000.00" },
	],
};

describe("TopProductsCard", () => {
	it("renders product list", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () => topProductsResponse,
		} as Response);

		render(<TopProductsCard />);

		await waitFor(() => {
			expect(screen.getByText("Widget A")).toBeTruthy();
		});

		expect(screen.getByText("Widget B")).toBeTruthy();
		expect(screen.getByText("Widget C")).toBeTruthy();
		expect(screen.getByText(/50,000\.00/)).toBeTruthy();
	});

	it("renders empty state when no data", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () => ({ ...topProductsResponse, items: [] }),
		} as Response);

		render(<TopProductsCard />);

		await waitFor(() => {
			expect(screen.getByTestId("top-products-empty")).toBeTruthy();
		});

		expect(screen.getByText("No sales data for this period")).toBeTruthy();
	});

	it("toggles between day and week", async () => {
		const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () => topProductsResponse,
		} as Response);

		render(<TopProductsCard />);

		await waitFor(() => {
			expect(screen.getByText("Widget A")).toBeTruthy();
		});

		// Click "This Week" toggle
		fireEvent.click(screen.getByText("This Week"));

		await waitFor(() => {
			// second fetch call should include period=week
			const calls = fetchSpy.mock.calls;
			const lastUrl = calls[calls.length - 1][0] as string;
			expect(lastUrl).toContain("period=week");
		});
	});

	it("shows loading state", () => {
		vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));

		render(<TopProductsCard />);

		expect(screen.getByTestId("top-products-loading")).toBeTruthy();
	});
});
