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

export type OpportunityPartyKind = "lead" | "customer" | "prospect";

export type OpportunityStatus =
  | "open"
  | "replied"
  | "quotation"
  | "converted"
  | "closed"
  | "lost";

export interface OpportunityItemPayload {
  item_name: string;
  item_code: string;
  description: string;
  quantity: string;
  unit_price: string;
  amount?: string | null;
}

export interface OpportunityCreatePayload {
  opportunity_title: string;
  opportunity_from: OpportunityPartyKind;
  party_name: string;
  sales_stage: string;
  probability: number;
  expected_closing: string | null;
  currency: string;
  opportunity_amount: string | null;
  opportunity_owner: string;
  territory: string;
  customer_group: string;
  contact_person: string;
  contact_email: string;
  contact_mobile: string;
  job_title: string;
  utm_source: string;
  utm_medium: string;
  utm_campaign: string;
  utm_content: string;
  items: OpportunityItemPayload[];
  notes: string;
}

export interface OpportunityUpdatePayload extends Partial<OpportunityCreatePayload> {
  version: number;
}

export interface OpportunityTransitionPayload {
  status: OpportunityStatus;
  lost_reason: string;
  competitor_name: string;
  loss_notes: string;
}

export interface OpportunityItemResponse {
  line_no: number;
  item_name: string;
  item_code: string;
  description: string;
  quantity: string;
  unit_price: string;
  amount: string;
}

export interface OpportunityResponse {
  id: string;
  tenant_id: string;
  opportunity_title: string;
  opportunity_from: OpportunityPartyKind;
  party_name: string;
  party_label: string;
  status: OpportunityStatus;
  sales_stage: string;
  probability: number;
  expected_closing: string | null;
  currency: string;
  opportunity_amount: string | null;
  base_opportunity_amount: string | null;
  opportunity_owner: string;
  territory: string;
  customer_group: string;
  contact_person: string;
  contact_email: string;
  contact_mobile: string;
  job_title: string;
  utm_source: string;
  utm_medium: string;
  utm_campaign: string;
  utm_content: string;
  items: OpportunityItemResponse[];
  notes: string;
  lost_reason: string;
  competitor_name: string;
  loss_notes: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface OpportunitySummary {
  id: string;
  opportunity_title: string;
  opportunity_from: OpportunityPartyKind;
  party_name: string;
  party_label: string;
  status: OpportunityStatus;
  sales_stage: string;
  probability: number;
  expected_closing: string | null;
  currency: string;
  opportunity_amount: string | null;
  opportunity_owner: string;
  territory: string;
  updated_at: string;
}

export interface OpportunityListResponse {
  items: OpportunitySummary[];
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
}

export interface OpportunityQuotationHandoff {
  opportunity_id: string;
  opportunity_title: string;
  opportunity_from: OpportunityPartyKind;
  party_name: string;
  party_label: string;
  customer_group: string;
  currency: string;
  opportunity_amount: string | null;
  base_opportunity_amount: string | null;
  territory: string;
  contact_person: string;
  contact_email: string;
  contact_mobile: string;
  job_title: string;
  utm_source: string;
  utm_medium: string;
  utm_campaign: string;
  utm_content: string;
  items: OpportunityItemResponse[];
}
