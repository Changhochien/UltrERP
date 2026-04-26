import { apiFetch } from "../apiFetch";

export interface CurrencyRecord {
  id: string;
  tenant_id: string;
  code: string;
  symbol: string;
  decimal_places: number;
  is_active: boolean;
  is_base_currency: boolean;
  created_at: string;
  updated_at: string;
}

export interface CurrencyListResponse {
  items: CurrencyRecord[];
  total: number;
  page: number;
  page_size: number;
}

export interface CurrencyCreatePayload {
  code: string;
  symbol: string;
  decimal_places: number;
  is_active: boolean;
  is_base_currency: boolean;
}

export interface CurrencyUpdatePayload {
  symbol?: string;
  decimal_places?: number;
  is_active?: boolean;
}

export interface ExchangeRateRecord {
  id: string;
  tenant_id: string;
  source_currency_code: string;
  target_currency_code: string;
  effective_date: string;
  rate: string;
  rate_source: string | null;
  is_inverse: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ExchangeRateListResponse {
  items: ExchangeRateRecord[];
  total: number;
  page: number;
  page_size: number;
}

export interface ExchangeRateCreatePayload {
  source_currency_code: string;
  target_currency_code: string;
  effective_date: string;
  rate: string;
  rate_source?: string | null;
  is_inverse?: boolean;
}

export interface ExchangeRateUpdatePayload {
  rate?: string;
  rate_source?: string | null;
  is_active?: boolean;
}

interface ApiErrorDetailResponse {
  detail?: string;
}

async function responseErrorMessage(resp: Response, fallback: string): Promise<string> {
  const body = await resp.json().catch(() => null) as ApiErrorDetailResponse | null;
  if (typeof body?.detail === "string" && body.detail.trim()) {
    return body.detail;
  }
  return fallback;
}

export async function listCurrencies(options?: {
  pageSize?: number;
  activeOnly?: boolean;
}): Promise<CurrencyListResponse> {
  const params = new URLSearchParams({
    page: "1",
    page_size: String(options?.pageSize ?? 200),
    active_only: String(options?.activeOnly ?? false),
  });
  const resp = await apiFetch(`/api/v1/settings/currencies?${params.toString()}`);
  if (!resp.ok) {
    throw new Error(await responseErrorMessage(resp, "Failed to load currencies"));
  }
  return resp.json();
}

export async function createCurrency(payload: CurrencyCreatePayload): Promise<CurrencyRecord> {
  const resp = await apiFetch("/api/v1/settings/currencies", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    throw new Error(await responseErrorMessage(resp, "Failed to create currency"));
  }
  return resp.json();
}

export async function updateCurrency(currencyId: string, payload: CurrencyUpdatePayload): Promise<CurrencyRecord> {
  const resp = await apiFetch(`/api/v1/settings/currencies/${currencyId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    throw new Error(await responseErrorMessage(resp, "Failed to update currency"));
  }
  return resp.json();
}

export async function setBaseCurrency(currencyId: string): Promise<CurrencyRecord> {
  const resp = await apiFetch(`/api/v1/settings/currencies/${currencyId}/set-base`, {
    method: "POST",
  });
  if (!resp.ok) {
    throw new Error(await responseErrorMessage(resp, "Failed to set base currency"));
  }
  return resp.json();
}

export async function listExchangeRates(options?: {
  pageSize?: number;
  activeOnly?: boolean;
}): Promise<ExchangeRateListResponse> {
  const params = new URLSearchParams({
    page: "1",
    page_size: String(options?.pageSize ?? 200),
    active_only: String(options?.activeOnly ?? false),
  });
  const resp = await apiFetch(`/api/v1/settings/exchange-rates?${params.toString()}`);
  if (!resp.ok) {
    throw new Error(await responseErrorMessage(resp, "Failed to load exchange rates"));
  }
  return resp.json();
}

export async function createExchangeRate(
  payload: ExchangeRateCreatePayload,
): Promise<ExchangeRateRecord> {
  const resp = await apiFetch("/api/v1/settings/exchange-rates", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    throw new Error(await responseErrorMessage(resp, "Failed to create exchange rate"));
  }
  return resp.json();
}

export async function updateExchangeRate(
  rateId: string,
  payload: ExchangeRateUpdatePayload,
): Promise<ExchangeRateRecord> {
  const resp = await apiFetch(`/api/v1/settings/exchange-rates/${rateId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    throw new Error(await responseErrorMessage(resp, "Failed to update exchange rate"));
  }
  return resp.json();
}