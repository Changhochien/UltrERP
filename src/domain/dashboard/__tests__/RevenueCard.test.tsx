import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { RevenueCard } from "../components/RevenueCard";
import type { RevenueSummary } from "../types";

afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
});

const mockData: RevenueSummary = {
	today_revenue: "10000.00",
	yesterday_revenue: "8000.00",
	change_percent: "25.0",
	today_date: "2026-06-01",
	yesterday_date: "2026-05-31",
};

describe("RevenueCard", () => {
	it("renders loading skeleton", () => {
		render(<RevenueCard data={null} isLoading={true} error={null} />);
		expect(screen.getByTestId("revenue-card-loading")).toBeTruthy();
		expect(screen.getByText("Revenue Comparison")).toBeTruthy();
	});

	it("renders error state", () => {
		render(<RevenueCard data={null} isLoading={false} error="Network error" />);
		expect(screen.getByTestId("revenue-card-error")).toBeTruthy();
		expect(screen.getByText("Network error")).toBeTruthy();
	});

	it("renders today and yesterday revenue", () => {
		render(<RevenueCard data={mockData} isLoading={false} error={null} />);
		expect(screen.getByText(/NT\$ 10,000\.00/)).toBeTruthy();
		expect(screen.getByText(/NT\$ 8,000\.00/)).toBeTruthy();
	});

	it("shows green indicator for positive change", () => {
		render(<RevenueCard data={mockData} isLoading={false} error={null} />);
		const indicator = screen.getByTestId("change-indicator");
		expect(indicator.textContent).toContain("▲");
		expect(indicator.textContent).toContain("+25.0%");
		expect(indicator.className).toContain("change--positive");
	});

	it("shows red indicator for negative change", () => {
		const negativeData: RevenueSummary = {
			...mockData,
			today_revenue: "3000.00",
			change_percent: "-62.5",
		};
		render(<RevenueCard data={negativeData} isLoading={false} error={null} />);
		const indicator = screen.getByTestId("change-indicator");
		expect(indicator.textContent).toContain("▼");
		expect(indicator.textContent).toContain("-62.5%");
		expect(indicator.className).toContain("change--negative");
	});

	it("shows dash when change_percent is null", () => {
		const zeroData: RevenueSummary = {
			...mockData,
			today_revenue: "0",
			yesterday_revenue: "0",
			change_percent: null,
		};
		render(<RevenueCard data={zeroData} isLoading={false} error={null} />);
		const indicator = screen.getByTestId("change-indicator");
		expect(indicator.textContent).toBe("—");
	});

	it("renders null when no data and not loading", () => {
		const { container } = render(<RevenueCard data={null} isLoading={false} error={null} />);
		expect(container.innerHTML).toBe("");
	});
});
