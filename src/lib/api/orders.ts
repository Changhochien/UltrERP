/** Orders API helpers. */

import type {
  OrderCreatePayload,
  OrderListResponse,
  OrderResponse,
  PaymentTermsListResponse,
  StockCheckResponse,
} from "../../domain/orders/types";

export interface OrderApiError {
  detail: Array<{ field: string; message: string }> | string;
}

export async function fetchPaymentTerms(): Promise<PaymentTermsListResponse> {
  const resp = await fetch("/api/v1/orders/payment-terms");
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
    resp = await fetch("/api/v1/orders", {
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
  status?: string;
  customer_id?: string;
  page?: number;
  page_size?: number;
}): Promise<OrderListResponse> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.customer_id) qs.set("customer_id", params.customer_id);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const qsStr = qs.toString();
  const url = `/api/v1/orders${qsStr ? `?${qsStr}` : ""}`;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error("Failed to fetch orders");
  return resp.json();
}

export async function fetchOrder(orderId: string): Promise<OrderResponse> {
  const resp = await fetch(`/api/v1/orders/${encodeURIComponent(orderId)}`);
  if (!resp.ok) throw new Error("Order not found");
  return resp.json();
}

export async function checkStock(productId: string): Promise<StockCheckResponse> {
  const resp = await fetch(
    `/api/v1/orders/check-stock?product_id=${encodeURIComponent(productId)}`,
  );
  if (!resp.ok) throw new Error("Failed to check stock");
  return resp.json();
}

export async function updateOrderStatus(
  orderId: string,
  newStatus: string,
): Promise<
  | { ok: true; data: OrderResponse }
  | { ok: false; error: string }
> {
  let resp: Response;
  try {
    resp = await fetch(`/api/v1/orders/${encodeURIComponent(orderId)}/status`, {
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
