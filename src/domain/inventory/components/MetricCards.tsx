import { Boxes, AlertTriangle, Bell } from "lucide-react";
import { useEffect } from "react";

import { MetricCard } from "@/components/layout/PageLayout";
import { Badge } from "@/components/ui/badge";
import { useProductSearch } from "../hooks/useProductSearch";
import { useReorderAlerts } from "../hooks/useReorderAlerts";

interface MetricCardsProps {
  warehouseId?: string;
}

export function MetricCards({ warehouseId }: MetricCardsProps) {
  const { total: allTotal, search: searchAll } = useProductSearch();
  const { alerts, total: alertTotal, reload: reloadAlerts } = useReorderAlerts({
    warehouseId,
  });

  useEffect(() => {
    searchAll("", warehouseId);
    void reloadAlerts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [warehouseId]);

  const pendingCount = alerts.filter((a) => a.status === "pending").length;

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <MetricCard
        title="Total SKUs"
        value={allTotal.toLocaleString()}
        description={warehouseId ? "Filtered scope" : "All warehouses"}
        badge={<Boxes className="size-5 text-muted-foreground" />}
      />
      <MetricCard
        title="Low Stock"
        value={String(pendingCount)}
        description={`${alertTotal} total alerts`}
        badge={
          pendingCount > 0 ? (
            <Badge variant="warning" className="gap-1.5 normal-case tracking-normal">
              <AlertTriangle className="size-3" />
              Attention
            </Badge>
          ) : (
            <Boxes className="size-5 text-muted-foreground" />
          )
        }
      />
      <MetricCard
        title="Pending Alerts"
        value={String(pendingCount)}
        description="Require action"
        badge={
          pendingCount > 0 ? (
            <Badge variant="destructive" className="gap-1.5 normal-case tracking-normal">
              <Bell className="size-3" />
              {pendingCount}
            </Badge>
          ) : (
            <Bell className="size-5 text-muted-foreground" />
          )
        }
      />
      <MetricCard
        title="Reorder Alerts"
        value={alertTotal.toLocaleString()}
        description="Across all warehouses"
        badge={<AlertTriangle className="size-5 text-muted-foreground" />}
      />
    </div>
  );
}
