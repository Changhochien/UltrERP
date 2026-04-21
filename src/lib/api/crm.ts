/** CRM lead API helpers. */

import type { CustomerCreatePayload } from "../../domain/customers/types";
import type {
  DuplicateLeadInfo,
  LeadCreatePayload,
  LeadCustomerConversionResult,
  LeadListResponse,
  LeadOpportunityHandoff,
  LeadQualificationStatus,
  LeadResponse,
  LeadStatus,
  LeadUpdatePayload,
} from "../../domain/crm/types";
import { apiFetch } from "../apiFetch";

export interface ApiError {
  detail: Array<{ field: string; message: string }>;
}

export interface VersionConflictInfo {
  expected_version: number;
  actual_version: number;
}

const NETWORK_ERROR_MESSAGE = "Unable to reach the server. Please try again.";

async function readErrorDetails(
  resp: Response,
  fallbackMessage: string,
): Promise<ApiError["detail"]> {
  const body = await resp.json().catch(() => null);
  if (Array.isArray(body?.detail)) {
    return body.detail;
  }
  if (typeof body?.detail === "string") {
    return [{ field: "", message: body.detail }];
  }
  if (typeof body?.message === "string") {
    return [{ field: "", message: body.message }];
  }
  return [{ field: "", message: fallbackMessage }];
}

function networkErrorDetail(): ApiError["detail"] {
  return [{ field: "", message: NETWORK_ERROR_MESSAGE }];
}

export type CreateLeadResult =
  | { ok: true; data: LeadResponse }
  | { ok: false; duplicate?: DuplicateLeadInfo; errors: ApiError["detail"] };

export type UpdateLeadResult =
  | { ok: true; data: LeadResponse }
  | {
      ok: false;
      duplicate?: DuplicateLeadInfo;
      versionConflict?: VersionConflictInfo;
      errors: ApiError["detail"];
    };

export type LeadActionResult<TData> =
  | { ok: true; data: TData }
  | { ok: false; errors: ApiError["detail"] };

export async function createLead(payload: LeadCreatePayload): Promise<CreateLeadResult> {
  let resp: Response;
  try {
    resp = await apiFetch("/api/v1/crm/leads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: LeadResponse = await resp.json();
    return { ok: true, data };
  }

  if (resp.status === 409) {
    const body = await resp.json().catch(() => ({ candidates: [] }));
    return {
      ok: false,
      duplicate: {
        candidates: Array.isArray(body.candidates) ? body.candidates : [],
      },
      errors: [],
    };
  }

  const body: ApiError = await resp.json().catch(() => ({ detail: [] }));
  return { ok: false, errors: body.detail ?? [] };
}

export async function listLeads(params: {
  q?: string;
  status?: LeadStatus;
  page?: number;
  page_size?: number;
}): Promise<LeadListResponse> {
  const qs = new URLSearchParams();
  if (params.q) qs.set("q", params.q);
  if (params.status) qs.set("status", params.status);
  if (params.page) qs.set("page", String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));

  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/leads?${qs.toString()}`);
  } catch {
    throw new Error(NETWORK_ERROR_MESSAGE);
  }

  if (!resp.ok) {
    const errors = await readErrorDetails(resp, "Failed to load leads.");
    throw new Error(errors[0]?.message ?? "Failed to load leads.");
  }

  return resp.json();
}

export async function getLead(id: string): Promise<LeadResponse | null> {
  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/leads/${id}`);
  } catch {
    throw new Error(NETWORK_ERROR_MESSAGE);
  }

  if (resp.status === 404) {
    return null;
  }

  if (!resp.ok) {
    const errors = await readErrorDetails(resp, "Failed to load lead.");
    throw new Error(errors[0]?.message ?? "Failed to load lead.");
  }

  return resp.json();
}

export async function updateLead(id: string, payload: LeadUpdatePayload): Promise<UpdateLeadResult> {
  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/leads/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: LeadResponse = await resp.json();
    return { ok: true, data };
  }

  if (resp.status === 409) {
    const body = await resp.json().catch(() => ({}));
    if (body.error === "duplicate_lead") {
      return {
        ok: false,
        duplicate: {
          candidates: Array.isArray(body.candidates) ? body.candidates : [],
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
  }

  if (resp.status === 404) {
    return { ok: false, errors: [{ field: "", message: "Lead not found." }] };
  }

  const body: ApiError = await resp.json().catch(() => ({ detail: [] }));
  return { ok: false, errors: body.detail ?? [] };
}

export async function transitionLeadStatus(
  id: string,
  status: LeadStatus,
): Promise<LeadActionResult<LeadResponse>> {
  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/leads/${id}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: LeadResponse = await resp.json();
    return { ok: true, data };
  }

  const body: ApiError = await resp.json().catch(() => ({ detail: [] }));
  return { ok: false, errors: body.detail ?? [] };
}

export async function handoffLeadToOpportunity(
  id: string,
): Promise<LeadActionResult<LeadOpportunityHandoff>> {
  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/leads/${id}/handoff/opportunity`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: LeadOpportunityHandoff = await resp.json();
    return { ok: true, data };
  }

  const body: ApiError = await resp.json().catch(() => ({ detail: [] }));
  return { ok: false, errors: body.detail ?? [] };
}

export async function convertLeadToCustomer(
  id: string,
  payload: CustomerCreatePayload,
): Promise<LeadActionResult<LeadCustomerConversionResult>> {
  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/leads/${id}/convert/customer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: LeadCustomerConversionResult = await resp.json();
    return { ok: true, data };
  }

  const body: ApiError = await resp.json().catch(() => ({ detail: [] }));
  return { ok: false, errors: body.detail ?? [] };
}

export const LEAD_STATUS_OPTIONS: LeadStatus[] = [
  "lead",
  "open",
  "replied",
  "opportunity",
  "quotation",
  "lost_quotation",
  "interested",
  "converted",
  "do_not_contact",
];

export const LEAD_QUALIFICATION_OPTIONS: LeadQualificationStatus[] = [
  "unqualified",
  "in_process",
  "qualified",
];
