/** Reusable customer create/edit form component — react-hook-form + native validation + shadcn field. */

import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";

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

// Plain TypeScript interface — mirrors CustomerCreatePayload
type CustomerFormValues = {
  company_name: string;
  business_number: string;
  billing_address: string;
  contact_name: string;
  contact_phone: string;
  contact_email: string;
  credit_limit: string;
};

// Custom native resolver — replicates zod validation and returns same i18n error keys
function buildNativeResolver(
  _t: (key: string) => string,
) {
  return async (values: CustomerFormValues) => {
    const errors: Record<string, { type: string; message: string }> = {};

    if (!values.company_name?.trim()) {
      errors.company_name = { type: "required", message: "customer.form.companyNameRequired" };
    } else if (values.company_name.length > 200) {
      errors.company_name = { type: "max", message: "customer.form.companyNameTooLong" };
    }

    if (!values.business_number?.trim()) {
      errors.business_number = { type: "required", message: "customer.form.businessNumberRequired" };
    } else if (values.business_number.length > 20) {
      errors.business_number = { type: "max", message: "customer.form.businessNumberTooLong" };
    }

    if (values.billing_address?.length > 500) {
      errors.billing_address = { type: "max", message: "customer.form.billingAddressTooLong" };
    }

    if (!values.contact_name?.trim()) {
      errors.contact_name = { type: "required", message: "customer.form.contactNameRequired" };
    } else if (values.contact_name.length > 100) {
      errors.contact_name = { type: "max", message: "customer.form.contactNameTooLong" };
    }

    if (!values.contact_phone?.trim()) {
      errors.contact_phone = { type: "required", message: "customer.form.contactPhoneRequired" };
    } else if (values.contact_phone.length > 30) {
      errors.contact_phone = { type: "max", message: "customer.form.contactPhoneTooLong" };
    }

    if (!values.contact_email?.trim()) {
      errors.contact_email = { type: "required", message: "customer.form.contactEmailRequired" };
    } else if (values.contact_email.length > 254) {
      errors.contact_email = { type: "max", message: "customer.form.contactEmailTooLong" };
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.contact_email)) {
      errors.contact_email = { type: "email", message: "customer.form.invalidEmail" };
    }

    return Object.keys(errors).length > 0 ? { errors, values } : { errors: {}, values };
  };
}

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
    resolver: buildNativeResolver(t) as any,
    defaultValues: {
      company_name: initialValues?.company_name ?? "",
      business_number: initialValues?.business_number ?? "",
      billing_address: initialValues?.billing_address ?? "",
      contact_name: initialValues?.contact_name ?? "",
      contact_phone: initialValues?.contact_phone ?? "",
      contact_email: initialValues?.contact_email ?? "",
      credit_limit: initialValues?.credit_limit ?? "0.00",
    },
    mode: "onSubmit",
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

        // Taiwan business number has a special checksum algorithm — run after native validation
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
