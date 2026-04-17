import { apiFetch } from "../apiFetch";
import type {
  AcknowledgeAlertResponse,
  DismissAlertResponse,
  PlanningSupportResponse,
  ProductSearchResponse,
  ProductDetail,
  ReorderAlertListResponse,
  SnoozeAlertResponse,
  WarehouseListResponse,
  TransferResponse,
  ReasonCodeListResponse,
  StockAdjustmentResponse,
  SupplierListResponse,
  SupplierOrderListResponse,
  SupplierOrder,
  UpdateOrderStatusRequest,
  ReceiveOrderRequest,
  CreateSupplierOrderRequest,
} from "../../domain/inventory/types";

export async function searchProducts(
  query: string,
  options?: {
    limit?: number;
    offset?: number;
    warehouseId?: string;
    sortBy?: string;
    sortDir?: string;
    signal?: AbortSignal;
  },
): Promise<ProductSearchResponse> {
  const params = new URLSearchParams({ q: query });
  if (options?.limit) params.set("limit", String(options.limit));
  if (options?.offset) params.set("offset", String(options.offset));
  if (options?.warehouseId) params.set("warehouse_id", options.warehouseId);
  if (options?.sortBy) params.set("sort_by", options.sortBy);
  if (options?.sortDir) params.set("sort_dir", options.sortDir);
  const resp = await apiFetch(
    `/api/v1/inventory/products/search?${params.toString()}`,
    { signal: options?.signal },
  );
  if (!resp.ok) throw new Error("Search failed");
  return resp.json() as Promise<ProductSearchResponse>;
}

