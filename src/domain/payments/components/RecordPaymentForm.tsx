/** Form for recording a payment against an invoice. */

import { useState } from "react";

import { SurfaceMessage } from "../../../components/layout/PageLayout";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import type { PaymentMethod } from "../types";
import { useCreatePayment } from "../hooks/usePayments";

const PAYMENT_METHODS: { value: PaymentMethod; label: string }[] = [
	{ value: "CASH", label: "Cash" },
	{ value: "BANK_TRANSFER", label: "Bank Transfer" },
	{ value: "CHECK", label: "Check" },
	{ value: "CREDIT_CARD", label: "Credit Card" },
	{ value: "OTHER", label: "Other" },
];

interface RecordPaymentFormProps {
	invoiceId: string;
	outstandingBalance: number;
	onSuccess: () => void;
	onCancel: () => void;
}

export default function RecordPaymentForm({
	invoiceId,
	outstandingBalance,
	onSuccess,
	onCancel,
}: RecordPaymentFormProps) {
	const [amount, setAmount] = useState(String(outstandingBalance));
	const [method, setMethod] = useState<PaymentMethod>("BANK_TRANSFER");
	const [paymentDate, setPaymentDate] = useState(
		new Date().toISOString().slice(0, 10),
	);
	const [referenceNumber, setReferenceNumber] = useState("");
	const [notes, setNotes] = useState("");
	const [formError, setFormError] = useState<string | null>(null);

	const { mutate, isLoading } = useCreatePayment();

	const parsedAmount = parseFloat(amount);
	const isValid =
		!isNaN(parsedAmount) &&
		parsedAmount > 0 &&
		parsedAmount <= outstandingBalance &&
		paymentDate.length > 0;

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		if (isLoading || !isValid) return;
		setFormError(null);

		const result = await mutate({
			invoice_id: invoiceId,
			amount: amount,
			payment_method: method,
			payment_date: paymentDate,
			reference_number: referenceNumber || undefined,
			notes: notes || undefined,
		});
		if (result && result.ok) {
			onSuccess();
		} else if (result && !result.ok) {
			setFormError(result.errors.map((e) => e.message).join("; "));
		}
	};

	return (
		<form onSubmit={handleSubmit} data-testid="record-payment-form" className="space-y-4">
			<h3 className="text-base font-semibold tracking-tight">Record Payment</h3>

			{formError ? (
				<SurfaceMessage tone="danger" role="alert">
					{formError}
				</SurfaceMessage>
			) : null}

			<div className="space-y-2">
				<label htmlFor="payment-amount">Amount</label>
				<Input
					id="payment-amount"
					type="number"
					step="0.01"
					min="0.01"
					max={outstandingBalance}
					value={amount}
					onChange={(e) => setAmount(e.target.value)}
					required
				/>
				{parsedAmount > outstandingBalance ? (
					<span className="text-sm text-destructive">
						Amount exceeds outstanding balance ({outstandingBalance})
					</span>
				) : null}
			</div>

			<div className="space-y-2">
				<label htmlFor="payment-method">Payment Method</label>
				<select
					id="payment-method"
					value={method}
					onChange={(e) => setMethod(e.target.value as PaymentMethod)}
					required
				>
					{PAYMENT_METHODS.map((m) => (
						<option key={m.value} value={m.value}>
							{m.label}
						</option>
					))}
				</select>
			</div>

			<div className="space-y-2">
				<label htmlFor="payment-date">Payment Date</label>
				<Input
					id="payment-date"
					type="date"
					value={paymentDate}
					onChange={(e) => setPaymentDate(e.target.value)}
					required
				/>
			</div>

			<div className="space-y-2">
				<label htmlFor="reference-number">Reference Number</label>
				<Input
					id="reference-number"
					type="text"
					maxLength={100}
					value={referenceNumber}
					onChange={(e) => setReferenceNumber(e.target.value)}
				/>
			</div>

			<div className="space-y-2">
				<label htmlFor="payment-notes">Notes</label>
				<textarea
					id="payment-notes"
					maxLength={500}
					value={notes}
					onChange={(e) => setNotes(e.target.value)}
				/>
			</div>

			<div className="flex gap-3">
				<Button type="submit" disabled={!isValid || isLoading}>
					{isLoading ? "Recording..." : "Record Payment"}
				</Button>
				<Button type="button" variant="outline" onClick={onCancel}>
					Cancel
				</Button>
			</div>
		</form>
	);
}
