/** Procurement domain types - RFQ and Supplier Quotation workspace. */

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

export type RFQStatus = "draft" | "submitted" | "closed" | "cancelled";
export type QuoteStatus = "pending" | "received" | "lost" | "cancelled";
export type SupplierQuotationStatus = "draft" | "submitted" | "cancelled";

// ---------------------------------------------------------------------------
// RFQ Types
// ---------------------------------------------------------------------------

export interface RFQItemPayload {
  item_code: string;
  item_name: string;
  description: string;
  qty: string;
  uom: string;
  warehouse: string;
}

export interface RFQSupplierPayload {
  supplier_id: string | null;
  supplier_name: string;
  contact_email: string;
  notes: string;
}

export interface RFQCreatePayload {
  name?: string;
  status?: RFQStatus;
  company: string;
  currency: string;
  transaction_date: string;
  schedule_date?: string | null;
  terms_and_conditions: string;
  notes: string;
  items: RFQItemPayload[];
  suppliers: RFQSupplierPayload[];
}

export interface RFQUpdatePayload {
  name?: string;
  status?: RFQStatus;
  company?: string;
  currency?: string;
  transaction_date?: string;
  schedule_date?: string | null;
  terms_and_conditions?: string;
  notes?: string;
}

export interface RFQItemResponse {
  id: string;
  rfq_id: string;
  idx: number;
  item_code: string;
  item_name: string;
  description: string;
  qty: string;
  uom: string;
  warehouse: string;
  created_at: string;
}

export interface RFQSupplierResponse {
  id: string;
  rfq_id: string;
  supplier_id: string | null;
  supplier_name: string;
  contact_email: string;
  quote_status: QuoteStatus;
  quotation_id: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface RFQResponse {
  id: string;
  tenant_id: string;
  name: string;
  status: RFQStatus;
  company: string;
  currency: string;
  transaction_date: string;
  schedule_date: string | null;
  terms_and_conditions: string;
  notes: string;
  supplier_count: number;
  quotes_received: number;
  created_at: string;
  updated_at: string;
  items: RFQItemResponse[];
  suppliers: RFQSupplierResponse[];
}

export interface RFQSummary {
  id: string;
  name: string;
  status: RFQStatus;
  company: string;
  currency: string;
  transaction_date: string;
  schedule_date: string | null;
  supplier_count: number;
  quotes_received: number;
  created_at: string;
}

export interface RFQListResponse {
  items: RFQSummary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ---------------------------------------------------------------------------
// Supplier Quotation Types
// ---------------------------------------------------------------------------

export interface SQItemPayload {
  rfq_item_id?: string | null;
  item_code: string;
  item_name: string;
  description: string;
  qty: string;
  uom: string;
  unit_rate: string;
  amount: string;
  tax_rate: string;
  tax_amount: string;
  tax_code: string;
  normalized_unit_rate: string;
  normalized_amount: string;
}

export interface SupplierQuotationCreatePayload {
  name?: string;
  status?: SupplierQuotationStatus;
  rfq_id?: string | null;
  supplier_id?: string | null;
  supplier_name: string;
  company: string;
  currency: string;
  transaction_date: string;
  valid_till?: string | null;
  lead_time_days?: number | null;
  delivery_date?: string | null;
  subtotal: string;
  total_taxes: string;
  grand_total: string;
  base_grand_total: string;
  taxes: Record<string, unknown>[];
  contact_person: string;
  contact_email: string;
  terms_and_conditions: string;
  notes: string;
  comparison_base_total: string;
  items: SQItemPayload[];
}

export interface SupplierQuotationUpdatePayload {
  name?: string;
  status?: SupplierQuotationStatus;
  valid_till?: string | null;
  lead_time_days?: number | null;
  delivery_date?: string | null;
  subtotal?: string;
  total_taxes?: string;
  grand_total?: string;
  base_grand_total?: string;
  taxes?: Record<string, unknown>[] | null;
  contact_person?: string;
  contact_email?: string;
  terms_and_conditions?: string;
  notes?: string;
  comparison_base_total?: string;
}

export interface SQItemResponse {
  id: string;
  quotation_id: string;
  idx: number;
  rfq_item_id: string | null;
  item_code: string;
  item_name: string;
  description: string;
  qty: string;
  uom: string;
  unit_rate: string;
  amount: string;
  tax_rate: string;
  tax_amount: string;
  tax_code: string;
  normalized_unit_rate: string;
  normalized_amount: string;
  created_at: string;
}

export interface SupplierQuotationResponse {
  id: string;
  tenant_id: string;
  name: string;
  status: SupplierQuotationStatus;
  rfq_id: string | null;
  supplier_id: string | null;
  supplier_name: string;
  company: string;
  currency: string;
  transaction_date: string;
  valid_till: string | null;
  lead_time_days: number | null;
  delivery_date: string | null;
  subtotal: string;
  total_taxes: string;
  grand_total: string;
  base_grand_total: string;
  taxes: Record<string, unknown>[];
  contact_person: string;
  contact_email: string;
  terms_and_conditions: string;
  notes: string;
  comparison_base_total: string;
  is_awarded: boolean;
  created_at: string;
  updated_at: string;
  items: SQItemResponse[];
}

export interface SupplierQuotationSummary {
  id: string;
  name: string;
  status: SupplierQuotationStatus;
  rfq_id: string | null;
  supplier_name: string;
  currency: string;
  transaction_date: string;
  valid_till: string | null;
  lead_time_days: number | null;
  grand_total: string;
  base_grand_total: string;
  comparison_base_total: string;
  is_awarded: boolean;
  created_at: string;
}

export interface SupplierQuotationListResponse {
  items: SupplierQuotationSummary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ---------------------------------------------------------------------------
// Award Types
// ---------------------------------------------------------------------------

export interface AwardCreatePayload {
  rfq_id: string;
  quotation_id: string;
  awarded_by: string;
}

export interface AwardResponse {
  id: string;
  tenant_id: string;
  rfq_id: string;
  quotation_id: string;
  awarded_supplier_name: string;
  awarded_total: string;
  awarded_currency: string;
  awarded_lead_time_days: number | null;
  awarded_by: string;
  awarded_at: string;
  po_created: boolean;
  po_reference: string;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Comparison Types
// ---------------------------------------------------------------------------

export interface SupplierComparisonRow {
  quotation_id: string;
  supplier_name: string;
  currency: string;
  grand_total: string;
  base_grand_total: string;
  comparison_base_total: string;
  lead_time_days: number | null;
  valid_till: string | null;
  is_awarded: boolean;
  is_expired: boolean;
  status: SupplierQuotationStatus;
  items: SQItemResponse[];
}

export interface RFQComparisonResponse {
  rfq_id: string;
  rfq_name: string;
  status: RFQStatus;
  items: RFQItemResponse[];
  quotations: SupplierComparisonRow[];
}
