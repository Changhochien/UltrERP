/** CRM lead domain types for API payloads and responses. */

import type { CustomerCreatePayload } from "../customers/types";

export type LeadStatus =
  | "lead"
  | "open"
  | "replied"
  | "opportunity"
  | "quotation"
  | "lost_quotation"
  | "interested"
  | "converted"
  | "do_not_contact";

export type LeadQualificationStatus = "unqualified" | "in_process" | "qualified";

export interface LeadCreatePayload {
  lead_name: string;
  company_name: string;
  email_id: string;
  phone: string;
  mobile_no: string;
  territory: string;
  lead_owner: string;
  source: string;
  qualification_status: LeadQualificationStatus;
  qualified_by: string;
  annual_revenue: string | null;
  no_of_employees: number | null;
  industry: string;
  market_segment: string;
  utm_source: string;
  utm_medium: string;
  utm_campaign: string;
  utm_content: string;
  notes: string;
}

export interface LeadUpdatePayload extends Partial<LeadCreatePayload> {
  version: number;
}

export interface LeadResponse {
  id: string;
  tenant_id: string;
  lead_name: string;
  company_name: string;
  email_id: string;
  phone: string;
  mobile_no: string;
  territory: string;
  lead_owner: string;
  source: string;
  status: LeadStatus;
  qualification_status: LeadQualificationStatus;
  qualified_by: string;
  annual_revenue: string | null;
  no_of_employees: number | null;
  industry: string;
  market_segment: string;
  utm_source: string;
  utm_medium: string;
  utm_campaign: string;
  utm_content: string;
  notes: string;
  converted_customer_id: string | null;
  converted_at: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface LeadSummary {
  id: string;
  lead_name: string;
  company_name: string;
  email_id: string;
  phone: string;
  mobile_no: string;
  territory: string;
  lead_owner: string;
  source: string;
  status: LeadStatus;
  qualification_status: LeadQualificationStatus;
  updated_at: string;
}

export interface LeadListResponse {
  items: LeadSummary[];
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
}

export interface DuplicateLeadCandidate {
  kind: "lead" | "customer";
  id: string;
  label: string;
  matched_on: "company_name" | "email_id" | "phone";
}

export interface DuplicateLeadInfo {
  candidates: DuplicateLeadCandidate[];
}

export interface LeadOpportunityHandoff {
  lead_id: string;
  lead_name: string;
  company_name: string;
  email_id: string;
  phone: string;
  mobile_no: string;
  territory: string;
  lead_owner: string;
  source: string;
  qualification_status: LeadQualificationStatus;
  utm_source: string;
  utm_medium: string;
  utm_campaign: string;
  utm_content: string;
}

export interface LeadCustomerConversionResult {
  lead_id: string;
  customer_id: string;
  status: LeadStatus;
}

export type LeadCustomerConversionPayload = CustomerCreatePayload;
