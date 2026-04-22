/** Form for recording a payment without a specific invoice (for reconciliation). */

import { useEffect, useState } from "react";
import { Controller, useForm, type Resolver } from "react-hook-form";
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
import type { CustomerSummary } from "../../customers/types";
import { createUnmatchedPayment } from "../../../lib/api/payments";
import { listCustomers } from "../../../lib/api/customers";
import {
	type UnmatchedPaymentFormValues,
	toUnmatchedPaymentPayload,
	unmatchedPaymentFormSchema,
} from "../../../lib/schemas/payment.schema";

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
	const [customers, setCustomers] = useState<CustomerSummary[]>([]);
	const [formError, setFormError] = useState<string | null>(null);
	const [isLoading, setIsLoading] = useState(false);
	const {
		control,
		handleSubmit,
		register,
		formState: { errors },
	} = useForm<UnmatchedPaymentFormValues>({
		resolver: zodResolver(unmatchedPaymentFormSchema as never) as Resolver<UnmatchedPaymentFormValues>,
		defaultValues: {
			customer_id: "",
			amount: "",
			payment_method: "BANK_TRANSFER",
			payment_date: appTodayISO(),
			reference_number: "",
			notes: "",
		},
		reValidateMode: "onChange",
	});

	useEffect(() => {
		listCustomers({ status: "active", page_size: 200 }).then((res) =>
			setCustomers(res.items),
		);
	}, []);

	const submitPayment = async (values: UnmatchedPaymentFormValues) => {
		if (isLoading) return;
		setIsLoading(true);
		setFormError(null);

		const result = await createUnmatchedPayment(toUnmatchedPaymentPayload(values));

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
		<form
			onSubmit={handleSubmit(submitPayment, () => setFormError(null))}
			data-testid="record-unmatched-payment-form"
			className="space-y-4"
			noValidate
		>
			<h3 className="text-base font-semibold tracking-tight">Record Unmatched Payment</h3>

			{formError ? (
				<SurfaceMessage tone="danger" role="alert">
					{formError}
				</SurfaceMessage>
			) : null}

			<Field data-invalid={errors.customer_id ? true : undefined} className="space-y-2">
				<FieldLabel htmlFor="customer-id">Customer</FieldLabel>
				<select
					id="customer-id"
					aria-invalid={errors.customer_id ? true : undefined}
					{...register("customer_id")}
					required
				>
					<option value="">-- Select customer --</option>
					{customers.map((c) => (
						<option key={c.id} value={c.id}>
							{c.company_name} ({c.normalized_business_number})
						</option>
					))}
				</select>
				<FieldError id={errors.customer_id ? "record-unmatched-customer-error" : undefined}>
					{errors.customer_id?.message ? t(errors.customer_id.message) : null}
				</FieldError>
			</Field>

			<Field data-invalid={errors.amount ? true : undefined} className="space-y-2">
				<FieldLabel htmlFor="unmatched-amount">Amount</FieldLabel>
				<Input
					id="unmatched-amount"
					type="number"
					step="0.01"
					min="0.01"
					aria-invalid={errors.amount ? true : undefined}
					{...register("amount")}
					required
				/>
				<FieldError>
					{errors.amount?.message ? t(errors.amount.message) : null}
				</FieldError>
			</Field>

			<Field data-invalid={errors.payment_method ? true : undefined} className="space-y-2">
				<FieldLabel htmlFor="unmatched-method">Payment Method</FieldLabel>
				<select
					id="unmatched-method"
					aria-invalid={errors.payment_method ? true : undefined}
					{...register("payment_method")}
				>
					{PAYMENT_METHODS.map((pm) => (
						<option key={pm.value} value={pm.value}>
							{pm.label}
						</option>
					))}
				</select>
				<FieldError>
					{errors.payment_method?.message ? t(errors.payment_method.message) : null}
				</FieldError>
			</Field>

			<Field data-invalid={errors.payment_date ? true : undefined} className="space-y-2">
				<FieldLabel htmlFor="unmatched-date">{t("payments.form.fields.paymentDate")}</FieldLabel>
				<Controller
					name="payment_date"
					control={control}
					render={({ field }) => (
						<DatePicker
							id="unmatched-date"
							placeholder={t("payments.form.fields.paymentDate")}
							value={parseDatePickerInputValue(field.value)}
							onChange={(value) => field.onChange(serializeDatePickerValue(value))}
							allowClear={false}
						/>
					)}
				/>
				<FieldError>
					{errors.payment_date?.message ? t(errors.payment_date.message) : null}
				</FieldError>
			</Field>

			<Field data-invalid={errors.reference_number ? true : undefined} className="space-y-2">
				<FieldLabel htmlFor="unmatched-ref">Reference Number</FieldLabel>
				<Input
					id="unmatched-ref"
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
				<FieldLabel htmlFor="unmatched-notes">Notes</FieldLabel>
				<textarea
					id="unmatched-notes"
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
