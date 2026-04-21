import { z } from "zod/v4";

import {
  INVOICE_TAX_POLICY_OPTIONS,
  type InvoiceBuyerType,
  type InvoiceCreatePayload,
  type InvoiceDraftLine,
  type InvoiceTaxPolicyCode,
} from "../../domain/invoices/types";

const invoiceTaxPolicyCodes = INVOICE_TAX_POLICY_OPTIONS.map(
  (option) => option.code,
) as [InvoiceTaxPolicyCode, ...InvoiceTaxPolicyCode[]];

function validateNumericString(
  value: string,
  ctx: z.RefinementCtx,
  options: { field: string; allowZero: boolean },
) {
  const normalized = value.trim();
  if (!normalized) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: `${options.field} is required`,
    });
    return;
  }

  const parsed = Number(normalized);
  if (!Number.isFinite(parsed)) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: `${options.field} must be a valid number`,
    });
    return;
  }

  if (options.allowZero ? parsed < 0 : parsed <= 0) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: options.allowZero
        ? `${options.field} must be zero or greater`
        : `${options.field} must be greater than zero`,
    });
  }
}

export const invoiceLineFormSchema = z.object({
  product_code: z.string(),
  product_id: z.string(),
  description: z.string().trim().min(1, "Description is required").max(500, "Description must be 500 characters or fewer"),
  quantity: z.string().superRefine((value, ctx) => {
    validateNumericString(value, ctx, { field: "Quantity", allowZero: false });
  }),
  unit_price: z.string().superRefine((value, ctx) => {
    validateNumericString(value, ctx, { field: "Unit price", allowZero: true });
  }),
  tax_policy_code: z.enum(invoiceTaxPolicyCodes),
});

export const invoiceFormSchema = z
  .object({
    customer_id: z.string().trim().min(1, "Customer is required"),
    buyer_type: z.enum(["b2b", "b2c"]),
    buyer_identifier: z.string().trim().max(20, "Buyer identifier must be 20 characters or fewer"),
    invoice_date: z.string().trim().min(1, "Invoice date is required"),
    currency_code: z.string().trim().length(3, "Currency code must be 3 characters"),
    lines: z.array(invoiceLineFormSchema).min(1, "Add at least one invoice line"),
  })
  .superRefine((value, ctx) => {
    if (value.buyer_type === "b2b" && value.buyer_identifier.trim().length === 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Buyer identifier is required for B2B invoices",
        path: ["buyer_identifier"],
      });
    }
  });

export type InvoiceFormLineValues = z.input<typeof invoiceLineFormSchema>;
export type InvoiceFormValues = z.input<typeof invoiceFormSchema>;

export function roundMoney(value: number): number {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

export function makeInvoiceDraftLine(): InvoiceFormLineValues {
  return {
    product_code: "",
    product_id: "",
    description: "",
    quantity: "1",
    unit_price: "0",
    tax_policy_code: "standard",
  };
}

export function buildLinePreview(line: InvoiceDraftLine) {
  const quantity = Number(line.quantity);
  const unitPrice = Number(line.unit_price);
  const policy =
    INVOICE_TAX_POLICY_OPTIONS.find((option) => option.code === line.tax_policy_code) ??
    INVOICE_TAX_POLICY_OPTIONS[0];
  const subtotalAmount =
    Number.isFinite(quantity) && Number.isFinite(unitPrice) ? roundMoney(quantity * unitPrice) : 0;
  const taxAmount = roundMoney(subtotalAmount * policy.taxRate);

  return {
    subtotalAmount,
    taxAmount,
    totalAmount: roundMoney(subtotalAmount + taxAmount),
    taxType: policy.taxType,
    taxRate: policy.taxRate,
  };
}

export function buildInvoiceFormValues(invoiceDate: string): InvoiceFormValues {
  return {
    customer_id: "",
    buyer_type: "b2b",
    buyer_identifier: "",
    invoice_date: invoiceDate,
    currency_code: "TWD",
    lines: [makeInvoiceDraftLine()],
  };
}

export function toInvoiceCreatePayload(values: InvoiceFormValues): InvoiceCreatePayload {
  return {
    customer_id: values.customer_id.trim(),
    buyer_type: values.buyer_type as InvoiceBuyerType,
    buyer_identifier: values.buyer_type === "b2b" ? values.buyer_identifier.trim() : null,
    invoice_date: values.invoice_date.trim(),
    currency_code: values.currency_code.trim(),
    lines: values.lines.map((line) => ({
      product_id: line.product_id.trim() || null,
      product_code: line.product_code.trim() || null,
      description: line.description.trim(),
      quantity: line.quantity.trim(),
      unit_price: line.unit_price.trim(),
      tax_policy_code: line.tax_policy_code,
    })),
  };
}