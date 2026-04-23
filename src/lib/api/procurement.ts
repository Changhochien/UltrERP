/** Procurement API client - RFQ, Supplier Quotation, and Purchase Order workspace. */

import type {
  AwardCreatePayload,
  AwardResponse,
  GoodsReceiptCreatePayload,
  GoodsReceiptListResponse,
  GoodsReceiptResponse,
  PurchaseOrderCreatePayload,
  PurchaseOrderListResponse,
  PurchaseOrderResponse,
  PurchaseOrderUpdatePayload,
  RFQComparisonResponse,
  RFQCreatePayload,
  RFQListResponse,
  RFQResponse,
  RFQUpdatePayload,
  SupplierQuotationCreatePayload,
  SupplierQuotationListResponse,
  SupplierQuotationResponse,
  SupplierQuotationUpdatePayload,
} from "../../domain/procurement/types";
import { apiFetch } from "../apiFetch";

// ---------------------------------------------------------------------------
// Error helper
// ---------------------------------------------------------------------------

async function parseErrorMessage(resp: Response, fallback: string): Promise<string> {
  try {
    const body = await resp.json();
    if (Array.isArray(body?.detail)) return body.detail[0]?.message ?? fallback;
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    // ignore parse errors
  }
  return fallback;
}

// ---------------------------------------------------------------------------
// RFQ API
// ---------------------------------------------------------------------------

export async function createRFQ(payload: RFQCreatePayload): Promise<RFQResponse> {
  const resp = await apiFetch("/api/v1/procurement/rfqs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to create RFQ"));
  return resp.json();
}

export async function listRFQs(params?: {
  status?: string;
  q?: string;
  page?: number;
  page_size?: number;
}): Promise<RFQListResponse> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.q) qs.set("q", params.q);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const resp = await apiFetch(`/api/v1/procurement/rfqs?${qs}`);
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to list RFQs"));
  return resp.json();
}

export async function getRFQ(rfqId: string): Promise<RFQResponse> {
  const resp = await apiFetch(`/api/v1/procurement/rfqs/${rfqId}`);
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to load RFQ"));
  return resp.json();
}

export async function updateRFQ(rfqId: string, payload: RFQUpdatePayload): Promise<RFQResponse> {
  const resp = await apiFetch(`/api/v1/procurement/rfqs/${rfqId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to update RFQ"));
  return resp.json();
}

export async function submitRFQ(rfqId: string): Promise<RFQResponse> {
  const resp = await apiFetch(`/api/v1/procurement/rfqs/${rfqId}/submit`, { method: "POST" });
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to submit RFQ"));
  return resp.json();
}

export async function getRFQComparison(rfqId: string): Promise<RFQComparisonResponse> {
  const resp = await apiFetch(`/api/v1/procurement/rfqs/${rfqId}/comparison`);
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to load comparison"));
  return resp.json();
}

// ---------------------------------------------------------------------------
// Supplier Quotation API
// ---------------------------------------------------------------------------

export async function createSupplierQuotation(
  payload: SupplierQuotationCreatePayload,
): Promise<SupplierQuotationResponse> {
  const resp = await apiFetch("/api/v1/procurement/supplier-quotations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to create quotation"));
  return resp.json();
}

export async function listSupplierQuotations(params?: {
  rfq_id?: string;
  status?: string;
  q?: string;
  page?: number;
  page_size?: number;
}): Promise<SupplierQuotationListResponse> {
  const qs = new URLSearchParams();
  if (params?.rfq_id) qs.set("rfq_id", params.rfq_id);
  if (params?.status) qs.set("status", params.status);
  if (params?.q) qs.set("q", params.q);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const resp = await apiFetch(`/api/v1/procurement/supplier-quotations?${qs}`);
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to list quotations"));
  return resp.json();
}

export async function getSupplierQuotation(quotationId: string): Promise<SupplierQuotationResponse> {
  const resp = await apiFetch(`/api/v1/procurement/supplier-quotations/${quotationId}`);
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to load quotation"));
  return resp.json();
}

export async function updateSupplierQuotation(
  quotationId: string,
  payload: SupplierQuotationUpdatePayload,
): Promise<SupplierQuotationResponse> {
  const resp = await apiFetch(`/api/v1/procurement/supplier-quotations/${quotationId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to update quotation"));
  return resp.json();
}

export async function submitSupplierQuotation(quotationId: string): Promise<SupplierQuotationResponse> {
  const resp = await apiFetch(`/api/v1/procurement/supplier-quotations/${quotationId}/submit`, {
    method: "POST",
  });
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to submit quotation"));
  return resp.json();
}

// ---------------------------------------------------------------------------
// Award API (PO handoff seam)
// ---------------------------------------------------------------------------

export async function createAward(payload: AwardCreatePayload): Promise<AwardResponse> {
  const resp = await apiFetch("/api/v1/procurement/awards", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to award quotation"));
  return resp.json();
}

export async function listAwards(params?: {
  page?: number;
  page_size?: number;
}): Promise<{ items: AwardResponse[] }> {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const resp = await apiFetch(`/api/v1/procurement/awards?${qs}`);
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to list awards"));
  return resp.json();
}

export async function getRFQAward(rfqId: string): Promise<AwardResponse | null> {
  const resp = await apiFetch(`/api/v1/procurement/rfqs/${rfqId}/award`);
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to load RFQ award"));
  return resp.json();
}

// ---------------------------------------------------------------------------
// Purchase Order API
// ---------------------------------------------------------------------------

export async function createPurchaseOrder(
  payload: PurchaseOrderCreatePayload,
): Promise<PurchaseOrderResponse> {
  const resp = await apiFetch("/api/v1/procurement/purchase-orders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to create purchase order"));
  return resp.json();
}

export async function listPurchaseOrders(params?: {
  status?: string;
  supplier_id?: string;
  q?: string;
  page?: number;
  page_size?: number;
}): Promise<PurchaseOrderListResponse> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.supplier_id) qs.set("supplier_id", params.supplier_id);
  if (params?.q) qs.set("q", params.q);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const resp = await apiFetch(`/api/v1/procurement/purchase-orders?${qs}`);
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to list purchase orders"));
  return resp.json();
}

