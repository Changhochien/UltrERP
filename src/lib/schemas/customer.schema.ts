import { z } from "zod";

import type { CustomerCreatePayload } from "../../domain/customers/types";
import { validateTaiwanBusinessNumber } from "../validation/taiwanBusinessNumber";

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export const customerFormSchema = z.object({
  company_name: z
    .string()
    .trim()
    .min(1, "customer.form.companyNameRequired")
    .max(200, "customer.form.companyNameTooLong"),
  business_number: z
    .string()
    .trim()
    .min(1, "customer.form.businessNumberRequired")
    .max(20, "customer.form.businessNumberTooLong")
    .superRefine((value, ctx) => {
      const normalized = value.trim();

      if (!normalized || normalized.length > 20) {
        return;
      }

      const result = validateTaiwanBusinessNumber(normalized);
      if (!result.valid) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: result.error ?? "customer.form.invalidBusinessNumber",
        });
      }
    }),
  billing_address: z.string().max(500, "customer.form.billingAddressTooLong"),
  contact_name: z
    .string()
    .trim()
    .min(1, "customer.form.contactNameRequired")
    .max(100, "customer.form.contactNameTooLong"),
  contact_phone: z
    .string()
    .trim()
    .min(1, "customer.form.contactPhoneRequired")
    .max(30, "customer.form.contactPhoneTooLong"),
  contact_email: z
    .string()
    .trim()
    .min(1, "customer.form.contactEmailRequired")
    .max(254, "customer.form.contactEmailTooLong")
    .superRefine((value, ctx) => {
      const normalized = value.trim();

      if (!normalized || normalized.length > 254) {
        return;
      }

      if (!EMAIL_REGEX.test(normalized)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "customer.form.invalidEmail",
        });
      }
    }),
  credit_limit: z.string().refine((value) => {
    const normalized = value.trim();

    if (!normalized) {
      return true;
    }

    const parsed = Number(normalized);
    return !Number.isNaN(parsed) && parsed >= 0;
  }, "customer.form.creditLimitNonNegative"),
});

export type CustomerFormValues = z.infer<typeof customerFormSchema>;

export function toCustomerCreatePayload(values: CustomerFormValues): CustomerCreatePayload {
  const creditLimit = Number(values.credit_limit.trim() || "0");

  return {
    company_name: values.company_name.trim(),
    business_number: values.business_number.trim(),
    billing_address: values.billing_address.trim(),
    contact_name: values.contact_name.trim(),
    contact_phone: values.contact_phone.trim(),
    contact_email: values.contact_email.trim().toLowerCase(),
    credit_limit: creditLimit.toFixed(2),
  };
}