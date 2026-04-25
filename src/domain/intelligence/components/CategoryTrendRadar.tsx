import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { formatChartCurrency } from "../../../components/charts/formatters";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../../components/ui/table";
import { useCategoryTrends, useMarketOpportunities } from "../hooks/useIntelligence";
import { OpportunitySignalBanner } from "./OpportunitySignalBanner";
import type { CategoryTrend } from "../types";

const TREND_BAR_COLORS = {
  growing: "#22c55e",
  declining: "#ef4444",
  stable: "#6b7280",
} as const;

const TREND_BADGE_VARIANTS = {
  growing: "success" as const,
  declining: "destructive" as const,
  stable: "secondary" as const,
};



function formatDelta(value: number | null): string {
  if (value == null) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function formatGeneratedAt(value: string, language: string): string {
  const locale = language === "zh-Hant" ? "zh-TW" : "en-US";
  return new Date(value).toLocaleString(locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function sortTrends(trends: CategoryTrend[]): CategoryTrend[] {
  return [...trends].sort((left, right) => {
    if (left.revenue_delta_pct == null && right.revenue_delta_pct == null) {
      const revenueDiff = Number(right.current_period_revenue) - Number(left.current_period_revenue);
      if (revenueDiff !== 0) {
        return revenueDiff;
      }
      if (right.customer_count !== left.customer_count) {
        return right.customer_count - left.customer_count;
      }
      return left.category.localeCompare(right.category);
    }
    if (left.revenue_delta_pct == null) return 1;
    if (right.revenue_delta_pct == null) return -1;
    if (right.revenue_delta_pct !== left.revenue_delta_pct) {
      return right.revenue_delta_pct - left.revenue_delta_pct;
    }
    return left.category.localeCompare(right.category);
  });
}

export function CategoryTrendRadar() {
  const { t, i18n } = useTranslation("common", { keyPrefix: "intelligence.categoryTrends" });
  const [period, setPeriod] = useState<"last_30d" | "last_90d" | "last_12m">("last_90d");
  const { data, isLoading, error } = useCategoryTrends(period);
  const { data: marketSignals } = useMarketOpportunities(period);
  const locale = i18n.resolvedLanguage ?? i18n.language ?? "en";
  const sortedTrends = data ? sortTrends(data.trends) : [];
  const chartData = sortedTrends.map((trend) => ({
    ...trend,
    current_period_revenue: Number(trend.current_period_revenue),
    prior_period_revenue: Number(trend.prior_period_revenue),
  }));

  return (
    <SectionCard
      title={t("title", { defaultValue: "Category Trend Radar" })}
      description={t("description", {
        defaultValue: "Rolling demand signals across categories, with current-vs-prior period comparison.",
      })}
      actions={(
        <div className="flex items-center gap-2" role="group" aria-label="Category trend period selector">
          <Button
            type="button"
            size="sm"
            variant={period === "last_30d" ? "default" : "outline"}
            onClick={() => setPeriod("last_30d")}
            aria-pressed={period === "last_30d"}
          >
            {t("period30d", { defaultValue: "30d" })}
          </Button>
          <Button
            type="button"
            size="sm"
            variant={period === "last_90d" ? "default" : "outline"}
            onClick={() => setPeriod("last_90d")}
            aria-pressed={period === "last_90d"}
          >
            {t("period90d", { defaultValue: "90d" })}
          </Button>
          <Button
            type="button"
            size="sm"
            variant={period === "last_12m" ? "default" : "outline"}
            onClick={() => setPeriod("last_12m")}
            aria-pressed={period === "last_12m"}
          >
            {t("period12m", { defaultValue: "12m" })}
          </Button>
        </div>
      )}
    >
      <div className="space-y-4">
        {isLoading ? (
          <div className="space-y-3" data-testid="category-trend-loading">
            <div className="h-10 rounded-xl bg-muted/60" />
            <div className="h-52 rounded-xl bg-muted/40" />
          </div>
        ) : null}

        {!isLoading && error ? (
          <SurfaceMessage tone="danger">
            {t("loadError", { defaultValue: "Failed to load category trends." })}
          </SurfaceMessage>
        ) : null}

        {!isLoading && !error && data ? (
          <>
            <OpportunitySignalBanner
              signals={marketSignals?.signals ?? []}
              deferredSignalTypes={marketSignals?.deferred_signal_types ?? []}
            />

            <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              <span>
                {t("generatedAt", {
                  value: formatGeneratedAt(data.generated_at, i18n.resolvedLanguage ?? i18n.language),
                  defaultValue: `Generated ${formatGeneratedAt(data.generated_at, i18n.resolvedLanguage ?? i18n.language)}`,
                })}
              </span>
              <span>
                {t("activityBasis", {
                  defaultValue: "Based on confirmed, shipped, and fulfilled order-line demand.",
                })}
              </span>
            </div>

            {sortedTrends.length === 0 ? (
              <SurfaceMessage>
                {t("empty", { defaultValue: "No category demand signals yet." })}
              </SurfaceMessage>
            ) : (
              <div className="space-y-6">
                <div className="h-[320px]" data-testid="category-trend-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
                      <XAxis dataKey="category" tickLine={false} axisLine={false} fontSize={12} />
                      <YAxis tickFormatter={(value) => `NT$ ${(Number(value) / 1000).toFixed(0)}k`} width={72} />
                      <Tooltip
                        formatter={(value: number, name: string) => [formatChartCurrency(value, locale, "TWD"), name]}
                        labelStyle={{ color: "#0f172a" }}
                      />
                      <Bar dataKey="prior_period_revenue" name={t("priorPeriod", { defaultValue: "Prior" })} fill="#d1d5db" radius={[6, 6, 0, 0]} />
                      <Bar dataKey="current_period_revenue" name={t("currentPeriod", { defaultValue: "Current" })} radius={[6, 6, 0, 0]}>
                        {chartData.map((entry) => (
                          <Cell key={entry.category} fill={TREND_BAR_COLORS[entry.trend]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t("title", { defaultValue: "Category Trend Radar" })}</TableHead>
                      <TableHead>{t("currentPeriod", { defaultValue: "Current" })}</TableHead>
                      <TableHead>{t("priorPeriod", { defaultValue: "Prior" })}</TableHead>
                      <TableHead>{t("delta", { defaultValue: "Revenue Delta" })}</TableHead>
                      <TableHead className="text-right">{t("newCustomers", { defaultValue: "New" })}</TableHead>
                      <TableHead className="text-right">{t("churnedCustomers", { defaultValue: "Churned" })}</TableHead>
                      <TableHead>{t("topProducts", { defaultValue: "Top Products" })}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sortedTrends.map((trend) => (
                      <TableRow key={trend.category}>
                        <TableCell>
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{trend.category}</span>
                              <Badge variant={TREND_BADGE_VARIANTS[trend.trend]}>
                                {t(`trend.${trend.trend}`, { defaultValue: trend.trend })}
                              </Badge>
                              {trend.trend_context ? (
                                <Badge variant="outline">
                                  {t(`trendContext.${trend.trend_context}`, { defaultValue: trend.trend_context })}
                                </Badge>
                              ) : null}
                            </div>
                            <p className="text-xs text-muted-foreground">
                              {t("customerFootnote", {
                                current: trend.customer_count,
                                prior: trend.prior_customer_count,
                                defaultValue: `${trend.customer_count} / ${trend.prior_customer_count} customers`,
                              })}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell>{formatChartCurrency(Number(trend.current_period_revenue), locale, "TWD")}</TableCell>
                        <TableCell>{formatChartCurrency(Number(trend.prior_period_revenue), locale, "TWD")}</TableCell>
                        <TableCell className="font-medium">{formatDelta(trend.revenue_delta_pct)}</TableCell>
                        <TableCell className="text-right">{trend.new_customer_count}</TableCell>
                        <TableCell className="text-right">{trend.churned_customer_count}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {trend.top_products.length > 0
                            ? trend.top_products.map((product) => product.product_name).join(", ")
                            : "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </>
        ) : null}
      </div>
    </SectionCard>
  );
}