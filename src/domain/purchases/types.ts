// ------------------------------------------------------------------
// Procurement Lineage Types (Story 24-4)
// ------------------------------------------------------------------

/** Mismatch status for three-way-match readiness. */
export type ProcurementMismatchStatus =
  | "not_checked"
  | "within_tolerance"
  | "outside_tolerance"
  | "review_required";

/** Procurement lineage trace for a single line item. */
export interface ProcurementLineage {
  rfq_id: string | null;
  rfq_name: string | null;
  rfq_item_id: string | null;
  supplier_quotation_id: string | null;
  supplier_quotation_name: string | null;
  supplier_quotation_item_id: string | null;
  purchase_order_id: string | null;
  purchase_order_name: string | null;
  purchase_order_line_id: string | null;
  goods_receipt_id: string | null;
  goods_receipt_name: string | null;
  goods_receipt_line_id: string | null;
  lineage_state: "linked" | "unlinked_historical" | "missing_reference";
}

/** Mismatch summary for a supplier invoice line. */
export interface MismatchSummary {
  mismatch_status: ProcurementMismatchStatus;
  quantity_variance: string | null;
  unit_price_variance: string | null;
  total_amount_variance: string | null;
  quantity_variance_pct: string | null;
  unit_price_variance_pct: string | null;
  total_amount_variance_pct: string | null;
  tolerance_rule_code: string | null;
  tolerance_rule_id: string | null;
  comparison_basis_snapshot: Record<string, unknown> | null;
}

// ------------------------------------------------------------------
// Supplier Invoice Line Types (Story 24-4)
// ------------------------------------------------------------------

/** Supplier invoice line with procurement lineage fields. */
export interface SupplierInvoiceLine {
  id: string;
  line_number: number;
  product_id: string | null;
  product_code_snapshot: string | null;
  product_name: string | null;
  description: string;
  quantity: string;
  unit_price: string;
  subtotal_amount: string;
  tax_type: number;
  tax_rate: string;
  tax_amount: string;
  total_amount: string;
  created_at: string;
  // Procurement lineage references (Story 24-4)
  rfq_item_id: string | null;
  supplier_quotation_item_id: string | null;
  purchase_order_line_id: string | null;
  goods_receipt_line_id: string | null;
  // Mismatch and tolerance-ready fields (Story 24-4)
  reference_quantity: string | null;
  reference_unit_price: string | null;
  reference_total_amount: string | null;
  quantity_variance: string | null;
  unit_price_variance: string | null;
  total_amount_variance: string | null;
  quantity_variance_pct: string | null;
  unit_price_variance_pct: string | null;
  total_amount_variance_pct: string | null;
  comparison_basis_snapshot: Record<string, unknown> | null;
  mismatch_status: ProcurementMismatchStatus;
  tolerance_rule_code: string | null;
  tolerance_rule_id: string | null;
}

/** Supplier invoice line with full lineage trace. */
export interface SupplierInvoiceLineWithLineage extends SupplierInvoiceLine {
  lineage: ProcurementLineage;
  mismatch_summary: MismatchSummary | null;
}

// ------------------------------------------------------------------
// Supplier Invoice Types (Story 24-4)
// ------------------------------------------------------------------

/** Supplier invoice with procurement lineage fields. */
export interface SupplierInvoice {
  id: string;
  supplier_id: string;
  supplier_name: string;
  invoice_number: string;
  invoice_date: string;
  currency_code: string;
  subtotal_amount: string;
  tax_amount: string;
  total_amount: string;
  status: SupplierInvoiceStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
  lines: SupplierInvoiceLine[];
  // Procurement lineage - header-level PO reference (Story 24-4)
  purchase_order_id: string | null;
}

/** Supplier invoice with full lineage trace. */
export interface SupplierInvoiceWithLineage extends SupplierInvoice {
  lines: SupplierInvoiceLineWithLineage[];
}

/** Supplier invoice list item. */
export interface SupplierInvoiceListItem {
  id: string;
  supplier_id: string;
  supplier_name: string;
  invoice_number: string;
  invoice_date: string;
  currency_code: string;
  total_amount: string;
  status: SupplierInvoiceStatus;
  created_at: string;
  updated_at: string;
  line_count: number;
  // Procurement lineage - header-level PO reference (Story 24-4)
  purchase_order_id: string | null;
}

export interface SupplierInvoiceListResponse {
  items: SupplierInvoiceListItem[];
  status_totals: SupplierInvoiceStatusTotals;
  total: number;
  page: number;
  page_size: number;
}

// ------------------------------------------------------------------
// Lineage Chain Response (Story 24-4)
// ------------------------------------------------------------------

/** Reference to a single document in the lineage chain. */
export interface LineageDocumentRef {
  id: string;
  name: string;
  document_type: "rfq" | "supplier_quotation" | "purchase_order" | "goods_receipt";
  status: string | null;
  transaction_date: string | null;
}

/** Full lineage chain from RFQ through supplier invoice. */
export interface LineageChainResponse {
  supplier_invoice_id: string;
  supplier_invoice_name: string;
  purchase_order_id: string | null;
  line_count: number;
  lines: SupplierInvoiceLineWithLineage[];
}

// Re-export the status type for convenience
export type SupplierInvoiceStatus = "open" | "paid" | "voided";
export type SupplierInvoiceStatusTotals = Record<SupplierInvoiceStatus, number>;
