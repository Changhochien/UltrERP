/** Form for recording a payment without a specific invoice (for reconciliation). */

import { useEffect, useState } from "react";
import type { PaymentMethod } from "../types";
import type { CustomerSummary } from "../../customers/types";
import { createUnmatchedPayment } from "../../../lib/api/payments";
import { listCustomers } from "../../../lib/api/customers";

const PAYMENT_METHODS: { value: PaymentMethod; label: string }[] = [
	{ value: "CASH", label: "Cash" },
	{ value: "BANK_TRANSFER", label: "Bank Transfer" },
	{ value: "CHECK", label: "Check" },
	{ value: "CREDIT_CARD", label: "Credit Card" },
	{ value: "OTHER", label: "Other" },
];

interface RecordUnmatchedPaymentProps {
	onSuccess: () => void;
	onCancel: () => void;
}

export default function RecordUnmatchedPayment({
	onSuccess,
	onCancel,
}: RecordUnmatchedPaymentProps) {
	const [customerId, setCustomerId] = useState("");
	const [customers, setCustomers] = useState<CustomerSummary[]>([]);
	const [amount, setAmount] = useState("");
	const [method, setMethod] = useState<PaymentMethod>("BANK_TRANSFER");
	const [paymentDate, setPaymentDate] = useState(
		new Date().toISOString().slice(0, 10),
	);
	const [referenceNumber, setReferenceNumber] = useState("");
	const [notes, setNotes] = useState("");
	const [formError, setFormError] = useState<string | null>(null);
	const [isLoading, setIsLoading] = useState(false);

	useEffect(() => {
		listCustomers({ status: "active", page_size: 200 }).then((res) =>
			setCustomers(res.items),
		);
	}, []);

	const parsedAmount = parseFloat(amount);
	const isValid =
		customerId.length > 0 &&
		!isNaN(parsedAmount) &&
		parsedAmount > 0 &&
		paymentDate.length > 0;

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		if (isLoading || !isValid) return;
		setIsLoading(true);
		setFormError(null);

		const result = await createUnmatchedPayment({
			customer_id: customerId,
			amount: amount,
			payment_method: method,
			payment_date: paymentDate,
			reference_number: referenceNumber || undefined,
			notes: notes || undefined,
		});

		setIsLoading(false);
		if (result.ok) {
			onSuccess();
		} else {
			setFormError(result.errors.map((e) => e.message).join("; "));
		}
	};

	return (
		<form onSubmit={handleSubmit} data-testid="record-unmatched-payment-form">
			<h3>Record Unmatched Payment</h3>

			{formError && (
				<div role="alert" style={{ color: "red" }}>
					{formError}
				</div>
			)}

			<div>
				<label htmlFor="customer-id">Customer</label>
				<select
					id="customer-id"
					value={customerId}
					onChange={(e) => setCustomerId(e.target.value)}
					required
				>
					<option value="">-- Select customer --</option>
					{customers.map((c) => (
						<option key={c.id} value={c.id}>
							{c.company_name} ({c.normalized_business_number})
						</option>
					))}
				</select>
			</div>

			<div>
				<label htmlFor="unmatched-amount">Amount</label>
				<input
					id="unmatched-amount"
					type="number"
					step="0.01"
					min="0.01"
					value={amount}
					onChange={(e) => setAmount(e.target.value)}
					required
				/>
			</div>

			<div>
				<label htmlFor="unmatched-method">Payment Method</label>
				<select
					id="unmatched-method"
					value={method}
					onChange={(e) => setMethod(e.target.value as PaymentMethod)}
				>
					{PAYMENT_METHODS.map((pm) => (
						<option key={pm.value} value={pm.value}>
							{pm.label}
						</option>
					))}
				</select>
			</div>

			<div>
				<label htmlFor="unmatched-date">Payment Date</label>
				<input
					id="unmatched-date"
					type="date"
					value={paymentDate}
					onChange={(e) => setPaymentDate(e.target.value)}
					required
				/>
			</div>

			<div>
				<label htmlFor="unmatched-ref">Reference Number</label>
				<input
					id="unmatched-ref"
					type="text"
					maxLength={100}
					value={referenceNumber}
					onChange={(e) => setReferenceNumber(e.target.value)}
				/>
			</div>

			<div>
				<label htmlFor="unmatched-notes">Notes</label>
				<textarea
					id="unmatched-notes"
					maxLength={500}
					value={notes}
					onChange={(e) => setNotes(e.target.value)}
				/>
			</div>

			<div>
				<button type="submit" disabled={!isValid || isLoading}>
					{isLoading ? "Submitting…" : "Record Payment"}
				</button>
				<button type="button" onClick={onCancel}>
					Cancel
				</button>
			</div>
		</form>
	);
}
