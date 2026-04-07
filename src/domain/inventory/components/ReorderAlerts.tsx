/** Reorder alerts list with filtering and acknowledge action. */

import { useMemo, useState } from "react";

import { DataTable, DataTableToolbar } from "../../../components/layout/DataTable";
import { SectionCard } from "../../../components/layout/PageLayout";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { useWarehouses } from "../hooks/useWarehouses";
import {
  useReorderAlerts,
  useAcknowledgeAlert,
} from "../hooks/useReorderAlerts";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "pending", label: "Pending" },
  { value: "acknowledged", label: "Acknowledged" },
  { value: "resolved", label: "Resolved" },
] as const;

export function ReorderAlerts() {
  const [statusFilter, setStatusFilter] = useState("");
  const [warehouseFilter, setWarehouseFilter] = useState("");

  const filters = useMemo(
    () => ({
      status: statusFilter || undefined,
      warehouseId: warehouseFilter || undefined,
    }),
    [statusFilter, warehouseFilter],
  );

  const { alerts, total, loading, error, reload } = useReorderAlerts(filters);
  const { warehouses, loading: whLoading } = useWarehouses();
  const { acknowledge, submitting, error: ackError } = useAcknowledgeAlert();

  const handleAcknowledge = async (alertId: string) => {
    const ok = await acknowledge(alertId);
    if (ok) void reload();
  };

  const statusVariant = (status: string) => {
    switch (status) {
      case "pending":
        return "warning" as const;
      case "acknowledged":
        return "default" as const;
      case "resolved":
        return "success" as const;
      default:
        return "outline" as const;
    }
  };

  return (
    <SectionCard title="Reorder Alerts" description="Prioritized low-stock exceptions for the current warehouse scope.">
      <DataTable
        tableClassName="min-w-[760px]"
        columns={[
          { id: "product_name", header: "Product", sortable: true, getSortValue: (item) => item.product_name, cell: (item) => <span className="font-medium">{item.product_name}</span> },
          { id: "warehouse_name", header: "Warehouse", sortable: true, getSortValue: (item) => item.warehouse_name, cell: (item) => item.warehouse_name },
          {
            id: "current_stock",
            header: "Current Stock",
            sortable: true,
            getSortValue: (item) => item.current_stock,
            cell: (item) => (
              <span className={item.current_stock < item.reorder_point ? "font-semibold text-destructive" : undefined}>
                {item.current_stock}
              </span>
            ),
          },
          { id: "reorder_point", header: "Reorder Point", sortable: true, getSortValue: (item) => item.reorder_point, cell: (item) => item.reorder_point },
          {
            id: "status",
            header: "Status",
            sortable: true,
            getSortValue: (item) => item.status,
            cell: (item) => (
              <Badge variant={statusVariant(item.status)} className="normal-case tracking-normal">
                {item.status}
              </Badge>
            ),
          },
          { id: "created_at", header: "Created", sortable: true, getSortValue: (item) => new Date(item.created_at).getTime(), cell: (item) => new Date(item.created_at).toLocaleDateString() },
          {
            id: "actions",
            header: "Action",
            className: "whitespace-nowrap",
            headerClassName: "whitespace-nowrap",
            cell: (item) => item.status === "pending" ? (
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="whitespace-nowrap"
                onClick={() => void handleAcknowledge(item.id)}
                disabled={submitting}
                aria-label={`Acknowledge alert for ${item.product_name}`}
              >
                Acknowledge
              </Button>
            ) : "—",
          },
        ]}
        data={alerts}
        loading={loading}
        error={error || ackError}
        emptyTitle="No reorder alerts found."
        emptyDescription="Critical stock alerts will appear here once inventory crosses reorder thresholds."
        toolbar={(
          <DataTableToolbar>
            <div className="text-sm text-muted-foreground">{alerts.length > 0 ? `Showing ${alerts.length} of ${total} alerts` : "Filter by status and warehouse."}</div>
            <div className="flex min-w-0 flex-col gap-3 md:flex-row md:items-center">
              <label className="flex flex-col items-start gap-2 text-sm font-medium text-foreground sm:flex-row sm:items-center sm:gap-3">
                <span>Status</span>
                <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} aria-label="Filter by status" className="w-full min-w-0 sm:w-44">
                  {STATUS_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col items-start gap-2 text-sm font-medium text-foreground sm:flex-row sm:items-center sm:gap-3">
                <span>Warehouse</span>
                <select value={warehouseFilter} onChange={(event) => setWarehouseFilter(event.target.value)} aria-label="Filter by warehouse" className="w-full min-w-0 sm:w-52" disabled={whLoading}>
                  <option value="">All warehouses</option>
                  {warehouses.map((warehouse) => (
                    <option key={warehouse.id} value={warehouse.id}>{warehouse.name}</option>
                  ))}
                </select>
              </label>
            </div>
          </DataTableToolbar>
        )}
        getRowId={(item) => item.id}
      />
    </SectionCard>
  );
}
