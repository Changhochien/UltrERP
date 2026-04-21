import { z } from "zod";

import type {
  OpportunityCreatePayload,
  OpportunityItemPayload,
  OpportunityTransitionPayload,
  OpportunityUpdatePayload,
} from "../../domain/crm/types";

const DATE_REGEX = /^\d{4}-\d{2}-\d{2}$/;

const itemSchema = z.object({
  item_name: z.string().trim().min(1, "crm.opportunities.form.itemNameRequired").max(200, "crm.opportunities.form.itemNameTooLong"),
  item_code: z.string().max(120, "crm.opportunities.form.itemCodeTooLong"),
  description: z.string().max(500, "crm.opportunities.form.itemDescriptionTooLong"),
  quantity: z.string().refine((value) => {
    const normalized = value.trim();
    if (!normalized) return false;
    const parsed = Number(normalized);
    return !Number.isNaN(parsed) && parsed > 0;
  }, "crm.opportunities.form.quantityPositive"),
  unit_price: z.string().refine((value) => {
    const normalized = value.trim();
    if (!normalized) return true;
    const parsed = Number(normalized);
    return !Number.isNaN(parsed) && parsed >= 0;
  }, "crm.opportunities.form.unitPriceNonNegative"),
});

export const opportunityFormSchema = z.object({
  opportunity_title: z.string().trim().min(1, "crm.opportunities.form.titleRequired").max(200, "crm.opportunities.form.titleTooLong"),
  opportunity_from: z.enum(["lead", "customer", "prospect"]),
  party_name: z.string().trim().min(1, "crm.opportunities.form.partyRequired").max(200, "crm.opportunities.form.partyTooLong"),
  sales_stage: z.string().max(120, "crm.opportunities.form.salesStageTooLong"),
  probability: z.string().refine((value) => {
    const normalized = value.trim();
    if (!normalized) return true;
    const parsed = Number(normalized);
    return Number.isInteger(parsed) && parsed >= 0 && parsed <= 100;
  }, "crm.opportunities.form.probabilityRange"),
  expected_closing: z.string().refine((value) => {
    const normalized = value.trim();
    if (!normalized) return true;
    return DATE_REGEX.test(normalized);
  }, "crm.opportunities.form.expectedClosingInvalid"),
  currency: z.string().trim().length(3, "crm.opportunities.form.currencyLength"),
  opportunity_amount: z.string().refine((value) => {
    const normalized = value.trim();
    if (!normalized) return true;
    const parsed = Number(normalized);
    return !Number.isNaN(parsed) && parsed >= 0;
  }, "crm.opportunities.form.amountNonNegative"),
  opportunity_owner: z.string().max(120, "crm.opportunities.form.ownerTooLong"),
  territory: z.string().max(120, "crm.opportunities.form.territoryTooLong"),
  customer_group: z.string().max(120, "crm.opportunities.form.customerGroupTooLong"),
  contact_person: z.string().max(120, "crm.opportunities.form.contactPersonTooLong"),
  contact_email: z.string().max(254, "crm.opportunities.form.contactEmailTooLong"),
  contact_mobile: z.string().max(30, "crm.opportunities.form.contactMobileTooLong"),
  job_title: z.string().max(120, "crm.opportunities.form.jobTitleTooLong"),
  utm_source: z.string().max(120, "crm.opportunities.form.utmSourceTooLong"),
  utm_medium: z.string().max(120, "crm.opportunities.form.utmMediumTooLong"),
  utm_campaign: z.string().max(120, "crm.opportunities.form.utmCampaignTooLong"),
  utm_content: z.string().max(200, "crm.opportunities.form.utmContentTooLong"),
  items: z.array(itemSchema),
  notes: z.string().max(4000, "crm.opportunities.form.notesTooLong"),
});

export type OpportunityFormValues = z.infer<typeof opportunityFormSchema>;
export type OpportunityItemFormValues = z.infer<typeof itemSchema>;

function normalizeOptionalDate(value: string): string | null {
  const normalized = value.trim();
  return normalized ? normalized : null;
}

function normalizeOptionalNumber(value: string): number {
  const normalized = value.trim();
  if (!normalized) {
    return 0;
  }
  return Number.parseInt(normalized, 10);
}

function normalizeOptionalAmount(value: string): string | null {
  const normalized = value.trim();
  if (!normalized) {
    return null;
  }
  return Number(normalized).toFixed(2);
}

function toItemPayload(item: OpportunityItemFormValues): OpportunityItemPayload {
  return {
    item_name: item.item_name.trim(),
    item_code: item.item_code.trim(),
    description: item.description.trim(),
    quantity: Number(item.quantity.trim()).toFixed(2),
    unit_price: item.unit_price.trim() ? Number(item.unit_price.trim()).toFixed(2) : "0.00",
  };
}

export function toOpportunityCreatePayload(values: OpportunityFormValues): OpportunityCreatePayload {
  return {
    opportunity_title: values.opportunity_title.trim(),
    opportunity_from: values.opportunity_from,
    party_name: values.party_name.trim(),
    sales_stage: values.sales_stage.trim(),
    probability: normalizeOptionalNumber(values.probability),
    expected_closing: normalizeOptionalDate(values.expected_closing),
    currency: values.currency.trim().toUpperCase(),
    opportunity_amount: normalizeOptionalAmount(values.opportunity_amount),
    opportunity_owner: values.opportunity_owner.trim(),
    territory: values.territory.trim(),
    customer_group: values.customer_group.trim(),
    contact_person: values.contact_person.trim(),
    contact_email: values.contact_email.trim().toLowerCase(),
    contact_mobile: values.contact_mobile.trim(),
    job_title: values.job_title.trim(),
    utm_source: values.utm_source.trim(),
    utm_medium: values.utm_medium.trim(),
    utm_campaign: values.utm_campaign.trim(),
    utm_content: values.utm_content.trim(),
    items: values.items.map(toItemPayload),
    notes: values.notes.trim(),
  };
}

export function toOpportunityUpdatePayload(
  values: OpportunityFormValues,
  version: number,
): OpportunityUpdatePayload {
  return {
    ...toOpportunityCreatePayload(values),
    version,
  };
}

export function toOpportunityTransitionPayload(values: {
  status: OpportunityTransitionPayload["status"];
  lost_reason?: string;
  competitor_name?: string;
  loss_notes?: string;
}): OpportunityTransitionPayload {
  return {
    status: values.status,
    lost_reason: values.lost_reason?.trim() ?? "",
    competitor_name: values.competitor_name?.trim() ?? "",
    loss_notes: values.loss_notes?.trim() ?? "",
  };
}