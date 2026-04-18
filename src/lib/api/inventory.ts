import { apiFetch } from "../apiFetch";
import type {
  AcknowledgeAlertResponse,
  BelowReorderReportResponse,
  Category,
  CategoryCreate,
  CategoryListResponse,
  CreateReorderSuggestionOrdersRequest,
  CreateReorderSuggestionOrdersResponse,
  CategoryUpdate,
  DismissAlertResponse,
  InventoryValuationResponse,
  PlanningSupportResponse,
  PhysicalCountSession,
  PhysicalCountSessionListResponse,
  ProductSearchResponse,
  ProductDetail,
  ProductCreate,
  ProductResponse,
  ProductSupplierAssociation,
  ProductSupplierAssociationCreate,
  ProductSupplierAssociationListResponse,
  ProductSupplierAssociationUpdate,
  ProductSupplierInfo,
  ProductUpdate,
  ReorderAlertListResponse,
  ReorderSuggestionListResponse,
  SnoozeAlertResponse,
  Supplier,
  SupplierCreate,
  SupplierListOptions,
  WarehouseListResponse,
  TransferResponse,
  ReasonCodeListResponse,
  StockAdjustmentResponse,
  SupplierListResponse,
  SupplierOrderListResponse,
  SupplierOrder,
  SupplierUpdate,
  TransferHistoryItem,
  TransferHistoryListResponse,
  UnitOfMeasure,
  UnitOfMeasureCreate,
  UnitOfMeasureListResponse,
  UnitOfMeasureUpdate,
  UpdateOrderStatusRequest,
  ReceiveOrderRequest,
  CreateSupplierOrderRequest,
} from "../../domain/inventory/types";

export async function searchProducts(
  query: string,
  options?: {
    limit?: number;
    offset?: number;
    category?: string;
    warehouseId?: string;
    includeInactive?: boolean;
    sortBy?: string;
    sortDir?: string;
    signal?: AbortSignal;
  },
): Promise<ProductSearchResponse> {
  const params = new URLSearchParams({ q: query });
  if (options?.limit) params.set("limit", String(options.limit));
  if (options?.offset) params.set("offset", String(options.offset));
  if (options?.category) params.set("category", options.category);
  if (options?.warehouseId) params.set("warehouse_id", options.warehouseId);
  if (options?.includeInactive) params.set("include_inactive", "true");
  if (options?.sortBy) params.set("sort_by", options.sortBy);
  if (options?.sortDir) params.set("sort_dir", options.sortDir);
  const resp = await apiFetch(
    `/api/v1/inventory/products/search?${params.toString()}`,
    { signal: options?.signal },
  );
  if (!resp.ok) throw new Error("Search failed");
  return resp.json() as Promise<ProductSearchResponse>;
}

export async function listCategories(options?: {
  q?: string;
  activeOnly?: boolean;
  limit?: number;
  offset?: number;
  signal?: AbortSignal;
}): Promise<CategoryListResponse> {
  const params = new URLSearchParams();
  if (options?.q) params.set("q", options.q);
  if (options?.activeOnly != null) params.set("active_only", String(options.activeOnly));
  if (options?.limit != null) params.set("limit", String(options.limit));
  if (options?.offset != null) params.set("offset", String(options.offset));

  const qs = params.toString();
  const resp = await apiFetch(`/api/v1/inventory/categories${qs ? `?${qs}` : ""}`, {
    signal: options?.signal,
  });
  if (!resp.ok) {
    throw new Error("Failed to load categories");
  }
  return resp.json() as Promise<CategoryListResponse>;
}

export type CategoryMutationResult =
  | { ok: true; data: Category }
  | { ok: false; error: string; errors?: InventoryFieldError[] };

export type UnitMutationResult =
  | { ok: true; data: UnitOfMeasure }
  | { ok: false; error: string; errors?: InventoryFieldError[] };

