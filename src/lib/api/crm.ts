/** CRM lead API helpers. */

import type { CustomerCreatePayload } from "../../domain/customers/types";
import type {
  CRMCustomerGroup,
  CRMCustomerGroupPayload,
  CRMPipelineReport,
  CRMPipelineReportParams,
  CRMSettings,
  CRMSettingsUpdatePayload,
  CRMSetupBundle,
  CRMSalesStage,
  CRMSalesStagePayload,
  CRMTerritory,
  CRMTerritoryPayload,
  DuplicateLeadInfo,
  LeadCreatePayload,
  LeadConversionPayload,
  LeadConversionResult,
  LeadCustomerConversionResult,
  LeadListResponse,
  LeadOpportunityHandoff,
  LeadQualificationStatus,
  LeadResponse,
  LeadStatus,
  LeadUpdatePayload,
  OpportunityCreatePayload,
  OpportunityListResponse,
  OpportunityPartyKind,
  OpportunityQuotationHandoff,
  OpportunityResponse,
  OpportunityStatus,
  OpportunityTransitionPayload,
  OpportunityUpdatePayload,
  QuotationCreatePayload,
  QuotationOrderHandoff,
  QuotationListResponse,
  QuotationPartyKind,
  QuotationResponse,
  QuotationRevisionPayload,
  QuotationStatus,
  QuotationTransitionPayload,
  QuotationUpdatePayload,
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

export type OpportunityActionResult<TData> =
  | { ok: true; data: TData }
  | { ok: false; errors: ApiError["detail"] };

export type CreateOpportunityResult =
  | { ok: true; data: OpportunityResponse }
  | { ok: false; errors: ApiError["detail"] };

export type UpdateOpportunityResult =
  | { ok: true; data: OpportunityResponse }
  | {
      ok: false;
      versionConflict?: VersionConflictInfo;
      errors: ApiError["detail"];
    };

export type CreateQuotationResult =
  | { ok: true; data: QuotationResponse }
  | { ok: false; errors: ApiError["detail"] };

export type UpdateQuotationResult =
  | { ok: true; data: QuotationResponse }
  | {
      ok: false;
      versionConflict?: VersionConflictInfo;
      errors: ApiError["detail"];
    };

export type CRMActionResult<TData> =
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

export async function convertLead(
  id: string,
  payload: LeadConversionPayload,
): Promise<LeadActionResult<LeadConversionResult>> {
  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/leads/${id}/convert`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: LeadConversionResult = await resp.json();
    return { ok: true, data };
  }

  const body: ApiError = await resp.json().catch(() => ({ detail: [] }));
  return { ok: false, errors: body.detail ?? [] };
}

export async function createOpportunity(
  payload: OpportunityCreatePayload,
): Promise<CreateOpportunityResult> {
  let resp: Response;
  try {
    resp = await apiFetch("/api/v1/crm/opportunities", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: OpportunityResponse = await resp.json();
    return { ok: true, data };
  }

  const body: ApiError = await resp.json().catch(() => ({ detail: [] }));
  return { ok: false, errors: body.detail ?? [] };
}

export async function listOpportunities(params: {
  q?: string;
  status?: OpportunityStatus;
  page?: number;
  page_size?: number;
}): Promise<OpportunityListResponse> {
  const qs = new URLSearchParams();
  if (params.q) qs.set("q", params.q);
  if (params.status) qs.set("status", params.status);
  if (params.page) qs.set("page", String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));

  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/opportunities?${qs.toString()}`);
  } catch {
    throw new Error(NETWORK_ERROR_MESSAGE);
  }

  if (!resp.ok) {
    const errors = await readErrorDetails(resp, "Failed to load opportunities.");
    throw new Error(errors[0]?.message ?? "Failed to load opportunities.");
  }

  return resp.json();
}

