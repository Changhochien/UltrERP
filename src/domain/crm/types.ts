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

export type CRMDuplicatePolicy = "block" | "allow";

export interface CRMSettings {
  lead_duplicate_policy: CRMDuplicatePolicy;
  contact_creation_enabled: boolean;
  default_quotation_validity_days: number;
  carry_forward_communications: boolean;
  carry_forward_comments: boolean;
  opportunity_auto_close_days: number | null;
}

export interface CRMSettingsUpdatePayload extends Partial<CRMSettings> {}

export interface CRMSalesStage {
  id: string;
  name: string;
  probability: number;
  sort_order: number;
  is_active: boolean;
}

export interface CRMSalesStagePayload {
  name: string;
  probability: number;
  sort_order: number;
  is_active: boolean;
}

export interface CRMTerritory {
  id: string;
  name: string;
  parent_id: string | null;
  is_group: boolean;
  sort_order: number;
  is_active: boolean;
}

export interface CRMTerritoryPayload {
  name: string;
  parent_id?: string | null;
  is_group: boolean;
  sort_order: number;
  is_active: boolean;
}

export interface CRMCustomerGroup {
  id: string;
  name: string;
  parent_id: string | null;
  is_group: boolean;
  sort_order: number;
  is_active: boolean;
}

export interface CRMCustomerGroupPayload {
  name: string;
  parent_id?: string | null;
  is_group: boolean;
  sort_order: number;
  is_active: boolean;
}

export interface CRMSetupBundle {
  settings: CRMSettings;
  sales_stages: CRMSalesStage[];
  territories: CRMTerritory[];
  customer_groups: CRMCustomerGroup[];
}

export type CRMPipelineScope = "all" | "open" | "terminal";
export type CRMPipelineRecordType = "all" | "lead" | "opportunity" | "quotation";

export interface CRMPipelineReportParams {
  record_type?: CRMPipelineRecordType;
  scope?: CRMPipelineScope;
  status?: string;
  sales_stage?: string;
  territory?: string;
  customer_group?: string;
  owner?: string;
  lost_reason?: string;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_content?: string;
}

export interface CRMPipelineSegment {
  record_type: string | null;
  key: string;
  label: string;
  count: number;
  amount: string;
  ordered_revenue?: string;
}

export interface CRMPipelineTotals {
  lead_count: number;
  opportunity_count: number;
  quotation_count: number;
  open_count: number;
  terminal_count: number;
  open_pipeline_amount: string;
  terminal_pipeline_amount: string;
  ordered_revenue?: string;
}

export interface CRMPipelineDropOff {
  lead_only_count: number;
  opportunity_without_quotation_count: number;
  quotation_without_order_count: number;
  quotation_with_order_count: number;
}

export interface CRMPipelineReport {
  filters: Required<CRMPipelineReportParams>;
  totals: CRMPipelineTotals;
  by_status: CRMPipelineSegment[];
  by_sales_stage: CRMPipelineSegment[];
  by_territory: CRMPipelineSegment[];
  by_customer_group: CRMPipelineSegment[];
  by_owner: CRMPipelineSegment[];
  by_lost_reason: CRMPipelineSegment[];
  by_utm_source: CRMPipelineSegment[];
  by_utm_medium?: CRMPipelineSegment[];
  by_utm_campaign?: CRMPipelineSegment[];
  by_utm_content?: CRMPipelineSegment[];
  dropoff: CRMPipelineDropOff;
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

export interface QuotationOrderHandoffLine {
  source_quotation_line_no: number;
  product_id: string;
  description: string;
  quantity: string;
  list_unit_price: string;
  unit_price: string;
  discount_amount: string;
  tax_policy_code: string;
}

export interface QuotationOrderHandoff {
  quotation_id: string;
  source_quotation_id: string;
  customer_id: string;
  crm_context_snapshot?: Record<string, unknown> | null;
  notes: string;
  lines: QuotationOrderHandoffLine[];
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
  linked_orders?: QuotationLinkedOrder[];
  remaining_items?: QuotationRemainingItem[];
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
  ordered_amount?: string;
  order_count?: number;
  opportunity_id: string | null;
  amended_from: string | null;
  revision_no: number;
  updated_at: string;
}

export interface QuotationLinkedOrder {
  order_id: string;
  order_number: string;
  status: string;
  total_amount: string | null;
  linked_line_count: number;
  created_at: string;
}

export interface QuotationRemainingItem {
  line_no: number;
  item_name: string;
  item_code: string;
  description: string;
  quoted_quantity: string;
  ordered_quantity: string;
  remaining_quantity: string;
  quoted_amount: string;
  ordered_amount: string;
  remaining_amount: string;
}

export interface QuotationListResponse {
  items: QuotationSummary[];
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
}