export async function createCategory(data: CategoryCreate): Promise<CategoryMutationResult> {
  try {
    const resp = await apiFetch("/api/v1/inventory/categories", {
      method: "POST",
      body: JSON.stringify(data),
    });
    const body = await resp.json().catch(() => ({}));

    if (resp.ok) {
      return { ok: true, data: body as Category };
    }

    if (resp.status === 409) {
      return {
        ok: false,
        error: (body as { detail?: string }).detail ?? "Category name already exists",
        errors: [{ field: "name", message: "Category name already exists" }],
      };
    }

    const errors = normalizeInventoryFieldErrors((body as { detail?: unknown }).detail);
    if (errors.length > 0) {
      return { ok: false, error: errors[0]?.message ?? "Failed to create category", errors };
    }

    return {
      ok: false,
      error: (body as { detail?: string }).detail ?? "Failed to create category",
    };
  } catch (e) {
    return {
      ok: false,
      error: e instanceof Error ? e.message : "Unknown error",
    };
  }
}

export async function updateCategory(
  categoryId: string,
  data: CategoryUpdate,
): Promise<CategoryMutationResult> {
  try {
    const resp = await apiFetch(`/api/v1/inventory/categories/${encodeURIComponent(categoryId)}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
    const body = await resp.json().catch(() => ({}));

    if (resp.ok) {
      return { ok: true, data: body as Category };
    }

    if (resp.status === 409) {
      return {
        ok: false,
        error: (body as { detail?: string }).detail ?? "Category name already exists",
        errors: [{ field: "name", message: "Category name already exists" }],
      };
    }

    const errors = normalizeInventoryFieldErrors((body as { detail?: unknown }).detail);
    if (errors.length > 0) {
      return { ok: false, error: errors[0]?.message ?? "Failed to update category", errors };
    }

    return {
      ok: false,
      error: (body as { detail?: string }).detail ?? "Failed to update category",
    };
  } catch (e) {
    return {
      ok: false,
      error: e instanceof Error ? e.message : "Unknown error",
    };
  }
}

export async function setCategoryStatus(
  categoryId: string,
  status: "active" | "inactive",
): Promise<CategoryMutationResult> {
  try {
    const resp = await apiFetch(`/api/v1/inventory/categories/${encodeURIComponent(categoryId)}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    const body = await resp.json().catch(() => ({}));

    if (resp.ok) {
      return { ok: true, data: body as Category };
    }

    return {
      ok: false,
      error: (body as { detail?: string }).detail ?? "Failed to update category status",
    };
  } catch (e) {
    return {
      ok: false,
      error: e instanceof Error ? e.message : "Unknown error",
    };
  }
}

export async function listUnits(options?: {
  q?: string;
  activeOnly?: boolean;
  limit?: number;
  offset?: number;
  signal?: AbortSignal;
}): Promise<UnitOfMeasureListResponse> {
  const params = new URLSearchParams();
  if (options?.q) params.set("q", options.q);
  if (options?.activeOnly != null) params.set("active_only", String(options.activeOnly));
  if (options?.limit != null) params.set("limit", String(options.limit));
  if (options?.offset != null) params.set("offset", String(options.offset));

  const qs = params.toString();
  const resp = await apiFetch(`/api/v1/inventory/units${qs ? `?${qs}` : ""}`, {
    signal: options?.signal,
  });
  if (!resp.ok) {
    throw new Error("Failed to load units");
  }
  return resp.json() as Promise<UnitOfMeasureListResponse>;
}

export async function createUnit(data: UnitOfMeasureCreate): Promise<UnitMutationResult> {
  try {
    const resp = await apiFetch("/api/v1/inventory/units", {
      method: "POST",
      body: JSON.stringify(data),
    });
    const body = await resp.json().catch(() => ({}));

    if (resp.ok) {
      return { ok: true, data: body as UnitOfMeasure };
    }

    if (resp.status === 409) {
      return {
        ok: false,
        error: "Unit code already exists",
        errors: [{ field: "code", message: "Unit code already exists" }],
      };
    }

    const errors = normalizeInventoryFieldErrors((body as { detail?: unknown }).detail);
    if (errors.length > 0) {
      return { ok: false, error: errors[0]?.message ?? "Failed to create unit", errors };
    }

    return {
      ok: false,
      error: (body as { detail?: string }).detail ?? "Failed to create unit",
    };
  } catch (e) {
    return {
      ok: false,
      error: e instanceof Error ? e.message : "Unknown error",
    };
  }
}

export async function updateUnit(
  unitId: string,
  data: UnitOfMeasureUpdate,
): Promise<UnitMutationResult> {
  try {
    const resp = await apiFetch(`/api/v1/inventory/units/${encodeURIComponent(unitId)}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
    const body = await resp.json().catch(() => ({}));

    if (resp.ok) {
      return { ok: true, data: body as UnitOfMeasure };
    }

    if (resp.status === 409) {
      return {
        ok: false,
        error: "Unit code already exists",
        errors: [{ field: "code", message: "Unit code already exists" }],
      };
    }

    const errors = normalizeInventoryFieldErrors((body as { detail?: unknown }).detail);
    if (errors.length > 0) {
      return { ok: false, error: errors[0]?.message ?? "Failed to update unit", errors };
    }

    return {
      ok: false,
      error: (body as { detail?: string }).detail ?? "Failed to update unit",
    };
  } catch (e) {
    return {
      ok: false,
      error: e instanceof Error ? e.message : "Unknown error",
    };
  }
}

export async function setUnitStatus(
  unitId: string,
  isActive: boolean,
): Promise<UnitMutationResult> {
  try {
    const resp = await apiFetch(`/api/v1/inventory/units/${encodeURIComponent(unitId)}/status`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: isActive }),
    });
    const body = await resp.json().catch(() => ({}));

    if (resp.ok) {
      return { ok: true, data: body as UnitOfMeasure };
    }

    return {
      ok: false,
      error: (body as { detail?: string }).detail ?? "Failed to update unit status",
    };
  } catch (e) {
    return {
      ok: false,
      error: e instanceof Error ? e.message : "Unknown error",
    };
  }
}

export async function fetchProductDetail(
  productId: string,
  options?: { historyLimit?: number; historyOffset?: number; signal?: AbortSignal },
): Promise<{ ok: true; data: ProductDetail } | { ok: false; error: string }> {
  try {
    const params = new URLSearchParams();
    if (options?.historyLimit != null)
      params.set("history_limit", String(options.historyLimit));
    if (options?.historyOffset != null)
      params.set("history_offset", String(options.historyOffset));
    const qs = params.toString();
    const url = `/api/v1/inventory/products/${encodeURIComponent(productId)}${qs ? `?${qs}` : ""}`;
    const resp = await apiFetch(url, options?.signal ? { signal: options.signal } : undefined);
    if (!resp.ok) return { ok: false, error: "Failed to fetch product detail" };
    return { ok: true, data: (await resp.json()) as ProductDetail };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function setProductStatus(
  productId: string,
  status: "active" | "inactive",
): Promise<{ ok: true; data: ProductResponse } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch(`/api/v1/inventory/products/${encodeURIComponent(productId)}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    const body = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      return {
        ok: false,
        error: (body as { detail?: string }).detail ?? "Failed to update product status",
      };
    }
    return { ok: true, data: body as ProductResponse };
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

export async function fetchBelowReorderReport(options?: {
  warehouseId?: string;
}): Promise<{ ok: true; data: BelowReorderReportResponse } | { ok: false; error: string }> {
  try {
    const params = new URLSearchParams();
    if (options?.warehouseId) params.set("warehouse_id", options.warehouseId);
    const qs = params.toString();
    const resp = await apiFetch(`/api/v1/inventory/reports/below-reorder${qs ? `?${qs}` : ""}`);
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      return {
        ok: false,
        error: (body as { detail?: string }).detail ?? "Failed to load below-reorder report",
      };
    }
    return { ok: true, data: (await resp.json()) as BelowReorderReportResponse };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function fetchInventoryValuation(
  options?: { warehouseId?: string },
  fetchOptions?: { signal?: AbortSignal },
): Promise<{ ok: true; data: InventoryValuationResponse } | { ok: false; error: string }> {
  try {
    const params = new URLSearchParams();
    if (options?.warehouseId) params.set("warehouse_id", options.warehouseId);
    const qs = params.toString();
    const resp = await apiFetch(`/api/v1/inventory/reports/valuation${qs ? `?${qs}` : ""}`, fetchOptions);
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      return {
        ok: false,
        error: (body as { detail?: string }).detail ?? "Failed to load inventory valuation",
      };
    }
    return { ok: true, data: (await resp.json()) as InventoryValuationResponse };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function exportBelowReorderReport(options?: {
  warehouseId?: string;
}): Promise<{ ok: true; filename: string } | { ok: false; status: number; message: string }> {
  const params = new URLSearchParams();
  if (options?.warehouseId) params.set("warehouse_id", options.warehouseId);
  const qs = params.toString();
  const resp = await apiFetch(`/api/v1/inventory/reports/below-reorder/export${qs ? `?${qs}` : ""}`);

  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ detail: "CSV export failed" }));
    return {
      ok: false,
      status: resp.status,
      message: (body as { detail?: string }).detail ?? "CSV export failed",
    };
  }

  const disposition = resp.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^\"]+)"?/);
  const filename = match?.[1] ?? "below-reorder-report.csv";

  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);

  return { ok: true, filename };
}

