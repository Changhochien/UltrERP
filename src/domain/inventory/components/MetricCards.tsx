import { Boxes, AlertTriangle, Bell } from "lucide-react";
import { useEffect } from "react";

import { MetricCard } from "@/components/layout/PageLayout";
import { Badge } from "@/components/ui/badge";
import { useTranslation } from "react-i18next";
import { useProductSearch } from "../hooks/useProductSearch";
import { useReorderAlerts } from "../hooks/useReorderAlerts";

interface MetricCardsProps {
  warehouseId?: string;
}

export function MetricCards({ warehouseId }: MetricCardsProps) {
  const { t } = useTranslation("inventory");
  const { total: allTotal, loading: productsLoading, search: searchAll } = useProductSearch();
  const {
    alerts,
    total: alertTotal,
    loading: alertsLoading,
    error: alertsError,
    reload: reloadAlerts,
  } = useReorderAlerts({
    warehouseId,
  });

  useEffect(() => {
    searchAll("", warehouseId);
    void reloadAlerts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [warehouseId]);

  const pendingCount = alerts.filter((a) => a.status === "pending").length;
  const alertsUnavailable = Boolean(alertsError);
  const loading = productsLoading || alertsLoading;

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <MetricCard
        title={t("totalSkus")}
        value={productsLoading ? "—" : allTotal.toLocaleString()}
        description={warehouseId ? t("filteredScope") : t("allWarehouses")}
        badge={<Boxes className="size-5 text-muted-foreground" />}
      />
      <MetricCard
        title={t("lowStock")}
        value={loading || alertsUnavailable ? "—" : String(pendingCount)}
        description={alertsUnavailable ? t("alertsUnavailable") : t("totalAlerts", { count: alertTotal })}
        badge={
          !alertsUnavailable && pendingCount > 0 ? (
            <Badge variant="warning" className="gap-1.5 normal-case tracking-normal">
              <AlertTriangle className="size-3" />
              {t("attention")}
            </Badge>
          ) : (
            <Boxes className="size-5 text-muted-foreground" />
          )
        }
      />
      <MetricCard
        title={t("pendingAlerts")}
        value={loading || alertsUnavailable ? "—" : String(pendingCount)}
        description={alertsUnavailable ? t("alertsUnavailable") : t("requireAction")}
        badge={
          !alertsUnavailable && pendingCount > 0 ? (
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
        title={t("reorderAlerts")}
        value={loading || alertsUnavailable ? "—" : alertTotal.toLocaleString()}
        description={alertsUnavailable ? t("alertsUnavailable") : t("acrossAllWarehouses")}
        badge={<AlertTriangle className="size-5 text-muted-foreground" />}
      />
    </div>
  );
}
