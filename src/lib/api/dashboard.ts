/** Dashboard API helpers. */

import { apiFetch } from "../apiFetch";
import type {
  RevenueSummary,
  TopProductsResponse,
  LowStockAlertListResponse,
  VisitorStatsResponse,
  KPISummary,
  TopCustomersResponse,
  ARAgingResponse,
  APAgingResponse,
  GrossMarginResponse,
  CashFlowResponse,
  RevenueTrendResponse,
} from "../../domain/dashboard/types";

export async function fetchRevenueSummary(): Promise<RevenueSummary> {
  const resp = await apiFetch("/api/v1/dashboard/revenue-summary");
  if (!resp.ok) throw new Error("Failed to fetch revenue summary");
  return resp.json();
}

export async function fetchTopProducts(period: "day" | "week"): Promise<TopProductsResponse> {
  const resp = await apiFetch(`/api/v1/dashboard/top-products?period=${encodeURIComponent(period)}`);
  if (!resp.ok) throw new Error("Failed to fetch top products");
  return resp.json();
}

export async function fetchLowStockAlerts(): Promise<LowStockAlertListResponse> {
  const resp = await apiFetch("/api/v1/inventory/alerts/reorder?status=pending&limit=10");
  if (!resp.ok) throw new Error("Failed to fetch low-stock alerts");
  return resp.json();
}

export async function fetchVisitorStats(): Promise<VisitorStatsResponse> {
  const resp = await apiFetch("/api/v1/dashboard/visitor-stats");
  if (!resp.ok) throw new Error("Failed to fetch visitor stats");
  return resp.json();
}

export async function fetchKPISummary(): Promise<KPISummary> {
  const resp = await apiFetch("/api/v1/dashboard/kpi-summary");
  if (!resp.ok) throw new Error("Failed to fetch KPI summary");
  return resp.json();
}

export async function fetchTopCustomers(
  period: "month" | "quarter" | "year",
  anchorDate: string | null = null,
): Promise<TopCustomersResponse> {
  const params = new URLSearchParams({ period });
  if (anchorDate) {
    params.set("anchor_date", anchorDate);
  }
  const resp = await apiFetch(`/api/v1/dashboard/top-customers?${params}`);
  if (!resp.ok) throw new Error("Failed to fetch top customers");
  return resp.json();
}

export async function fetchARAging(): Promise<ARAgingResponse> {
  const resp = await apiFetch("/api/v1/reports/ar-aging");
  if (!resp.ok) throw new Error("Failed to fetch AR aging");
  return resp.json();
}

export async function fetchAPAging(): Promise<APAgingResponse> {
  const resp = await apiFetch("/api/v1/reports/ap-aging");
  if (!resp.ok) throw new Error("Failed to fetch AP aging");
  return resp.json();
}

export async function fetchGrossMargin(): Promise<GrossMarginResponse> {
  const resp = await apiFetch("/api/v1/dashboard/gross-margin");
  if (!resp.ok) throw new Error("Failed to fetch gross margin");
  return resp.json();
}

export async function fetchCashFlow(): Promise<CashFlowResponse> {
  const resp = await apiFetch("/api/v1/dashboard/cash-flow");
  if (!resp.ok) throw new Error("Failed to fetch cash flow");
  return resp.json();
}

export async function fetchRevenueTrend(
  period: "month" | "quarter" | "year",
  before: string | null = null,
): Promise<RevenueTrendResponse> {
  // "month" (30d) → daily granularity, paginated via `before`
  // "quarter" → weekly granularity for 3 months, paginated via `before`
  // "year" → monthly granularity, paginated via `before`
  const granularity = period === "month" ? "day" : period === "quarter" ? "week" : "month";
  const params = new URLSearchParams({ granularity });
  if (period === "month") {
    params.set("days", "30");
  } else if (period === "quarter") {
    params.set("months", "3");
  } else {
    params.set("months", "12");
  }
  if (before) {
    params.set("before", before);
  }
  const resp = await apiFetch(`/api/v1/dashboard/revenue-trend?${params}`);
  if (!resp.ok) throw new Error("Failed to fetch revenue trend");
  return resp.json();
}
