import { useEffect, useState } from "react";

import { DataTable } from "../components/layout/DataTable";
import { PageHeader, SectionCard, SurfaceMessage } from "../components/layout/PageLayout";
import { Badge } from "../components/ui/badge";
import { Skeleton } from "../components/ui/skeleton";
import {
  fetchAuditLogs,
  fetchUsers,
  type AdminUser,
  type AuditLogEntry,
} from "../lib/api/admin";

export function AdminPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [userItems, auditItems] = await Promise.all([
          fetchUsers(),
          fetchAuditLogs(),
        ]);
        if (!active) return;
        setUsers(userItems);
        setAuditLogs(auditItems);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load admin data");
      } finally {
        if (active) setLoading(false);
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, []);

  const statusVariant = (status: string) => {
    switch (status) {
      case "active":
        return "success" as const;
      case "disabled":
        return "destructive" as const;
      default:
        return "outline" as const;
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Administration"
        title="Admin"
        description="Owner-only visibility into workspace users, roles, and the latest audit activity."
      />

      {error ? <SurfaceMessage tone="danger">{error}</SurfaceMessage> : null}

      {loading ? (
        <div className="grid gap-4 xl:grid-cols-2">
          <SectionCard title="Users" description="Workspace access roster.">
            <div className="space-y-3">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          </SectionCard>
          <SectionCard title="Audit Log" description="Recent administrative actions.">
            <div className="space-y-3">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          </SectionCard>
        </div>
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          <SectionCard title="Users" description="Workspace roster with role and status visibility.">
            <DataTable
              columns={[
                {
                  id: "email",
                  header: "Email",
                  sortable: true,
                  getSortValue: (user) => user.email,
                  cell: (user) => <span className="font-medium">{user.email}</span>,
                },
                {
                  id: "display_name",
                  header: "Name",
                  sortable: true,
                  getSortValue: (user) => user.display_name,
                  cell: (user) => user.display_name,
                },
                {
                  id: "role",
                  header: "Role",
                  sortable: true,
                  getSortValue: (user) => user.role,
                  cell: (user) => user.role,
                },
                {
                  id: "status",
                  header: "Status",
                  sortable: true,
                  getSortValue: (user) => user.status,
                  cell: (user) => (
                    <Badge variant={statusVariant(user.status)} className="normal-case tracking-normal">
                      {user.status}
                    </Badge>
                  ),
                },
              ]}
              data={users}
              emptyTitle="No users found."
              emptyDescription="No users are currently available for this tenant."
              getRowId={(user) => user.id}
            />
          </SectionCard>

          <SectionCard title="Audit Log" description="Most recent administrative events for this workspace.">
            <DataTable
              columns={[
                {
                  id: "created_at",
                  header: "When",
                  sortable: true,
                  getSortValue: (entry) => new Date(entry.created_at).getTime(),
                  cell: (entry) => new Date(entry.created_at).toLocaleString(),
                },
                {
                  id: "actor_id",
                  header: "Actor",
                  sortable: true,
                  getSortValue: (entry) => entry.actor_id,
                  cell: (entry) => entry.actor_id,
                },
                {
                  id: "action",
                  header: "Action",
                  sortable: true,
                  getSortValue: (entry) => entry.action,
                  cell: (entry) => entry.action,
                },
                {
                  id: "target",
                  header: "Target",
                  sortable: true,
                  getSortValue: (entry) => `${entry.entity_type}:${entry.entity_id}`,
                  cell: (entry) => `${entry.entity_type}:${entry.entity_id}`,
                },
              ]}
              data={auditLogs}
              emptyTitle="No audit entries found."
              emptyDescription="Administrative events will appear here as activity occurs."
              getRowId={(entry) => entry.id}
            />
          </SectionCard>
        </div>
      )}
    </div>
  );
}