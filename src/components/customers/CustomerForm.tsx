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
import { useCommercialDefaultsOptions } from "../../hooks/useCommercialDefaultsOptions";

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
  const { t } = useTranslation("customer");
  const commercialOptions = useCommercialDefaultsOptions();
  const _submitLabel = submitLabel ?? t("form.createTitle");
  const _submittingLabel = submittingLabel ?? t("form.creating");

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
      default_currency_code: initialValues?.default_currency_code ?? "",
      payment_terms_template_id: initialValues?.payment_terms_template_id ?? "",
    },
    mode: "onSubmit",
  });

  function translateFormMessage(message: string): string {
    return t(message.startsWith("customer.") ? message.slice("customer.".length) : message);
  }

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
          <FieldLabel htmlFor="company_name">{t("form.companyName")} *</FieldLabel>
          <Input
            id="company_name"
            {...register("company_name")}
            maxLength={200}
            aria-invalid={!!errors.company_name}
          />
          <FieldError
            errors={errors.company_name ? [{ message: translateFormMessage(errors.company_name.message!) }] : []}
          />
        </Field>

        <Field>
          <FieldLabel htmlFor="business_number">{t("form.businessNumber")} *</FieldLabel>
          <Input
            id="business_number"
            {...register("business_number")}
            maxLength={20}
            aria-invalid={!!errors.business_number}
          />
          <FieldError
            errors={errors.business_number ? [{ message: translateFormMessage(errors.business_number.message!) }] : []}
          />
        </Field>
      </div>

      <Field>
        <FieldLabel htmlFor="billing_address">{t("form.billingAddress")}</FieldLabel>
        <Input
          id="billing_address"
          {...register("billing_address")}
          maxLength={500}
        />
      </Field>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="contact_name">{t("form.contactName")} *</FieldLabel>
          <Input
            id="contact_name"
            {...register("contact_name")}
            maxLength={100}
            aria-invalid={!!errors.contact_name}
          />
          <FieldError
            errors={errors.contact_name ? [{ message: translateFormMessage(errors.contact_name.message!) }] : []}
          />
        </Field>

        <Field>
          <FieldLabel htmlFor="contact_phone">{t("form.contactPhone")} *</FieldLabel>
          <Input
            id="contact_phone"
            {...register("contact_phone")}
            maxLength={30}
            aria-invalid={!!errors.contact_phone}
          />
          <FieldError
            errors={errors.contact_phone ? [{ message: translateFormMessage(errors.contact_phone.message!) }] : []}
          />
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="contact_email">{t("form.contactEmail")} *</FieldLabel>
          <Input
            id="contact_email"
            type="email"
            {...register("contact_email")}
            maxLength={254}
            aria-invalid={!!errors.contact_email}
          />
          <FieldError
            errors={errors.contact_email ? [{ message: translateFormMessage(errors.contact_email.message!) }] : []}
          />
        </Field>

        <Field>
          <FieldLabel htmlFor="credit_limit">{t("form.creditLimit")}</FieldLabel>
          <Input
            id="credit_limit"
            type="number"
            step="0.01"
            min="0"
            {...register("credit_limit")}
            aria-invalid={!!errors.credit_limit}
          />
          <FieldError
            errors={errors.credit_limit ? [{ message: translateFormMessage(errors.credit_limit.message!) }] : []}
          />
        </Field>
      </div>

      <fieldset className="space-y-3 rounded-lg border border-border/70 p-4">
        <legend className="px-1 text-sm font-semibold">{t("form.commercialDefaults")}</legend>
        <div className="grid gap-5 sm:grid-cols-2">
          <Field>
            <FieldLabel htmlFor="default_currency_code">{t("form.defaultCurrency")}</FieldLabel>
            <select
              id="default_currency_code"
              className="h-8 w-full rounded-lg border border-input bg-background px-2.5 py-1 text-sm"
              disabled={submitting || commercialOptions.loading}
              {...register("default_currency_code")}
            >
              <option value="">{t("form.useTenantDefault")}</option>
              {initialValues?.default_currency_code && !commercialOptions.currencies.some((currency) => currency.code === initialValues.default_currency_code) ? (
                <option value={initialValues.default_currency_code}>{initialValues.default_currency_code}</option>
              ) : null}
              {commercialOptions.currencies.map((currency) => (
                <option key={currency.id} value={currency.code}>
                  {currency.code}{currency.is_base_currency ? ` (${t("form.baseCurrency")})` : ""}
                </option>
              ))}
            </select>
          </Field>

          <Field>
            <FieldLabel htmlFor="payment_terms_template_id">{t("form.paymentTerms")}</FieldLabel>
            <select
              id="payment_terms_template_id"
              className="h-8 w-full rounded-lg border border-input bg-background px-2.5 py-1 text-sm"
              disabled={submitting || commercialOptions.loading}
              {...register("payment_terms_template_id")}
            >
              <option value="">{t("form.useTenantDefault")}</option>
              {initialValues?.payment_terms_template_id && !commercialOptions.paymentTerms.some((template) => template.id === initialValues.payment_terms_template_id) ? (
                <option value={initialValues.payment_terms_template_id}>{initialValues.payment_terms_template_id}</option>
              ) : null}
              {commercialOptions.paymentTerms.map((template) => (
                <option key={template.id} value={template.id}>{template.template_name}</option>
              ))}
            </select>
          </Field>
        </div>
        {commercialOptions.error ? <p className="text-sm text-destructive">{commercialOptions.error}</p> : null}
      </fieldset>

      <Button type="submit" disabled={submitting}>
        {submitting ? _submittingLabel : _submitLabel}
      </Button>
    </form>
  );
}
