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
  actor_type?: string;
  entity_type?: string;
  entity_id?: string;
  created_after?: string;
  created_before?: string;
  sort_by?: "created_at" | "actor_id" | "actor_type" | "action" | "entity_id";
  sort_direction?: "asc" | "desc";
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
  if (params?.actor_type) qs.set("actor_type", params.actor_type);
  if (params?.entity_type) qs.set("entity_type", params.entity_type);
  if (params?.entity_id) qs.set("entity_id", params.entity_id);
  if (params?.created_after) qs.set("created_after", params.created_after);
  if (params?.created_before) qs.set("created_before", params.created_before);
  if (params?.sort_by) qs.set("sort_by", params.sort_by);
  if (params?.sort_direction) qs.set("sort_direction", params.sort_direction);
  const qsStr = qs.toString();
  const url = `/api/v1/admin/audit-logs/${qsStr ? `?${qsStr}` : ""}`;
  const resp = await apiFetch(url);
  if (!resp.ok) {
    throw new Error(await responseErrorMessage(resp, "Failed to load audit logs"));
  }
  return resp.json();
}

// ---------------------------------------------------------------------------
// Legacy Refresh Admin API
// ---------------------------------------------------------------------------

export type RefreshMode = "full-rebaseline" | "incremental";

export interface LegacyRefreshTriggerRequest {
  tenant_id: string;
  schema_name: string;
  source_schema?: string;
  mode: RefreshMode;
  dry_run?: boolean;
  lookback_days?: number;
  reconciliation_threshold?: number;
}

export interface LegacyRefreshJobLaunched {
  job_id: string;
  lane_key: string;
  mode: RefreshMode;
  batch_id: string;
  launched_at: string;
  status: string;
}

export interface LegacyRefreshConflict {
  lane_key: string;
  conflict: string;
  detail: string;
  existing_lock: Record<string, unknown> | null;
}

export interface BatchPointer {
  batch_id: string | null;
  summary_path: string | null;
  started_at: string | null;
  completed_at: string | null;
  final_disposition: string | null;
  exit_code: number | null;
  validation_status: string | null;
  blocking_issue_count: number | null;
  reconciliation_gap_count: number | null;
  promotion_policy: Record<string, unknown> | null;
}

export interface LegacyRefreshLaneStatus {
  lane_key: string;
  tenant_id: string;
  schema_name: string;
  source_schema: string;
  lane_locked: boolean;
  current_job_id: string | null;
  lock_acquired_at: string | null;
  latest_run: BatchPointer | null;
  latest_success: BatchPointer | null;
  latest_promoted: BatchPointer | null;
  current_batch_mode: string | null;
  promotion_eligible: boolean;
  promotion_classification: string | null;
  affected_domains: string[];
  root_failure: string | null;
  blocked_reason: string | null;
  incremental_state_path: string | null;
  nightly_rebaseline_path: string | null;
  summary_root: string | null;
}

export interface RefreshJobRecord {
  job_id: string;
  batch_id: string;
  mode: string;
  started_at: string;
  completed_at: string | null;
  final_disposition: string;
  validation_status: string | null;
  promotion_eligible: boolean;
  blocked: boolean;
  blocked_reason: string | null;
}

export interface LegacyRefreshJobStatus {
  job_id: string;
  batch_id: string;
  mode: string;
  status: string;
  [key: string]: unknown;
}

export async function triggerLegacyRefresh(
  payload: LegacyRefreshTriggerRequest,
): Promise<LegacyRefreshJobLaunched | LegacyRefreshConflict> {
  const resp = await apiFetch("/api/v1/admin/legacy-refresh/trigger", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await resp.json();
  if (!resp.ok) {
    throw new Error(
      await responseErrorMessage(
        resp,
        body?.detail || "Failed to trigger legacy refresh",
      ),
    );
  }
  return body;
}

export async function fetchLegacyRefreshLanes(): Promise<{
  lanes: LegacyRefreshLaneStatus[];
}> {
  const resp = await apiFetch("/api/v1/admin/legacy-refresh/lanes");
  if (!resp.ok) {
    throw new Error(
      await responseErrorMessage(resp, "Failed to load legacy refresh lanes"),
    );
  }
  return resp.json();
}

export async function fetchLegacyRefreshStatus(
  tenantId: string,
  schemaName: string,
  sourceSchema = "public",
): Promise<LegacyRefreshLaneStatus> {
  const qs = new URLSearchParams({
    tenant_id: tenantId,
    schema_name: schemaName,
    source_schema: sourceSchema,
  });
  const resp = await apiFetch(
    `/api/v1/admin/legacy-refresh/status?${qs.toString()}`,
  );
  if (!resp.ok) {
    throw new Error(
      await responseErrorMessage(resp, "Failed to load lane status"),
    );
  }
  return resp.json();
}

export async function fetchLegacyRefreshJobStatus(
  jobId: string,
): Promise<LegacyRefreshJobStatus> {
  const resp = await apiFetch(
    `/api/v1/admin/legacy-refresh/jobs/${encodeURIComponent(jobId)}`,
  );
  if (!resp.ok) {
    throw new Error(
      await responseErrorMessage(resp, "Failed to load job status"),
    );
  }
  return resp.json();
}

export async function fetchLegacyRefreshRecentRuns(
  limit = 10,
): Promise<RefreshJobRecord[]> {
  const qs = new URLSearchParams({ limit: String(limit) });
  const resp = await apiFetch(
    `/api/v1/admin/legacy-refresh/recent-runs?${qs.toString()}`,
  );
  if (!resp.ok) {
    throw new Error(
      await responseErrorMessage(resp, "Failed to load recent runs"),
    );
  }
  return resp.json();
}