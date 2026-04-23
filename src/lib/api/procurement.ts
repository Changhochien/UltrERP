/** Procurement API client - RFQ and Supplier Quotation workspace. */

import type {
  AwardCreatePayload,
  AwardResponse,
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

export interface ProcurementApiError {
  detail: Array<{ field: string; message: string }>;
}

const NETWORK_ERROR_MESSAGE = "Unable to reach the server. Please try again.";

async function parseErrorDetails(resp: Response): Promise<ProcurementApiError["detail"]> {
  const body = await resp.json().catch(() => null);
  if (Array.isArray(body?.detail)) {
    return body.detail;
  }
  if (typeof body?.detail === "string") {
    return [{ field: "", message: body.detail }];
  }
  return [{ field: "", message: NETWORK_ERROR_MESSAGE }];
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
  if (!resp.ok) {
    const details = await parseErrorDetails(resp);
    throw new Error(details[0]?.message ?? "Failed to create RFQ");
  }
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
  if (!resp.ok) {
    const details = await parseErrorDetails(resp);
    throw new Error(details[0]?.message ?? "Failed to list RFQs");
  }
  return resp.json();
}

export async function getRFQ(rfqId: string): Promise<RFQResponse> {
  const resp = await apiFetch(`/api/v1/procurement/rfqs/${rfqId}`);
  if (!resp.ok) {
    const details = await parseErrorDetails(resp);
    throw new Error(details[0]?.message ?? "Failed to load RFQ");
  }
  return resp.json();
}

export async function updateRFQ(
  rfqId: string,
  payload: RFQUpdatePayload,
): Promise<RFQResponse> {
  const resp = await apiFetch(`/api/v1/procurement/rfqs/${rfqId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const details = await parseErrorDetails(resp);
    throw new Error(details[0]?.message ?? "Failed to update RFQ");
  }
  return resp.json();
}

export async function submitRFQ(rfqId: string): Promise<RFQResponse> {
  const resp = await apiFetch(`/api/v1/procurement/rfqs/${rfqId}/submit`, {
    method: "POST",
  });
  if (!resp.ok) {
    const details = await parseErrorDetails(resp);
    throw new Error(details[0]?.message ?? "Failed to submit RFQ");
  }
  return resp.json();
}

export async function getRFQComparison(rfqId: string): Promise<RFQComparisonResponse> {
  const resp = await apiFetch(`/api/v1/procurement/rfqs/${rfqId}/comparison`);
  if (!resp.ok) {
    const details = await parseErrorDetails(resp);
    throw new Error(details[0]?.message ?? "Failed to load comparison");
  }
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
  if (!resp.ok) {
    const details = await parseErrorDetails(resp);
    throw new Error(details[0]?.message ?? "Failed to create supplier quotation");
  }
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
  if (!resp.ok) {
    const details = await parseErrorDetails(resp);
    throw new Error(details[0]?.message ?? "Failed to list supplier quotations");
  }
  return resp.json();
}

export async function getSupplierQuotation(quotationId: string): Promise<SupplierQuotationResponse> {
  const resp = await apiFetch(`/api/v1/procurement/supplier-quotations/${quotationId}`);
  if (!resp.ok) {
    const details = await parseErrorDetails(resp);
    throw new Error(details[0]?.message ?? "Failed to load supplier quotation");
  }
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
  if (!resp.ok) {
    const details = await parseErrorDetails(resp);
    throw new Error(details[0]?.message ?? "Failed to update supplier quotation");
  }
  return resp.json();
}

export async function submitSupplierQuotation(quotationId: string): Promise<SupplierQuotationResponse> {
  const resp = await apiFetch(`/api/v1/procurement/supplier-quotations/${quotationId}/submit`, {
    method: "POST",
  });
  if (!resp.ok) {
    const details = await parseErrorDetails(resp);
    throw new Error(details[0]?.message ?? "Failed to submit supplier quotation");
  }
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
  if (!resp.ok) {
    const details = await parseErrorDetails(resp);
    throw new Error(details[0]?.message ?? "Failed to award quotation");
  }
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
  if (!resp.ok) {
    const details = await parseErrorDetails(resp);
    throw new Error(details[0]?.message ?? "Failed to list awards");
  }
  return resp.json();
}

export async function getRFQAward(rfqId: string): Promise<AwardResponse | null> {
  const resp = await apiFetch(`/api/v1/procurement/rfqs/${rfqId}/award`);
  if (!resp.ok) {
    const details = await parseErrorDetails(resp);
    throw new Error(details[0]?.message ?? "Failed to load RFQ award");
  }
  return resp.json();
}
