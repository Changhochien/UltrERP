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
  base_unit_price?: string | null;
  base_subtotal_amount?: string | null;
  base_tax_amount?: string | null;
  base_total_amount?: string | null;
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
  conversion_rate?: string | null;
  conversion_effective_date?: string | null;
  applied_rate_source?: string | null;
  currency_source?: string | null;
  base_subtotal_amount?: string | null;
  base_tax_amount?: string | null;
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
  conversion_rate?: string | null;
  conversion_effective_date?: string | null;
  applied_rate_source?: string | null;
  currency_source?: string | null;
  base_subtotal_amount?: string | null;
  base_tax_amount?: string | null;
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

// ---------------------------------------------------------------------------
// Purchase Order Types
// ---------------------------------------------------------------------------

export type POStatus =
  | "draft"
  | "submitted"
  | "on_hold"
  | "to_receive"
  | "to_bill"
  | "to_receive_and_bill"
  | "completed"
  | "cancelled"
  | "closed";

export interface POItemPayload {
  quotation_item_id?: string | null;
  rfq_item_id?: string | null;
  item_code: string;
  item_name: string;
  description: string;
  qty: string;
  uom: string;
  warehouse: string;
  unit_rate: string;
  amount: string;
  tax_rate: string;
  tax_amount: string;
  tax_code: string;
}

export interface POItemResponse {
  id: string;
  purchase_order_id: string;
  idx: number;
  quotation_item_id: string | null;
  rfq_item_id: string | null;
  item_code: string;
  item_name: string;
  description: string;
  qty: string;
  uom: string;
  warehouse: string;
  unit_rate: string;
  amount: string;
  base_unit_price?: string | null;
  base_subtotal_amount?: string | null;
  base_tax_amount?: string | null;
  base_total_amount?: string | null;
  tax_rate: string;
  tax_amount: string;
  tax_code: string;
  received_qty: string;
  billed_amount: string;
  created_at: string;
}

export interface PurchaseOrderCreatePayload {
  name?: string;
  status?: POStatus;
  award_id?: string | null;
  rfq_id?: string | null;
  quotation_id?: string | null;
  supplier_id?: string | null;
  supplier_name: string;
  company: string;
  currency: string;
  transaction_date: string;
  schedule_date?: string | null;
  subtotal: string;
  total_taxes: string;
  grand_total: string;
  base_grand_total: string;
  taxes: Record<string, unknown>[];
  contact_person: string;
  contact_email: string;
  set_warehouse: string;
  terms_and_conditions: string;
  notes: string;
  // Extension hooks (Story 24-5)
  blanket_order_reference_id?: string | null;
  landed_cost_reference_id?: string | null;
  // Subcontracting metadata (Story 24-6)
  is_subcontracted?: boolean;
  finished_goods_item_code?: string | null;
  finished_goods_item_name?: string | null;
  expected_subcontracted_qty?: string | null;
  items: POItemPayload[];
}

export interface PurchaseOrderUpdatePayload {
  name?: string;
  status?: POStatus;
  supplier_name?: string;
  company?: string;
  currency?: string;
  transaction_date?: string;
  schedule_date?: string | null;
  subtotal?: string;
  total_taxes?: string;
  grand_total?: string;
  base_grand_total?: string;
  taxes?: Record<string, unknown>[] | null;
  contact_person?: string;
  contact_email?: string;
  set_warehouse?: string;
  terms_and_conditions?: string;
  notes?: string;
  // Extension hooks (Story 24-5)
  blanket_order_reference_id?: string | null;
  landed_cost_reference_id?: string | null;
  // Subcontracting metadata (Story 24-6)
  is_subcontracted?: boolean;
  finished_goods_item_code?: string | null;
  finished_goods_item_name?: string | null;
  expected_subcontracted_qty?: string | null;
}

export interface PurchaseOrderResponse {
  id: string;
  tenant_id: string;
  name: string;
  status: POStatus;
  supplier_id: string | null;
  supplier_name: string;
  rfq_id: string | null;
  quotation_id: string | null;
  award_id: string | null;
  company: string;
  currency: string;
  transaction_date: string;
  schedule_date: string | null;
  subtotal: string;
  total_taxes: string;
  grand_total: string;
  conversion_rate?: string | null;
  conversion_effective_date?: string | null;
  applied_rate_source?: string | null;
  currency_source?: string | null;
  base_subtotal_amount?: string | null;
  base_tax_amount?: string | null;
  base_grand_total: string;
  taxes: Record<string, unknown>[];
  contact_person: string;
  contact_email: string;
  set_warehouse: string;
  terms_and_conditions: string;
  notes: string;
  per_received: string;
  per_billed: string;
  is_approved: boolean;
  approved_by: string;
  approved_at: string | null;
  // Extension hooks (Story 24-5)
  blanket_order_reference_id: string | null;
  landed_cost_reference_id: string | null;
  // Subcontracting metadata (Story 24-6)
  is_subcontracted: boolean;
  finished_goods_item_code: string | null;
  finished_goods_item_name: string | null;
  expected_subcontracted_qty: string | null;
  created_at: string;
  updated_at: string;
  items: POItemResponse[];
}

