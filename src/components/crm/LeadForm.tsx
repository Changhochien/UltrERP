import { useEffect } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, type Resolver } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { Button } from "../ui/button";
import { Field, FieldError, FieldLabel } from "../ui/field";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import { useCRMSetupBundle } from "../../domain/crm/hooks/useCRMSetupBundle";
import {
  leadFormSchema,
  type LeadFormValues,
  toLeadCreatePayload,
} from "../../lib/schemas/lead.schema";

const SELECT_CLASS_NAME =
  "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

export interface LeadFormProps {
  onSubmit: (payload: ReturnType<typeof toLeadCreatePayload>) => void;
  submitting?: boolean;
  disabled?: boolean;
  serverErrors?: Array<{ field: string; message: string }>;
  initialValues?: Partial<LeadFormValues>;
  submitLabel?: string;
  submittingLabel?: string;
}

export function LeadForm({
  onSubmit,
  submitting,
  disabled,
  serverErrors,
  initialValues,
  submitLabel,
  submittingLabel,
}: LeadFormProps) {
  const { t } = useTranslation("common");
  const resolvedSubmitLabel = submitLabel ?? t("crm.form.createTitle");
  const resolvedSubmittingLabel = submittingLabel ?? t("crm.form.creating");
  const { territoryOptions } = useCRMSetupBundle();

  const buildDefaultValues = (): LeadFormValues => ({
    lead_name: initialValues?.lead_name ?? "",
    company_name: initialValues?.company_name ?? "",
    email_id: initialValues?.email_id ?? "",
    phone: initialValues?.phone ?? "",
    mobile_no: initialValues?.mobile_no ?? "",
    territory: initialValues?.territory ?? "",
    lead_owner: initialValues?.lead_owner ?? "",
    source: initialValues?.source ?? "",
    qualification_status: initialValues?.qualification_status ?? "in_process",
    qualified_by: initialValues?.qualified_by ?? "",
    annual_revenue: initialValues?.annual_revenue ?? "",
    no_of_employees: initialValues?.no_of_employees ?? "",
    industry: initialValues?.industry ?? "",
    market_segment: initialValues?.market_segment ?? "",
    utm_source: initialValues?.utm_source ?? "",
    utm_medium: initialValues?.utm_medium ?? "",
    utm_campaign: initialValues?.utm_campaign ?? "",
    utm_content: initialValues?.utm_content ?? "",
    notes: initialValues?.notes ?? "",
  });

  const {
    register,
    handleSubmit,
    reset,
    setError,
    watch,
    formState: { errors },
  } = useForm<LeadFormValues>({
    resolver: zodResolver(leadFormSchema as never) as Resolver<LeadFormValues>,
    defaultValues: buildDefaultValues(),
    mode: "onSubmit",
  });

  useEffect(() => {
    reset(buildDefaultValues());
  }, [initialValues, reset]);

  useEffect(() => {
    if (!serverErrors?.length) {
      return;
    }
    for (const error of serverErrors) {
      if (error.field) {
        setError(error.field as keyof LeadFormValues, { message: error.message });
      }
    }
  }, [serverErrors, setError]);

  const generalErrors = serverErrors?.filter((error) => !error.field) ?? [];
  const currentTerritory = watch("territory");

  return (
    <form
      className="flex flex-col gap-5"
      noValidate
      onSubmit={handleSubmit((values) => {
        onSubmit(toLeadCreatePayload(values));
      })}
    >
      {generalErrors.length > 0 ? (
        <div
          className="rounded-xl border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive"
          role="alert"
        >
          {generalErrors.map((error) => (
            <p key={error.message}>{error.message}</p>
          ))}
        </div>
      ) : null}

      <div className="grid gap-5 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="lead_name">{t("crm.form.leadName")} *</FieldLabel>
          <Input id="lead_name" {...register("lead_name")} maxLength={140} aria-invalid={!!errors.lead_name} />
          <FieldError errors={errors.lead_name ? [{ message: t(errors.lead_name.message!) }] : []} />
        </Field>
        <Field>
          <FieldLabel htmlFor="company_name">{t("crm.form.companyName")}</FieldLabel>
          <Input id="company_name" {...register("company_name")} maxLength={200} aria-invalid={!!errors.company_name} />
          <FieldError errors={errors.company_name ? [{ message: t(errors.company_name.message!) }] : []} />
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="email_id">{t("crm.form.email")}</FieldLabel>
          <Input id="email_id" type="email" {...register("email_id")} maxLength={254} aria-invalid={!!errors.email_id} />
          <FieldError errors={errors.email_id ? [{ message: t(errors.email_id.message!) }] : []} />
        </Field>
        <Field>
          <FieldLabel htmlFor="lead_owner">{t("crm.form.owner")}</FieldLabel>
          <Input id="lead_owner" {...register("lead_owner")} maxLength={120} aria-invalid={!!errors.lead_owner} />
          <FieldError errors={errors.lead_owner ? [{ message: t(errors.lead_owner.message!) }] : []} />
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="phone">{t("crm.form.phone")}</FieldLabel>
          <Input id="phone" {...register("phone")} maxLength={30} aria-invalid={!!errors.phone} />
          <FieldError errors={errors.phone ? [{ message: t(errors.phone.message!) }] : []} />
        </Field>
        <Field>
          <FieldLabel htmlFor="mobile_no">{t("crm.form.mobile")}</FieldLabel>
          <Input id="mobile_no" {...register("mobile_no")} maxLength={30} aria-invalid={!!errors.mobile_no} />
          <FieldError errors={errors.mobile_no ? [{ message: t(errors.mobile_no.message!) }] : []} />
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="territory">{t("crm.form.territory")}</FieldLabel>
          <select id="territory" {...register("territory")} className={SELECT_CLASS_NAME} aria-invalid={!!errors.territory}>
            <option value="">{t("crm.setup.selectPlaceholder")}</option>
            {currentTerritory && !territoryOptions.some((option) => option.name === currentTerritory) ? (
              <option value={currentTerritory}>{currentTerritory}</option>
            ) : null}
            {territoryOptions.map((option) => (
              <option key={option.id} value={option.name}>{option.name}</option>
            ))}
          </select>
          <FieldError errors={errors.territory ? [{ message: t(errors.territory.message!) }] : []} />
        </Field>
        <Field>
          <FieldLabel htmlFor="source">{t("crm.form.source")}</FieldLabel>
          <Input id="source" {...register("source")} maxLength={120} aria-invalid={!!errors.source} />
          <FieldError errors={errors.source ? [{ message: t(errors.source.message!) }] : []} />
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="qualification_status">{t("crm.form.qualificationStatus")}</FieldLabel>
          <select id="qualification_status" {...register("qualification_status")} className={SELECT_CLASS_NAME}>
            <option value="unqualified">{t("crm.qualificationValues.unqualified")}</option>
            <option value="in_process">{t("crm.qualificationValues.in_process")}</option>
            <option value="qualified">{t("crm.qualificationValues.qualified")}</option>
          </select>
        </Field>
        <Field>
          <FieldLabel htmlFor="qualified_by">{t("crm.form.qualifiedBy")}</FieldLabel>
          <Input id="qualified_by" {...register("qualified_by")} maxLength={120} aria-invalid={!!errors.qualified_by} />
          <FieldError errors={errors.qualified_by ? [{ message: t(errors.qualified_by.message!) }] : []} />
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="annual_revenue">{t("crm.form.annualRevenue")}</FieldLabel>
          <Input id="annual_revenue" type="number" min="0" step="0.01" {...register("annual_revenue")} aria-invalid={!!errors.annual_revenue} />
          <FieldError errors={errors.annual_revenue ? [{ message: t(errors.annual_revenue.message!) }] : []} />
        </Field>
        <Field>
          <FieldLabel htmlFor="no_of_employees">{t("crm.form.employeeCount")}</FieldLabel>
          <Input id="no_of_employees" type="number" min="0" step="1" {...register("no_of_employees")} aria-invalid={!!errors.no_of_employees} />
          <FieldError errors={errors.no_of_employees ? [{ message: t(errors.no_of_employees.message!) }] : []} />
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="industry">{t("crm.form.industry")}</FieldLabel>
          <Input id="industry" {...register("industry")} maxLength={120} aria-invalid={!!errors.industry} />
          <FieldError errors={errors.industry ? [{ message: t(errors.industry.message!) }] : []} />
        </Field>
        <Field>
          <FieldLabel htmlFor="market_segment">{t("crm.form.marketSegment")}</FieldLabel>
          <Input id="market_segment" {...register("market_segment")} maxLength={120} aria-invalid={!!errors.market_segment} />
          <FieldError errors={errors.market_segment ? [{ message: t(errors.market_segment.message!) }] : []} />
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="utm_source">{t("crm.form.utmSource")}</FieldLabel>
          <Input id="utm_source" {...register("utm_source")} maxLength={120} aria-invalid={!!errors.utm_source} />
          <FieldError errors={errors.utm_source ? [{ message: t(errors.utm_source.message!) }] : []} />
        </Field>
        <Field>
          <FieldLabel htmlFor="utm_medium">{t("crm.form.utmMedium")}</FieldLabel>
          <Input id="utm_medium" {...register("utm_medium")} maxLength={120} aria-invalid={!!errors.utm_medium} />
          <FieldError errors={errors.utm_medium ? [{ message: t(errors.utm_medium.message!) }] : []} />
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="utm_campaign">{t("crm.form.utmCampaign")}</FieldLabel>
          <Input id="utm_campaign" {...register("utm_campaign")} maxLength={120} aria-invalid={!!errors.utm_campaign} />
          <FieldError errors={errors.utm_campaign ? [{ message: t(errors.utm_campaign.message!) }] : []} />
        </Field>
        <Field>
          <FieldLabel htmlFor="utm_content">{t("crm.form.utmContent")}</FieldLabel>
          <Input id="utm_content" {...register("utm_content")} maxLength={200} aria-invalid={!!errors.utm_content} />
          <FieldError errors={errors.utm_content ? [{ message: t(errors.utm_content.message!) }] : []} />
        </Field>
      </div>

      <Field>
        <FieldLabel htmlFor="notes">{t("crm.form.notes")}</FieldLabel>
        <Textarea id="notes" {...register("notes")} maxLength={4000} aria-invalid={!!errors.notes} />
        <FieldError errors={errors.notes ? [{ message: t(errors.notes.message!) }] : []} />
      </Field>

      <Button type="submit" disabled={submitting || disabled}>
        {submitting ? resolvedSubmittingLabel : resolvedSubmitLabel}
      </Button>
    </form>
  );
}

export default LeadForm;
