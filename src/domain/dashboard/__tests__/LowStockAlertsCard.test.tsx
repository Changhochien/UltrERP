import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { LowStockAlertsCard } from "../components/LowStockAlertsCard";

afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
});

const alertsResponse = {
	items: [
		{
			id: "a1",
			product_id: "p1",
			product_name: "Widget A",
			warehouse_id: "w1",
			warehouse_name: "Main",
			current_stock: 5,
			reorder_point: 20,
			status: "pending",
			created_at: "2026-06-01T00:00:00Z",
			acknowledged_at: null,
			acknowledged_by: null,
		},
		{
			id: "a2",
			product_id: "p2",
			product_name: "Widget B",
			warehouse_id: "w1",
			warehouse_name: "Main",
			current_stock: 15,
			reorder_point: 20,
			status: "pending",
			created_at: "2026-06-01T00:00:00Z",
			acknowledged_at: null,
			acknowledged_by: null,
		},
	],
	total: 2,
};

function renderCard() {
	return render(
		<MemoryRouter>
			<LowStockAlertsCard />
		</MemoryRouter>,
	);
}

describe("LowStockAlertsCard", () => {
	it("renders alert list with details", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () => alertsResponse,
		} as Response);

		renderCard();

		await waitFor(() => {
			expect(screen.getByText("Widget A")).toBeTruthy();
		});

		expect(screen.getByText("Widget B")).toBeTruthy();
		expect(screen.getByText(/Stock: 5/)).toBeTruthy();
		expect(screen.getAllByText(/Reorder: 20/)).toHaveLength(2);
	});

	it("shows badge count", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () => alertsResponse,
		} as Response);

		renderCard();

		await waitFor(() => {
			const badge = screen.getByTestId("alert-badge");
			expect(badge.textContent).toBe("2");
		});
	});

	it("shows all-ok when no alerts", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () => ({ items: [], total: 0 }),
		} as Response);

		renderCard();

		await waitFor(() => {
			expect(screen.getByTestId("low-stock-ok")).toBeTruthy();
		});

		expect(screen.getByText(/All stock levels OK/)).toBeTruthy();
	});

	it("shows loading state", () => {
		vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));

		renderCard();

		expect(screen.getByTestId("low-stock-loading")).toBeTruthy();
	});

	it("applies critical class when stock < 50% of reorder point", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () => alertsResponse,
		} as Response);

		renderCard();

		await waitFor(() => {
			expect(screen.getByText("Widget A")).toBeTruthy();
		});

		const list = screen.getByTestId("low-stock-list");
		const items = list.querySelectorAll("li");
		// Widget A: 5 < 20 * 0.5 = 10 → critical
		expect(items[0].className).toContain("alert-item--critical");
		// Widget B: 15 >= 20 * 0.5 = 10 → warning
		expect(items[1].className).toContain("alert-item--warning");
	});

	it("shows error message on fetch failure", async () => {
		vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Network error"));

		renderCard();

		await waitFor(() => {
			expect(screen.getByText(/Network error/)).toBeTruthy();
		});
	});
});