export async function fetchReorderSuggestions(options?: {
  warehouseId?: string;
  limit?: number;
  offset?: number;
}): Promise<{ ok: true; data: ReorderSuggestionListResponse } | { ok: false; error: string }> {
  try {
    const params = new URLSearchParams();
    if (options?.warehouseId) params.set("warehouse_id", options.warehouseId);
    if (options?.limit != null) params.set("limit", String(options.limit));
    if (options?.offset != null) params.set("offset", String(options.offset));
    const qs = params.toString();
    const resp = await apiFetch(`/api/v1/inventory/reorder-suggestions${qs ? `?${qs}` : ""}`);
    if (!resp.ok) return { ok: false, error: "Failed to fetch reorder suggestions" };
    return { ok: true, data: (await resp.json()) as ReorderSuggestionListResponse };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function createReorderSuggestionOrders(
  data: CreateReorderSuggestionOrdersRequest,
): Promise<{ ok: true; data: CreateReorderSuggestionOrdersResponse } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch("/api/v1/inventory/reorder-suggestions/orders", {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      return {
        ok: false,
        error: (body as { detail?: string }).detail ?? "Failed to create reorder drafts",
      };
    }
    return {
      ok: true,
      data: (await resp.json()) as CreateReorderSuggestionOrdersResponse,
    };
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
    const body = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      const errors = normalizeInventoryFieldErrors((body as { detail?: unknown }).detail);
      if (errors.length > 0) {
        return { ok: false, error: errors[0]?.message ?? "Failed to create transfer" };
      }

      return {
        ok: false,
        error: readInventoryErrorMessage(
          (body as { detail?: unknown }).detail,
          "Failed to create transfer",
        ),
      };
    }
    return { ok: true, data: body as TransferResponse };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function fetchTransferHistory(options?: {
  productId?: string;
  warehouseId?: string;
  limit?: number;
  offset?: number;
  signal?: AbortSignal;
}): Promise<{ ok: true; data: TransferHistoryListResponse } | { ok: false; error: string }> {
  try {
    const params = new URLSearchParams();
    if (options?.productId) params.set("product_id", options.productId);
    if (options?.warehouseId) params.set("warehouse_id", options.warehouseId);
    if (options?.limit != null) params.set("limit", String(options.limit));
    if (options?.offset != null) params.set("offset", String(options.offset));

    const qs = params.toString();
    const resp = await apiFetch(`/api/v1/inventory/transfers${qs ? `?${qs}` : ""}`, {
      signal: options?.signal,
    });
    const body = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      return {
        ok: false,
        error: readInventoryErrorMessage(
          (body as { detail?: unknown }).detail,
          "Failed to fetch transfer history",
        ),
      };
    }
    return { ok: true, data: body as TransferHistoryListResponse };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function fetchTransferDetail(
  transferId: string,
  options?: { signal?: AbortSignal },
): Promise<{ ok: true; data: TransferHistoryItem } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch(`/api/v1/inventory/transfers/${encodeURIComponent(transferId)}`, {
      signal: options?.signal,
    });
    const body = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      return {
        ok: false,
        error: readInventoryErrorMessage(
          (body as { detail?: unknown }).detail,
          "Failed to fetch transfer details",
        ),
      };
    }
    return { ok: true, data: body as TransferHistoryItem };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function fetchPhysicalCountSessions(options?: {
  warehouseId?: string;
  status?: string;
  limit?: number;
  offset?: number;
  signal?: AbortSignal;
}): Promise<{ ok: true; data: PhysicalCountSessionListResponse } | { ok: false; error: string }> {
  try {
    const params = new URLSearchParams();
    if (options?.warehouseId) params.set("warehouse_id", options.warehouseId);
    if (options?.status) params.set("status", options.status);
    if (options?.limit != null) params.set("limit", String(options.limit));
    if (options?.offset != null) params.set("offset", String(options.offset));

    const qs = params.toString();
    const resp = await apiFetch(`/api/v1/inventory/count-sessions${qs ? `?${qs}` : ""}`, {
      signal: options?.signal,
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      return {
        ok: false,
        error: (body as { detail?: string }).detail ?? "Failed to fetch count sessions",
      };
    }
    return { ok: true, data: (await resp.json()) as PhysicalCountSessionListResponse };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function fetchPhysicalCountSession(
  sessionId: string,
  options?: { signal?: AbortSignal },
): Promise<{ ok: true; data: PhysicalCountSession } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch(`/api/v1/inventory/count-sessions/${encodeURIComponent(sessionId)}`, {
      signal: options?.signal,
    });
    const body = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      return {
        ok: false,
        error: (body as { detail?: string }).detail ?? "Failed to fetch count session",
      };
    }
    return { ok: true, data: body as PhysicalCountSession };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function createPhysicalCountSession(data: {
  warehouse_id: string;
}): Promise<{ ok: true; data: PhysicalCountSession } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch("/api/v1/inventory/count-sessions", {
      method: "POST",
      body: JSON.stringify(data),
    });
    const body = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      return {
        ok: false,
        error: (body as { detail?: string }).detail ?? "Failed to create count session",
      };
    }
    return { ok: true, data: body as PhysicalCountSession };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function updatePhysicalCountLine(
  sessionId: string,
  lineId: string,
  data: { counted_qty: number; notes?: string },
): Promise<{ ok: true; data: PhysicalCountSession } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch(
      `/api/v1/inventory/count-sessions/${encodeURIComponent(sessionId)}/lines/${encodeURIComponent(lineId)}`,
      {
        method: "PATCH",
        body: JSON.stringify(data),
      },
    );
    const body = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      return {
        ok: false,
        error: (body as { detail?: string }).detail ?? "Failed to update count line",
      };
    }
    return { ok: true, data: body as PhysicalCountSession };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function submitPhysicalCountSession(
  sessionId: string,
): Promise<{ ok: true; data: PhysicalCountSession } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch(`/api/v1/inventory/count-sessions/${encodeURIComponent(sessionId)}/submit`, {
      method: "POST",
    });
    const body = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      return {
        ok: false,
        error: (body as { detail?: string }).detail ?? "Failed to submit count session",
      };
    }
    return { ok: true, data: body as PhysicalCountSession };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function approvePhysicalCountSession(
  sessionId: string,
): Promise<{ ok: true; data: PhysicalCountSession } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch(`/api/v1/inventory/count-sessions/${encodeURIComponent(sessionId)}/approve`, {
      method: "POST",
    });
    const body = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      return {
        ok: false,
        error: (body as { detail?: string }).detail ?? "Failed to approve count session",
      };
    }
    return { ok: true, data: body as PhysicalCountSession };
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

