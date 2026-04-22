import "../../../tests/helpers/i18n";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import RecordUnmatchedPayment from "../components/RecordUnmatchedPayment";
import { ToastProvider } from "../../../providers/ToastProvider";

import type { CustomerSummary } from "../../../domain/customers/types";
import type { Payment } from "../types";

const MOCK_CUSTOMERS: { items: CustomerSummary[]; page: number; page_size: number; total_count: number; total_pages: number } = {
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
		render(
			<ToastProvider>
				<RecordUnmatchedPayment onSuccess={noop} onCancel={noop} />
			</ToastProvider>,
		);
		await waitFor(() => expect(screen.getByLabelText("Customer")).toBeTruthy());
		expect(screen.getByLabelText("Amount")).toBeTruthy();
		expect(screen.getByLabelText("Payment Method")).toBeTruthy();
		expect(screen.getByLabelText("Payment Date")).toBeTruthy();
		expect(screen.getByLabelText("Reference Number")).toBeTruthy();
		expect(screen.getByLabelText("Notes")).toBeTruthy();
	});

	it("shows inline required errors and does not submit when required fields are empty", async () => {
		vi.restoreAllMocks();
		const fetchSpy = mockFetchForCustomers();

		render(
			<ToastProvider>
				<RecordUnmatchedPayment onSuccess={noop} onCancel={noop} />
			</ToastProvider>,
		);
		await waitFor(() => expect(screen.getByText("Test Corp (12345678)")).toBeTruthy());

		fireEvent.click(screen.getByRole("button", { name: "Record Payment" }));

		await waitFor(() => {
			expect(screen.getByText("Customer is required.")).toBeTruthy();
			expect(screen.getByText("Amount is required.")).toBeTruthy();
		});
		expect(fetchSpy).toHaveBeenCalledTimes(1);
	});

	it("clears client errors once customer and amount are provided", async () => {
		render(
			<ToastProvider>
				<RecordUnmatchedPayment onSuccess={noop} onCancel={noop} />
			</ToastProvider>,
		);
		await waitFor(() => expect(screen.getByText("Test Corp (12345678)")).toBeTruthy());

		fireEvent.click(screen.getByRole("button", { name: "Record Payment" }));
		await waitFor(() => {
			expect(screen.getByText("Customer is required.")).toBeTruthy();
			expect(screen.getByText("Amount is required.")).toBeTruthy();
		});

		fireEvent.change(screen.getByLabelText("Customer"), { target: { value: "cust-123" } });
		fireEvent.change(screen.getByLabelText("Amount"), { target: { value: "100.00" } });

		await waitFor(() => {
			expect(screen.queryByText("Customer is required.")).toBeNull();
			expect(screen.queryByText("Amount is required.")).toBeNull();
		});
	});

	it("submits and calls onSuccess", async () => {
		const onSuccess = vi.fn();
		vi.restoreAllMocks();
		mockFetchForCustomers({
			ok: true,
			json: async (): Promise<Payment> => ({
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

		render(
			<ToastProvider>
				<RecordUnmatchedPayment onSuccess={onSuccess} onCancel={noop} />
			</ToastProvider>,
		);
		await waitFor(() => expect(screen.getByText("Test Corp (12345678)")).toBeTruthy());

		fireEvent.change(screen.getByLabelText("Customer"), { target: { value: "cust-123" } });
		fireEvent.change(screen.getByLabelText("Amount"), { target: { value: "100.00" } });

		fireEvent.click(screen.getByRole("button", { name: "Record Payment" }));

		await waitFor(() => expect(onSuccess).toHaveBeenCalled());
		expect(screen.getByText("Unmatched payment recorded")).toBeTruthy();
		expect(screen.getByText("Receipt PAY-20260401-0001 is ready for reconciliation.")).toBeTruthy();
	});

	it("shows error on failure", async () => {
		vi.restoreAllMocks();
		mockFetchForCustomers({
			ok: false,
			json: async () => ({
				detail: [{ field: "amount", message: "Invalid amount" }],
			}),
		});

		render(
			<ToastProvider>
				<RecordUnmatchedPayment onSuccess={noop} onCancel={noop} />
			</ToastProvider>,
		);
		await waitFor(() => expect(screen.getByText("Test Corp (12345678)")).toBeTruthy());

		fireEvent.change(screen.getByLabelText("Customer"), { target: { value: "cust-123" } });
		fireEvent.change(screen.getByLabelText("Amount"), { target: { value: "100.00" } });

		fireEvent.click(screen.getByRole("button", { name: "Record Payment" }));

		await waitFor(() => {
			expect(screen.getByRole("alert")).toBeTruthy();
			expect(screen.getAllByText("Invalid amount").length).toBe(2);
		});
		expect(screen.getByText("Payment could not be recorded")).toBeTruthy();
	});

	it("calls onCancel when cancel clicked", () => {
		const onCancel = vi.fn();
		render(
			<ToastProvider>
				<RecordUnmatchedPayment onSuccess={noop} onCancel={onCancel} />
			</ToastProvider>,
		);
		fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
		expect(onCancel).toHaveBeenCalled();
	});
});
