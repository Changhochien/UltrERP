import "../../../tests/helpers/i18n";

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import RecordPaymentForm from "../components/RecordPaymentForm";
import { ToastProvider } from "../../../providers/ToastProvider";

afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
});

describe("RecordPaymentForm", () => {
	const noop = () => {};

	it("renders with pre-filled amount", () => {
		render(
			<ToastProvider>
				<RecordPaymentForm
					invoiceId="inv-1"
					outstandingBalance={500}
					onSuccess={noop}
					onCancel={noop}
				/>
			</ToastProvider>,
		);
		const input = screen.getByLabelText("Amount") as HTMLInputElement;
		expect(input.value).toBe("500");
	});

	it("shows all payment methods", () => {
		render(
			<ToastProvider>
				<RecordPaymentForm
					invoiceId="inv-1"
					outstandingBalance={500}
					onSuccess={noop}
					onCancel={noop}
				/>
			</ToastProvider>,
		);
		expect(screen.getByText("Cash")).toBeTruthy();
		expect(screen.getByText("Bank Transfer")).toBeTruthy();
		expect(screen.getByText("Check")).toBeTruthy();
		expect(screen.getByText("Credit Card")).toBeTruthy();
		expect(screen.getByText("Other")).toBeTruthy();
	});

	it("disables submit when amount exceeds outstanding", () => {
		render(
			<ToastProvider>
				<RecordPaymentForm
					invoiceId="inv-1"
					outstandingBalance={500}
					onSuccess={noop}
					onCancel={noop}
				/>
			</ToastProvider>,
		);
		const input = screen.getByLabelText("Amount") as HTMLInputElement;
		fireEvent.change(input, { target: { value: "600" } });
		const submitBtn = screen.getByRole("button", { name: "Record Payment" });
		expect((submitBtn as HTMLButtonElement).disabled).toBe(true);
	});

	it("shows warning when amount exceeds outstanding", () => {
		render(
			<ToastProvider>
				<RecordPaymentForm
					invoiceId="inv-1"
					outstandingBalance={500}
					onSuccess={noop}
					onCancel={noop}
				/>
			</ToastProvider>,
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
			<ToastProvider>
				<RecordPaymentForm
					invoiceId="inv-1"
					outstandingBalance={500}
					onSuccess={onSuccess}
					onCancel={noop}
				/>
			</ToastProvider>,
		);

		const submitBtn = screen.getByRole("button", { name: "Record Payment" });
		fireEvent.click(submitBtn);

		await waitFor(() => {
			expect(onSuccess).toHaveBeenCalled();
		});
		expect(screen.getByText("Payment recorded")).toBeTruthy();
		expect(screen.getByText("Receipt PAY-20260401-0001 was recorded for this invoice.")).toBeTruthy();
	});

	it("shows inline and toast feedback when recording fails", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue({
			ok: false,
			json: async () => ({
				detail: [{ field: "amount", message: "Payment exceeds invoice balance." }],
			}),
		} as Response);

		render(
			<ToastProvider>
				<RecordPaymentForm
					invoiceId="inv-1"
					outstandingBalance={500}
					onSuccess={noop}
					onCancel={noop}
				/>
			</ToastProvider>,
		);

		fireEvent.click(screen.getByRole("button", { name: "Record Payment" }));

		await waitFor(() => {
			expect(screen.getByRole("alert")).toBeTruthy();
			expect(screen.getAllByText("Payment exceeds invoice balance.").length).toBe(2);
		});
		expect(screen.getByText("Payment could not be recorded")).toBeTruthy();
	});

	it("calls onCancel when cancel button clicked", () => {
		const onCancel = vi.fn();
		render(
			<ToastProvider>
				<RecordPaymentForm
					invoiceId="inv-1"
					outstandingBalance={500}
					onSuccess={noop}
					onCancel={onCancel}
				/>
			</ToastProvider>,
		);
		fireEvent.click(screen.getByText("Cancel"));
		expect(onCancel).toHaveBeenCalled();
	});
});
