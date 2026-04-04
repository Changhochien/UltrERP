/** Inventory API helpers. */

import { apiFetch } from "../apiFetch";
import type {
  AcknowledgeAlertResponse,
  CreateSupplierOrderRequest,
  ProductDetail,
  ProductSearchResponse,
  ReasonCodeListResponse,
  ReceiveOrderRequest,
  ReorderAlertListResponse,
  StockAdjustmentRequest,
  StockAdjustmentResponse,
  SupplierListResponse,
  SupplierOrder,
  SupplierOrderListResponse,
  TransferRequest,
  TransferResponse,
  UpdateOrderStatusRequest,
  Warehouse,
  WarehouseListResponse,
} from "../../domain/inventory/types";

export async function fetchWarehouses(
  activeOnly = true,
): Promise<WarehouseListResponse> {
  const resp = await apiFetch(
    `/api/v1/inventory/warehouses?active_only=${activeOnly}`,
  );
  if (!resp.ok) throw new Error("Failed to fetch warehouses");
  return resp.json();
}

export async function fetchWarehouse(id: string): Promise<Warehouse> {
  const resp = await apiFetch(`/api/v1/inventory/warehouses/${id}`);
  if (!resp.ok) throw new Error("Warehouse not found");
  return resp.json();
}

export interface TransferError {
  detail: string;
  available?: number;
  requested?: number;
}

export async function createTransfer(
  payload: TransferRequest,
): Promise<
  | { ok: true; data: TransferResponse }
  | { ok: false; error: TransferError }
> {
  const resp = await apiFetch("/api/v1/inventory/transfers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (resp.ok) {
    const data: TransferResponse = await resp.json();
    return { ok: true, data };
  }

  const error: TransferError = await resp.json();
  return { ok: false, error };
}

export async function searchProducts(
  query: string,
  options?: { limit?: number; warehouseId?: string; signal?: AbortSignal },
): Promise<ProductSearchResponse> {
  const params = new URLSearchParams({ q: query });
  if (options?.limit) params.set("limit", String(options.limit));
  if (options?.warehouseId) params.set("warehouse_id", options.warehouseId);
  const resp = await apiFetch(
    `/api/v1/inventory/products/search?${params.toString()}`,
    { signal: options?.signal },
  );
  if (!resp.ok) throw new Error("Search failed");
  return resp.json();
}

export async function fetchProductDetail(
  productId: string,
  options?: { historyLimit?: number; historyOffset?: number },
): Promise<ProductDetail> {
  const params = new URLSearchParams();
  if (options?.historyLimit != null)
    params.set("history_limit", String(options.historyLimit));
  if (options?.historyOffset != null)
    params.set("history_offset", String(options.historyOffset));
  const qs = params.toString();
  const url = `/api/v1/inventory/products/${encodeURIComponent(productId)}${qs ? `?${qs}` : ""}`;
  const resp = await apiFetch(url);
  if (!resp.ok) throw new Error("Failed to fetch product detail");
  return resp.json();
}

export async function fetchReasonCodes(): Promise<ReasonCodeListResponse> {
  const resp = await apiFetch("/api/v1/inventory/reason-codes");
  if (!resp.ok) throw new Error("Failed to fetch reason codes");
  return resp.json();
}

export interface AdjustmentError {
  detail: string | { message: string; available?: number; requested?: number };
}

export async function submitAdjustment(
  payload: StockAdjustmentRequest,
): Promise<
  | { ok: true; data: StockAdjustmentResponse }
  | { ok: false; error: AdjustmentError }
> {
  const resp = await apiFetch("/api/v1/inventory/adjustments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (resp.ok) {
    const data: StockAdjustmentResponse = await resp.json();
    return { ok: true, data };
  }

  const error: AdjustmentError = await resp.json();
  return { ok: false, error };
}

export async function fetchReorderAlerts(options?: {
  status?: string;
  warehouseId?: string;
  limit?: number;
  offset?: number;
}): Promise<ReorderAlertListResponse> {
  const params = new URLSearchParams();
  if (options?.status) params.set("status", options.status);
  if (options?.warehouseId) params.set("warehouse_id", options.warehouseId);
  if (options?.limit != null) params.set("limit", String(options.limit));
  if (options?.offset != null) params.set("offset", String(options.offset));
  const qs = params.toString();
  const url = `/api/v1/inventory/alerts/reorder${qs ? `?${qs}` : ""}`;
  const resp = await apiFetch(url);
  if (!resp.ok) throw new Error("Failed to fetch reorder alerts");
  return resp.json();
}

