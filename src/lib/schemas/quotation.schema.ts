import { z } from "zod";

import type {
  QuotationCreatePayload,
  QuotationItemPayload,
  QuotationRevisionPayload,
  QuotationTaxPayload,
  QuotationTransitionPayload,
  QuotationUpdatePayload,
} from "../../domain/crm/types";

const DATE_REGEX = /^\d{4}-\d{2}-\d{2}$/;

const itemSchema = z.object({
  item_name: z.string().trim().min(1, "crm.quotations.form.itemNameRequired").max(200, "crm.quotations.form.itemNameTooLong"),
  item_code: z.string().max(120, "crm.quotations.form.itemCodeTooLong"),
  description: z.string().max(500, "crm.quotations.form.itemDescriptionTooLong"),
  quantity: z.string().refine((value) => {
    const normalized = value.trim();
    if (!normalized) return false;
    const parsed = Number(normalized);
    return !Number.isNaN(parsed) && parsed > 0;
  }, "crm.quotations.form.quantityPositive"),
  unit_price: z.string().refine((value) => {
    const normalized = value.trim();
    if (!normalized) return true;
    const parsed = Number(normalized);
    return !Number.isNaN(parsed) && parsed >= 0;
  }, "crm.quotations.form.unitPriceNonNegative"),
});

const taxSchema = z.object({
  description: z.string().trim().min(1, "crm.quotations.form.taxDescriptionRequired").max(200, "crm.quotations.form.taxDescriptionTooLong"),
  rate: z.string().refine((value) => {
    const normalized = value.trim();
    if (!normalized) return true;
    const parsed = Number(normalized);
    return !Number.isNaN(parsed) && parsed >= 0;
  }, "crm.quotations.form.taxRateNonNegative"),
  tax_amount: z.string().refine((value) => {
    const normalized = value.trim();
    if (!normalized) return true;
    const parsed = Number(normalized);
    return !Number.isNaN(parsed) && parsed >= 0;
  }, "crm.quotations.form.taxAmountNonNegative"),
});

export const quotationFormSchema = z
  .object({
    quotation_to: z.enum(["lead", "customer", "prospect"]),
    party_name: z.string().trim().min(1, "crm.quotations.form.partyRequired").max(200, "crm.quotations.form.partyTooLong"),
    transaction_date: z.string().refine((value) => DATE_REGEX.test(value.trim()), "crm.quotations.form.transactionDateInvalid"),
    valid_till: z.string().refine((value) => DATE_REGEX.test(value.trim()), "crm.quotations.form.validTillInvalid"),
    company: z.string().trim().min(1, "crm.quotations.form.companyRequired").max(200, "crm.quotations.form.companyTooLong"),
    currency: z.string().trim().length(3, "crm.quotations.form.currencyLength"),
    contact_person: z.string().max(120, "crm.quotations.form.contactPersonTooLong"),
    contact_email: z.string().max(254, "crm.quotations.form.contactEmailTooLong"),
    contact_mobile: z.string().max(30, "crm.quotations.form.contactMobileTooLong"),
    job_title: z.string().max(120, "crm.quotations.form.jobTitleTooLong"),
    territory: z.string().max(120, "crm.quotations.form.territoryTooLong"),
    customer_group: z.string().max(120, "crm.quotations.form.customerGroupTooLong"),
    billing_address: z.string().max(4000, "crm.quotations.form.billingAddressTooLong"),
    shipping_address: z.string().max(4000, "crm.quotations.form.shippingAddressTooLong"),
    utm_source: z.string().max(120, "crm.quotations.form.utmSourceTooLong"),
    utm_medium: z.string().max(120, "crm.quotations.form.utmMediumTooLong"),
    utm_campaign: z.string().max(120, "crm.quotations.form.utmCampaignTooLong"),
    utm_content: z.string().max(200, "crm.quotations.form.utmContentTooLong"),
    opportunity_id: z.string().max(120).optional(),
    items: z.array(itemSchema).min(1, "crm.quotations.form.itemsRequired"),
    taxes: z.array(taxSchema),
    terms_template: z.string().max(200, "crm.quotations.form.termsTemplateTooLong"),
    terms_and_conditions: z.string().max(4000, "crm.quotations.form.termsTooLong"),
    auto_repeat_enabled: z.boolean(),
    auto_repeat_frequency: z.string().max(40, "crm.quotations.form.autoRepeatFrequencyTooLong"),
    auto_repeat_until: z.string().refine((value) => {
      const normalized = value.trim();
      if (!normalized) return true;
      return DATE_REGEX.test(normalized);
    }, "crm.quotations.form.autoRepeatUntilInvalid"),
    notes: z.string().max(4000, "crm.quotations.form.notesTooLong"),
  })
  .superRefine((values, ctx) => {
    if (values.auto_repeat_enabled && !values.auto_repeat_frequency.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["auto_repeat_frequency"],
        message: "crm.quotations.form.autoRepeatFrequencyRequired",
      });
    }

    const transactionDate = new Date(values.transaction_date);
    const validTill = new Date(values.valid_till);
    if (!Number.isNaN(transactionDate.valueOf()) && !Number.isNaN(validTill.valueOf()) && validTill < transactionDate) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["valid_till"],
        message: "crm.quotations.form.validTillAfterTransaction",
      });
    }
  });

export type QuotationFormValues = z.infer<typeof quotationFormSchema>;
export type QuotationItemFormValues = z.infer<typeof itemSchema>;
export type QuotationTaxFormValues = z.infer<typeof taxSchema>;

function normalizeOptionalDate(value: string): string | null {
  const normalized = value.trim();
  return normalized ? normalized : null;
}

function normalizeOptionalAmount(value: string): string | null {
  const normalized = value.trim();
  if (!normalized) {
    return null;
  }
  return Number(normalized).toFixed(2);
}