export async function fetchProductDetail(
  productId: string,
  options?: { historyLimit?: number; historyOffset?: number },
): Promise<{ ok: true; data: ProductDetail } | { ok: false; error: string }> {
  try {
    const params = new URLSearchParams();
    if (options?.historyLimit != null)
      params.set("history_limit", String(options.historyLimit));
    if (options?.historyOffset != null)
      params.set("history_offset", String(options.historyOffset));
    const qs = params.toString();
    const url = `/api/v1/inventory/products/${encodeURIComponent(productId)}${qs ? `?${qs}` : ""}`;
    const resp = await apiFetch(url);
    if (!resp.ok) return { ok: false, error: "Failed to fetch product detail" };
    return { ok: true, data: (await resp.json()) as ProductDetail };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function fetchPlanningSupport(
  productId: string,
  options?: {
    months?: number;
    includeCurrentMonth?: boolean;
    signal?: AbortSignal;
  },
): Promise<{ ok: true; data: PlanningSupportResponse } | { ok: false; error: string }> {
  try {
    const params = new URLSearchParams();
    if (options?.months != null) params.set("months", String(options.months));
    if (options?.includeCurrentMonth != null) {
      params.set("include_current_month", String(options.includeCurrentMonth));
    }
    const qs = params.toString();
    const resp = await apiFetch(
      `/api/v1/inventory/products/${encodeURIComponent(productId)}/planning-support${qs ? `?${qs}` : ""}`,
      { signal: options?.signal },
    );
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      return {
        ok: false,
        error: (body as { detail?: string }).detail ?? "Failed to fetch planning support",
      };
    }
    return { ok: true, data: (await resp.json()) as PlanningSupportResponse };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function fetchReorderAlerts(options?: {
  status?: string;
  warehouseId?: string;
  limit?: number;
  offset?: number;
}): Promise<{ ok: true; data: ReorderAlertListResponse } | { ok: false; error: string }> {
  try {
    const params = new URLSearchParams();
    if (options?.status) params.set("status", options.status);
    if (options?.warehouseId) params.set("warehouse_id", options.warehouseId);
    if (options?.limit != null) params.set("limit", String(options.limit));
    if (options?.offset != null) params.set("offset", String(options.offset));
    const qs = params.toString();
    const resp = await apiFetch(`/api/v1/inventory/alerts/reorder${qs ? `?${qs}` : ""}`);
    if (!resp.ok) return { ok: false, error: "Failed to fetch reorder alerts" };
    return { ok: true, data: (await resp.json()) as ReorderAlertListResponse };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function acknowledgeAlert(
  alertId: string,
): Promise<
  { ok: true; data: AcknowledgeAlertResponse } |
  { ok: false; error: string; alreadyResolved?: boolean }
> {
  try {
    const resp = await apiFetch(
      `/api/v1/inventory/alerts/reorder/${encodeURIComponent(alertId)}/acknowledge`,
      { method: "PUT" },
    );
    const body = await resp.json().catch(() => ({}));
    // Handle "already resolved" case (HTTP 200 with status: "already_resolved")
    if ((body as { status?: string }).status === "already_resolved") {
      return { ok: false, error: "Alert was already resolved", alreadyResolved: true };
    }
    if (!resp.ok) {
      return { ok: false, error: (body as { detail?: string }).detail ?? "Failed to acknowledge alert" };
    }
    return { ok: true, data: body as AcknowledgeAlertResponse };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function snoozeAlert(
  alertId: string,
  durationMinutes: number,
): Promise<
  { ok: true; data: SnoozeAlertResponse } |
  { ok: false; error: string; alreadyResolved?: boolean }
> {
  try {
    const resp = await apiFetch(
      `/api/v1/inventory/alerts/reorder/${encodeURIComponent(alertId)}/snooze`,
      {
        method: "PUT",
        body: JSON.stringify({ duration_minutes: durationMinutes }),
      },
    );
    const body = await resp.json().catch(() => ({}));
    if ((body as { status?: string }).status === "already_resolved") {
      return { ok: false, error: "Alert was already closed", alreadyResolved: true };
    }
    if (!resp.ok) {
      return { ok: false, error: (body as { detail?: string }).detail ?? "Failed to snooze alert" };
    }
    return { ok: true, data: body as SnoozeAlertResponse };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function dismissAlert(
  alertId: string,
): Promise<
  { ok: true; data: DismissAlertResponse } |
  { ok: false; error: string; alreadyResolved?: boolean }
> {
  try {
    const resp = await apiFetch(
      `/api/v1/inventory/alerts/reorder/${encodeURIComponent(alertId)}/dismiss`,
      { method: "PUT" },
    );
    const body = await resp.json().catch(() => ({}));
    if ((body as { status?: string }).status === "already_resolved") {
      return { ok: false, error: "Alert was already closed", alreadyResolved: true };
    }
    if (!resp.ok) {
      return { ok: false, error: (body as { detail?: string }).detail ?? "Failed to dismiss alert" };
    }
    return { ok: true, data: body as DismissAlertResponse };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function fetchWarehouses(
  activeOnly = true,
): Promise<{ ok: true; data: WarehouseListResponse } | { ok: false; error: string }> {
  try {
    const params = new URLSearchParams();
    if (activeOnly) params.set("active", "1");
    const qs = params.toString();
    const resp = await apiFetch(`/api/v1/inventory/warehouses${qs ? `?${qs}` : ""}`);
    if (!resp.ok) return { ok: false, error: "Failed to fetch warehouses" };
    return { ok: true, data: (await resp.json()) as WarehouseListResponse };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function createTransfer(data: {
  from_warehouse_id: string;
  to_warehouse_id: string;
  product_id: string;
  quantity: number;
  notes?: string;
}): Promise<{ ok: true; data: TransferResponse } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch("/api/v1/inventory/transfers", {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      return { ok: false, error: (body as { detail?: string }).detail ?? "Failed to create transfer" };
    }
    return { ok: true, data: (await resp.json()) as TransferResponse };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function fetchReasonCodes(): Promise<{
  ok: true;
  data: ReasonCodeListResponse;
} | { ok: false; error: string }> {
  try {
    const resp = await apiFetch("/api/v1/inventory/reason-codes");
    if (!resp.ok) return { ok: false, error: "Failed to fetch reason codes" };
    return { ok: true, data: (await resp.json()) as ReasonCodeListResponse };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function submitAdjustment(
  data: {
    product_id: string;
    warehouse_id: string;
    quantity_change: number;
    reason_code: string;
    notes?: string;
  },
): Promise<{ ok: true; data: StockAdjustmentResponse } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch("/api/v1/inventory/adjustments", {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      return { ok: false, error: (body as { detail?: string }).detail ?? "Failed to submit adjustment" };
    }
    return { ok: true, data: (await resp.json()) as StockAdjustmentResponse };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function fetchSuppliers(): Promise<{
  ok: true;
  data: SupplierListResponse;
} | { ok: false; error: string }> {
  try {
    const resp = await apiFetch("/api/v1/inventory/suppliers");
    if (!resp.ok) return { ok: false, error: "Failed to fetch suppliers" };
    return { ok: true, data: (await resp.json()) as SupplierListResponse };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function createSupplierOrder(
  data: CreateSupplierOrderRequest,
): Promise<{ ok: true; data: SupplierOrder } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch("/api/v1/inventory/supplier-orders", {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      return { ok: false, error: (body as { detail?: string }).detail ?? "Failed to create order" };
    }
    return { ok: true, data: (await resp.json()) as SupplierOrder };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function fetchSupplierOrders(options?: {
  status?: string;
  supplierId?: string;
}): Promise<{ ok: true; data: SupplierOrderListResponse } | { ok: false; error: string }> {
  try {
    const params = new URLSearchParams();
    if (options?.status) params.set("status", options.status);
    if (options?.supplierId) params.set("supplier_id", options.supplierId);
    const qs = params.toString();
    const resp = await apiFetch(`/api/v1/inventory/supplier-orders${qs ? `?${qs}` : ""}`);
    if (!resp.ok) return { ok: false, error: "Failed to fetch supplier orders" };
    return { ok: true, data: (await resp.json()) as SupplierOrderListResponse };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function fetchSupplierOrder(
  orderId: string,
): Promise<{ ok: true; data: SupplierOrder } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch(
      `/api/v1/inventory/supplier-orders/${encodeURIComponent(orderId)}`,
    );
    if (!resp.ok) return { ok: false, error: "Failed to fetch supplier order" };
    return { ok: true, data: (await resp.json()) as SupplierOrder };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function updateSupplierOrderStatus(
  orderId: string,
  data: UpdateOrderStatusRequest,
): Promise<{ ok: true; data: SupplierOrder } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch(
      `/api/v1/inventory/supplier-orders/${encodeURIComponent(orderId)}/status`,
      { method: "PUT", body: JSON.stringify(data) },
    );
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      return { ok: false, error: (body as { detail?: string }).detail ?? "Failed to update status" };
    }
    return { ok: true, data: (await resp.json()) as SupplierOrder };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function receiveSupplierOrder(
  orderId: string,
  data?: ReceiveOrderRequest,
): Promise<{ ok: true; data: SupplierOrder } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch(
      `/api/v1/inventory/supplier-orders/${encodeURIComponent(orderId)}/receive`,
      { method: "PUT", body: JSON.stringify(data ?? {}) },
    );
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      return { ok: false, error: (body as { detail?: string }).detail ?? "Failed to receive order" };
    }
    return { ok: true, data: (await resp.json()) as SupplierOrder };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}
