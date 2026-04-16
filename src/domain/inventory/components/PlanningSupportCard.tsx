import { Badge } from "@/components/ui/badge";
import { SectionCard } from "@/components/layout/PageLayout";
import { useTranslation } from "react-i18next";

import { useProductPlanningSupport } from "../hooks/useProductPlanningSupport";
import type { PlanningSupportDataBasis } from "../types";

interface PlanningSupportCardProps {
  productId: string;
}

function formatNumber(value: number | string | null | undefined, maximumFractionDigits = 3): string {
  if (value == null) return "—";
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(parsed)) return String(value);
  return parsed.toLocaleString(undefined, { maximumFractionDigits });
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border/60 bg-muted/20 p-4">
      <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="mt-2 font-mono text-2xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}

export function PlanningSupportCard({ productId }: PlanningSupportCardProps) {
  const { t } = useTranslation("common", {
    keyPrefix: "inventory.productDetail.analyticsTab.planningSupport",
  });
  const { data, loading, error } = useProductPlanningSupport(productId, {
    months: 12,
    includeCurrentMonth: true,
  });

  const actions = data ? (
    <div className="flex flex-wrap items-center gap-2">
      {data.advisory_only ? (
        <Badge variant="warning" className="normal-case tracking-normal">
          {t("advisory")}
        </Badge>
      ) : null}
      {data.window.is_partial ? (
        <Badge variant="secondary" className="normal-case tracking-normal">
          {t("partial")}
        </Badge>
      ) : null}
      <Badge variant="outline" className="normal-case tracking-normal">
        {t(`dataBasisLabels.${data.data_basis as PlanningSupportDataBasis}`)}
      </Badge>
    </div>
  ) : undefined;

  if (loading) {
    return (
      <SectionCard title={t("title")} description={t("description")}>
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={index} className="h-20 animate-pulse rounded-xl bg-muted" />
            ))}
          </div>
          <div className="h-36 animate-pulse rounded-xl bg-muted" />
        </div>
      </SectionCard>
    );
  }

  return (
    <SectionCard title={t("title")} description={t("description")} actions={actions}>
      {error ? (
        <div className="rounded-xl border border-destructive/20 bg-destructive/8 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      ) : !data ? null : (
        <div className="space-y-6">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
            <Metric label={t("metrics.avgMonthly")} value={formatNumber(data.avg_monthly_quantity)} />
            <Metric label={t("metrics.peakMonthly")} value={formatNumber(data.peak_monthly_quantity)} />
            <Metric label={t("metrics.lowMonthly")} value={formatNumber(data.low_monthly_quantity)} />
            <Metric label={t("metrics.seasonalityIndex")} value={formatNumber(data.seasonality_index)} />
            <Metric label={t("metrics.historyMonths")} value={formatNumber(data.history_months_used, 0)} />
            <Metric label={t("metrics.currentMonthLive")} value={formatNumber(data.current_month_live_quantity)} />
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Metric label={t("metrics.reorderPoint")} value={formatNumber(data.reorder_point, 0)} />
            <Metric label={t("metrics.onOrder")} value={formatNumber(data.on_order_qty, 0)} />
            <Metric label={t("metrics.inTransit")} value={formatNumber(data.in_transit_qty, 0)} />
            <Metric label={t("metrics.reserved")} value={formatNumber(data.reserved_qty, 0)} />
          </div>

          <div className="space-y-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <h4 className="text-sm font-semibold text-foreground">{t("historySeries")}</h4>
              <p className="text-xs text-muted-foreground">
                {t("window", {
                  start: data.window.start_month,
                  end: data.window.end_month,
                })}
              </p>
            </div>
            {data.items.length ? (
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                {data.items.map((item) => (
                  <div key={`${item.month}-${item.source}`} className="rounded-xl border border-border/60 bg-muted/20 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium text-foreground">{item.month}</p>
                      <Badge variant={item.source === "live" ? "warning" : "outline"} className="normal-case tracking-normal">
                        {t(`sourceLabels.${item.source}`)}
                      </Badge>
                    </div>
                    <p className="mt-3 font-mono text-2xl font-semibold tabular-nums">
                      {formatNumber(item.quantity)}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-border/70 bg-muted/10 px-4 py-5">
                <p className="font-medium text-foreground">{t("emptyTitle")}</p>
                <p className="mt-1 text-sm text-muted-foreground">{t("emptyBody")}</p>
              </div>
            )}
          </div>

          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-foreground">{t("aboveAverage")}</h4>
            {data.above_average_months.length ? (
              <div className="flex flex-wrap gap-2">
                {data.above_average_months.map((month) => (
                  <Badge key={month} variant="outline" className="normal-case tracking-normal">
                    {month}
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">{t("none")}</p>
            )}
          </div>
        </div>
      )}
    </SectionCard>
  );
}