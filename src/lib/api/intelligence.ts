import type {
  CategoryTrends,
  CustomerRiskSignals,
  CustomerProductProfile,
  MarketOpportunities,
  ProspectGaps,
  ProspectGapCustomerFilter,
  ProductAffinityMap,
  RevenueDiagnosis,
  RevenueDiagnosisPeriod,
} from "../../domain/intelligence/types";
import { apiFetch } from "../apiFetch";

export async function fetchCustomerProductProfile(customerId: string): Promise<CustomerProductProfile> {
  const resp = await apiFetch(`/api/v1/intelligence/customers/${customerId}/product-profile`);
  if (!resp.ok) {
    throw new Error("Failed to fetch customer product profile");
  }
  return resp.json();
}

export async function fetchProductAffinityMap(
  minShared = 2,
  limit = 50,
): Promise<ProductAffinityMap> {
  const params = new URLSearchParams({
    min_shared: String(minShared),
    limit: String(limit),
  });
  const resp = await apiFetch(`/api/v1/intelligence/affinity?${params.toString()}`);
  if (!resp.ok) {
    throw new Error("Failed to fetch product affinity map");
  }
  return resp.json();
}

export async function fetchCategoryTrends(
  period: "last_30d" | "last_90d" | "last_12m" = "last_90d",
): Promise<CategoryTrends> {
  const resp = await apiFetch(`/api/v1/intelligence/category-trends?period=${period}`);
  if (!resp.ok) {
    throw new Error("Failed to fetch category trends");
  }
  return resp.json();
}

export async function fetchCustomerRiskSignals(
  status: "all" | "growing" | "at_risk" | "dormant" | "new" | "stable" = "all",
  limit = 50,
): Promise<CustomerRiskSignals> {
  const params = new URLSearchParams({ status, limit: String(limit) });
  const resp = await apiFetch(`/api/v1/intelligence/customers/risk-signals?${params.toString()}`);
  if (!resp.ok) {
    throw new Error("Failed to fetch customer risk signals");
  }
  return resp.json();
}

export async function fetchProspectGaps(
  category: string,
  customerType: ProspectGapCustomerFilter = "dealer",
  limit = 20,
): Promise<ProspectGaps> {
  const params = new URLSearchParams({
    category,
    customer_type: customerType,
    limit: String(limit),
  });
  const resp = await apiFetch(`/api/v1/intelligence/prospect-gaps?${params.toString()}`);
  if (!resp.ok) {
    throw new Error("Failed to fetch prospect gaps");
  }
  return resp.json();
}

export async function fetchMarketOpportunities(
  period: "last_30d" | "last_90d" | "last_12m" = "last_90d",
): Promise<MarketOpportunities> {
  const resp = await apiFetch(`/api/v1/intelligence/market-opportunities?period=${period}`);
  if (!resp.ok) {
    throw new Error("Failed to fetch market opportunities");
  }
  return resp.json();
}

export async function fetchRevenueDiagnosis(
  period: RevenueDiagnosisPeriod = "1m",
  anchorMonth?: string,
  category?: string,
  limit = 10,
): Promise<RevenueDiagnosis> {
  const params = new URLSearchParams({
    period,
    limit: String(limit),
  });
  if (anchorMonth) {
    params.set("anchor_month", anchorMonth);
  }
  if (category) {
    params.set("category", category);
  }

  const resp = await apiFetch(`/api/v1/intelligence/revenue-diagnosis?${params.toString()}`);
  if (!resp.ok) {
    throw new Error("Failed to fetch revenue diagnosis");
  }
  return resp.json();
}