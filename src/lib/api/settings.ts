/** Settings API helpers. */

import { apiFetch } from "../apiFetch";

export type SettingValueType = "str" | "int" | "bool" | "tuple" | "json" | "literal";

export interface SettingItem {
  key: string;
  value: string;
  display_value: string;
  value_type: SettingValueType;
  allowed_values: string[] | null;
  nullable: boolean;
  is_null: boolean;
  is_sensitive: boolean;
  description: string;
  category: string;
  updated_at: string | null;
  updated_by: string | null;
}

export interface SettingsCategory {
  category: string;
  description: string;
  items: SettingItem[];
}

interface ApiErrorDetailResponse {
  detail?: string;
}

async function responseErrorMessage(
  resp: Response,
  fallback: string,
): Promise<string> {
  const body = await resp.json().catch(() => null) as ApiErrorDetailResponse | null;
  if (typeof body?.detail === "string" && body.detail.trim()) {
    return body.detail;
  }
  return fallback;
}

export async function getSettings(): Promise<SettingsCategory[]> {
  const resp = await apiFetch("/api/v1/settings");
  if (!resp.ok) {
    throw new Error(await responseErrorMessage(resp, "Failed to load settings"));
  }
  return resp.json();
}

export async function getSetting(key: string): Promise<SettingItem> {
  const resp = await apiFetch(`/api/v1/settings/${encodeURIComponent(key)}`);
  if (!resp.ok) {
    throw new Error(await responseErrorMessage(resp, "Failed to load setting"));
  }
  return resp.json();
}

export async function updateSetting(key: string, value: string): Promise<SettingItem> {
  const resp = await apiFetch(`/api/v1/settings/${encodeURIComponent(key)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ value }),
  });
  if (!resp.ok) {
    const detail = await responseErrorMessage(resp, "Failed to update setting");
    throw new Error(detail);
  }
  return resp.json();
}

export async function resetSetting(key: string): Promise<void> {
  const resp = await apiFetch(`/api/v1/settings/${encodeURIComponent(key)}`, {
    method: "DELETE",
  });
  if (!resp.ok) {
    throw new Error(await responseErrorMessage(resp, "Failed to reset setting"));
  }
}

export async function getCategories(): Promise<Array<{ category: string; description: string }>> {
  const resp = await apiFetch("/api/v1/settings/categories");
  if (!resp.ok) {
    throw new Error(await responseErrorMessage(resp, "Failed to load categories"));
  }
  return resp.json();
}
