/** Audit log table — shows per-field change entries for a product. */

import { parseBackendDate } from "@/lib/time";
import type { AuditLogItem } from "../hooks/useProductAuditLog";

interface AuditLogTableProps {
  items: AuditLogItem[];
  loading?: boolean;
  error?: string | null;
}

export function AuditLogTable({ items, loading, error }: AuditLogTableProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <span className="text-sm text-muted-foreground">Loading...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-4 text-sm text-destructive">{error}</div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <p className="text-sm text-muted-foreground">No audit log entries found.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border">
            <th className="pb-2 text-left font-medium text-muted-foreground">Date</th>
            <th className="pb-2 text-left font-medium text-muted-foreground">Field</th>
            <th className="pb-2 text-left font-medium text-muted-foreground">Old Value</th>
            <th className="pb-2 text-left font-medium text-muted-foreground">New Value</th>
            <th className="pb-2 text-left font-medium text-muted-foreground">Actor</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, i) => (
            <tr key={i} className="border-b border-border/50">
              <td className="py-2">
                {parseBackendDate(item.created_at).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </td>
              <td className="py-2 capitalize">
                <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
                  {item.field}
                </span>
              </td>
              <td className="py-2 font-mono text-muted-foreground">
                {item.old_value ?? "—"}
              </td>
              <td className="py-2 font-mono text-foreground">
                {item.new_value ?? "—"}
              </td>
              <td className="py-2 text-muted-foreground">{item.actor_id}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
