/** Form for recording a payment against an invoice. */

import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";

import { SurfaceMessage } from "../../../components/layout/PageLayout";
import { Button } from "../../../components/ui/button";
import { DatePicker } from "../../../components/ui/DatePicker";
import {
	parseDatePickerInputValue,
	serializeDatePickerValue,
} from "../../../components/ui/date-picker-utils";


import { Field, FieldError, FieldLabel } from "../../../components/ui/field";
import { Input } from "../../../components/ui/input";
import { useToast } from "../../../hooks/useToast";
import { appTodayISO } from "../../../lib/time";
import type { PaymentMethod } from "../types";
import { useCreatePayment } from "../hooks/usePayments";
import {
	createRecordPaymentFormSchema,
	type RecordPaymentFormValues,
	toRecordPaymentPayload,
} from "../../../lib/schemas/payment.schema";

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
	const { t } = useTranslation("common");
	const { error: showErrorToast, success: showSuccessToast } = useToast();
	const [formError, setFormError] = useState<string | null>(null);

	const { mutate, isLoading } = useCreatePayment();
	const {
		control,
		handleSubmit,
		register,
		formState: { errors },
		watch,
	} = useForm<RecordPaymentFormValues>({
		resolver: zodResolver(createRecordPaymentFormSchema(outstandingBalance)),
		defaultValues: {
			amount: String(outstandingBalance),
			payment_method: "BANK_TRANSFER",
			payment_date: appTodayISO(),
			reference_number: "",
			notes: "",
		},
		reValidateMode: "onChange",
	});

	const amount = watch("amount");
	const parsedAmount = Number(amount);
	const amountWarningId = parsedAmount > outstandingBalance ? "payment-amount-warning" : undefined;
	const formErrorId = formError ? "record-payment-form-error" : undefined;
	const amountErrorId = errors.amount ? "record-payment-amount-error" : undefined;
	const paymentDateErrorId = errors.payment_date ? "record-payment-date-error" : undefined;
	const amountDescribedBy = [formErrorId, amountWarningId, amountErrorId]
		.filter(Boolean)
		.join(" ") || undefined;
	const paymentDateDescribedBy = [paymentDateErrorId].filter(Boolean).join(" ") || undefined;

	const submitPayment = async (values: RecordPaymentFormValues) => {
		if (isLoading) return;
		setFormError(null);

		const result = await mutate(toRecordPaymentPayload(invoiceId, values));
		if (result && result.ok) {
			showSuccessToast(
				t("payments.form.toast.recordedTitle"),
				t("payments.form.toast.recordedDescription", { paymentRef: result.data.payment_ref }),
			);
			onSuccess();
		} else if (result && !result.ok) {
			const message = result.errors.map((e) => e.message).join("; ");
			setFormError(message);
			showErrorToast(t("payments.form.toast.errorTitle"), message);
		}
	};

	return (
		<form
			onSubmit={handleSubmit(submitPayment, () => setFormError(null))}
			data-testid="record-payment-form"
			className="space-y-4"
			noValidate
		>
			<h3 className="text-base font-semibold tracking-tight">Record Payment</h3>

			{formError ? (
				<SurfaceMessage id={formErrorId} tone="danger" role="alert">
					{formError}
				</SurfaceMessage>
			) : null}

			<Field data-invalid={errors.amount ? true : undefined} className="space-y-2">
				<FieldLabel htmlFor="payment-amount">Amount</FieldLabel>
				<Input
					id="payment-amount"
					type="number"
					aria-describedby={amountDescribedBy}
					aria-invalid={errors.amount ? true : undefined}
					step="0.01"
					min="0.01"
					max={outstandingBalance}
					{...register("amount")}
					required
				/>
				{parsedAmount > outstandingBalance ? (
					<span id={amountWarningId} className="text-sm text-destructive">
						{t("payments.form.amountExceeded", { amount: outstandingBalance })}
					</span>
				) : null}
				<FieldError id={amountErrorId}>
					{errors.amount?.message ? t(errors.amount.message) : null}
				</FieldError>
			</Field>

			<Field data-invalid={errors.payment_method ? true : undefined} className="space-y-2">
				<FieldLabel htmlFor="payment-method">Payment Method</FieldLabel>
				<select
					id="payment-method"
					aria-invalid={errors.payment_method ? true : undefined}
					{...register("payment_method")}
					required
				>
					{PAYMENT_METHODS.map((m) => (
						<option key={m.value} value={m.value}>
							{m.label}
						</option>
					))}
				</select>
				<FieldError>
					{errors.payment_method?.message ? t(errors.payment_method.message) : null}
				</FieldError>
			</Field>

			<Field data-invalid={errors.payment_date ? true : undefined} className="space-y-2">
				<FieldLabel htmlFor="payment-date">{t("payments.form.fields.paymentDate")}</FieldLabel>
				<Controller
					name="payment_date"
					control={control}
					render={({ field }) => (
						<DatePicker
							id="payment-date"
							placeholder={t("payments.form.fields.paymentDate")}
							value={parseDatePickerInputValue(field.value)}
							onChange={(value) => field.onChange(serializeDatePickerValue(value))}
							allowClear={false}
							aria-describedby={paymentDateDescribedBy}
						/>
					)}
				/>
				<FieldError id={paymentDateErrorId}>
					{errors.payment_date?.message ? t(errors.payment_date.message) : null}
				</FieldError>
			</Field>

			<Field data-invalid={errors.reference_number ? true : undefined} className="space-y-2">
				<FieldLabel htmlFor="reference-number">Reference Number</FieldLabel>
				<Input
					id="reference-number"
					type="text"
					maxLength={100}
					aria-invalid={errors.reference_number ? true : undefined}
					{...register("reference_number")}
				/>
				<FieldError>
					{errors.reference_number?.message ? t(errors.reference_number.message) : null}
				</FieldError>
			</Field>

			<Field data-invalid={errors.notes ? true : undefined} className="space-y-2">
				<FieldLabel htmlFor="payment-notes">Notes</FieldLabel>
				<textarea
					id="payment-notes"
					maxLength={500}
					aria-invalid={errors.notes ? true : undefined}
					{...register("notes")}
				/>
				<FieldError>
					{errors.notes?.message ? t(errors.notes.message) : null}
				</FieldError>
			</Field>

			<div className="flex gap-3">
				<Button type="submit" disabled={isLoading}>
					{isLoading ? "Recording..." : "Record Payment"}
				</Button>
				<Button type="button" variant="outline" onClick={onCancel}>
					Cancel
				</Button>
			</div>
		</form>
	);
}
