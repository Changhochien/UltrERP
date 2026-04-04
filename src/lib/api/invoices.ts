/** Invoice API helpers. */

import { apiFetch } from "../apiFetch";
import type {
  InvoiceCreatePayload,
  CustomerOutstandingSummary,
  InvoiceEguiSubmission,
  InvoiceListResponse,
  InvoiceResponse,
} from "../../domain/invoices/types";

interface ApiError {
  detail: Array<{ field: string; message: string }>;
}

interface ApiErrorDetailResponse {
  detail?: string;
}

const NETWORK_ERROR_MESSAGE = "Unable to reach the server. Please try again.";

export class ApiResponseError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiResponseError";
    this.status = status;
  }
}

function networkErrorDetail(): ApiError["detail"] {
  return [{ field: "", message: NETWORK_ERROR_MESSAGE }];
}

async function responseErrorMessage(
  resp: Response,
  fallback: string,
): Promise<string> {
  const body = await resp.json().catch(() => null) as ApiError | ApiErrorDetailResponse | null;
  if (typeof body?.detail === "string" && body.detail.trim()) {
    return body.detail;
  }
  if (Array.isArray(body?.detail)) {
    const messages = body.detail
      .map((entry) => (entry && typeof entry.message === "string" ? entry.message : ""))
      .filter(Boolean);
    if (messages.length > 0) {
      return messages.join("; ");
    }
  }
  return fallback;
}

export type CreateInvoiceResult =
  | { ok: true; data: InvoiceResponse }
  | { ok: false; errors: ApiError["detail"] };

export async function createInvoice(
  payload: InvoiceCreatePayload,
): Promise<CreateInvoiceResult> {
  let resp: Response;
  try {
    resp = await apiFetch("/api/v1/invoices", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: InvoiceResponse = await resp.json();
    return { ok: true, data };
  }

  const body: ApiError = await resp.json().catch(() => ({ detail: [] }));
  return { ok: false, errors: body.detail ?? [] };
}

export async function fetchInvoices(params?: {
  payment_status?: string;
  sort_by?: string;
  sort_order?: string;
  page?: number;
  page_size?: number;
}): Promise<InvoiceListResponse> {
  const qs = new URLSearchParams();
  if (params?.payment_status) qs.set("payment_status", params.payment_status);
  if (params?.sort_by) qs.set("sort_by", params.sort_by);
  if (params?.sort_order) qs.set("sort_order", params.sort_order);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const qsStr = qs.toString();
  const url = `/api/v1/invoices${qsStr ? `?${qsStr}` : ""}`;
  const resp = await apiFetch(url);
  if (!resp.ok) throw new Error("Failed to fetch invoices");
  return resp.json();
}

export async function fetchInvoice(invoiceId: string): Promise<InvoiceResponse> {
  const resp = await apiFetch(`/api/v1/invoices/${encodeURIComponent(invoiceId)}`);
  if (!resp.ok) {
    const fallback = resp.status === 404 ? "Invoice not found" : "Failed to load invoice";
    throw new Error(await responseErrorMessage(resp, fallback));
  }
  return resp.json();
}

export async function refreshInvoiceEguiStatus(
  invoiceId: string,
): Promise<InvoiceEguiSubmission> {
  const resp = await apiFetch(
    `/api/v1/invoices/${encodeURIComponent(invoiceId)}/egui/refresh`,
    { method: "POST" },
  );
  if (!resp.ok) {
    throw new ApiResponseError(
      resp.status,
      await responseErrorMessage(resp, "Failed to refresh eGUI status"),
    );
  }
  return resp.json();
}

export async function fetchCustomerOutstanding(
  customerId: string,
): Promise<CustomerOutstandingSummary> {
  const resp = await apiFetch(
    `/api/v1/customers/${encodeURIComponent(customerId)}/outstanding`,
  );
  if (!resp.ok) {
    throw new Error(
      await responseErrorMessage(resp, "Failed to fetch customer outstanding"),
    );
  }
  return resp.json();
}
