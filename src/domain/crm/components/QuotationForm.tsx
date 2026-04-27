import { useEffect, useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useFieldArray, useForm, type Resolver } from "react-hook-form";
import { useTranslation } from "react-i18next";

import type { CustomerSummary } from "@/domain/customers/types";
import type { LeadSummary } from "@/domain/crm/types";
import { useCRMSetupBundle } from "@/domain/crm/hooks/useCRMSetupBundle";
import { listCustomers } from "@/lib/api/customers";
import { listLeads } from "@/lib/api/crm";
import {
  quotationFormSchema,
  toQuotationCreatePayload,
  type QuotationFormValues,
} from "@/lib/schemas/quotation.schema";
import { Button } from "@/components/ui/button";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const SELECT_CLASS_NAME =
  "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

const DEFAULT_COMPANY = "UltrERP Taiwan";

function formatDateInput(value: Date): string {
  return value.toISOString().slice(0, 10);
}

function addDays(value: Date, days: number): Date {
  const next = new Date(value);
  next.setDate(next.getDate() + days);
  return next;
}

function blankItem() {
  return {
    item_name: "",
    item_code: "",
    description: "",
    quantity: "1",
    unit_price: "",
  };
}

function defaultValues(initialValues?: Partial<QuotationFormValues>): QuotationFormValues {
  const today = formatDateInput(new Date());
  const defaultValidTill = formatDateInput(addDays(new Date(), 30));

  return {
    quotation_to: initialValues?.quotation_to ?? "prospect",
    party_name: initialValues?.party_name ?? "",
    transaction_date: initialValues?.transaction_date ?? today,
    valid_till: initialValues?.valid_till ?? defaultValidTill,
    company: initialValues?.company ?? DEFAULT_COMPANY,
    currency: initialValues?.currency ?? "TWD",
    contact_person: initialValues?.contact_person ?? "",
    contact_email: initialValues?.contact_email ?? "",
    contact_mobile: initialValues?.contact_mobile ?? "",
    job_title: initialValues?.job_title ?? "",
    territory: initialValues?.territory ?? "",
    customer_group: initialValues?.customer_group ?? "",
    billing_address: initialValues?.billing_address ?? "",
    shipping_address: initialValues?.shipping_address ?? "",
    utm_source: initialValues?.utm_source ?? "",
    utm_medium: initialValues?.utm_medium ?? "",
    utm_campaign: initialValues?.utm_campaign ?? "",
    utm_content: initialValues?.utm_content ?? "",
    opportunity_id: initialValues?.opportunity_id ?? "",
    items: initialValues?.items?.length ? initialValues.items : [blankItem()],
    taxes: initialValues?.taxes ?? [],
    terms_template: initialValues?.terms_template ?? "",
    terms_and_conditions: initialValues?.terms_and_conditions ?? "",
    auto_repeat_enabled: initialValues?.auto_repeat_enabled ?? false,
    auto_repeat_frequency: initialValues?.auto_repeat_frequency ?? "",
    auto_repeat_until: initialValues?.auto_repeat_until ?? "",
    notes: initialValues?.notes ?? "",
  };
}

