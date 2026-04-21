import { useEffect, useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useFieldArray, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";

import type { CustomerSummary } from "../../domain/customers/types";
import type { LeadSummary } from "../../domain/crm/types";
import { listCustomers } from "../../lib/api/customers";
import { listLeads } from "../../lib/api/crm";
import {
  opportunityFormSchema,
  type OpportunityFormValues,
  toOpportunityCreatePayload,
} from "../../lib/schemas/opportunity.schema";
import { Button } from "../ui/button";
import { Field, FieldError, FieldLabel } from "../ui/field";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";

const SELECT_CLASS_NAME =
  "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

function defaultValues(initialValues?: Partial<OpportunityFormValues>): OpportunityFormValues {
  return {
    opportunity_title: initialValues?.opportunity_title ?? "",
    opportunity_from: initialValues?.opportunity_from ?? "prospect",
    party_name: initialValues?.party_name ?? "",
    sales_stage: initialValues?.sales_stage ?? "qualification",
    probability: initialValues?.probability ?? "0",
    expected_closing: initialValues?.expected_closing ?? "",
    currency: initialValues?.currency ?? "TWD",
    opportunity_amount: initialValues?.opportunity_amount ?? "",
    opportunity_owner: initialValues?.opportunity_owner ?? "",
    territory: initialValues?.territory ?? "",
    customer_group: initialValues?.customer_group ?? "",
    contact_person: initialValues?.contact_person ?? "",
    contact_email: initialValues?.contact_email ?? "",
    contact_mobile: initialValues?.contact_mobile ?? "",
    job_title: initialValues?.job_title ?? "",
    utm_source: initialValues?.utm_source ?? "",
    utm_medium: initialValues?.utm_medium ?? "",
    utm_campaign: initialValues?.utm_campaign ?? "",
    utm_content: initialValues?.utm_content ?? "",
    items: initialValues?.items ?? [],
    notes: initialValues?.notes ?? "",
  };
}

function partyLabel(
  currentPartyType: OpportunityFormValues["opportunity_from"],
  leadOptions: LeadSummary[],
  customerOptions: CustomerSummary[],
  value: string,
) {
  if (!value) {
    return "";
  }
  if (currentPartyType === "lead") {
    const match = leadOptions.find((lead) => lead.id === value);
    return match ? `${match.lead_name} · ${match.company_name || match.id}` : value;
  }
  if (currentPartyType === "customer") {
    const match = customerOptions.find((customer) => customer.id === value);
    return match ? match.company_name : value;
  }
  return value;
}

export interface OpportunityFormProps {
  onSubmit: (payload: ReturnType<typeof toOpportunityCreatePayload>) => void;
  submitting?: boolean;
  disabled?: boolean;
  serverErrors?: Array<{ field: string; message: string }>;
  initialValues?: Partial<OpportunityFormValues>;
  submitLabel?: string;
  submittingLabel?: string;
}

export function OpportunityForm({
  onSubmit,
  submitting,
  disabled,
  serverErrors,
  initialValues,
  submitLabel,
  submittingLabel,
}: OpportunityFormProps) {
  const { t } = useTranslation("common");
  const resolvedSubmitLabel = submitLabel ?? t("crm.opportunities.form.createTitle");
  const resolvedSubmittingLabel = submittingLabel ?? t("crm.opportunities.form.creating");
  const [leadOptions, setLeadOptions] = useState<LeadSummary[]>([]);
  const [customerOptions, setCustomerOptions] = useState<CustomerSummary[]>([]);

  const {
    register,
    control,
    handleSubmit,
    reset,
    setError,
    watch,
    formState: { errors },
  } = useForm<OpportunityFormValues>({
    resolver: zodResolver(opportunityFormSchema),
    defaultValues: defaultValues(initialValues),
    mode: "onSubmit",
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: "items",
  });

  const currentPartyType = watch("opportunity_from");
  const currentPartyValue = watch("party_name");

  useEffect(() => {
    reset(defaultValues(initialValues));
  }, [initialValues, reset]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      listLeads({ page: 1, page_size: 100 }).catch(() => ({ items: [] })),
      listCustomers({ page: 1, page_size: 100 }),
    ]).then(([leadResponse, customerResponse]) => {
      if (!cancelled) {
        setLeadOptions(leadResponse.items ?? []);
        setCustomerOptions(customerResponse.items ?? []);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!serverErrors?.length) {
      return;
    }
    for (const error of serverErrors) {
      if (error.field) {
        setError(error.field as never, { message: error.message });
      }
    }
  }, [serverErrors, setError]);

  const generalErrors = serverErrors?.filter((error) => !error.field) ?? [];

  const partyOptions = useMemo(() => {
    if (currentPartyType === "lead") {
      return leadOptions.map((lead) => ({
        value: lead.id,
        label: `${lead.lead_name} · ${lead.company_name || lead.id}`,
      }));
    }
    if (currentPartyType === "customer") {
      return customerOptions.map((customer) => ({
        value: customer.id,
        label: customer.company_name,
      }));
    }
    return [];
  }, [currentPartyType, customerOptions, leadOptions]);

  const currentPartyLabel = partyLabel(currentPartyType, leadOptions, customerOptions, currentPartyValue);

  return (
    <form
      className="flex flex-col gap-5"
      noValidate
      onSubmit={handleSubmit((values) => onSubmit(toOpportunityCreatePayload(values)))}
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
          <FieldLabel htmlFor="opportunity_title">{t("crm.opportunities.form.title")} *</FieldLabel>
          <Input id="opportunity_title" {...register("opportunity_title")} maxLength={200} aria-invalid={!!errors.opportunity_title} />
          <FieldError errors={errors.opportunity_title ? [{ message: t(errors.opportunity_title.message!) }] : []} />
        </Field>
        <Field>
          <FieldLabel htmlFor="opportunity_from">{t("crm.opportunities.form.partyType")}</FieldLabel>
          <select id="opportunity_from" {...register("opportunity_from")} className={SELECT_CLASS_NAME}>
            <option value="lead">{t("crm.opportunities.partyValues.lead")}</option>
            <option value="customer">{t("crm.opportunities.partyValues.customer")}</option>
            <option value="prospect">{t("crm.opportunities.partyValues.prospect")}</option>
          </select>
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="party_name">{t("crm.opportunities.form.partyName")}</FieldLabel>
          {currentPartyType === "prospect" ? (
            <Input id="party_name" {...register("party_name")} maxLength={200} aria-invalid={!!errors.party_name} />
          ) : (
            <select id="party_name" {...register("party_name")} className={SELECT_CLASS_NAME}>
              <option value="">{t("crm.opportunities.form.selectParty")}</option>
              {currentPartyValue && !partyOptions.some((option) => option.value === currentPartyValue) ? (
                <option value={currentPartyValue}>{currentPartyLabel}</option>
              ) : null}
              {partyOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          )}
          <FieldError errors={errors.party_name ? [{ message: t(errors.party_name.message!) }] : []} />
        </Field>
        <Field>
          <FieldLabel htmlFor="sales_stage">{t("crm.opportunities.form.salesStage")}</FieldLabel>
          <Input id="sales_stage" {...register("sales_stage")} maxLength={120} aria-invalid={!!errors.sales_stage} />
          <FieldError errors={errors.sales_stage ? [{ message: t(errors.sales_stage.message!) }] : []} />
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-4">
        <Field>
          <FieldLabel htmlFor="probability">{t("crm.opportunities.form.probability")}</FieldLabel>
          <Input id="probability" type="number" min="0" max="100" step="1" {...register("probability")} aria-invalid={!!errors.probability} />
          <FieldError errors={errors.probability ? [{ message: t(errors.probability.message!) }] : []} />
        </Field>
        <Field>
          <FieldLabel htmlFor="expected_closing">{t("crm.opportunities.form.expectedClosing")}</FieldLabel>
          <Input id="expected_closing" type="date" {...register("expected_closing")} aria-invalid={!!errors.expected_closing} />
          <FieldError errors={errors.expected_closing ? [{ message: t(errors.expected_closing.message!) }] : []} />
        </Field>
        <Field>
          <FieldLabel htmlFor="currency">{t("crm.opportunities.form.currency")}</FieldLabel>
          <Input id="currency" {...register("currency")} maxLength={3} aria-invalid={!!errors.currency} />
          <FieldError errors={errors.currency ? [{ message: t(errors.currency.message!) }] : []} />
        </Field>
        <Field>
          <FieldLabel htmlFor="opportunity_amount">{t("crm.opportunities.form.amount")}</FieldLabel>
          <Input id="opportunity_amount" type="number" min="0" step="0.01" {...register("opportunity_amount")} aria-invalid={!!errors.opportunity_amount} />
          <FieldError errors={errors.opportunity_amount ? [{ message: t(errors.opportunity_amount.message!) }] : []} />
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="opportunity_owner">{t("crm.opportunities.form.owner")}</FieldLabel>
          <Input id="opportunity_owner" {...register("opportunity_owner")} maxLength={120} aria-invalid={!!errors.opportunity_owner} />
          <FieldError errors={errors.opportunity_owner ? [{ message: t(errors.opportunity_owner.message!) }] : []} />
        </Field>
        <Field>
          <FieldLabel htmlFor="territory">{t("crm.opportunities.form.territory")}</FieldLabel>
          <Input id="territory" {...register("territory")} maxLength={120} aria-invalid={!!errors.territory} />
          <FieldError errors={errors.territory ? [{ message: t(errors.territory.message!) }] : []} />
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="customer_group">{t("crm.opportunities.form.customerGroup")}</FieldLabel>
          <Input id="customer_group" {...register("customer_group")} maxLength={120} aria-invalid={!!errors.customer_group} />
          <FieldError errors={errors.customer_group ? [{ message: t(errors.customer_group.message!) }] : []} />
        </Field>
        <Field>
          <FieldLabel htmlFor="job_title">{t("crm.opportunities.form.jobTitle")}</FieldLabel>
          <Input id="job_title" {...register("job_title")} maxLength={120} aria-invalid={!!errors.job_title} />
          <FieldError errors={errors.job_title ? [{ message: t(errors.job_title.message!) }] : []} />
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-3">
        <Field>
          <FieldLabel htmlFor="contact_person">{t("crm.opportunities.form.contactPerson")}</FieldLabel>
          <Input id="contact_person" {...register("contact_person")} maxLength={120} aria-invalid={!!errors.contact_person} />
          <FieldError errors={errors.contact_person ? [{ message: t(errors.contact_person.message!) }] : []} />
        </Field>
        <Field>
          <FieldLabel htmlFor="contact_email">{t("crm.opportunities.form.contactEmail")}</FieldLabel>
          <Input id="contact_email" type="email" {...register("contact_email")} maxLength={254} aria-invalid={!!errors.contact_email} />
          <FieldError errors={errors.contact_email ? [{ message: t(errors.contact_email.message!) }] : []} />
        </Field>
        <Field>
          <FieldLabel htmlFor="contact_mobile">{t("crm.opportunities.form.contactMobile")}</FieldLabel>
          <Input id="contact_mobile" {...register("contact_mobile")} maxLength={30} aria-invalid={!!errors.contact_mobile} />
          <FieldError errors={errors.contact_mobile ? [{ message: t(errors.contact_mobile.message!) }] : []} />
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="utm_source">{t("crm.opportunities.form.utmSource")}</FieldLabel>
          <Input id="utm_source" {...register("utm_source")} maxLength={120} aria-invalid={!!errors.utm_source} />
          <FieldError errors={errors.utm_source ? [{ message: t(errors.utm_source.message!) }] : []} />
        </Field>
        <Field>
          <FieldLabel htmlFor="utm_medium">{t("crm.opportunities.form.utmMedium")}</FieldLabel>
          <Input id="utm_medium" {...register("utm_medium")} maxLength={120} aria-invalid={!!errors.utm_medium} />
          <FieldError errors={errors.utm_medium ? [{ message: t(errors.utm_medium.message!) }] : []} />
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="utm_campaign">{t("crm.opportunities.form.utmCampaign")}</FieldLabel>
          <Input id="utm_campaign" {...register("utm_campaign")} maxLength={120} aria-invalid={!!errors.utm_campaign} />
          <FieldError errors={errors.utm_campaign ? [{ message: t(errors.utm_campaign.message!) }] : []} />
        </Field>
        <Field>
          <FieldLabel htmlFor="utm_content">{t("crm.opportunities.form.utmContent")}</FieldLabel>
          <Input id="utm_content" {...register("utm_content")} maxLength={200} aria-invalid={!!errors.utm_content} />
          <FieldError errors={errors.utm_content ? [{ message: t(errors.utm_content.message!) }] : []} />
        </Field>
      </div>

      <div className="space-y-4 rounded-xl border border-border/70 bg-muted/20 p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold">{t("crm.opportunities.form.itemsTitle")}</h3>
            <p className="text-sm text-muted-foreground">{t("crm.opportunities.form.itemsDescription")}</p>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => append({ item_name: "", item_code: "", description: "", quantity: "1", unit_price: "0.00" })}
          >
            {t("crm.opportunities.form.addItem")}
          </Button>
        </div>

        {fields.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("crm.opportunities.form.itemsEmpty")}</p>
        ) : null}

        {fields.map((field, index) => (
          <div key={field.id} className="space-y-4 rounded-xl border border-border/70 bg-background px-4 py-4">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Field className="lg:col-span-2">
                <FieldLabel htmlFor={`items.${index}.item_name`}>{t("crm.opportunities.form.itemName")}</FieldLabel>
                <Input id={`items.${index}.item_name`} {...register(`items.${index}.item_name`)} aria-invalid={!!errors.items?.[index]?.item_name} />
                <FieldError errors={errors.items?.[index]?.item_name ? [{ message: t(errors.items[index]!.item_name!.message!) }] : []} />
              </Field>
              <Field>
                <FieldLabel htmlFor={`items.${index}.quantity`}>{t("crm.opportunities.form.quantity")}</FieldLabel>
                <Input id={`items.${index}.quantity`} type="number" min="0.01" step="0.01" {...register(`items.${index}.quantity`)} aria-invalid={!!errors.items?.[index]?.quantity} />
                <FieldError errors={errors.items?.[index]?.quantity ? [{ message: t(errors.items[index]!.quantity!.message!) }] : []} />
              </Field>
              <Field>
                <FieldLabel htmlFor={`items.${index}.unit_price`}>{t("crm.opportunities.form.unitPrice")}</FieldLabel>
                <Input id={`items.${index}.unit_price`} type="number" min="0" step="0.01" {...register(`items.${index}.unit_price`)} aria-invalid={!!errors.items?.[index]?.unit_price} />
                <FieldError errors={errors.items?.[index]?.unit_price ? [{ message: t(errors.items[index]!.unit_price!.message!) }] : []} />
              </Field>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <Field>
                <FieldLabel htmlFor={`items.${index}.item_code`}>{t("crm.opportunities.form.itemCode")}</FieldLabel>
                <Input id={`items.${index}.item_code`} {...register(`items.${index}.item_code`)} aria-invalid={!!errors.items?.[index]?.item_code} />
                <FieldError errors={errors.items?.[index]?.item_code ? [{ message: t(errors.items[index]!.item_code!.message!) }] : []} />
              </Field>
              <Field>
                <FieldLabel htmlFor={`items.${index}.description`}>{t("crm.opportunities.form.itemDescription")}</FieldLabel>
                <Input id={`items.${index}.description`} {...register(`items.${index}.description`)} aria-invalid={!!errors.items?.[index]?.description} />
                <FieldError errors={errors.items?.[index]?.description ? [{ message: t(errors.items[index]!.description!.message!) }] : []} />
              </Field>
            </div>

            <div className="flex justify-end">
              <Button type="button" variant="ghost" size="sm" onClick={() => remove(index)}>
                {t("crm.opportunities.form.removeItem")}
              </Button>
            </div>
          </div>
        ))}
      </div>

      <Field>
        <FieldLabel htmlFor="notes">{t("crm.opportunities.form.notes")}</FieldLabel>
        <Textarea id="notes" {...register("notes")} maxLength={4000} aria-invalid={!!errors.notes} />
        <FieldError errors={errors.notes ? [{ message: t(errors.notes.message!) }] : []} />
      </Field>

      <Button type="submit" disabled={submitting || disabled}>
        {submitting ? resolvedSubmittingLabel : resolvedSubmitLabel}
      </Button>
    </form>
  );
}

export default OpportunityForm;