export interface PurchaseOrderSummary {
  id: string;
  name: string;
  status: POStatus;
  supplier_name: string;
  company: string;
  currency: string;
  transaction_date: string;
  schedule_date: string | null;
  grand_total: string;
  conversion_rate?: string | null;
  conversion_effective_date?: string | null;
  applied_rate_source?: string | null;
  currency_source?: string | null;
  base_subtotal_amount?: string | null;
  base_tax_amount?: string | null;
  base_grand_total?: string | null;
  per_received: string;
  per_billed: string;
  is_approved: boolean;
  created_at: string;
}

export interface PurchaseOrderListResponse {
  items: PurchaseOrderSummary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ---------------------------------------------------------------------------
// Goods Receipt Types (Story 24-3)
// ---------------------------------------------------------------------------

export type GoodsReceiptStatus = "draft" | "submitted" | "cancelled";

export interface GRItemPayload {
  purchase_order_item_id: string;
  item_code: string;
  item_name: string;
  description: string;
  accepted_qty: string;
  rejected_qty: string;
  uom: string;
  warehouse: string;
  rejected_warehouse: string;
  batch_no: string;
  serial_no: string;
  exception_notes: string;
  unit_rate: string;
}

export interface GRItemResponse {
  id: string;
  goods_receipt_id: string;
  idx: number;
  purchase_order_item_id: string;
  item_code: string;
  item_name: string;
  description: string;
  accepted_qty: string;
  rejected_qty: string;
  total_qty: string;
  uom: string;
  warehouse: string;
  rejected_warehouse: string;
  batch_no: string;
  serial_no: string;
  exception_notes: string;
  is_rejected: boolean;
  unit_rate: string;
  created_at: string;
}

export interface GoodsReceiptCreatePayload {
  purchase_order_id: string;
  transaction_date: string;
  posting_date?: string | null;
  set_warehouse: string;
  contact_person: string;
  notes: string;
  items: GRItemPayload[];
}

export interface GoodsReceiptResponse {
  id: string;
  tenant_id: string;
  name: string;
  status: GoodsReceiptStatus;
  purchase_order_id: string;
  supplier_id: string | null;
  supplier_name: string;
  company: string;
  transaction_date: string;
  posting_date: string | null;
  set_warehouse: string;
  contact_person: string;
  notes: string;
  inventory_mutated: boolean;
  inventory_mutated_at: string | null;
  created_at: string;
  updated_at: string;
  items: GRItemResponse[];
}

export interface GoodsReceiptSummary {
  id: string;
  name: string;
  status: GoodsReceiptStatus;
  purchase_order_id: string;
  supplier_name: string;
  transaction_date: string;
  posting_date: string | null;
  inventory_mutated: boolean;
  created_at: string;
}

export interface GoodsReceiptListResponse {
  items: GoodsReceiptSummary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// --------------------------------------------------------------------------
// Supplier Control Types (Story 24-5)
// --------------------------------------------------------------------------

export interface SupplierControlResult {
  is_blocked: boolean;
  is_warned: boolean;
  reason: string;
  supplier_name: string;
  controls: SupplierControlFlags;
}

export interface SupplierControlFlags {
  on_hold?: boolean;
  hold_type?: string | null;
  release_date?: string | null;
  scorecard_standing?: string | null;
  warn_rfqs?: boolean;
  prevent_rfqs?: boolean;
  warn_pos?: boolean;
  prevent_pos?: boolean;
}

export interface SupplierControlsStatus {
  supplier_id: string;
  supplier_name: string;
  is_active: boolean;
  is_subcontractor: boolean;
  // Hold status
  on_hold: boolean;
  hold_type: string | null;
  release_date: string | null;
  is_effectively_on_hold: boolean;
  // Scorecard controls
  scorecard_standing: string | null;
  scorecard_last_evaluated_at: string | null;
  // RFQ controls
  warn_rfqs: boolean;
  prevent_rfqs: boolean;
  rfq_blocked: boolean;
  rfq_warned: boolean;
  rfq_control_reason: string;
  // PO controls
  warn_pos: boolean;
  prevent_pos: boolean;
  po_blocked: boolean;
  po_warned: boolean;
  po_control_reason: string;
}

// --------------------------------------------------------------------------
// Procurement Reporting Types (Story 24-5)
// --------------------------------------------------------------------------

export interface ProcurementSummary {
  period: {
    from: string;
    to: string;
  };
  rfqs: {
    total: number;
    submitted: number;
    pending: number;
  };
  supplier_quotations: {
    total: number;
    submitted: number;
    pending: number;
  };
  awards: {
    total: number;
  };
  purchase_orders: {
    total: number;
    active: number;
    draft: number;
  };
  supplier_controls: {
    blocked_suppliers: number;
    warned_suppliers: number;
  };
}

export interface QuoteTurnaroundStats {
  rfq_id: string | null;
  total_quotes: number;
  avg_turnaround_days: number | null;
  min_turnaround_days: number | null;
  max_turnaround_days: number | null;
}

export interface SupplierPerformanceStats {
  supplier_id: string | null;
  overall: {
    total_quotes: number;
    awarded_quotes: number;
    award_rate: number;
  };
  by_supplier: {
    supplier_name: string;
    supplier_id: string | null;
    total_quotes: number;
    awarded_quotes: number;
    award_rate: number;
  }[];
  supplier_controls: {
    total_suppliers: number;
    blocked_count: number;
    warn_rfq_count: number;
    warn_po_count: number;
    prevent_rfq_count: number;
    prevent_po_count: number;
  };
}

// --------------------------------------------------------------------------
// Subcontracting Types (Story 24-6)
// --------------------------------------------------------------------------

// --- Subcontracting Material Transfer Types ---

export type SubcontractingMaterialTransferStatus = "draft" | "pending" | "in_transit" | "delivered" | "cancelled";

export interface SMTItemPayload {
  item_code: string;
  item_name: string;
  description: string;
  qty: string;
  uom: string;
  warehouse: string;
}

export interface SMTItemResponse {
  id: string;
  material_transfer_id: string;
  idx: number;
  item_code: string;
  item_name: string;
  description: string;
  qty: string;
  uom: string;
  warehouse: string;
  created_at: string;
}

export interface SubcontractingMaterialTransferCreatePayload {
  purchase_order_id: string;
  transfer_date: string;
  source_warehouse: string;
  contact_person: string;
  contact_email: string;
  notes: string;
  items: SMTItemPayload[];
}

export interface SubcontractingMaterialTransferResponse {
  id: string;
  tenant_id: string;
  name: string;
  status: SubcontractingMaterialTransferStatus;
  purchase_order_id: string;
  supplier_id: string | null;
  supplier_name: string;
  company: string;
  transfer_date: string;
  shipped_date: string | null;
  received_date: string | null;
  source_warehouse: string;
  contact_person: string;
  contact_email: string;
  notes: string;
  created_at: string;
  updated_at: string;
  items: SMTItemResponse[];
}

export interface SubcontractingMaterialTransferSummary {
  id: string;
  name: string;
  status: SubcontractingMaterialTransferStatus;
  purchase_order_id: string;
  supplier_name: string;
  transfer_date: string;
  shipped_date: string | null;
  received_date: string | null;
  created_at: string;
}

export interface SubcontractingMaterialTransferListResponse {
  items: SubcontractingMaterialTransferSummary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// --- Subcontracting Receipt Types ---

export type SubcontractingReceiptStatus = "draft" | "submitted" | "cancelled";

export interface SCRItemPayload {
  item_code: string;
  item_name: string;
  description: string;
  accepted_qty: string;
  rejected_qty: string;
  uom: string;
  warehouse: string;
  unit_rate: string;
  exception_notes: string;
}

export interface SCRItemResponse {
  id: string;
  subcontracting_receipt_id: string;
  idx: number;
  item_code: string;
  item_name: string;
  description: string;
  accepted_qty: string;
  rejected_qty: string;
  total_qty: string;
  uom: string;
  warehouse: string;
  unit_rate: string;
  exception_notes: string;
  is_rejected: boolean;
  created_at: string;
}

export interface SubcontractingReceiptMaterialRefResponse {
  id: string;
  subcontracting_receipt_id: string;
  material_transfer_id: string;
  created_at: string;
}

export interface SubcontractingReceiptCreatePayload {
  purchase_order_id: string;
  receipt_date: string;
  posting_date?: string | null;
  set_warehouse: string;
  contact_person: string;
  notes: string;
  material_transfer_ids: string[];
  items: SCRItemPayload[];
}

export interface SubcontractingReceiptResponse {
  id: string;
  tenant_id: string;
  name: string;
  status: SubcontractingReceiptStatus;
  purchase_order_id: string;
  supplier_id: string | null;
  supplier_name: string;
  company: string;
  receipt_date: string;
  posting_date: string | null;
  set_warehouse: string;
  contact_person: string;
  notes: string;
  inventory_mutated: boolean;
  inventory_mutated_at: string | null;
  created_at: string;
  updated_at: string;
  items: SCRItemResponse[];
  material_transfer_refs: SubcontractingReceiptMaterialRefResponse[];
}

export interface SubcontractingReceiptSummary {
  id: string;
  name: string;
  status: SubcontractingReceiptStatus;
  purchase_order_id: string;
  supplier_name: string;
  receipt_date: string;
  posting_date: string | null;
  inventory_mutated: boolean;
  created_at: string;
}

export interface SubcontractingReceiptListResponse {
  items: SubcontractingReceiptSummary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
