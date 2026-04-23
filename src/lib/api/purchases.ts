import { apiFetch } from "../apiFetch";
import type {
  SupplierInvoice,
  SupplierInvoiceWithLineage,
  SupplierInvoiceListResponse,
  SupplierInvoiceStatus,
  LineageChainResponse,
} from "../../domain/purchases/types";

async function responseErrorMessage(
  resp: Response,
  fallback: string,
): Promise<string> {
  const body = await resp.json().catch(() => null) as { detail?: string } | null;
  if (typeof body?.detail === "string" && body.detail.trim()) {
    return body.detail;
  }
  return fallback;
}

export async function fetchSupplierInvoices(params?: {
  status?: SupplierInvoiceStatus;
  page?: number;
  page_size?: number;
  sort_by?: "created_at" | "invoice_date" | "total_amount";
  sort_order?: "asc" | "desc";
}): Promise<SupplierInvoiceListResponse> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  if (params?.sort_by) qs.set("sort_by", params.sort_by);
  if (params?.sort_order) qs.set("sort_order", params.sort_order);
  const qsStr = qs.toString();
  const url = `/api/v1/purchases/supplier-invoices${qsStr ? `?${qsStr}` : ""}`;
  const resp = await apiFetch(url);
  if (!resp.ok) {
    throw new Error(await responseErrorMessage(resp, "Failed to fetch supplier invoices"));
  }
  return resp.json();
}

export async function fetchSupplierInvoice(invoiceId: string): Promise<SupplierInvoice> {
  const resp = await apiFetch(
    `/api/v1/purchases/supplier-invoices/${encodeURIComponent(invoiceId)}`,
  );
  if (!resp.ok) {
    const fallback = resp.status === 404
      ? "Supplier invoice not found"
      : "Failed to load supplier invoice";
    throw new Error(await responseErrorMessage(resp, fallback));
  }
  return resp.json();
}

/**
 * Fetch supplier invoice with procurement lineage trace (Story 24-4).
 * 
 * Returns full lineage chain from RFQ through supplier quotation,
 * PO, goods receipt, to supplier invoice for audit and three-way-match review.
 * 
 * Note: This is a readiness endpoint - no AP posting workflow is implemented.
 */
export async function fetchSupplierInvoiceWithLineage(invoiceId: string): Promise<SupplierInvoiceWithLineage> {
  const resp = await apiFetch(
    `/api/v1/purchases/supplier-invoices/${encodeURIComponent(invoiceId)}/lineage`,
  );
  if (!resp.ok) {
    const fallback = resp.status === 404
      ? "Supplier invoice not found"
      : "Failed to load supplier invoice lineage";
    throw new Error(await responseErrorMessage(resp, fallback));
  }
  return resp.json();
}

/**
 * Fetch full lineage chain for a supplier invoice (Story 24-4).
 * 
 * Provides detailed lineage trace including upstream document references.
 * Used for audit views and three-way-match review screens.
 */
export async function fetchSupplierInvoiceLineage(invoiceId: string): Promise<LineageChainResponse> {
  const resp = await apiFetch(
    `/api/v1/purchases/supplier-invoices/${encodeURIComponent(invoiceId)}/lineage-chain`,
  );
  if (!resp.ok) {
    const fallback = resp.status === 404
      ? "Supplier invoice not found"
      : "Failed to load supplier invoice lineage chain";
    throw new Error(await responseErrorMessage(resp, fallback));
  }
  return resp.json();
}
