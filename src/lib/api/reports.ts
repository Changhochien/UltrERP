/**
 * API client for financial reports (Epic 26.3).
 */

import { apiFetch } from "../apiFetch";

// Re-export report types for convenience
export type {
  EmptyReason,
  ReportMetadata,
  ProfitAndLossRow,
  ProfitAndLossResponse,
  BalanceSheetRow,
  BalanceSheetResponse,
  TrialBalanceRow,
  TrialBalanceResponse,
} from "../../domain/accounting/types";

import type {
  ProfitAndLossResponse,
  BalanceSheetResponse,
  TrialBalanceResponse,
} from "../../domain/accounting/types";

// Re-export constants for convenience
export { EMPTY_REASON_LABELS } from "../../domain/accounting/types";

// ============================================================
// API Functions
// ============================================================

const API_BASE = "/api/v1";

async function fetchApi<T>(
  path: string,
  options?: RequestInit & { signal?: AbortSignal }
): Promise<T> {
  const response = await apiFetch(`${API_BASE}${path}`, options);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw error;
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// ============================================================
// Profit and Loss
// ============================================================

export interface ProfitAndLossParams {
  from_date: string;
  to_date: string;
}

/**
 * Fetch Profit and Loss report.
 */
export async function fetchProfitAndLoss(params: ProfitAndLossParams): Promise<ProfitAndLossResponse> {
  const searchParams = new URLSearchParams({
    from_date: params.from_date,
    to_date: params.to_date,
  });

  return fetchApi<ProfitAndLossResponse>(`/reports/profit-and-loss?${searchParams}`);
}

/**
 * Export Profit and Loss report as CSV.
 */
export async function exportProfitAndLossCSV(params: ProfitAndLossParams): Promise<Blob> {
  const searchParams = new URLSearchParams({
    from_date: params.from_date,
    to_date: params.to_date,
    export: "csv",
  });

  const response = await apiFetch(`${API_BASE}/reports/profit-and-loss?${searchParams}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw error;
  }

  return response.blob();
}

// ============================================================
// Balance Sheet
// ============================================================

export interface BalanceSheetParams {
  as_of_date: string;
}

/**
 * Fetch Balance Sheet report.
 */
export async function fetchBalanceSheet(params: BalanceSheetParams): Promise<BalanceSheetResponse> {
  const searchParams = new URLSearchParams({
    as_of_date: params.as_of_date,
  });

  return fetchApi<BalanceSheetResponse>(`/reports/balance-sheet?${searchParams}`);
}

/**
 * Export Balance Sheet report as CSV.
 */
export async function exportBalanceSheetCSV(params: BalanceSheetParams): Promise<Blob> {
  const searchParams = new URLSearchParams({
    as_of_date: params.as_of_date,
    export: "csv",
  });

  const response = await apiFetch(`${API_BASE}/reports/balance-sheet?${searchParams}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw error;
  }

  return response.blob();
}

// ============================================================
// Trial Balance
// ============================================================

export interface TrialBalanceParams {
  as_of_date?: string;
  from_date?: string;
  to_date?: string;
}

/**
 * Fetch Trial Balance report.
 */
export async function fetchTrialBalance(params?: TrialBalanceParams): Promise<TrialBalanceResponse> {
  const searchParams = new URLSearchParams();

  if (params?.as_of_date) {
    searchParams.set("as_of_date", params.as_of_date);
  }
  if (params?.from_date) {
    searchParams.set("from_date", params.from_date);
  }
  if (params?.to_date) {
    searchParams.set("to_date", params.to_date);
  }

  const queryString = searchParams.toString();
  const path = queryString
    ? `/reports/trial-balance?${queryString}`
    : "/reports/trial-balance";

  return fetchApi<TrialBalanceResponse>(path);
}

/**
 * Export Trial Balance report as CSV.
 */
export async function exportTrialBalanceCSV(params?: TrialBalanceParams): Promise<Blob> {
  const searchParams = new URLSearchParams({ export: "csv" });

  if (params?.as_of_date) {
    searchParams.set("as_of_date", params.as_of_date);
  }
  if (params?.from_date) {
    searchParams.set("from_date", params.from_date);
  }
  if (params?.to_date) {
    searchParams.set("to_date", params.to_date);
  }

  const response = await apiFetch(`${API_BASE}/reports/trial-balance?${searchParams}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw error;
  }

  return response.blob();
}

// ============================================================
// Utility Functions
// ============================================================

/**
 * Download a blob as a file.
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Format a decimal string for display.
 */
export function formatCurrency(value: string | number): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}

/**
 * Format a decimal string for display (without currency symbol).
 */
export function formatNumber(value: string | number): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}