export async function acknowledgeAlert(
  alertId: string,
): Promise<
  | { ok: true; data: AcknowledgeAlertResponse }
  | { ok: false; error: string }
> {
  const resp = await apiFetch(
    `/api/v1/inventory/alerts/reorder/${encodeURIComponent(alertId)}/acknowledge`,
    { method: "PUT" },
  );
  if (resp.ok) {
    const data: AcknowledgeAlertResponse = await resp.json();
    return { ok: true, data };
  }
  const body = await resp.json().catch(() => ({ detail: "Unknown error" }));
  return { ok: false, error: body.detail ?? "Failed to acknowledge alert" };
}

// --- Supplier API ---

export async function fetchSuppliers(
  activeOnly = true,
): Promise<SupplierListResponse> {
  const resp = await apiFetch(
    `/api/v1/inventory/suppliers?active_only=${activeOnly}`,
  );
  if (!resp.ok) throw new Error("Failed to fetch suppliers");
  return resp.json();
}

// --- Supplier order API ---

export async function createSupplierOrder(
  payload: CreateSupplierOrderRequest,
): Promise<
  | { ok: true; data: SupplierOrder }
  | { ok: false; error: string }
> {
  const resp = await apiFetch("/api/v1/inventory/supplier-orders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (resp.ok) {
    const data: SupplierOrder = await resp.json();
    return { ok: true, data };
  }

  const body = await resp.json().catch(() => ({ detail: "Unknown error" }));
  return { ok: false, error: body.detail ?? "Failed to create supplier order" };
}

export async function fetchSupplierOrders(options?: {
  status?: string;
  supplierId?: string;
  limit?: number;
  offset?: number;
}): Promise<SupplierOrderListResponse> {
  const params = new URLSearchParams();
  if (options?.status) params.set("status", options.status);
  if (options?.supplierId) params.set("supplier_id", options.supplierId);
  if (options?.limit != null) params.set("limit", String(options.limit));
  if (options?.offset != null) params.set("offset", String(options.offset));
  const qs = params.toString();
  const url = `/api/v1/inventory/supplier-orders${qs ? `?${qs}` : ""}`;
  const resp = await apiFetch(url);
  if (!resp.ok) throw new Error("Failed to fetch supplier orders");
  return resp.json();
}

export async function fetchSupplierOrder(
  orderId: string,
): Promise<SupplierOrder> {
  const resp = await apiFetch(
    `/api/v1/inventory/supplier-orders/${encodeURIComponent(orderId)}`,
  );
  if (!resp.ok) throw new Error("Supplier order not found");
  return resp.json();
}

export async function updateSupplierOrderStatus(
  orderId: string,
  payload: UpdateOrderStatusRequest,
): Promise<
  | { ok: true; data: SupplierOrder }
  | { ok: false; error: string }
> {
  const resp = await apiFetch(
    `/api/v1/inventory/supplier-orders/${encodeURIComponent(orderId)}/status`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );

  if (resp.ok) {
    const data: SupplierOrder = await resp.json();
    return { ok: true, data };
  }

  const body = await resp.json().catch(() => ({ detail: "Unknown error" }));
  return { ok: false, error: body.detail ?? "Failed to update order status" };
}

export async function receiveSupplierOrder(
  orderId: string,
  payload: ReceiveOrderRequest,
): Promise<
  | { ok: true; data: SupplierOrder }
  | { ok: false; error: string }
> {
  const resp = await apiFetch(
    `/api/v1/inventory/supplier-orders/${encodeURIComponent(orderId)}/receive`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );

  if (resp.ok) {
    const data: SupplierOrder = await resp.json();
    return { ok: true, data };
  }

  const body = await resp.json().catch(() => ({ detail: "Unknown error" }));
  return { ok: false, error: body.detail ?? "Failed to receive order" };
}
