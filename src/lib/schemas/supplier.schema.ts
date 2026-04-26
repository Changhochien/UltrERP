import { z } from "zod";

import type { SupplierCreate } from "../../domain/inventory/types";

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export const supplierFormSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Supplier name is required")
    .max(300, "Supplier name must be 300 characters or fewer"),
  contact_email: z
    .string()
    .superRefine((value, ctx) => {
      const normalized = value.trim();

      if (!normalized) {
        return;
      }

      if (normalized.length > 255) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Contact email must be 255 characters or fewer",
        });
        return;
      }

      if (!EMAIL_REGEX.test(normalized)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Contact email must be a valid email address",
        });
      }
    }),
  phone: z.string().max(50, "Phone must be 50 characters or fewer"),
  address: z.string().max(500, "Address must be 500 characters or fewer"),
  default_lead_time_days: z
    .string()
    .superRefine((value, ctx) => {
      const normalized = value.trim();

      if (!normalized) {
        return;
      }

      const parsed = Number(normalized);
      if (!Number.isFinite(parsed) || parsed < 0 || !Number.isInteger(parsed)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Lead time must be zero or greater",
        });
      }
    }),
  default_currency_code: z.string().trim().max(3, "Default currency must be 3 characters or fewer").default(""),
  payment_terms_template_id: z.string().trim().default(""),
});

export type SupplierFormValues = z.infer<typeof supplierFormSchema>;

export const defaultSupplierFormValues: SupplierFormValues = {
  name: "",
  contact_email: "",
  phone: "",
  address: "",
  default_lead_time_days: "",
  default_currency_code: "",
  payment_terms_template_id: "",
};

export function toSupplierCreatePayload(values: SupplierFormValues): SupplierCreate {
  const normalizedLeadTime = values.default_lead_time_days.trim();
  const defaultCurrencyCode = values.default_currency_code.trim();
  const paymentTermsTemplateId = values.payment_terms_template_id.trim();

  return {
    name: values.name.trim(),
    contact_email: values.contact_email.trim() || undefined,
    phone: values.phone.trim() || undefined,
    address: values.address.trim() || undefined,
    default_lead_time_days: normalizedLeadTime === "" ? undefined : Number(normalizedLeadTime),
    default_currency_code: defaultCurrencyCode || null,
    payment_terms_template_id: paymentTermsTemplateId || null,
  };
}