export async function fetchSuppliers(
  options?: SupplierListOptions & { signal?: AbortSignal },
): Promise<{
  ok: true;
  data: SupplierListResponse;
} | { ok: false; error: string }> {
  try {
    const params = new URLSearchParams();
    if (options?.q) params.set("q", options.q);
    if (options?.activeOnly != null) params.set("active_only", String(options.activeOnly));
    if (options?.limit != null) params.set("limit", String(options.limit));
    if (options?.offset != null) params.set("offset", String(options.offset));

    const qs = params.toString();
    const resp = await apiFetch(`/api/v1/inventory/suppliers${qs ? `?${qs}` : ""}`, {
      signal: options?.signal,
    });
    if (!resp.ok) return { ok: false, error: "Failed to fetch suppliers" };
    return { ok: true, data: (await resp.json()) as SupplierListResponse };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function fetchSupplier(
  supplierId: string,
  options?: { signal?: AbortSignal },
): Promise<{ ok: true; data: Supplier } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch(`/api/v1/inventory/suppliers/${encodeURIComponent(supplierId)}`, {
      signal: options?.signal,
    });
    const body = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      return {
        ok: false,
        error: (body as { detail?: string }).detail ?? "Failed to fetch supplier",
      };
    }
    return { ok: true, data: body as Supplier };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function fetchProductSupplier(
  productId: string,
  options?: { signal?: AbortSignal },
): Promise<{ ok: true; data: ProductSupplierInfo | null } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch(
      `/api/v1/inventory/products/${encodeURIComponent(productId)}/supplier`,
      { signal: options?.signal },
    );
    const body = await resp.json().catch(() => null);
    if (!resp.ok) {
      return {
        ok: false,
        error: (body as { detail?: string } | null)?.detail ?? "Failed to fetch product supplier",
      };
    }
    return { ok: true, data: body as ProductSupplierInfo | null };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function listProductSuppliers(
  productId: string,
  options?: { signal?: AbortSignal },
): Promise<{ ok: true; data: ProductSupplierAssociationListResponse } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch(
      `/api/v1/inventory/products/${encodeURIComponent(productId)}/suppliers`,
      { signal: options?.signal },
    );
    const body = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      return {
        ok: false,
        error: (body as { detail?: string }).detail ?? "Failed to fetch product suppliers",
      };
    }
    return { ok: true, data: body as ProductSupplierAssociationListResponse };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function createProductSupplier(
  productId: string,
  data: ProductSupplierAssociationCreate,
): Promise<{ ok: true; data: ProductSupplierAssociation } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch(
      `/api/v1/inventory/products/${encodeURIComponent(productId)}/suppliers`,
      {
        method: "POST",
        body: JSON.stringify(data),
      },
    );
    const body = await resp.json().catch(() => ({}));

    if (resp.ok) {
      return { ok: true, data: body as ProductSupplierAssociation };
    }

    const detail = (body as { detail?: Array<{ msg?: string }> | string }).detail;
    if (Array.isArray(detail)) {
      return { ok: false, error: detail[0]?.msg ?? "Failed to create product supplier" };
    }

    return {
      ok: false,
      error: typeof detail === "string" ? detail : "Failed to create product supplier",
    };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function updateProductSupplier(
  productId: string,
  supplierId: string,
  data: ProductSupplierAssociationUpdate,
): Promise<{ ok: true; data: ProductSupplierAssociation } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch(
      `/api/v1/inventory/products/${encodeURIComponent(productId)}/suppliers/${encodeURIComponent(supplierId)}`,
      {
        method: "PATCH",
        body: JSON.stringify(data),
      },
    );
    const body = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      return {
        ok: false,
        error: (body as { detail?: string }).detail ?? "Failed to update product supplier",
      };
    }
    return { ok: true, data: body as ProductSupplierAssociation };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export async function deleteProductSupplier(
  productId: string,
  supplierId: string,
): Promise<{ ok: true } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch(
      `/api/v1/inventory/products/${encodeURIComponent(productId)}/suppliers/${encodeURIComponent(supplierId)}`,
      { method: "DELETE" },
    );
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      return {
        ok: false,
        error: (body as { detail?: string }).detail ?? "Failed to delete product supplier",
      };
    }
    return { ok: true };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Unknown error" };
  }
}

