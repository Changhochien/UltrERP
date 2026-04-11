/** Low-stock alerts dashboard card. */

import { useTranslation } from "react-i18next";

import { Badge } from "../../../components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Skeleton } from "../../../components/ui/skeleton";
import { normalizeAlertSeverity } from "../../../lib/alertSeverity";
import { cn } from "../../../lib/utils";
import { useLowStockAlerts } from "../hooks/useDashboard";

export function LowStockAlertsCard() {
  const { t } = useTranslation("common");
  const { data, isLoading, error } = useLowStockAlerts();

  const alerts = data?.items ?? [];
  const highestSeverity = alerts.some((alert) => normalizeAlertSeverity(alert.severity) === "CRITICAL")
    ? "CRITICAL"
    : alerts.some((alert) => normalizeAlertSeverity(alert.severity) === "WARNING")
      ? "WARNING"
      : "INFO";

  return (
    <Card data-testid="low-stock-card" className="h-full">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="space-y-1">
          <CardTitle>{t("dashboard.lowStock.title")}</CardTitle>
          <p className="text-sm text-muted-foreground">{t("dashboard.lowStock.description")}</p>
        </div>
        {!isLoading && !error && alerts.length > 0 ? (
          <Badge
            variant={
              highestSeverity === "CRITICAL"
                ? "destructive"
                : highestSeverity === "WARNING"
                  ? "warning"
                  : "info"
            }
            data-testid="alert-badge"
          >
            {alerts.length}
          </Badge>
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
          <p className="rounded-xl border px-4 py-6 text-sm alert-success" data-testid="low-stock-ok">
            {t("dashboard.lowStock.allOk")}
          </p>
        )}

        {!isLoading && !error && alerts.length > 0 && (
          <ul className="space-y-3" data-testid="low-stock-list">
            {alerts.map((alert) => {
              const severity = normalizeAlertSeverity(alert.severity);
              return (
                <li
                  key={alert.id}
                  className={cn(
                    "rounded-2xl border px-4 py-3",
                    severity === "CRITICAL"
                      ? "alert-item--critical border-destructive/20 bg-destructive/8"
                      : severity === "WARNING"
                        ? "alert-item--warning border alert-warning"
                        : "alert-item--info border alert-info",
                  )}
                  aria-label={`${alert.product_name}. Stock: ${alert.current_stock}, Reorder point: ${alert.reorder_point}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium text-foreground">{alert.product_name}</p>
                      <p className="text-sm text-muted-foreground">{alert.warehouse_name}</p>
                    </div>
                    <Badge
                      variant={
                        severity === "CRITICAL"
                          ? "destructive"
                          : severity === "WARNING"
                            ? "warning"
                            : "info"
                      }
                    >
                      {severity}
                    </Badge>
                  </div>
                  <p className="mt-3 text-sm text-muted-foreground">
                    {t("dashboard.lowStock.stock", { current: alert.current_stock, point: alert.reorder_point })}
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
