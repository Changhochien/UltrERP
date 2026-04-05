/** Reusable customer create/edit form component — react-hook-form + zod + shadcn field. */

import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Field, FieldLabel, FieldError } from "../ui/field";
import type { CustomerCreatePayload } from "../../domain/customers/types";
import { validateTaiwanBusinessNumber } from "../../lib/validation/taiwanBusinessNumber";

export interface CustomerFormProps {
  onSubmit: (payload: CustomerCreatePayload) => void;
  submitting?: boolean;
  serverErrors?: Array<{ field: string; message: string }>;
  initialValues?: Partial<CustomerCreatePayload>;
  submitLabel?: string;
  submittingLabel?: string;
}

// Zod schema — mirrors CustomerCreatePayload with all validation rules
// NOTE: all fields typed as string to match HTML input values; number conversion happens on submit
const customerSchema = z.object({
  company_name: z.string().min(1, "customer.form.companyNameRequired").max(200),
  business_number: z.string().min(1, "customer.form.businessNumberRequired").max(20),
  billing_address: z.string().max(500),
  contact_name: z.string().min(1, "customer.form.contactNameRequired").max(100),
  contact_phone: z.string().min(1, "customer.form.contactPhoneRequired").max(30),
  contact_email: z
    .string()
    .min(1, "customer.form.contactEmailRequired")
    .email("customer.form.invalidEmail")
    .max(254),
  credit_limit: z.string(),
});

type CustomerFormValues = z.infer<typeof customerSchema>;

export default function CustomerForm({
  onSubmit,
  submitting,
  serverErrors,
  initialValues,
  submitLabel,
  submittingLabel,
}: CustomerFormProps) {
  const { t } = useTranslation("common");
  const _submitLabel = submitLabel ?? t("customer.form.createTitle");
  const _submittingLabel = submittingLabel ?? t("customer.form.creating");

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<CustomerFormValues>({
    resolver: zodResolver(customerSchema),
    defaultValues: {
      company_name: initialValues?.company_name ?? "",
      business_number: initialValues?.business_number ?? "",
      billing_address: initialValues?.billing_address ?? "",
      contact_name: initialValues?.contact_name ?? "",
      contact_phone: initialValues?.contact_phone ?? "",
      contact_email: initialValues?.contact_email ?? "",
      credit_limit: initialValues?.credit_limit ?? "0.00",
    },
    mode: "onBlur",
  });

  // Map server errors onto the correct form fields
  useEffect(() => {
    if (!serverErrors?.length) return;
    for (const err of serverErrors) {
      if (err.field) {
        setError(err.field as keyof CustomerFormValues, { message: err.message });
      }
    }
  }, [serverErrors, setError]);

  const generalErrors = serverErrors?.filter((e) => !e.field) ?? [];

  return (
    <form
      onSubmit={handleSubmit((values) => {
        // Validate credit_limit as a non-negative number
        const limitNum = Number(values.credit_limit);
        if (Number.isNaN(limitNum) || limitNum < 0) {
          setError("credit_limit", { message: t("customer.form.creditLimitNonNegative") });
          return;
        }

        // Taiwan business number has a special checksum algorithm — run after zod
        const ban = validateTaiwanBusinessNumber(values.business_number ?? "");
        if (!ban.valid) {
          setError("business_number", {
            message: ban.error ?? t("customer.form.invalidBusinessNumber"),
          });
          return;
        }
        onSubmit({
          company_name: (values.company_name ?? "").trim(),
          business_number: (values.business_number ?? "").trim(),
          billing_address: (values.billing_address ?? "").trim(),
          contact_name: (values.contact_name ?? "").trim(),
          contact_phone: (values.contact_phone ?? "").trim(),
          contact_email: (values.contact_email ?? "").trim().toLowerCase(),
          credit_limit: String(limitNum.toFixed(2)),
        });
      })}
      className="flex flex-col gap-5"
      noValidate
    >
      {generalErrors.length > 0 && (
        <div
          className="rounded-xl border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive"
          role="alert"
        >
          {generalErrors.map((e) => (
            <p key={e.message}>{e.message}</p>
          ))}
        </div>
      )}

      <div className="grid gap-5 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="company_name">{t("customer.form.companyName")} *</FieldLabel>
          <Input
            id="company_name"
            {...register("company_name")}
            maxLength={200}
            aria-invalid={!!errors.company_name}
          />
          <FieldError
            errors={errors.company_name ? [{ message: t(errors.company_name.message!) }] : []}
          />
        </Field>

        <Field>
          <FieldLabel htmlFor="business_number">{t("customer.form.businessNumber")} *</FieldLabel>
          <Input
            id="business_number"
            {...register("business_number")}
            maxLength={20}
            aria-invalid={!!errors.business_number}
          />
          <FieldError
            errors={errors.business_number ? [{ message: t(errors.business_number.message!) }] : []}
          />
        </Field>
      </div>

      <Field>
        <FieldLabel htmlFor="billing_address">{t("customer.form.billingAddress")}</FieldLabel>
        <Input
          id="billing_address"
          {...register("billing_address")}
          maxLength={500}
        />
      </Field>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="contact_name">{t("customer.form.contactName")} *</FieldLabel>
          <Input
            id="contact_name"
            {...register("contact_name")}
            maxLength={100}
            aria-invalid={!!errors.contact_name}
          />
          <FieldError
            errors={errors.contact_name ? [{ message: t(errors.contact_name.message!) }] : []}
          />
        </Field>

        <Field>
          <FieldLabel htmlFor="contact_phone">{t("customer.form.contactPhone")} *</FieldLabel>
          <Input
            id="contact_phone"
            {...register("contact_phone")}
            maxLength={30}
            aria-invalid={!!errors.contact_phone}
          />
          <FieldError
            errors={errors.contact_phone ? [{ message: t(errors.contact_phone.message!) }] : []}
          />
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="contact_email">{t("customer.form.contactEmail")} *</FieldLabel>
          <Input
            id="contact_email"
            type="email"
            {...register("contact_email")}
            maxLength={254}
            aria-invalid={!!errors.contact_email}
          />
          <FieldError
            errors={errors.contact_email ? [{ message: t(errors.contact_email.message!) }] : []}
          />
        </Field>

        <Field>
          <FieldLabel htmlFor="credit_limit">{t("customer.form.creditLimit")}</FieldLabel>
          <Input
            id="credit_limit"
            type="number"
            step="0.01"
            min="0"
            {...register("credit_limit")}
            aria-invalid={!!errors.credit_limit}
          />
          <FieldError
            errors={errors.credit_limit ? [{ message: t(errors.credit_limit.message!) }] : []}
          />
        </Field>
      </div>

      <Button type="submit" disabled={submitting}>
        {submitting ? _submittingLabel : _submitLabel}
      </Button>
    </form>
  );
}
