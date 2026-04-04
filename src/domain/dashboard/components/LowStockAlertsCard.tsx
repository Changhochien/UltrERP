/** Low-stock alerts dashboard card. */

import { Badge } from "../../../components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Skeleton } from "../../../components/ui/skeleton";
import { cn } from "../../../lib/utils";
import { useLowStockAlerts } from "../hooks/useDashboard";

export function LowStockAlertsCard() {
  const { data, isLoading, error } = useLowStockAlerts();

  const alerts = data?.items ?? [];

  return (
    <Card data-testid="low-stock-card" className="h-full">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="space-y-1">
          <CardTitle>Low-Stock Alerts</CardTitle>
          <p className="text-sm text-muted-foreground">Items at or below reorder coverage thresholds.</p>
        </div>
        {!isLoading && !error && alerts.length > 0 ? (
          <Badge variant="warning" data-testid="alert-badge">{alerts.length}</Badge>
        ) : null}
      </CardHeader>
      <CardContent className="space-y-4 pt-0">

        {isLoading && (
          <div data-testid="low-stock-loading" className="space-y-3">
            <Skeleton className="h-5 w-36" />
            <Skeleton className="h-28 w-full" />
          </div>
        )}

        {error && <p className="text-sm text-destructive">{error}</p>}

        {!isLoading && !error && alerts.length === 0 && (
          <p className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-6 text-sm text-emerald-700 dark:text-emerald-300" data-testid="low-stock-ok">
            All stock levels OK ✓
          </p>
        )}

        {!isLoading && !error && alerts.length > 0 && (
          <ul className="space-y-3" data-testid="low-stock-list">
            {alerts.map((alert) => {
              const critical = alert.current_stock < alert.reorder_point * 0.5;
              return (
                <li
                  key={alert.id}
                  className={cn(
                    "rounded-2xl border px-4 py-3",
                    critical
                      ? "alert-item--critical border-destructive/20 bg-destructive/8"
                      : "alert-item--warning border-amber-500/20 bg-amber-500/10",
                  )}
                  aria-label={`${alert.product_name}. Stock: ${alert.current_stock}, Reorder point: ${alert.reorder_point}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium text-foreground">{alert.product_name}</p>
                      <p className="text-sm text-muted-foreground">{alert.warehouse_name}</p>
                    </div>
                    <Badge variant={critical ? "destructive" : "warning"}>{alert.status}</Badge>
                  </div>
                  <p className="mt-3 text-sm text-muted-foreground">
                    Stock: {alert.current_stock} · Reorder: {alert.reorder_point}
                  </p>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
