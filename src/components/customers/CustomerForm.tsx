/** Reusable customer create/edit form component — react-hook-form + native validation + shadcn field. */

import { useEffect } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { useForm, type Resolver } from "react-hook-form";

import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Field, FieldLabel, FieldError } from "../ui/field";
import {
  customerFormSchema,
  type CustomerFormValues,
  toCustomerCreatePayload,
} from "../../lib/schemas/customer.schema";

export interface CustomerFormProps {
  onSubmit: (payload: ReturnType<typeof toCustomerCreatePayload>) => void;
  submitting?: boolean;
  serverErrors?: Array<{ field: string; message: string }>;
  initialValues?: Partial<CustomerFormValues>;
  submitLabel?: string;
  submittingLabel?: string;
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
    resolver: zodResolver(customerFormSchema as never) as Resolver<CustomerFormValues>,
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
        onSubmit(toCustomerCreatePayload(values));
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
