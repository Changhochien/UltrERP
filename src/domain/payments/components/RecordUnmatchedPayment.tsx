/** Form for recording a payment without a specific invoice (for reconciliation). */

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { SurfaceMessage } from "../../../components/layout/PageLayout";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { useToast } from "../../../hooks/useToast";
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
	const { t } = useTranslation("common");
	const { error: showErrorToast, success: showSuccessToast } = useToast();
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
			showSuccessToast(
				t("payments.form.toast.unmatchedRecordedTitle"),
				t("payments.form.toast.unmatchedRecordedDescription", { paymentRef: result.data.payment_ref }),
			);
			onSuccess();
		} else {
			const message = result.errors.map((e) => e.message).join("; ");
			setFormError(message);
			showErrorToast(t("payments.form.toast.errorTitle"), message);
		}
	};

	return (
		<form onSubmit={handleSubmit} data-testid="record-unmatched-payment-form" className="space-y-4">
			<h3 className="text-base font-semibold tracking-tight">Record Unmatched Payment</h3>

			{formError ? (
				<SurfaceMessage tone="danger" role="alert">
					{formError}
				</SurfaceMessage>
			) : null}

			<div className="space-y-2">
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

			<div className="space-y-2">
				<label htmlFor="unmatched-amount">Amount</label>
				<Input
					id="unmatched-amount"
					type="number"
					step="0.01"
					min="0.01"
					value={amount}
					onChange={(e) => setAmount(e.target.value)}
					required
				/>
			</div>

			<div className="space-y-2">
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

			<div className="space-y-2">
				<label htmlFor="unmatched-date">Payment Date</label>
				<Input
					id="unmatched-date"
					type="date"
					value={paymentDate}
					onChange={(e) => setPaymentDate(e.target.value)}
					required
				/>
			</div>

			<div className="space-y-2">
				<label htmlFor="unmatched-ref">Reference Number</label>
				<Input
					id="unmatched-ref"
					type="text"
					maxLength={100}
					value={referenceNumber}
					onChange={(e) => setReferenceNumber(e.target.value)}
				/>
			</div>

			<div className="space-y-2">
				<label htmlFor="unmatched-notes">Notes</label>
				<textarea
					id="unmatched-notes"
					maxLength={500}
					value={notes}
					onChange={(e) => setNotes(e.target.value)}
				/>
			</div>

			<div className="flex gap-3">
				<Button type="submit" disabled={!isValid || isLoading}>
					{isLoading ? "Submitting…" : "Record Payment"}
				</Button>
				<Button type="button" variant="outline" onClick={onCancel}>
					Cancel
				</Button>
			</div>
		</form>
	);
}
