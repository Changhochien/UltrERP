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

export type QuotationPartyKind = OpportunityPartyKind;

export type QuotationStatus =
  | "draft"
  | "open"
  | "replied"
  | "partially_ordered"
  | "ordered"
  | "lost"
  | "cancelled"
  | "expired";

export interface QuotationItemPayload extends OpportunityItemPayload {}

export interface QuotationTaxPayload {
  description: string;
  rate: string;
  tax_amount?: string | null;
}

export interface QuotationCreatePayload {
  quotation_to: QuotationPartyKind;
  party_name: string;
  transaction_date: string;
  valid_till: string;
  company: string;
  currency: string;
  contact_person: string;
  contact_email: string;
  contact_mobile: string;
  job_title: string;
  territory: string;
  customer_group: string;
  billing_address: string;
  shipping_address: string;
  utm_source: string;
  utm_medium: string;
  utm_campaign: string;
  utm_content: string;
  opportunity_id: string | null;
  items: QuotationItemPayload[];
  taxes: QuotationTaxPayload[];
  terms_template: string;
  terms_and_conditions: string;
  auto_repeat_enabled: boolean;
  auto_repeat_frequency: string;
  auto_repeat_until: string | null;
  notes: string;
}

export interface QuotationRevisionPayload extends Partial<QuotationCreatePayload> {}

export interface QuotationUpdatePayload extends Partial<QuotationCreatePayload> {
  version: number;
}

export interface QuotationTransitionPayload {
  status: QuotationStatus;
  lost_reason: string;
  competitor_name: string;
  loss_notes: string;
}

export interface QuotationItemResponse extends OpportunityItemResponse {}

export interface QuotationTaxResponse {
  line_no: number;
  description: string;
  rate: string;
  tax_amount: string;
}

export interface QuotationResponse {
  id: string;
  tenant_id: string;
  quotation_to: QuotationPartyKind;
  party_name: string;
  party_label: string;
  status: QuotationStatus;
  transaction_date: string;
  valid_till: string;
  company: string;
  currency: string;
  subtotal: string;
  total_taxes: string;
  grand_total: string;
  base_grand_total: string;
  ordered_amount: string;
  order_count: number;
  contact_person: string;
  contact_email: string;
  contact_mobile: string;
  job_title: string;
  territory: string;
  customer_group: string;
  billing_address: string;
  shipping_address: string;
  utm_source: string;
  utm_medium: string;
  utm_campaign: string;
  utm_content: string;
  items: QuotationItemResponse[];
  taxes: QuotationTaxResponse[];
  terms_template: string;
  terms_and_conditions: string;
  opportunity_id: string | null;
  amended_from: string | null;
  revision_no: number;
  lost_reason: string;
  competitor_name: string;
  loss_notes: string;
  auto_repeat_enabled: boolean;
  auto_repeat_frequency: string;
  auto_repeat_until: string | null;
  notes: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface QuotationSummary {
  id: string;
  quotation_to: QuotationPartyKind;
  party_name: string;
  party_label: string;
  status: QuotationStatus;
  transaction_date: string;
  valid_till: string;
  company: string;
  currency: string;
  grand_total: string;
  opportunity_id: string | null;
  amended_from: string | null;
  revision_no: number;
  updated_at: string;
}

export interface QuotationListResponse {
  items: QuotationSummary[];
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
}
