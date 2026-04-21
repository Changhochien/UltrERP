import { z } from "zod";

import type {
  OrderCreatePayload,
  OrderLineCreate,
  OrderSalesTeamAssignmentCreate,
  PaymentTermsCode,
} from "../../domain/orders/types";

const paymentTermsValues = ["NET_30", "NET_60", "COD"] as const;

const numberFromInput = (value: unknown) => {
  if (value === "" || value === null || value === undefined) {
    return 0;
  }

  const parsed = Number(value);
  return Number.isNaN(parsed) ? Number.NaN : parsed;
};

export const orderLineFormSchema = z.object({
  product_id: z.string().trim().min(1, "orders.form.errors.lineProductRequired"),
  source_quotation_line_no: z.number().int().positive().optional(),
  description: z
    .string()
    .trim()
    .min(1, "orders.form.errors.lineDescriptionRequired")
    .max(500, "orders.form.errors.lineDescriptionTooLong"),
  quantity: z.number().gt(0, "orders.form.errors.lineQuantityPositive"),
  list_unit_price: z.number().min(0, "orders.form.errors.lineListPriceNonNegative"),
  unit_price: z.number().min(0, "orders.form.errors.lineUnitPriceNonNegative"),
  discount_amount: z.number().min(0, "orders.form.errors.lineDiscountNonNegative"),
  tax_policy_code: z.string().trim().min(1, "orders.form.errors.lineTaxPolicyRequired"),
});

export type OrderLineFormValues = z.infer<typeof orderLineFormSchema>;

export const orderSalesTeamMemberSchema = z.object({
  sales_person: z
    .string()
    .trim()
    .min(1, "orders.form.errors.salesPersonRequired")
    .max(120, "orders.form.errors.salesPersonTooLong"),
  allocated_percentage: z
    .number()
    .gt(0, "orders.form.errors.allocatedPercentagePositive")
    .max(100, "orders.form.errors.allocatedPercentageMax"),
  commission_rate: z
    .number()
    .min(0, "orders.form.errors.commissionRateNonNegative")
    .max(100, "orders.form.errors.commissionRateMax"),
});

export type OrderSalesTeamMemberFormValues = z.infer<typeof orderSalesTeamMemberSchema>;

export const orderFormSchema = z
  .object({
    customer_id: z.string().trim().min(1, "orders.form.errors.customerRequired"),
    source_quotation_id: z.string().trim().optional(),
    payment_terms_code: z.enum(paymentTermsValues),
    discount_amount: z.number().min(0, "orders.form.errors.discountAmountNonNegative"),
    discount_percent: z
      .number()
      .min(0, "orders.form.errors.discountPercentRange")
      .max(100, "orders.form.errors.discountPercentRange"),
    crm_context_snapshot: z.record(z.string(), z.unknown()).nullable().optional(),
    notes: z.string().trim().max(2000, "orders.form.errors.notesTooLong"),
    sales_team: z.array(orderSalesTeamMemberSchema).max(10, "orders.form.errors.salesTeamTooLarge"),
    lines: z.array(orderLineFormSchema).min(1, "orders.form.errors.linesRequired").max(200, "orders.form.errors.linesTooLarge"),
  })
  .superRefine((value, ctx) => {
    if (value.discount_amount > 0 && value.discount_percent > 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "orders.form.errors.discountConflict",
        path: ["discount_amount"],
      });
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "orders.form.errors.discountConflict",
        path: ["discount_percent"],
      });
    }

    const allocationTotal = value.sales_team.reduce(
      (sum, member) => sum + Number(member.allocated_percentage || 0),
      0,
    );
    if (allocationTotal > 100) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "orders.form.salesTeamOverflow",
        path: ["sales_team"],
      });
    }
  });

export type OrderFormValues = z.infer<typeof orderFormSchema>;

export function emptyOrderFormLine(): OrderLineFormValues {
  return {
    product_id: "",
    source_quotation_line_no: undefined,
    description: "",
    quantity: 1,
    list_unit_price: 0,
    unit_price: 0,
    discount_amount: 0,
    tax_policy_code: "standard",
  };
}

export function emptyOrderSalesTeamMember(): OrderSalesTeamMemberFormValues {
  return { sales_person: "", allocated_percentage: 0, commission_rate: 0 };
}

export const numericFieldOptions = {
  setValueAs: numberFromInput,
};

export function toOrderCreatePayload(values: OrderFormValues): OrderCreatePayload {
  const lines: OrderLineCreate[] = values.lines.map((line) => ({
    product_id: line.product_id.trim(),
    ...(typeof line.source_quotation_line_no === "number"
      ? { source_quotation_line_no: line.source_quotation_line_no }
      : {}),
    description: line.description.trim(),
    quantity: Number(line.quantity),
    list_unit_price: Number(line.list_unit_price),
    unit_price: Number(line.unit_price),
    discount_amount: Number(line.discount_amount),
    tax_policy_code: line.tax_policy_code.trim(),
  }));

  const salesTeam: OrderSalesTeamAssignmentCreate[] = values.sales_team.map((member) => ({
    sales_person: member.sales_person.trim(),
    allocated_percentage: Number(member.allocated_percentage),
    commission_rate: Number(member.commission_rate),
  }));

  const payload: OrderCreatePayload = {
    customer_id: values.customer_id.trim(),
    payment_terms_code: values.payment_terms_code as PaymentTermsCode,
    lines,
  };

  const sourceQuotationId = values.source_quotation_id?.trim();
  if (sourceQuotationId) {
    payload.source_quotation_id = sourceQuotationId;
  }

  if (values.crm_context_snapshot) {
    payload.crm_context_snapshot = values.crm_context_snapshot;
  }

  if (values.discount_amount > 0) {
    payload.discount_amount = Number(values.discount_amount);
  }

  if (values.discount_percent > 0) {
    payload.discount_percent = Number((values.discount_percent / 100).toFixed(4));
  }

  const normalizedNotes = values.notes.trim();
  if (normalizedNotes) {
    payload.notes = normalizedNotes;
  }

  if (salesTeam.length > 0) {
    payload.sales_team = salesTeam;
  }

  return payload;
}