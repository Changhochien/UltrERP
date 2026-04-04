import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import RecordUnmatchedPayment from "../components/RecordUnmatchedPayment";

const MOCK_CUSTOMERS = {
	items: [
		{ id: "cust-123", company_name: "Test Corp", normalized_business_number: "12345678", contact_phone: "09", status: "active" },
	],
	page: 1,
	page_size: 200,
	total_count: 1,
	total_pages: 1,
};

function mockFetchForCustomers(paymentResponse?: { ok: boolean; json: () => Promise<unknown> }) {
	return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
		const url = typeof input === "string" ? input : (input as Request).url;
		if (url.includes("/api/v1/customers")) {
			return { ok: true, json: async () => MOCK_CUSTOMERS } as Response;
		}
		if (paymentResponse) return paymentResponse as Response;
		return { ok: true, json: async () => ({}) } as Response;
	});
}

afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
});

describe("RecordUnmatchedPayment", () => {
	const noop = () => {};

	beforeEach(() => {
		mockFetchForCustomers();
	});

	it("renders form fields", async () => {
		render(<RecordUnmatchedPayment onSuccess={noop} onCancel={noop} />);
		await waitFor(() => expect(screen.getByLabelText("Customer")).toBeTruthy());
		expect(screen.getByLabelText("Amount")).toBeTruthy();
		expect(screen.getByLabelText("Payment Method")).toBeTruthy();
		expect(screen.getByLabelText("Payment Date")).toBeTruthy();
		expect(screen.getByLabelText("Reference Number")).toBeTruthy();
		expect(screen.getByLabelText("Notes")).toBeTruthy();
	});

	it("disables submit when required fields are empty", () => {
		render(<RecordUnmatchedPayment onSuccess={noop} onCancel={noop} />);
		const submitBtn = screen.getByRole("button", { name: "Record Payment" });
		expect((submitBtn as HTMLButtonElement).disabled).toBe(true);
	});

	it("enables submit when customer and amount provided", async () => {
		render(<RecordUnmatchedPayment onSuccess={noop} onCancel={noop} />);
		await waitFor(() => expect(screen.getByText("Test Corp (12345678)")).toBeTruthy());

		fireEvent.change(screen.getByLabelText("Customer"), { target: { value: "cust-123" } });
		fireEvent.change(screen.getByLabelText("Amount"), { target: { value: "100.00" } });

		const submitBtn = screen.getByRole("button", { name: "Record Payment" });
		expect((submitBtn as HTMLButtonElement).disabled).toBe(false);
	});

	it("submits and calls onSuccess", async () => {
		const onSuccess = vi.fn();
		vi.restoreAllMocks();
		mockFetchForCustomers({
			ok: true,
			json: async () => ({
				id: "pay-1",
				invoice_id: null,
				customer_id: "cust-123",
				payment_ref: "PAY-20260401-0001",
				amount: "100.00",
				payment_method: "BANK_TRANSFER",
				payment_date: "2026-04-01",
				reference_number: null,
				notes: null,
				created_by: "system",
				created_at: "2026-04-01T00:00:00Z",
				updated_at: "2026-04-01T00:00:00Z",
				match_status: "unmatched",
				match_type: null,
				matched_at: null,
				suggested_invoice_id: null,
			}),
		});

		render(<RecordUnmatchedPayment onSuccess={onSuccess} onCancel={noop} />);
		await waitFor(() => expect(screen.getByText("Test Corp (12345678)")).toBeTruthy());

		fireEvent.change(screen.getByLabelText("Customer"), { target: { value: "cust-123" } });
		fireEvent.change(screen.getByLabelText("Amount"), { target: { value: "100.00" } });

		fireEvent.click(screen.getByRole("button", { name: "Record Payment" }));

		await waitFor(() => expect(onSuccess).toHaveBeenCalled());
	});

	it("shows error on failure", async () => {
		vi.restoreAllMocks();
		mockFetchForCustomers({
			ok: false,
			json: async () => ({
				detail: [{ field: "amount", message: "Invalid amount" }],
			}),
		});

		render(<RecordUnmatchedPayment onSuccess={noop} onCancel={noop} />);
		await waitFor(() => expect(screen.getByText("Test Corp (12345678)")).toBeTruthy());

		fireEvent.change(screen.getByLabelText("Customer"), { target: { value: "cust-123" } });
		fireEvent.change(screen.getByLabelText("Amount"), { target: { value: "100.00" } });

		fireEvent.click(screen.getByRole("button", { name: "Record Payment" }));

		await waitFor(() => {
			expect(screen.getByRole("alert")).toBeTruthy();
			expect(screen.getByText("Invalid amount")).toBeTruthy();
		});
	});

	it("calls onCancel when cancel clicked", () => {
		const onCancel = vi.fn();
		render(<RecordUnmatchedPayment onSuccess={noop} onCancel={onCancel} />);
		fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
		expect(onCancel).toHaveBeenCalled();
	});
});
