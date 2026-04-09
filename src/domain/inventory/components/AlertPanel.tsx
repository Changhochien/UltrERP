import { Package, RefreshCw } from "lucide-react";
import { parseBackendDate } from "@/lib/time";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SectionCard } from "@/components/layout/PageLayout";
import {
  useAcknowledgeAlert,
  useReorderAlerts,
} from "../hooks/useReorderAlerts";
import { useWarehouseContext } from "../context/WarehouseContext";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "pending", label: "Pending" },
  { value: "acknowledged", label: "Acknowledged" },
  { value: "resolved", label: "Resolved" },
] as const;

function formatDate(dateStr: string): string {
  return parseBackendDate(dateStr).toLocaleDateString("zh-TW", {
    timeZone: "Asia/Taipei",
    month: "short",
    day: "numeric",
  });
}

export function AlertPanel() {
  const [statusFilter, setStatusFilter] = useState("");
  const { selectedWarehouse } = useWarehouseContext();
  const { alerts, total, loading, error, reload } = useReorderAlerts({
    status: statusFilter || undefined,
    warehouseId: selectedWarehouse?.id,
  });
  const { acknowledge, submitting } = useAcknowledgeAlert();

  // Reload when warehouse or status filter changes
  useEffect(() => {
    void reload();
  }, [selectedWarehouse?.id, statusFilter, reload]);

  const handleAcknowledge = async (alertId: string) => {
    const ok = await acknowledge(alertId);
    if (ok) void reload();
  };

  const statusVariant = (status: string) => {
    switch (status) {
      case "pending": return "warning" as const;
      case "acknowledged": return "default" as const;
      case "resolved": return "success" as const;
      default: return "outline" as const;
    }
  };

  return (
    <SectionCard
      title="Reorder Alerts"
      description="Low-stock exceptions for the current warehouse scope."
      actions={
        <Badge variant="outline" className="normal-case tracking-normal">
          {total} total
        </Badge>
      }
    >
      {/* Filters */}
      <div className="mb-4 flex items-center gap-3">
        <label className="flex items-center gap-2 text-sm font-medium">
          <span className="text-muted-foreground">Status</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-8 rounded-lg border border-input bg-background px-2 text-sm"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </label>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => void reload()}
          disabled={loading}
          aria-label="Refresh alerts"
        >
          <RefreshCw className={`Size-3.5 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {/* List */}
      <div className="space-y-2">
        {loading ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <RefreshCw className="mr-2 size-4 animate-spin" />
            <span className="text-sm">Loading…</span>
          </div>
        ) : error ? (
          <div className="rounded-xl border border-destructive/20 bg-destructive/8 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        ) : alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-muted-foreground">
            <Package className="mb-2 size-8 opacity-30" />
            <p className="text-sm font-medium">No alerts found</p>
            <p className="text-xs">Critical stock alerts appear here</p>
          </div>
        ) : (
          alerts.map((alert) => (
            <div
              key={alert.id}
              className="flex items-start justify-between gap-3 rounded-xl border border-border/60 bg-card/60 p-3 transition-colors hover:bg-muted/20"
            >
              <div className="min-w-0 flex-1">
                <div className="mb-0.5 flex items-center gap-2">
                  <span className="truncate text-sm font-semibold">{alert.product_name}</span>
                  <Badge
                    variant={statusVariant(alert.status)}
                    className="shrink-0 normal-case tracking-normal"
                  >
                    {alert.status}
                  </Badge>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>{alert.warehouse_name}</span>
                  <span>·</span>
                  <span
                    className={
                      alert.current_stock < alert.reorder_point
                        ? "font-semibold text-destructive"
                        : ""
                    }
                  >
                    {alert.current_stock} / {alert.reorder_point}
                  </span>
                  <span>·</span>
                  <span>{formatDate(alert.created_at)}</span>
                </div>
              </div>
              {alert.status === "pending" && (
                <Button
                  type="button"
                  variant="ghost"
                  size="xs"
                  onClick={() => void handleAcknowledge(alert.id)}
                  disabled={submitting}
                  className="shrink-0"
                >
                  Ack
                </Button>
              )}
            </div>
          ))
        )}
      </div>
    </SectionCard>
  );
}