function toItemPayload(item: QuotationItemFormValues): QuotationItemPayload {
  return {
    item_name: item.item_name.trim(),
    item_code: item.item_code.trim(),
    description: item.description.trim(),
    quantity: Number(item.quantity.trim()).toFixed(2),
    unit_price: item.unit_price.trim() ? Number(item.unit_price.trim()).toFixed(2) : "0.00",
  };
}

function toTaxPayload(tax: QuotationTaxFormValues): QuotationTaxPayload {
  return {
    description: tax.description.trim(),
    rate: tax.rate.trim() ? Number(tax.rate.trim()).toFixed(2) : "0.00",
    tax_amount: normalizeOptionalAmount(tax.tax_amount),
  };
}

export function toQuotationCreatePayload(values: QuotationFormValues): QuotationCreatePayload {
  return {
    quotation_to: values.quotation_to,
    party_name: values.party_name.trim(),
    transaction_date: values.transaction_date.trim(),
    valid_till: values.valid_till.trim(),
    company: values.company.trim(),
    currency: values.currency.trim().toUpperCase(),
    contact_person: values.contact_person.trim(),
    contact_email: values.contact_email.trim().toLowerCase(),
    contact_mobile: values.contact_mobile.trim(),
    job_title: values.job_title.trim(),
    territory: values.territory.trim(),
    customer_group: values.customer_group.trim(),
    billing_address: values.billing_address.trim(),
    shipping_address: values.shipping_address.trim(),
    utm_source: values.utm_source.trim(),
    utm_medium: values.utm_medium.trim(),
    utm_campaign: values.utm_campaign.trim(),
    utm_content: values.utm_content.trim(),
    opportunity_id: values.opportunity_id?.trim() ? values.opportunity_id.trim() : null,
    items: values.items.map(toItemPayload),
    taxes: values.taxes.filter((tax) => tax.description.trim()).map(toTaxPayload),
    terms_template: values.terms_template.trim(),
    terms_and_conditions: values.terms_and_conditions.trim(),
    auto_repeat_enabled: values.auto_repeat_enabled,
    auto_repeat_frequency: values.auto_repeat_frequency.trim(),
    auto_repeat_until: normalizeOptionalDate(values.auto_repeat_until),
    notes: values.notes.trim(),
  };
}

export function toQuotationUpdatePayload(
  values: QuotationFormValues,
  version: number,
): QuotationUpdatePayload {
  return {
    ...toQuotationCreatePayload(values),
    version,
  };
}

export function toQuotationTransitionPayload(values: {
  status: QuotationTransitionPayload["status"];
  lost_reason?: string;
  competitor_name?: string;
  loss_notes?: string;
}): QuotationTransitionPayload {
  return {
    status: values.status,
    lost_reason: values.lost_reason?.trim() ?? "",
    competitor_name: values.competitor_name?.trim() ?? "",
    loss_notes: values.loss_notes?.trim() ?? "",
  };
}

export function toQuotationRevisionPayload(values: Partial<QuotationFormValues>): QuotationRevisionPayload {
  const payload: QuotationRevisionPayload = {};

  if (values.quotation_to) payload.quotation_to = values.quotation_to;
  if (values.party_name !== undefined) payload.party_name = values.party_name.trim();
  if (values.transaction_date !== undefined) payload.transaction_date = values.transaction_date.trim();
  if (values.valid_till !== undefined) payload.valid_till = values.valid_till.trim();
  if (values.company !== undefined) payload.company = values.company.trim();
  if (values.currency !== undefined) payload.currency = values.currency.trim().toUpperCase();
  if (values.contact_person !== undefined) payload.contact_person = values.contact_person.trim();
  if (values.contact_email !== undefined) payload.contact_email = values.contact_email.trim().toLowerCase();
  if (values.contact_mobile !== undefined) payload.contact_mobile = values.contact_mobile.trim();
  if (values.job_title !== undefined) payload.job_title = values.job_title.trim();
  if (values.territory !== undefined) payload.territory = values.territory.trim();
  if (values.customer_group !== undefined) payload.customer_group = values.customer_group.trim();
  if (values.billing_address !== undefined) payload.billing_address = values.billing_address.trim();
  if (values.shipping_address !== undefined) payload.shipping_address = values.shipping_address.trim();
  if (values.utm_source !== undefined) payload.utm_source = values.utm_source.trim();
  if (values.utm_medium !== undefined) payload.utm_medium = values.utm_medium.trim();
  if (values.utm_campaign !== undefined) payload.utm_campaign = values.utm_campaign.trim();
  if (values.utm_content !== undefined) payload.utm_content = values.utm_content.trim();
  if (values.opportunity_id !== undefined) payload.opportunity_id = values.opportunity_id?.trim() ? values.opportunity_id.trim() : null;
  if (values.items !== undefined) payload.items = values.items.map(toItemPayload);
  if (values.taxes !== undefined) payload.taxes = values.taxes.filter((tax) => tax.description.trim()).map(toTaxPayload);
  if (values.terms_template !== undefined) payload.terms_template = values.terms_template.trim();
  if (values.terms_and_conditions !== undefined) payload.terms_and_conditions = values.terms_and_conditions.trim();
  if (values.auto_repeat_enabled !== undefined) payload.auto_repeat_enabled = values.auto_repeat_enabled;
  if (values.auto_repeat_frequency !== undefined) payload.auto_repeat_frequency = values.auto_repeat_frequency.trim();
  if (values.auto_repeat_until !== undefined) payload.auto_repeat_until = normalizeOptionalDate(values.auto_repeat_until);
  if (values.notes !== undefined) payload.notes = values.notes.trim();

  return payload;
}