export type SupplierMutationResult =
  | { ok: true; data: Supplier }
  | { ok: false; error: string; errors?: InventoryFieldError[] };

export async function createSupplier(data: SupplierCreate): Promise<SupplierMutationResult> {
  try {
    const resp = await apiFetch("/api/v1/inventory/suppliers", {
      method: "POST",
      body: JSON.stringify(data),
    });
    const body = await resp.json().catch(() => ({}));

    if (resp.ok) {
      return { ok: true, data: body as Supplier };
    }

    const errors = normalizeInventoryFieldErrors((body as { detail?: unknown }).detail);
    if (errors.length > 0) {
      return { ok: false, error: errors[0]?.message ?? "Failed to create supplier", errors };
    }

    return {
      ok: false,
      error: (body as { detail?: string }).detail ?? "Failed to create supplier",
    };
  } catch (e) {
    return {
      ok: false,
      error: e instanceof Error ? e.message : "Unknown error",
    };
  }
}

export async function updateSupplier(
  supplierId: string,
  data: SupplierUpdate,
): Promise<SupplierMutationResult> {
  try {
    const resp = await apiFetch(`/api/v1/inventory/suppliers/${encodeURIComponent(supplierId)}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
    const body = await resp.json().catch(() => ({}));

    if (resp.ok) {
      return { ok: true, data: body as Supplier };
    }

    const errors = normalizeInventoryFieldErrors((body as { detail?: unknown }).detail);
    if (errors.length > 0) {
      return { ok: false, error: errors[0]?.message ?? "Failed to update supplier", errors };
    }

    return {
      ok: false,
      error: (body as { detail?: string }).detail ?? "Failed to update supplier",
    };
  } catch (e) {
    return {
      ok: false,
      error: e instanceof Error ? e.message : "Unknown error",
    };
  }
}

export async function setSupplierStatus(
  supplierId: string,
  isActive: boolean,
): Promise<SupplierMutationResult> {
  try {
    const resp = await apiFetch(`/api/v1/inventory/suppliers/${encodeURIComponent(supplierId)}/status`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: isActive }),
    });
    const body = await resp.json().catch(() => ({}));

    if (resp.ok) {
      return { ok: true, data: body as Supplier };
    }

    return {
      ok: false,
      error: (body as { detail?: string }).detail ?? "Failed to update supplier status",
    };
  } catch (e) {
    return {
      ok: false,
      error: e instanceof Error ? e.message : "Unknown error",
    };
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

export async function createProduct(data: ProductCreate): Promise<ProductResponse> {
  const resp = await apiFetch("/api/v1/inventory/products", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    if (resp.status === 409) {
      throw new Error("Product code already exists");
    }
    throw new Error((body as { detail?: string }).detail ?? "Failed to create product");
  }
  return resp.json() as Promise<ProductResponse>;
}

export interface InventoryFieldError {
  field: string;
  message: string;
}

export type UpdateProductResult =
  | { ok: true; data: ProductResponse }
  | { ok: false; errors: InventoryFieldError[] };

function normalizeInventoryFieldErrors(detail: unknown): InventoryFieldError[] {
  if (!Array.isArray(detail)) {
    return [];
  }

  return detail.map((item) => {
    const field =
      item && typeof item === "object" && Array.isArray((item as { loc?: unknown }).loc)
        ? String(((item as { loc: unknown[] }).loc as unknown[]).at(-1) ?? "")
        : "";
    const message =
      item && typeof item === "object" && typeof (item as { msg?: unknown }).msg === "string"
        ? (item as { msg: string }).msg
        : "Invalid value";
    return { field, message };
  });
}

function readInventoryErrorMessage(detail: unknown, fallback: string): string {
  if (typeof detail === "string") {
    return detail;
  }

  if (detail && typeof detail === "object") {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === "string" && message.trim()) {
      return message;
    }

    const error = (detail as { error?: unknown }).error;
    if (typeof error === "string" && error.trim()) {
      return error;
    }

    const nestedDetail = (detail as { detail?: unknown }).detail;
    if (typeof nestedDetail === "string" && nestedDetail.trim()) {
      return nestedDetail;
    }
  }

  return fallback;
}

export async function updateProduct(
  productId: string,
  data: ProductUpdate,
): Promise<UpdateProductResult> {
  try {
    const resp = await apiFetch(`/api/v1/inventory/products/${encodeURIComponent(productId)}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
    const body = await resp.json().catch(() => ({}));

    if (resp.ok) {
      return { ok: true, data: body as ProductResponse };
    }

    if (resp.status === 409) {
      return {
        ok: false,
        errors: [{ field: "code", message: "Product code already exists" }],
      };
    }

    if (resp.status === 404) {
      return {
        ok: false,
        errors: [{ field: "", message: (body as { detail?: string }).detail ?? "Product not found" }],
      };
    }

    const errors = normalizeInventoryFieldErrors((body as { detail?: unknown }).detail);
    if (errors.length > 0) {
      return { ok: false, errors };
    }

    return {
      ok: false,
      errors: [{ field: "", message: (body as { detail?: string }).detail ?? "Failed to update product" }],
    };
  } catch (e) {
    return {
      ok: false,
      errors: [{ field: "", message: e instanceof Error ? e.message : "Unknown error" }],
    };
  }
}
