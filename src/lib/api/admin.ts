import { apiFetch } from "../apiFetch";

export const ADMIN_USER_ROLES = ["owner", "finance", "warehouse", "sales"] as const;
export const ADMIN_USER_STATUSES = ["active", "disabled"] as const;

export type AdminUserRole = (typeof ADMIN_USER_ROLES)[number];
export type AdminUserStatus = (typeof ADMIN_USER_STATUSES)[number];

export interface AdminUser {
  id: string;
  email: string;
  display_name: string;
  role: AdminUserRole;
  status: AdminUserStatus;
  created_at: string;
}

export interface AuditLogEntry {
  id: string;
  tenant_id: string;
  actor_id: string;
  actor_type: string;
  action: string;
  entity_type: string;
  entity_id: string;
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
  correlation_id: string | null;
  notes: string | null;
  created_at: string;
}

export interface AuditLogQueryParams {
  page?: number;
  page_size?: number;
  action?: string;
  actor_id?: string;
  entity_type?: string;
  entity_id?: string;
  created_after?: string;
  created_before?: string;
}

export interface AuditLogListResult {
  items: AuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface AdminUserCreateRequest {
  email: string;
  password: string;
  display_name: string;
  role: AdminUserRole;
}

export interface AdminUserUpdateRequest {
  display_name?: string;
  role?: AdminUserRole;
  status?: AdminUserStatus;
  password?: string;
}

async function responseErrorMessage(
  resp: Response,
  fallback: string,
): Promise<string> {
  const body = await resp.json().catch(() => null) as { detail?: string } | null;
  if (typeof body?.detail === "string" && body.detail.trim()) {
    return body.detail;
  }
  return fallback;
}

export async function fetchUsers(): Promise<AdminUser[]> {
  const resp = await apiFetch("/api/v1/admin/users/");
  if (!resp.ok) {
    throw new Error(await responseErrorMessage(resp, "Failed to load users"));
  }
  const body = await resp.json();
  return body.items ?? [];
}

export async function createUser(payload: AdminUserCreateRequest): Promise<AdminUser> {
  const resp = await apiFetch("/api/v1/admin/users/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    throw new Error(
      await responseErrorMessage(
        resp,
        resp.status === 409 ? "A user with this email already exists" : "Failed to create user",
      ),
    );
  }
  return resp.json();
}

export async function updateUser(
  userId: string,
  payload: AdminUserUpdateRequest,
): Promise<AdminUser> {
  const resp = await apiFetch(`/api/v1/admin/users/${encodeURIComponent(userId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    throw new Error(await responseErrorMessage(resp, "Failed to update user"));
  }
  return resp.json();
}

export async function fetchAuditLogs(
  params?: AuditLogQueryParams,
): Promise<AuditLogListResult> {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  if (params?.action) qs.set("action", params.action);
  if (params?.actor_id) qs.set("actor_id", params.actor_id);
  if (params?.entity_type) qs.set("entity_type", params.entity_type);
  if (params?.entity_id) qs.set("entity_id", params.entity_id);
  if (params?.created_after) qs.set("created_after", params.created_after);
  if (params?.created_before) qs.set("created_before", params.created_before);
  const qsStr = qs.toString();
  const url = `/api/v1/admin/audit-logs/${qsStr ? `?${qsStr}` : ""}`;
  const resp = await apiFetch(url);
  if (!resp.ok) {
    throw new Error(await responseErrorMessage(resp, "Failed to load audit logs"));
  }
  return resp.json();
}