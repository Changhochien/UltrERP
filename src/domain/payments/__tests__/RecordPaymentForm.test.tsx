import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import RecordPaymentForm from "../components/RecordPaymentForm";

afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
});

describe("RecordPaymentForm", () => {
	const noop = () => {};

	it("renders with pre-filled amount", () => {
		render(
			<RecordPaymentForm
				invoiceId="inv-1"
				outstandingBalance={500}
				onSuccess={noop}
				onCancel={noop}
			/>,
		);
		const input = screen.getByLabelText("Amount") as HTMLInputElement;
		expect(input.value).toBe("500");
	});

	it("shows all payment methods", () => {
		render(
			<RecordPaymentForm
				invoiceId="inv-1"
				outstandingBalance={500}
				onSuccess={noop}
				onCancel={noop}
			/>,
		);
		expect(screen.getByText("Cash")).toBeTruthy();
		expect(screen.getByText("Bank Transfer")).toBeTruthy();
		expect(screen.getByText("Check")).toBeTruthy();
		expect(screen.getByText("Credit Card")).toBeTruthy();
		expect(screen.getByText("Other")).toBeTruthy();
	});

	it("disables submit when amount exceeds outstanding", () => {
		render(
			<RecordPaymentForm
				invoiceId="inv-1"
				outstandingBalance={500}
				onSuccess={noop}
				onCancel={noop}
			/>,
		);
		const input = screen.getByLabelText("Amount") as HTMLInputElement;
		fireEvent.change(input, { target: { value: "600" } });
		const submitBtn = screen.getByRole("button", { name: "Record Payment" });
		expect((submitBtn as HTMLButtonElement).disabled).toBe(true);
	});

	it("shows warning when amount exceeds outstanding", () => {
		render(
			<RecordPaymentForm
				invoiceId="inv-1"
				outstandingBalance={500}
				onSuccess={noop}
				onCancel={noop}
			/>,
		);
		const input = screen.getByLabelText("Amount") as HTMLInputElement;
		fireEvent.change(input, { target: { value: "600" } });
		expect(screen.getByText(/exceeds outstanding balance/i)).toBeTruthy();
	});

	it("submits and calls onSuccess", async () => {
		const onSuccess = vi.fn();
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: true,
			json: async () => ({
				id: "pay-1",
				invoice_id: "inv-1",
				customer_id: "c1",
				payment_ref: "PAY-20260401-0001",
				amount: "500.00",
				payment_method: "BANK_TRANSFER",
				payment_date: "2026-04-01",
				reference_number: null,
				notes: null,
				created_by: "system",
				created_at: "2026-04-01T00:00:00Z",
				updated_at: "2026-04-01T00:00:00Z",
			}),
		} as Response);

		render(
			<RecordPaymentForm
				invoiceId="inv-1"
				outstandingBalance={500}
				onSuccess={onSuccess}
				onCancel={noop}
			/>,
		);

		const submitBtn = screen.getByRole("button", { name: "Record Payment" });
		fireEvent.click(submitBtn);

		await waitFor(() => {
			expect(onSuccess).toHaveBeenCalled();
		});
	});

	it("calls onCancel when cancel button clicked", () => {
		const onCancel = vi.fn();
		render(
			<RecordPaymentForm
				invoiceId="inv-1"
				outstandingBalance={500}
				onSuccess={noop}
				onCancel={onCancel}
			/>,
		);
		fireEvent.click(screen.getByText("Cancel"));
		expect(onCancel).toHaveBeenCalled();
	});
});