function partyLabel(
  currentPartyType: QuotationFormValues["quotation_to"],
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

export interface QuotationFormProps {
  onSubmit: (payload: ReturnType<typeof toQuotationCreatePayload>) => void;
  submitting?: boolean;
  disabled?: boolean;
  serverErrors?: Array<{ field: string; message: string }>;
  initialValues?: Partial<QuotationFormValues>;
  submitLabel?: string;
  submittingLabel?: string;
}

export function QuotationForm({
  onSubmit,
  submitting,
  disabled,
  serverErrors,
  initialValues,
  submitLabel,
  submittingLabel,
}: QuotationFormProps) {
  const { t } = useTranslation("crm");
  const resolvedSubmitLabel = submitLabel ?? t("quotations.form.createTitle");
  const resolvedSubmittingLabel = submittingLabel ?? t("quotations.form.creating");
  const [leadOptions, setLeadOptions] = useState<LeadSummary[]>([]);
  const [customerOptions, setCustomerOptions] = useState<CustomerSummary[]>([]);
  const { data: setupBundle, territoryOptions, customerGroupOptions } = useCRMSetupBundle();

  const {
    register,
    control,
    getValues,
    handleSubmit,
    reset,
    setError,
    setValue,
    watch,
    formState: { errors },
  } = useForm<QuotationFormValues>({
    resolver: zodResolver(quotationFormSchema as never) as Resolver<QuotationFormValues>,
    defaultValues: defaultValues(initialValues),
    mode: "onSubmit",
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: "items",
  });

  const {
    fields: taxFields,
    append: appendTax,
    remove: removeTax,
  } = useFieldArray({
    control,
    name: "taxes",
  });

  const currentPartyType = watch("quotation_to");
  const currentPartyValue = watch("party_name");
  const currentItems = watch("items");
  const currentTaxes = watch("taxes");
  const autoRepeatEnabled = watch("auto_repeat_enabled");
  const currentTerritory = watch("territory");
  const currentCustomerGroup = watch("customer_group");

  useEffect(() => {
    reset(defaultValues(initialValues));
  }, [initialValues, reset]);

  useEffect(() => {
    if (initialValues?.valid_till) {
      return;
    }
    const fallbackValidTill = formatDateInput(addDays(new Date(), 30));
    const currentValidTill = getValues("valid_till");
    if (!currentValidTill || currentValidTill === fallbackValidTill) {
      setValue(
        "valid_till",
        formatDateInput(addDays(new Date(), setupBundle.settings.default_quotation_validity_days)),
      );
    }
  }, [getValues, initialValues?.valid_till, setValue, setupBundle.settings.default_quotation_validity_days]);

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
    let options: Array<{ value: string; label: string }> = [];
    if (currentPartyType === "lead") {
      options = leadOptions.map((lead) => ({
        value: lead.id,
        label: `${lead.lead_name} · ${lead.company_name || lead.id}`,
      }));
    } else if (currentPartyType === "customer") {
      options = customerOptions.map((customer) => ({
        value: customer.id,
        label: customer.company_name,
      }));
    }

    if (currentPartyValue && !options.some((option) => option.value === currentPartyValue)) {
      return [
        {
          value: currentPartyValue,
          label: partyLabel(currentPartyType, leadOptions, customerOptions, currentPartyValue),
        },
        ...options,
      ];
    }

    return options;
  }, [currentPartyType, currentPartyValue, customerOptions, leadOptions]);

  const subtotal = useMemo(() => {
    return currentItems.reduce((sum, item) => {
      const quantity = Number(item.quantity || 0);
      const unitPrice = Number(item.unit_price || 0);
      if (Number.isNaN(quantity) || Number.isNaN(unitPrice)) {
        return sum;
      }
      return sum + quantity * unitPrice;
    }, 0);
  }, [currentItems]);

  const totalTaxes = useMemo(() => {
    return currentTaxes.reduce((sum, tax) => {
      const explicitAmount = Number(tax.tax_amount || 0);
      if (tax.tax_amount?.trim()) {
        return sum + (Number.isNaN(explicitAmount) ? 0 : explicitAmount);
      }
      const rate = Number(tax.rate || 0);
      if (Number.isNaN(rate)) {
        return sum;
      }
      return sum + (subtotal * rate) / 100;
    }, 0);
  }, [currentTaxes, subtotal]);

  const grandTotal = subtotal + totalTaxes;

  return (
    <form className="space-y-6" onSubmit={handleSubmit((values) => onSubmit(toQuotationCreatePayload(values)))}>
      {generalErrors.length > 0 ? (
        <div className="rounded-xl border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive" role="alert">
          {generalErrors.map((error) => (
            <p key={error.message}>{error.message}</p>
          ))}
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="quotation_to">{t("quotations.form.partyType")}</FieldLabel>
          <select id="quotation_to" className={SELECT_CLASS_NAME} disabled={disabled} {...register("quotation_to")}>
            <option value="lead">{t("quotations.partyValues.lead")}</option>
            <option value="customer">{t("quotations.partyValues.customer")}</option>
            <option value="prospect">{t("quotations.partyValues.prospect")}</option>
          </select>
          <FieldError>{errors.quotation_to?.message ? t(errors.quotation_to.message) : undefined}</FieldError>
        </Field>

        {currentPartyType === "prospect" ? (
          <Field>
            <FieldLabel htmlFor="party_name">{t("quotations.form.partyNameRequiredLabel")}</FieldLabel>
            <Input id="party_name" disabled={disabled} {...register("party_name")} />
            <FieldError>{errors.party_name?.message ? t(errors.party_name.message) : undefined}</FieldError>
          </Field>
        ) : (
          <Field>
            <FieldLabel htmlFor="party_name">{t("quotations.form.partyNameRequiredLabel")}</FieldLabel>
            <select id="party_name" className={SELECT_CLASS_NAME} disabled={disabled} {...register("party_name")}>
              <option value="">{t("quotations.form.selectParty")}</option>
              {partyOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <FieldError>{errors.party_name?.message ? t(errors.party_name.message) : undefined}</FieldError>
          </Field>
        )}

        <Field>
          <FieldLabel htmlFor="company">{t("quotations.form.companyRequiredLabel")}</FieldLabel>
          <Input id="company" disabled={disabled} {...register("company")} />
          <FieldError>{errors.company?.message ? t(errors.company.message) : undefined}</FieldError>
        </Field>

        <Field>
          <FieldLabel htmlFor="currency">{t("quotations.form.currency")}</FieldLabel>
          <Input id="currency" disabled={disabled} {...register("currency")} />
          <FieldError>{errors.currency?.message ? t(errors.currency.message) : undefined}</FieldError>
        </Field>

        <Field>
          <FieldLabel htmlFor="transaction_date">{t("quotations.form.transactionDateRequiredLabel")}</FieldLabel>
          <Input id="transaction_date" type="date" disabled={disabled} {...register("transaction_date")} />
          <FieldError>{errors.transaction_date?.message ? t(errors.transaction_date.message) : undefined}</FieldError>
        </Field>

        <Field>
          <FieldLabel htmlFor="valid_till">{t("quotations.form.validTillRequiredLabel")}</FieldLabel>
          <Input id="valid_till" type="date" disabled={disabled} {...register("valid_till")} />
          <FieldError>{errors.valid_till?.message ? t(errors.valid_till.message) : undefined}</FieldError>
        </Field>

        <Field>
          <FieldLabel htmlFor="territory">{t("quotations.form.territory")}</FieldLabel>
          <select id="territory" className={SELECT_CLASS_NAME} disabled={disabled} {...register("territory")}>
            <option value="">{t("setup.selectPlaceholder")}</option>
            {currentTerritory && !territoryOptions.some((option) => option.name === currentTerritory) ? (
              <option value={currentTerritory}>{currentTerritory}</option>
            ) : null}
            {territoryOptions.map((option) => (
              <option key={option.id} value={option.name}>{option.name}</option>
            ))}
          </select>
          <FieldError>{errors.territory?.message ? t(errors.territory.message) : undefined}</FieldError>
        </Field>

        <Field>
          <FieldLabel htmlFor="customer_group">{t("quotations.form.customerGroup")}</FieldLabel>
          <select id="customer_group" className={SELECT_CLASS_NAME} disabled={disabled} {...register("customer_group")}>
            <option value="">{t("setup.selectPlaceholder")}</option>
            {currentCustomerGroup && !customerGroupOptions.some((option) => option.name === currentCustomerGroup) ? (
              <option value={currentCustomerGroup}>{currentCustomerGroup}</option>
            ) : null}
            {customerGroupOptions.map((option) => (
              <option key={option.id} value={option.name}>{option.name}</option>
            ))}
          </select>
          <FieldError>{errors.customer_group?.message ? t(errors.customer_group.message) : undefined}</FieldError>
        </Field>

        <Field>
          <FieldLabel htmlFor="contact_person">{t("quotations.form.contactPerson")}</FieldLabel>
          <Input id="contact_person" disabled={disabled} {...register("contact_person")} />
          <FieldError>{errors.contact_person?.message ? t(errors.contact_person.message) : undefined}</FieldError>
        </Field>

        <Field>
          <FieldLabel htmlFor="contact_email">{t("quotations.form.contactEmail")}</FieldLabel>
          <Input id="contact_email" disabled={disabled} {...register("contact_email")} />
          <FieldError>{errors.contact_email?.message ? t(errors.contact_email.message) : undefined}</FieldError>
        </Field>

        <Field>
          <FieldLabel htmlFor="contact_mobile">{t("quotations.form.contactMobile")}</FieldLabel>
          <Input id="contact_mobile" disabled={disabled} {...register("contact_mobile")} />
          <FieldError>{errors.contact_mobile?.message ? t(errors.contact_mobile.message) : undefined}</FieldError>
        </Field>

        <Field>
          <FieldLabel htmlFor="job_title">{t("quotations.form.jobTitle")}</FieldLabel>
          <Input id="job_title" disabled={disabled} {...register("job_title")} />
          <FieldError>{errors.job_title?.message ? t(errors.job_title.message) : undefined}</FieldError>
        </Field>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="billing_address">{t("quotations.form.billingAddress")}</FieldLabel>
          <Textarea id="billing_address" disabled={disabled} {...register("billing_address")} />
          <FieldError>{errors.billing_address?.message ? t(errors.billing_address.message) : undefined}</FieldError>
        </Field>
        <Field>
          <FieldLabel htmlFor="shipping_address">{t("quotations.form.shippingAddress")}</FieldLabel>
          <Textarea id="shipping_address" disabled={disabled} {...register("shipping_address")} />
          <FieldError>{errors.shipping_address?.message ? t(errors.shipping_address.message) : undefined}</FieldError>
        </Field>
      </div>

      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
        <Field>
          <FieldLabel htmlFor="utm_source">{t("quotations.form.utmSource")}</FieldLabel>
          <Input id="utm_source" disabled={disabled} {...register("utm_source")} />
          <FieldError>{errors.utm_source?.message ? t(errors.utm_source.message) : undefined}</FieldError>
        </Field>
        <Field>
          <FieldLabel htmlFor="utm_medium">{t("quotations.form.utmMedium")}</FieldLabel>
          <Input id="utm_medium" disabled={disabled} {...register("utm_medium")} />
          <FieldError>{errors.utm_medium?.message ? t(errors.utm_medium.message) : undefined}</FieldError>
        </Field>
        <Field>
          <FieldLabel htmlFor="utm_campaign">{t("quotations.form.utmCampaign")}</FieldLabel>
          <Input id="utm_campaign" disabled={disabled} {...register("utm_campaign")} />
          <FieldError>{errors.utm_campaign?.message ? t(errors.utm_campaign.message) : undefined}</FieldError>
        </Field>
        <Field>
          <FieldLabel htmlFor="utm_content">{t("quotations.form.utmContent")}</FieldLabel>
          <Input id="utm_content" disabled={disabled} {...register("utm_content")} />
          <FieldError>{errors.utm_content?.message ? t(errors.utm_content.message) : undefined}</FieldError>
        </Field>
      </div>

      <div className="rounded-xl border border-border/70 p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="font-semibold">{t("quotations.form.itemsTitle")}</h3>
            <p className="text-sm text-muted-foreground">{t("quotations.form.itemsDescription")}</p>
          </div>
          <Button type="button" variant="outline" size="sm" onClick={() => append(blankItem())} disabled={disabled}>
            {t("quotations.form.addItem")}
          </Button>
        </div>
        <div className="mt-4 space-y-4">
          {fields.map((field, index) => (
            <div key={field.id} className="rounded-lg border border-border/70 p-4">
              <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-5">
                <Field className="xl:col-span-2">
                  <FieldLabel htmlFor={`items.${index}.item_name`}>{t("quotations.form.itemNameRequiredLabel")}</FieldLabel>
                  <Input id={`items.${index}.item_name`} disabled={disabled} {...register(`items.${index}.item_name`)} />
                  <FieldError>{errors.items?.[index]?.item_name?.message ? t(errors.items[index]?.item_name?.message as string) : undefined}</FieldError>
                </Field>
                <Field>
                  <FieldLabel htmlFor={`items.${index}.quantity`}>{t("quotations.form.quantityRequiredLabel")}</FieldLabel>
                  <Input id={`items.${index}.quantity`} disabled={disabled} {...register(`items.${index}.quantity`)} />
                  <FieldError>{errors.items?.[index]?.quantity?.message ? t(errors.items[index]?.quantity?.message as string) : undefined}</FieldError>
                </Field>
                <Field>
                  <FieldLabel htmlFor={`items.${index}.unit_price`}>{t("quotations.form.unitPrice")}</FieldLabel>
                  <Input id={`items.${index}.unit_price`} disabled={disabled} {...register(`items.${index}.unit_price`)} />
                  <FieldError>{errors.items?.[index]?.unit_price?.message ? t(errors.items[index]?.unit_price?.message as string) : undefined}</FieldError>
                </Field>
                <Field>
                  <FieldLabel htmlFor={`items.${index}.item_code`}>{t("quotations.form.itemCode")}</FieldLabel>
                  <Input id={`items.${index}.item_code`} disabled={disabled} {...register(`items.${index}.item_code`)} />
                  <FieldError>{errors.items?.[index]?.item_code?.message ? t(errors.items[index]?.item_code?.message as string) : undefined}</FieldError>
                </Field>
              </div>
              <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
                <Field>
                  <FieldLabel htmlFor={`items.${index}.description`}>{t("quotations.form.itemDescription")}</FieldLabel>
                  <Textarea id={`items.${index}.description`} disabled={disabled} {...register(`items.${index}.description`)} />
                  <FieldError>{errors.items?.[index]?.description?.message ? t(errors.items[index]?.description?.message as string) : undefined}</FieldError>
                </Field>
                <Button type="button" variant="ghost" size="sm" onClick={() => remove(index)} disabled={disabled || fields.length === 1}>
                  {t("quotations.form.removeItem")}
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-border/70 p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="font-semibold">{t("quotations.form.taxesTitle")}</h3>
            <p className="text-sm text-muted-foreground">{t("quotations.form.taxesDescription")}</p>
          </div>
          <Button type="button" variant="outline" size="sm" onClick={() => appendTax({ description: "", rate: "", tax_amount: "" })} disabled={disabled}>
            {t("quotations.form.addTax")}
          </Button>
        </div>
        <div className="mt-4 space-y-4">
          {taxFields.length === 0 ? <p className="text-sm text-muted-foreground">{t("quotations.form.taxesEmpty")}</p> : null}
          {taxFields.map((field, index) => (
            <div key={field.id} className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_160px_160px_auto] lg:items-end">
              <Field>
                <FieldLabel htmlFor={`taxes.${index}.description`}>{t("quotations.form.taxDescription")}</FieldLabel>
                <Input id={`taxes.${index}.description`} disabled={disabled} {...register(`taxes.${index}.description`)} />
                <FieldError>{errors.taxes?.[index]?.description?.message ? t(errors.taxes[index]?.description?.message as string) : undefined}</FieldError>
              </Field>
              <Field>
                <FieldLabel htmlFor={`taxes.${index}.rate`}>{t("quotations.form.taxRate")}</FieldLabel>
                <Input id={`taxes.${index}.rate`} disabled={disabled} {...register(`taxes.${index}.rate`)} />
                <FieldError>{errors.taxes?.[index]?.rate?.message ? t(errors.taxes[index]?.rate?.message as string) : undefined}</FieldError>
              </Field>
              <Field>
                <FieldLabel htmlFor={`taxes.${index}.tax_amount`}>{t("quotations.form.taxAmount")}</FieldLabel>
                <Input id={`taxes.${index}.tax_amount`} disabled={disabled} {...register(`taxes.${index}.tax_amount`)} />
                <FieldError>{errors.taxes?.[index]?.tax_amount?.message ? t(errors.taxes[index]?.tax_amount?.message as string) : undefined}</FieldError>
              </Field>
              <Button type="button" variant="ghost" size="sm" onClick={() => removeTax(index)} disabled={disabled}>
                {t("quotations.form.removeTax")}
              </Button>
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="terms_template">{t("quotations.form.termsTemplate")}</FieldLabel>
          <Input id="terms_template" disabled={disabled} {...register("terms_template")} />
          <FieldError>{errors.terms_template?.message ? t(errors.terms_template.message) : undefined}</FieldError>
        </Field>
        <Field className="rounded-xl border border-border/70 px-4 py-3">
          <label className="flex items-center gap-3 text-sm font-medium text-foreground" htmlFor="auto_repeat_enabled">
            <input id="auto_repeat_enabled" type="checkbox" disabled={disabled} {...register("auto_repeat_enabled")} />
            <span>{t("quotations.form.autoRepeatEnabled")}</span>
          </label>
        </Field>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="terms_and_conditions">{t("quotations.form.termsAndConditions")}</FieldLabel>
          <Textarea id="terms_and_conditions" disabled={disabled} {...register("terms_and_conditions")} />
          <FieldError>{errors.terms_and_conditions?.message ? t(errors.terms_and_conditions.message) : undefined}</FieldError>
        </Field>
        <div className="grid gap-4">
          <Field>
            <FieldLabel htmlFor="auto_repeat_frequency">{t("quotations.form.autoRepeatFrequency")}</FieldLabel>
            <Input id="auto_repeat_frequency" disabled={disabled || !autoRepeatEnabled} {...register("auto_repeat_frequency")} />
            <FieldError>{errors.auto_repeat_frequency?.message ? t(errors.auto_repeat_frequency.message) : undefined}</FieldError>
          </Field>
          <Field>
            <FieldLabel htmlFor="auto_repeat_until">{t("quotations.form.autoRepeatUntil")}</FieldLabel>
            <Input id="auto_repeat_until" type="date" disabled={disabled || !autoRepeatEnabled} {...register("auto_repeat_until")} />
            <FieldError>{errors.auto_repeat_until?.message ? t(errors.auto_repeat_until.message) : undefined}</FieldError>
          </Field>
        </div>
      </div>

      <Field>
        <FieldLabel htmlFor="notes">{t("quotations.form.notes")}</FieldLabel>
        <Textarea id="notes" disabled={disabled} {...register("notes")} />
        <FieldError>{errors.notes?.message ? t(errors.notes.message) : undefined}</FieldError>
      </Field>

      <div className="rounded-xl border border-border/70 bg-muted/20 px-4 py-4 text-sm">
        <h3 className="font-semibold">{t("quotations.form.summaryTitle")}</h3>
        <dl className="mt-3 grid gap-3 sm:grid-cols-3">
          <div>
            <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("quotations.form.subtotal")}</dt>
            <dd className="mt-1">{subtotal.toFixed(2)}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("quotations.form.totalTaxes")}</dt>
            <dd className="mt-1">{totalTaxes.toFixed(2)}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{t("quotations.form.grandTotal")}</dt>
            <dd className="mt-1 font-semibold">{grandTotal.toFixed(2)}</dd>
          </div>
        </dl>
      </div>

      <input type="hidden" {...register("opportunity_id")} />

      <Button type="submit" disabled={disabled || submitting}>
        {submitting ? resolvedSubmittingLabel : resolvedSubmitLabel}
      </Button>
    </form>
  );
}

export default QuotationForm;