/** Dashboard API helpers. */

import { apiFetch } from "../apiFetch";
import type { RevenueSummary, TopProductsResponse, LowStockAlertListResponse, VisitorStatsResponse } from "../../domain/dashboard/types";

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
