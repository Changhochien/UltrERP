import { apiFetch } from "../apiFetch";

export interface AdminUser {
  id: string;
  email: string;
  display_name: string;
  role: string;
  status: string;
  created_at: string;
}

export interface AuditLogEntry {
  id: string;
  actor_id: string;
  actor_type: string;
  action: string;
  entity_type: string;
  entity_id: string;
  created_at: string;
}

export async function fetchUsers(): Promise<AdminUser[]> {
  const resp = await apiFetch("/api/v1/admin/users/");
  if (!resp.ok) throw new Error("Failed to load users");
  const body = await resp.json();
  return body.items ?? [];
}

export async function fetchAuditLogs(): Promise<AuditLogEntry[]> {
  const resp = await apiFetch("/api/v1/admin/audit-logs/?page=1&page_size=20");
  if (!resp.ok) throw new Error("Failed to load audit logs");
  const body = await resp.json();
  return body.items ?? [];
}