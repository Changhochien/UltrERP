/** Orders API helpers. */

import { apiFetch } from "../apiFetch";
import type {
  OrderCreatePayload,
  OrderListResponse,
  OrderResponse,
  OrderStatus,
  PaymentTermsListResponse,
  StockCheckResponse,
} from "../../domain/orders/types";

export interface OrderApiError {
  detail: Array<{ field: string; message: string }> | string;
}

export async function fetchPaymentTerms(): Promise<PaymentTermsListResponse> {
  const resp = await apiFetch("/api/v1/orders/payment-terms");
  if (!resp.ok) throw new Error("Failed to fetch payment terms");
  return resp.json();
}

export async function createOrder(
  payload: OrderCreatePayload,
): Promise<
  | { ok: true; data: OrderResponse }
  | { ok: false; errors: Array<{ field: string; message: string }> }
> {
  let resp: Response;
  try {
    resp = await apiFetch("/api/v1/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: [{ field: "", message: "Unable to reach the server. Please try again." }] };
  }

  if (resp.ok) {
    const data: OrderResponse = await resp.json();
    return { ok: true, data };
  }

  const body: OrderApiError = await resp.json().catch(() => ({ detail: "Unknown error" }));
  if (typeof body.detail === "string") {
    return { ok: false, errors: [{ field: "", message: body.detail }] };
  }
  return { ok: false, errors: body.detail ?? [] };
}

export async function fetchOrders(params?: {
  status?: string | string[];
  customer_id?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
  sort_by?: string;
  sort_order?: string;
  page?: number;
  page_size?: number;
}): Promise<OrderListResponse> {
  const qs = new URLSearchParams();
  if (params?.status) {
    if (Array.isArray(params.status)) {
      params.status.forEach((v) => qs.append("status", v));
    } else {
      qs.set("status", params.status);
    }
  }
  if (params?.customer_id) qs.set("customer_id", params.customer_id);
  if (params?.date_from) qs.set("date_from", params.date_from);
  if (params?.date_to) qs.set("date_to", params.date_to);
  if (params?.search) qs.set("search", params.search);
  if (params?.sort_by) qs.set("sort_by", params.sort_by);
  if (params?.sort_order) qs.set("sort_order", params.sort_order);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const qsStr = qs.toString();
  const url = `/api/v1/orders${qsStr ? `?${qsStr}` : ""}`;
  const resp = await apiFetch(url);
  if (!resp.ok) throw new Error("Failed to fetch orders");
  return resp.json();
}

export async function fetchOrder(orderId: string): Promise<OrderResponse> {
  const resp = await apiFetch(`/api/v1/orders/${encodeURIComponent(orderId)}`);
  if (!resp.ok) throw new Error("Order not found");
  return resp.json();
}

export async function checkStock(productId: string): Promise<StockCheckResponse> {
  const resp = await apiFetch(
    `/api/v1/orders/check-stock?product_id=${encodeURIComponent(productId)}`,
  );
  if (!resp.ok) throw new Error("Failed to check stock");
  return resp.json();
}

export async function updateOrderStatus(
  orderId: string,
  newStatus: OrderStatus,
): Promise<
  | { ok: true; data: OrderResponse }
  | { ok: false; error: string }
> {
  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/orders/${encodeURIComponent(orderId)}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ new_status: newStatus }),
    });
  } catch {
    return { ok: false, error: "Unable to reach the server." };
  }

  if (resp.ok) {
    const data: OrderResponse = await resp.json();
    return { ok: true, data };
  }

  const body = await resp.json().catch(() => ({ detail: "Unknown error" }));
  const msg = typeof body.detail === "string" ? body.detail : "Status update failed";
  return { ok: false, error: msg };
}
