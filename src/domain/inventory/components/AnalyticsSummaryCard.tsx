/** Analytics summary card — displays avg_daily, lead_time, ROP, safety_stock. */

import { useTranslation } from "react-i18next";

import { SectionCard } from "@/components/layout/PageLayout";

interface AnalyticsSummaryCardProps {
  avgDailyUsage: number | null;
  leadTimeDays: number | null;
  reorderPoint: number;
  safetyStock: number | null;
  loading?: boolean;
}

function num(value: number | null | undefined, fallback = "—"): string {
  if (value == null) return fallback;
  return value.toFixed(1);
}

export function AnalyticsSummaryCard({
  avgDailyUsage,
  leadTimeDays,
  reorderPoint,
  safetyStock,
  loading,
}: AnalyticsSummaryCardProps) {
  const { t } = useTranslation("common", {
    keyPrefix: "inventory.productDetail.analyticsTab.summary",
  });

  if (loading) {
    return (
      <SectionCard title={t("title")}>
        <div className="flex gap-8">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-12 w-24 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      </SectionCard>
    );
  }

  return (
    <SectionCard title={t("title")}>
      <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{t("metrics.avgDailyUsage")}</p>
          <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">{num(avgDailyUsage)}</p>
          <p className="text-xs text-muted-foreground">{t("metrics.avgDailyUsageUnit")}</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{t("metrics.leadTime")}</p>
          <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">{num(leadTimeDays)}</p>
          <p className="text-xs text-muted-foreground">{t("metrics.leadTimeUnit")}</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{t("metrics.reorderPoint")}</p>
          <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">{reorderPoint.toLocaleString()}</p>
          <p className="text-xs text-muted-foreground">{t("metrics.reorderPointUnit")}</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{t("metrics.safetyStock")}</p>
          <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">{num(safetyStock)}</p>
          <p className="text-xs text-muted-foreground">{t("metrics.safetyStockUnit")}</p>
        </div>
      </div>
    </SectionCard>
  );
}
