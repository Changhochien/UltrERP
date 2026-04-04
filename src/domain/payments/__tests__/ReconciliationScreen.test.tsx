import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import ReconciliationScreen from "../components/ReconciliationScreen";

afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
});

const reconcileResult = {
	matched_count: 1,
	suggested_count: 1,
	unmatched_count: 1,
	details: [
		{ payment_id: "pid-1", payment_ref: "PAY-20260401-0001", match_status: "matched", match_type: "exact_amount", invoice_number: "INV-001", suggested_invoice_number: null },
		{ payment_id: "pid-2", payment_ref: "PAY-20260401-0002", match_status: "suggested", match_type: "date_proximity", invoice_number: null, suggested_invoice_number: "INV-002" },
		{ payment_id: "pid-3", payment_ref: "PAY-20260401-0003", match_status: "unmatched", match_type: null, invoice_number: null, suggested_invoice_number: null },
	],
};

describe("ReconciliationScreen", () => {
	it("renders run button", () => {
		render(<ReconciliationScreen />);
		expect(screen.getByRole("button", { name: "Run Reconciliation" })).toBeTruthy();
	});

	it("runs reconciliation and shows results", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () => reconcileResult,
		} as Response);

		render(<ReconciliationScreen />);
		fireEvent.click(screen.getByRole("button", { name: "Run Reconciliation" }));

		await waitFor(() => {
			expect(screen.getByText("Matched: 1 | Suggested: 1 | Unmatched: 1")).toBeTruthy();
		});

		// Auto-matched section
		expect(screen.getByText("Auto-Matched")).toBeTruthy();
		expect(screen.getByText("PAY-20260401-0001")).toBeTruthy();
		expect(screen.getByText("INV-001")).toBeTruthy();

		// Suggested section
		expect(screen.getByText("Suggested Matches")).toBeTruthy();
		expect(screen.getByText("PAY-20260401-0002")).toBeTruthy();
		expect(screen.getByText("INV-002")).toBeTruthy();
		expect(screen.getByRole("button", { name: "Confirm" })).toBeTruthy();

		// Unmatched section
		expect(screen.getByText("Unmatched Payments")).toBeTruthy();
		expect(screen.getByText("PAY-20260401-0003")).toBeTruthy();
	});

	it("shows error on reconciliation failure", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: false,
			json: async () => ({ detail: "Server error" }),
		} as Response);

		render(<ReconciliationScreen />);
		fireEvent.click(screen.getByRole("button", { name: "Run Reconciliation" }));

		await waitFor(() => {
			expect(screen.getByText(/Error:/)).toBeTruthy();
		});
	});

	it("renders empty state before running", () => {
		render(<ReconciliationScreen />);
		expect(screen.queryByText("Auto-Matched")).toBeNull();
		expect(screen.queryByText("Suggested Matches")).toBeNull();
		expect(screen.queryByText("Unmatched Payments")).toBeNull();
	});
});
