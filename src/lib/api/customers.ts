/** Customer API helpers. */

import { apiFetch } from "../apiFetch";
import type {
  CustomerCreatePayload,
  CustomerListResponse,
  CustomerResponse,
  CustomerUpdatePayload,
} from "../../domain/customers/types";

export interface ApiError {
  detail: Array<{ field: string; message: string }>;
}

export interface DuplicateInfo {
  existing_customer_id: string;
  existing_customer_name: string;
  normalized_business_number: string;
}

const NETWORK_ERROR_MESSAGE = "Unable to reach the server. Please try again.";

function networkErrorDetail(): ApiError["detail"] {
  return [{ field: "", message: NETWORK_ERROR_MESSAGE }];
}

export type CreateCustomerResult =
  | { ok: true; data: CustomerResponse }
  | { ok: false; duplicate?: DuplicateInfo; errors: ApiError["detail"] };

export async function createCustomer(
  payload: CustomerCreatePayload,
): Promise<CreateCustomerResult> {
  let resp: Response;
  try {
    resp = await apiFetch("/api/v1/customers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: CustomerResponse = await resp.json();
    return { ok: true, data };
  }

  if (resp.status === 409) {
    const body = await resp.json();
    return {
      ok: false,
      duplicate: {
        existing_customer_id: body.existing_customer_id,
        existing_customer_name: body.existing_customer_name,
        normalized_business_number: body.normalized_business_number,
      },
      errors: [],
    };
  }

  const body: ApiError = await resp.json().catch(() => ({ detail: [] }));
  return { ok: false, errors: body.detail ?? [] };
}

export async function listCustomers(params: {
  q?: string;
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<CustomerListResponse> {
  const emptyResponse: CustomerListResponse = {
    items: [],
    page: 1,
    page_size: 20,
    total_count: 0,
    total_pages: 1,
  };
  const qs = new URLSearchParams();
  if (params.q) qs.set("q", params.q);
  if (params.status) qs.set("status", params.status);
  if (params.page) qs.set("page", String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));
  try {
    const resp = await apiFetch(`/api/v1/customers?${qs.toString()}`);
    if (!resp.ok) {
      return emptyResponse;
    }
    return resp.json();
  } catch {
    return emptyResponse;
  }
}

export async function getCustomer(id: string): Promise<CustomerResponse | null> {
  const resp = await apiFetch(`/api/v1/customers/${id}`);
  if (!resp.ok) return null;
  return resp.json();
}

export async function lookupCustomerByBan(
  businessNumber: string,
): Promise<CustomerResponse | null> {
  const resp = await apiFetch(
    `/api/v1/customers/lookup?business_number=${encodeURIComponent(businessNumber)}`,
  );
  if (!resp.ok) return null;
  return resp.json();
}

export interface VersionConflictInfo {
  expected_version: number;
  actual_version: number;
}

export type UpdateCustomerResult =
  | { ok: true; data: CustomerResponse }
  | { ok: false; duplicate?: DuplicateInfo; versionConflict?: VersionConflictInfo; errors: ApiError["detail"] };

export async function updateCustomer(
  id: string,
  payload: CustomerUpdatePayload,
): Promise<UpdateCustomerResult> {
  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/customers/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: CustomerResponse = await resp.json();
    return { ok: true, data };
  }

  if (resp.status === 409) {
    const body = await resp.json().catch(() => ({}));
    if (body.error === "duplicate_business_number") {
      return {
        ok: false,
        duplicate: {
          existing_customer_id: body.existing_customer_id,
          existing_customer_name: body.existing_customer_name,
          normalized_business_number: body.normalized_business_number,
        },
        errors: [],
      };
    }
    if (body.error === "version_conflict") {
      return {
        ok: false,
        versionConflict: {
          expected_version: body.expected_version,
          actual_version: body.actual_version,
        },
        errors: [],
      };
    }
    // Unexpected 409 format
    return { ok: false, errors: body.detail ?? [] };
  }

  if (resp.status === 404) {
    return { ok: false, errors: [{ field: "", message: "Customer not found." }] };
  }

  const body: ApiError = await resp.json().catch(() => ({ detail: [] }));
  return { ok: false, errors: body.detail ?? [] };
}

export interface CustomerAnalyticsSummary {
  total_revenue_12m: string;
  invoice_count_12m: number;
  avg_invoice_value: string;
  outstanding_balance: string;
  credit_limit: string;
  credit_utilization_pct: number;
  avg_days_to_pay: number | null;
  payment_score: "excellent" | "prompt" | "late" | "at_risk";
  days_overdue_avg: number | null;
}

export interface RevenueTrendPoint {
  month: string;
  revenue: string;
}

export interface CustomerRevenueTrend {
  trend: RevenueTrendPoint[];
}

export async function getCustomerAnalyticsSummary(customerId: string): Promise<CustomerAnalyticsSummary> {
  const resp = await apiFetch(`/api/v1/customers/${customerId}/analytics/summary`);
  if (!resp.ok) throw new Error("Failed to fetch customer analytics summary");
  return resp.json();
}

export async function getCustomerRevenueTrend(customerId: string, months = 12): Promise<CustomerRevenueTrend> {
  const resp = await apiFetch(`/api/v1/customers/${customerId}/analytics/revenue-trend?months=${months}`);
  if (!resp.ok) throw new Error("Failed to fetch customer revenue trend");
  return resp.json();
}

export interface StatementLine {
  date: string;
  type: "invoice" | "payment";
  reference: string;
  description: string;
  debit: string;
  credit: string;
  balance: string;
}

export interface CustomerStatementResponse {
  customer_id: string;
  company_name: string;
  currency_code: string;
  opening_balance: string;
  current_balance: string;
  lines: StatementLine[];
}

export async function getCustomerStatement(
  customerId: string,
  from?: string,
  to?: string,
): Promise<CustomerStatementResponse> {
  const params = new URLSearchParams();
  if (from) params.set("from_date", from);
  if (to) params.set("to_date", to);
  const qs = params.toString();
  const resp = await apiFetch(`/api/v1/customers/${customerId}/statement${qs ? `?${qs}` : ""}`);
  return resp.json();
}