export async function getOpportunity(id: string): Promise<OpportunityResponse | null> {
  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/opportunities/${id}`);
  } catch {
    throw new Error(NETWORK_ERROR_MESSAGE);
  }

  if (resp.status === 404) {
    return null;
  }

  if (!resp.ok) {
    const errors = await readErrorDetails(resp, "Failed to load opportunity.");
    throw new Error(errors[0]?.message ?? "Failed to load opportunity.");
  }

  return resp.json();
}

export async function updateOpportunity(
  id: string,
  payload: OpportunityUpdatePayload,
): Promise<UpdateOpportunityResult> {
  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/opportunities/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: OpportunityResponse = await resp.json();
    return { ok: true, data };
  }

  if (resp.status === 409) {
    const body = await resp.json().catch(() => ({}));
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
    return { ok: false, errors: [{ field: "", message: "Opportunity not found." }] };
  }

  const body: ApiError = await resp.json().catch(() => ({ detail: [] }));
  return { ok: false, errors: body.detail ?? [] };
}

export async function transitionOpportunityStatus(
  id: string,
  payload: OpportunityTransitionPayload,
): Promise<OpportunityActionResult<OpportunityResponse>> {
  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/opportunities/${id}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: OpportunityResponse = await resp.json();
    return { ok: true, data };
  }

  const body: ApiError = await resp.json().catch(() => ({ detail: [] }));
  return { ok: false, errors: body.detail ?? [] };
}

export async function prepareOpportunityQuotationHandoff(
  id: string,
): Promise<OpportunityActionResult<OpportunityQuotationHandoff>> {
  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/opportunities/${id}/handoff/quotation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: OpportunityQuotationHandoff = await resp.json();
    return { ok: true, data };
  }

  const body: ApiError = await resp.json().catch(() => ({ detail: [] }));
  return { ok: false, errors: body.detail ?? [] };
}

export type QuotationActionResult<TData> =
  | { ok: true; data: TData }
  | { ok: false; errors: ApiError["detail"] };

export async function createQuotation(
  payload: QuotationCreatePayload,
): Promise<CreateQuotationResult> {
  let resp: Response;
  try {
    resp = await apiFetch("/api/v1/crm/quotations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: QuotationResponse = await resp.json();
    return { ok: true, data };
  }

  const body: ApiError = await resp.json().catch(() => ({ detail: [] }));
  return { ok: false, errors: body.detail ?? [] };
}

export async function listQuotations(params: {
  q?: string;
  status?: QuotationStatus;
  page?: number;
  page_size?: number;
}): Promise<QuotationListResponse> {
  const qs = new URLSearchParams();
  if (params.q) qs.set("q", params.q);
  if (params.status) qs.set("status", params.status);
  if (params.page) qs.set("page", String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));

  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/quotations?${qs.toString()}`);
  } catch {
    throw new Error(NETWORK_ERROR_MESSAGE);
  }

  if (!resp.ok) {
    const errors = await readErrorDetails(resp, "Failed to load quotations.");
    throw new Error(errors[0]?.message ?? "Failed to load quotations.");
  }

  return resp.json();
}

export async function getQuotation(id: string): Promise<QuotationResponse | null> {
  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/quotations/${id}`);
  } catch {
    throw new Error(NETWORK_ERROR_MESSAGE);
  }

  if (resp.status === 404) {
    return null;
  }

  if (!resp.ok) {
    const errors = await readErrorDetails(resp, "Failed to load quotation.");
    throw new Error(errors[0]?.message ?? "Failed to load quotation.");
  }

  return resp.json();
}

export async function getCRMSetupBundle(): Promise<CRMSetupBundle> {
  let resp: Response;
  try {
    resp = await apiFetch("/api/v1/crm/setup");
  } catch {
    throw new Error(NETWORK_ERROR_MESSAGE);
  }

  if (!resp.ok) {
    const errors = await readErrorDetails(resp, "Failed to load CRM setup.");
    throw new Error(errors[0]?.message ?? "Failed to load CRM setup.");
  }

  return resp.json();
}

export async function updateCRMSettings(payload: CRMSettingsUpdatePayload): Promise<CRMActionResult<CRMSettings>> {
  let resp: Response;
  try {
    resp = await apiFetch("/api/v1/crm/settings", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: CRMSettings = await resp.json();
    return { ok: true, data };
  }

  return { ok: false, errors: await readErrorDetails(resp, "Failed to update CRM settings.") };
}

export async function createCRMSalesStage(payload: CRMSalesStagePayload): Promise<CRMActionResult<CRMSalesStage>> {
  let resp: Response;
  try {
    resp = await apiFetch("/api/v1/crm/setup/sales-stages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: CRMSalesStage = await resp.json();
    return { ok: true, data };
  }

  return { ok: false, errors: await readErrorDetails(resp, "Failed to create sales stage.") };
}

export async function updateCRMSalesStage(
  id: string,
  payload: Partial<CRMSalesStagePayload>,
): Promise<CRMActionResult<CRMSalesStage>> {
  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/setup/sales-stages/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: CRMSalesStage = await resp.json();
    return { ok: true, data };
  }

  return { ok: false, errors: await readErrorDetails(resp, "Failed to update sales stage.") };
}

export async function createCRMTerritory(payload: CRMTerritoryPayload): Promise<CRMActionResult<CRMTerritory>> {
  let resp: Response;
  try {
    resp = await apiFetch("/api/v1/crm/setup/territories", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: CRMTerritory = await resp.json();
    return { ok: true, data };
  }

  return { ok: false, errors: await readErrorDetails(resp, "Failed to create territory.") };
}

export async function updateCRMTerritory(
  id: string,
  payload: Partial<CRMTerritoryPayload>,
): Promise<CRMActionResult<CRMTerritory>> {
  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/setup/territories/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: CRMTerritory = await resp.json();
    return { ok: true, data };
  }

  return { ok: false, errors: await readErrorDetails(resp, "Failed to update territory.") };
}

export async function createCRMCustomerGroup(
  payload: CRMCustomerGroupPayload,
): Promise<CRMActionResult<CRMCustomerGroup>> {
  let resp: Response;
  try {
    resp = await apiFetch("/api/v1/crm/setup/customer-groups", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: CRMCustomerGroup = await resp.json();
    return { ok: true, data };
  }

  return { ok: false, errors: await readErrorDetails(resp, "Failed to create customer group.") };
}

export async function updateCRMCustomerGroup(
  id: string,
  payload: Partial<CRMCustomerGroupPayload>,
): Promise<CRMActionResult<CRMCustomerGroup>> {
  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/setup/customer-groups/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: CRMCustomerGroup = await resp.json();
    return { ok: true, data };
  }

  return { ok: false, errors: await readErrorDetails(resp, "Failed to update customer group.") };
}

export async function getCRMPipelineReport(params: CRMPipelineReportParams): Promise<CRMPipelineReport> {
  const qs = new URLSearchParams();
  if (params.record_type) qs.set("record_type", params.record_type);
  if (params.scope) qs.set("scope", params.scope);
  if (params.status) qs.set("status", params.status);
  if (params.sales_stage) qs.set("sales_stage", params.sales_stage);
  if (params.territory) qs.set("territory", params.territory);
  if (params.customer_group) qs.set("customer_group", params.customer_group);
  if (params.owner) qs.set("owner", params.owner);
  if (params.lost_reason) qs.set("lost_reason", params.lost_reason);
  if (params.utm_source) qs.set("utm_source", params.utm_source);
  if (params.utm_medium) qs.set("utm_medium", params.utm_medium);
  if (params.utm_campaign) qs.set("utm_campaign", params.utm_campaign);
  if (params.utm_content) qs.set("utm_content", params.utm_content);

  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/reports/pipeline?${qs.toString()}`);
  } catch {
    throw new Error(NETWORK_ERROR_MESSAGE);
  }

  if (!resp.ok) {
    const errors = await readErrorDetails(resp, "Failed to load CRM pipeline report.");
    throw new Error(errors[0]?.message ?? "Failed to load CRM pipeline report.");
  }

  return resp.json();
}

