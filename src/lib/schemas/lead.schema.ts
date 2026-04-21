import { z } from "zod";

import type { LeadCreatePayload, LeadUpdatePayload } from "../../domain/crm/types";

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export const leadFormSchema = z.object({
  lead_name: z
    .string()
    .trim()
    .min(1, "crm.form.leadNameRequired")
    .max(140, "crm.form.leadNameTooLong"),
  company_name: z.string().max(200, "crm.form.companyNameTooLong"),
  email_id: z
    .string()
    .max(254, "crm.form.emailTooLong")
    .superRefine((value, ctx) => {
      const normalized = value.trim();
      if (!normalized) {
        return;
      }
      if (!EMAIL_REGEX.test(normalized)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "crm.form.invalidEmail",
        });
      }
    }),
  phone: z.string().max(30, "crm.form.phoneTooLong"),
  mobile_no: z.string().max(30, "crm.form.mobileTooLong"),
  territory: z.string().max(120, "crm.form.territoryTooLong"),
  lead_owner: z.string().max(120, "crm.form.ownerTooLong"),
  source: z.string().max(120, "crm.form.sourceTooLong"),
  qualification_status: z.enum(["unqualified", "in_process", "qualified"]),
  qualified_by: z.string().max(120, "crm.form.qualifiedByTooLong"),
  annual_revenue: z.string().refine((value) => {
    const normalized = value.trim();
    if (!normalized) {
      return true;
    }
    const parsed = Number(normalized);
    return !Number.isNaN(parsed) && parsed >= 0;
  }, "crm.form.annualRevenueNonNegative"),
  no_of_employees: z.string().refine((value) => {
    const normalized = value.trim();
    if (!normalized) {
      return true;
    }
    const parsed = Number(normalized);
    return Number.isInteger(parsed) && parsed >= 0;
  }, "crm.form.employeeCountNonNegative"),
  industry: z.string().max(120, "crm.form.industryTooLong"),
  market_segment: z.string().max(120, "crm.form.marketSegmentTooLong"),
  utm_source: z.string().max(120, "crm.form.utmSourceTooLong"),
  utm_medium: z.string().max(120, "crm.form.utmMediumTooLong"),
  utm_campaign: z.string().max(120, "crm.form.utmCampaignTooLong"),
  utm_content: z.string().max(200, "crm.form.utmContentTooLong"),
  notes: z.string().max(4000, "crm.form.notesTooLong"),
});

export type LeadFormValues = z.infer<typeof leadFormSchema>;

function normalizeAnnualRevenue(value: string): string | null {
  const normalized = value.trim();
  if (!normalized) {
    return null;
  }
  return Number(normalized).toFixed(2);
}

function normalizeEmployeeCount(value: string): number | null {
  const normalized = value.trim();
  if (!normalized) {
    return null;
  }
  return Number.parseInt(normalized, 10);
}

export function toLeadCreatePayload(values: LeadFormValues): LeadCreatePayload {
  return {
    lead_name: values.lead_name.trim(),
    company_name: values.company_name.trim(),
    email_id: values.email_id.trim().toLowerCase(),
    phone: values.phone.trim(),
    mobile_no: values.mobile_no.trim(),
    territory: values.territory.trim(),
    lead_owner: values.lead_owner.trim(),
    source: values.source.trim(),
    qualification_status: values.qualification_status,
    qualified_by: values.qualified_by.trim(),
    annual_revenue: normalizeAnnualRevenue(values.annual_revenue),
    no_of_employees: normalizeEmployeeCount(values.no_of_employees),
    industry: values.industry.trim(),
    market_segment: values.market_segment.trim(),
    utm_source: values.utm_source.trim(),
    utm_medium: values.utm_medium.trim(),
    utm_campaign: values.utm_campaign.trim(),
    utm_content: values.utm_content.trim(),
    notes: values.notes.trim(),
  };
}

export function toLeadUpdatePayload(values: LeadFormValues, version: number): LeadUpdatePayload {
  return {
    ...toLeadCreatePayload(values),
    version,
  };
}