export async function getPurchaseOrder(poId: string): Promise<PurchaseOrderResponse> {
  const resp = await apiFetch(`/api/v1/procurement/purchase-orders/${poId}`);
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to load purchase order"));
  return resp.json();
}

export async function updatePurchaseOrder(
  poId: string,
  payload: PurchaseOrderUpdatePayload,
): Promise<PurchaseOrderResponse> {
  const resp = await apiFetch(`/api/v1/procurement/purchase-orders/${poId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to update purchase order"));
  return resp.json();
}

export async function submitPurchaseOrder(poId: string): Promise<PurchaseOrderResponse> {
  const resp = await apiFetch(`/api/v1/procurement/purchase-orders/${poId}/submit`, {
    method: "POST",
  });
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to submit purchase order"));
  return resp.json();
}

export async function holdPurchaseOrder(poId: string): Promise<PurchaseOrderResponse> {
  const resp = await apiFetch(`/api/v1/procurement/purchase-orders/${poId}/hold`, {
    method: "POST",
  });
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to hold purchase order"));
  return resp.json();
}

export async function releasePurchaseOrder(poId: string): Promise<PurchaseOrderResponse> {
  const resp = await apiFetch(`/api/v1/procurement/purchase-orders/${poId}/release`, {
    method: "POST",
  });
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to release purchase order"));
  return resp.json();
}

export async function completePurchaseOrder(poId: string): Promise<PurchaseOrderResponse> {
  const resp = await apiFetch(`/api/v1/procurement/purchase-orders/${poId}/complete`, {
    method: "POST",
  });
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to complete purchase order"));
  return resp.json();
}

export async function cancelPurchaseOrder(poId: string): Promise<PurchaseOrderResponse> {
  const resp = await apiFetch(`/api/v1/procurement/purchase-orders/${poId}/cancel`, {
    method: "POST",
  });
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to cancel purchase order"));
  return resp.json();
}

export async function closePurchaseOrder(poId: string): Promise<PurchaseOrderResponse> {
  const resp = await apiFetch(`/api/v1/procurement/purchase-orders/${poId}/close`, {
    method: "POST",
  });
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to close purchase order"));
  return resp.json();
}

export async function createPOFromAward(awardId: string): Promise<PurchaseOrderResponse> {
  const resp = await apiFetch(`/api/v1/procurement/awards/${awardId}/create-po`, {
    method: "GET",
  });
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to create PO from award"));
  return resp.json();
}

// ---------------------------------------------------------------------------
// Goods Receipt API (Story 24-3)
// ---------------------------------------------------------------------------

export async function createGoodsReceipt(
  payload: GoodsReceiptCreatePayload,
): Promise<GoodsReceiptResponse> {
  const resp = await apiFetch("/api/v1/procurement/goods-receipts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to create goods receipt"));
  return resp.json();
}

export async function listGoodsReceipts(params?: {
  purchase_order_id?: string;
  status?: string;
  q?: string;
  page?: number;
  page_size?: number;
}): Promise<GoodsReceiptListResponse> {
  const qs = new URLSearchParams();
  if (params?.purchase_order_id) qs.set("purchase_order_id", params.purchase_order_id);
  if (params?.status) qs.set("status", params.status);
  if (params?.q) qs.set("q", params.q);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const resp = await apiFetch(`/api/v1/procurement/goods-receipts?${qs}`);
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to list goods receipts"));
  return resp.json();
}

export async function getGoodsReceipt(grId: string): Promise<GoodsReceiptResponse> {
  const resp = await apiFetch(`/api/v1/procurement/goods-receipts/${grId}`);
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to load goods receipt"));
  return resp.json();
}

export async function submitGoodsReceipt(grId: string): Promise<GoodsReceiptResponse> {
  const resp = await apiFetch(`/api/v1/procurement/goods-receipts/${grId}/submit`, {
    method: "POST",
  });
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to submit goods receipt"));
  return resp.json();
}

export async function cancelGoodsReceipt(grId: string): Promise<GoodsReceiptResponse> {
  const resp = await apiFetch(`/api/v1/procurement/goods-receipts/${grId}/cancel`, {
    method: "POST",
  });
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to cancel goods receipt"));
  return resp.json();
}

export async function listReceiptsForPO(poId: string, params?: {
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<GoodsReceiptListResponse> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const resp = await apiFetch(`/api/v1/procurement/purchase-orders/${poId}/receipts?${qs}`);
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to list receipts for PO"));
  return resp.json();
}

// ---------------------------------------------------------------------------
// Procurement Lineage - Downstream Invoice Links (Story 24-4)
// ---------------------------------------------------------------------------

/**
 * Invoices linked to a purchase order (Story 24-4).
 */
export interface POLineageResponse {
  purchase_order_id: string;
  purchase_order_name: string;
  linked_invoices: {
    invoice_id: string;
    invoice_number: string;
    invoice_date: string;
    total_amount: string;
    status: string;
    linked_lines: number;
  }[];
}

/**
 * Invoices linked to a goods receipt line (Story 24-4).
 */
export interface GRLineageResponse {
  goods_receipt_id: string;
  goods_receipt_name: string;
  linked_invoices: {
    invoice_id: string;
    invoice_number: string;
    invoice_date: string;
    total_amount: string;
    status: string;
    linked_lines: number;
  }[];
}

/**
 * Fetch downstream supplier invoices linked to a purchase order (Story 24-4).
 * Allows procurement users to see what invoices reference their PO.
 */
export async function fetchPOLineage(poId: string): Promise<POLineageResponse> {
  const resp = await apiFetch(`/api/v1/procurement/purchase-orders/${poId}/invoice-lineage`);
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to load PO invoice lineage"));
  return resp.json();
}

/**
 * Fetch downstream supplier invoices linked to a goods receipt line (Story 24-4).
 * Allows procurement users to see what invoices reference their receipt.
 */
export async function fetchGRLineage(grId: string, grLineId: string): Promise<GRLineageResponse> {
  const resp = await apiFetch(
    `/api/v1/procurement/goods-receipts/${grId}/lines/${grLineId}/invoice-lineage`,
  );
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to load GR invoice lineage"));
  return resp.json();
}

// --------------------------------------------------------------------------
// Supplier Controls API (Story 24-5)
// --------------------------------------------------------------------------

import type {
  SupplierControlResult,
  SupplierControlsStatus,
  ProcurementSummary,
  QuoteTurnaroundStats,
  SupplierPerformanceStats,
} from "../../domain/procurement/types";

/**
 * Get detailed supplier control status (Story 24-5).
 */
export async function getSupplierControls(supplierId: string): Promise<SupplierControlsStatus> {
  const resp = await apiFetch(`/api/v1/procurement/suppliers/${supplierId}/controls`);
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to load supplier controls"));
  return resp.json();
}

/**
 * Check RFQ controls for a supplier (Story 24-5).
 */
export async function checkSupplierRFQControls(supplierId: string): Promise<SupplierControlResult> {
  const resp = await apiFetch(`/api/v1/procurement/suppliers/${supplierId}/check-rfq-controls`, {
    method: "POST",
  });
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to check RFQ controls"));
  return resp.json();
}

/**
 * Check PO controls for a supplier (Story 24-5).
 */
export async function checkSupplierPOControls(supplierId: string): Promise<SupplierControlResult> {
  const resp = await apiFetch(`/api/v1/procurement/suppliers/${supplierId}/check-po-controls`, {
    method: "POST",
  });
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to check PO controls"));
  return resp.json();
}

// --------------------------------------------------------------------------
// Procurement Reporting API (Story 24-5)
// --------------------------------------------------------------------------

/**
 * Get procurement summary statistics (Story 24-5).
 */
export async function getProcurementSummary(params?: {
  date_from?: string;
  date_to?: string;
}): Promise<ProcurementSummary> {
  const qs = new URLSearchParams();
  if (params?.date_from) qs.set("date_from", params.date_from);
  if (params?.date_to) qs.set("date_to", params.date_to);
  const resp = await apiFetch(`/api/v1/procurement/reports/procurement-summary?${qs}`);
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to load procurement summary"));
  return resp.json();
}

/**
 * Get quote turnaround statistics (Story 24-5).
 */
export async function getQuoteTurnaroundStats(rfqId?: string): Promise<QuoteTurnaroundStats> {
  const qs = new URLSearchParams();
  if (rfqId) qs.set("rfq_id", rfqId);
  const resp = await apiFetch(`/api/v1/procurement/reports/quote-turnaround?${qs}`);
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to load quote turnaround stats"));
  return resp.json();
}

/**
 * Get supplier performance statistics (Story 24-5).
 */
export async function getSupplierPerformanceStats(supplierId?: string): Promise<SupplierPerformanceStats> {
  const qs = new URLSearchParams();
  if (supplierId) qs.set("supplier_id", supplierId);
  const resp = await apiFetch(`/api/v1/procurement/reports/supplier-performance?${qs}`);
  if (!resp.ok) throw new Error(await parseErrorMessage(resp, "Failed to load supplier performance stats"));
  return resp.json();
}
