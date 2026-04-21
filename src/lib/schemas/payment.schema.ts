import { z } from "zod";

import type { PaymentCreate, PaymentCreateUnmatched } from "../../domain/payments/types";

const paymentMethodValues = ["CASH", "BANK_TRANSFER", "CHECK", "CREDIT_CARD", "OTHER"] as const;

export const paymentMethodSchema = z.enum(paymentMethodValues);

const paymentBaseSchema = z.object({
  amount: z
    .string()
    .trim()
    .min(1, "payments.form.errors.amountRequired")
    .superRefine((value, ctx) => {
      const normalized = value.trim();

      if (!normalized) {
        return;
      }

      const parsed = Number(normalized);
      if (Number.isNaN(parsed) || parsed <= 0) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "payments.form.errors.amountPositive",
        });
      }
    }),
  payment_method: paymentMethodSchema,
  payment_date: z.string().trim().min(1, "payments.form.errors.paymentDateRequired"),
  reference_number: z
    .string()
    .trim()
    .max(100, "payments.form.errors.referenceNumberTooLong"),
  notes: z.string().trim().max(500, "payments.form.errors.notesTooLong"),
});

export type PaymentFormValues = z.input<typeof paymentBaseSchema>;

export function createRecordPaymentFormSchema(outstandingBalance: number) {
  return paymentBaseSchema.superRefine((value, ctx) => {
    const normalized = value.amount.trim();

    if (!normalized) {
      return;
    }

    const parsed = Number(normalized);
    if (!Number.isNaN(parsed) && parsed > outstandingBalance) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "payments.form.errors.amountExceedsOutstanding",
        path: ["amount"],
      });
    }
  });
}

export type RecordPaymentFormValues = z.input<ReturnType<typeof createRecordPaymentFormSchema>>;

export const unmatchedPaymentFormSchema = paymentBaseSchema.extend({
  customer_id: z.string().trim().min(1, "payments.form.errors.customerRequired"),
});

export type UnmatchedPaymentFormValues = z.input<typeof unmatchedPaymentFormSchema>;

function normalizeOptional(value: string) {
  const normalized = value.trim();
  return normalized || undefined;
}

export function toRecordPaymentPayload(
  invoiceId: string,
  values: PaymentFormValues,
): PaymentCreate {
  return {
    invoice_id: invoiceId,
    amount: values.amount.trim(),
    payment_method: values.payment_method,
    payment_date: values.payment_date.trim(),
    reference_number: normalizeOptional(values.reference_number),
    notes: normalizeOptional(values.notes),
  };
}

export function toUnmatchedPaymentPayload(
  values: UnmatchedPaymentFormValues,
): PaymentCreateUnmatched {
  return {
    customer_id: values.customer_id.trim(),
    amount: values.amount.trim(),
    payment_method: values.payment_method,
    payment_date: values.payment_date.trim(),
    reference_number: normalizeOptional(values.reference_number),
    notes: normalizeOptional(values.notes),
  };
}