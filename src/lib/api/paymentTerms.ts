import { apiFetch } from "../apiFetch";

export interface PaymentTermsTemplateDetailPayload {
  row_number: number;
  invoice_portion: string;
  credit_days?: number;
  credit_months?: number;
  discount_percent?: string | null;
  discount_validity_days?: number | null;
  mode_of_payment?: string | null;
  description?: string | null;
}

export interface PaymentTermsTemplateCreate {
  template_name: string;
  description?: string | null;
  allocate_payment_based_on_payment_terms?: boolean;
  legacy_code?: string | null;
  details: PaymentTermsTemplateDetailPayload[];
}

export interface PaymentTermsTemplateUpdate {
  template_name?: string;
  description?: string | null;
  allocate_payment_based_on_payment_terms?: boolean;
  is_active?: boolean;
  legacy_code?: string | null;
  details?: PaymentTermsTemplateDetailPayload[];
}

export interface PaymentTermsTemplateDetail {
  id: string;
  tenant_id: string;
  template_id: string;
  row_number: number;
  invoice_portion: string;
  credit_days: number;
  credit_months: number;
  discount_percent: string | null;
  discount_validity_days: number | null;
  mode_of_payment: string | null;
  description: string | null;
  created_at: string;
}

export interface PaymentTermsTemplate {
  id: string;
  tenant_id: string;
  template_name: string;
  description: string | null;
  allocate_payment_based_on_payment_terms: boolean;
  is_active: boolean;
  legacy_code: string | null;
  created_at: string;
  updated_at: string;
  details: PaymentTermsTemplateDetail[];
}

export interface PaymentTermsTemplateListResponse {
  items: PaymentTermsTemplate[];
  total: number;
}

export async function fetchPaymentTermsTemplates(options?: {
  includeInactive?: boolean;
  signal?: AbortSignal;
}): Promise<{ ok: true; data: PaymentTermsTemplateListResponse } | { ok: false; error: string }> {
  const params = new URLSearchParams();
  if (options?.includeInactive) params.set("include_inactive", "true");
  const qs = params.toString();
  try {
    const resp = await apiFetch(`/api/v1/settings/payment-terms-templates${qs ? `?${qs}` : ""}`, {
      signal: options?.signal,
    });
    if (!resp.ok) return { ok: false, error: "Failed to fetch payment terms templates" };
    return { ok: true, data: (await resp.json()) as PaymentTermsTemplateListResponse };
  } catch {
    return { ok: false, error: "Unable to reach the server" };
  }
}

export async function createPaymentTermsTemplate(
  data: PaymentTermsTemplateCreate,
): Promise<{ ok: true; data: PaymentTermsTemplate } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch("/api/v1/settings/payment-terms-templates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    const body = await resp.json().catch(() => null);
    if (!resp.ok) {
      return { ok: false, error: (body as { detail?: string } | null)?.detail ?? "Failed to create payment terms template" };
    }
    return { ok: true, data: body as PaymentTermsTemplate };
  } catch {
    return { ok: false, error: "Unable to reach the server" };
  }
}

export async function updatePaymentTermsTemplate(
  templateId: string,
  data: PaymentTermsTemplateUpdate,
): Promise<{ ok: true; data: PaymentTermsTemplate } | { ok: false; error: string }> {
  try {
    const resp = await apiFetch(`/api/v1/settings/payment-terms-templates/${encodeURIComponent(templateId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    const body = await resp.json().catch(() => null);
    if (!resp.ok) {
      return { ok: false, error: (body as { detail?: string } | null)?.detail ?? "Failed to update payment terms template" };
    }
    return { ok: true, data: body as PaymentTermsTemplate };
  } catch {
    return { ok: false, error: "Unable to reach the server" };
  }
}