export async function prepareQuotationOrderHandoff(
  id: string,
): Promise<QuotationActionResult<QuotationOrderHandoff>> {
  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/quotations/${id}/handoff/order`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: QuotationOrderHandoff = await resp.json();
    return { ok: true, data };
  }

  const body: ApiError = await resp.json().catch(() => ({ detail: [] }));
  return { ok: false, errors: body.detail ?? [] };
}

export async function updateQuotation(
  id: string,
  payload: QuotationUpdatePayload,
): Promise<UpdateQuotationResult> {
  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/quotations/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: QuotationResponse = await resp.json();
    return { ok: true, data };
  }

  if (resp.status === 409) {
    const body = await resp.json().catch(() => ({}));
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
    return { ok: false, errors: [{ field: "", message: "Quotation not found." }] };
  }

  const body: ApiError = await resp.json().catch(() => ({ detail: [] }));
  return { ok: false, errors: body.detail ?? [] };
}

export async function transitionQuotationStatus(
  id: string,
  payload: QuotationTransitionPayload,
): Promise<QuotationActionResult<QuotationResponse>> {
  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/quotations/${id}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: QuotationResponse = await resp.json();
    return { ok: true, data };
  }

  const body: ApiError = await resp.json().catch(() => ({ detail: [] }));
  return { ok: false, errors: body.detail ?? [] };
}

export async function reviseQuotation(
  id: string,
  payload: QuotationRevisionPayload,
): Promise<QuotationActionResult<QuotationResponse>> {
  let resp: Response;
  try {
    resp = await apiFetch(`/api/v1/crm/quotations/${id}/revise`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return { ok: false, errors: networkErrorDetail() };
  }

  if (resp.ok) {
    const data: QuotationResponse = await resp.json();
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

export const OPPORTUNITY_STATUS_OPTIONS: OpportunityStatus[] = [
  "open",
  "replied",
  "quotation",
  "converted",
  "closed",
  "lost",
];

export const OPPORTUNITY_PARTY_OPTIONS: OpportunityPartyKind[] = [
  "lead",
  "customer",
  "prospect",
];

export const QUOTATION_STATUS_OPTIONS: QuotationStatus[] = [
  "draft",
  "open",
  "replied",
  "partially_ordered",
  "ordered",
  "lost",
  "cancelled",
  "expired",
];

export const QUOTATION_PARTY_OPTIONS: QuotationPartyKind[] = OPPORTUNITY_PARTY_OPTIONS;
