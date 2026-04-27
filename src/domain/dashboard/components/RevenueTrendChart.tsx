/** Revenue trend line chart — configurable period (month/quarter/year) daily revenue using recharts. */

import { useTranslation } from "react-i18next";
import {
  Brush,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatBackendCalendarDate } from "../../../lib/time";

import { SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { formatChartCurrency, formatCurrencyAxis } from "../../../components/charts/formatters";
import { Button } from "../../../components/ui/button";
import { Skeleton } from "../../../components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "../../../components/ui/tabs";

interface RevenueTrendChartProps {
  data: Array<{ date: string; revenue: string }>;
  isLoading: boolean;
  isLoadingMore?: boolean;
  error: string | null;
  onRetry: () => void;
  period: "month" | "quarter" | "year";
  onPeriodChange: (period: "month" | "quarter" | "year") => void;
  hasMore?: boolean;
  onLoadMore?: () => void;
}

export function RevenueTrendChart(props: RevenueTrendChartProps) {
  const { t, i18n } = useTranslation("common");
  const {
    data,
    isLoading,
    isLoadingMore,
    error,
    onRetry,
    period,
    onPeriodChange,
    hasMore,
    onLoadMore,
  } = props;

  const periodLabel =
    period === "month"
      ? t("dashboard.revenueTrend.30d")
      : period === "quarter"
        ? t("dashboard.revenueTrend.90d")
        : t("dashboard.revenueTrend.1y");

  const xInterval: number | "preserveStartEnd" = period === "month" ? 6 : "preserveStartEnd";

  const chartData = data.map((d) => ({ ...d, revenue: Number(d.revenue) }));
  const locale = i18n.resolvedLanguage ?? i18n.language ?? "en";
  const showZoomNavigator = chartData.length > 10 || Boolean(hasMore);

  const loadMoreContent = (): React.ReactNode => {
    if (!hasMore) return null;
    const label = isLoadingMore ? t("loading") : t("dashboard.revenueTrend.loadMore");
    return (
      <div className="mt-3 flex justify-center">
        <Button variant="outline" size="sm" onClick={onLoadMore} disabled={isLoadingMore}>
          {label}
        </Button>
      </div>
    );
  };

  return (
    <SectionCard
      title={t("dashboard.revenueTrend.title")}
      description={periodLabel}
      actions={
        <Tabs value={period} onValueChange={(v) => onPeriodChange(v as "month" | "quarter" | "year")}>
          <TabsList>
            <TabsTrigger value="month">{t("dashboard.revenueTrend.month")}</TabsTrigger>
            <TabsTrigger value="quarter">{t("dashboard.revenueTrend.quarter")}</TabsTrigger>
            <TabsTrigger value="year">{t("dashboard.revenueTrend.year")}</TabsTrigger>
          </TabsList>
        </Tabs>
      }
    >
      {isLoading ? (
        <Skeleton className="h-[300px] w-full" />
      ) : error ? (
        <>
          <SurfaceMessage tone="danger">{error}</SurfaceMessage>
          <Button variant="outline" onClick={onRetry} className="mt-2">
            {t("retry")}
          </Button>
        </>
      ) : (
        <>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="date"
                tickFormatter={(d) => formatBackendCalendarDate(d as string, "MM/dd")}
                interval={xInterval}
                minTickGap={24}
                fontSize={12}
                tick={{ fill: "currentColor" }}
                axisLine={{ stroke: "currentColor" }}
                style={{ fontSize: "12px" }}
              />
              <YAxis
                tickFormatter={(v) => formatCurrencyAxis(Number(v), locale, "NT$")}
                fontSize={12}
                width={60}
                domain={[0, "auto"]}
                padding={{ top: 2, bottom: 0 }}
                tick={{ fill: "currentColor" }}
                axisLine={{ stroke: "currentColor" }}
                style={{ fontSize: "12px" }}
              />
              <Tooltip
                cursor={{ stroke: "#6366f1", strokeWidth: 1 }}
                contentStyle={{ color: "#000" }}
                labelFormatter={(d) => formatBackendCalendarDate(d as string, "yyyy-MM-dd")}
                formatter={(val) => [formatChartCurrency(Number(val), locale, "TWD"), "Revenue"]}
              />
              <Line
                type="monotone"
                dataKey="revenue"
                stroke="#6366f1"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="revenue"
                stroke="url(#revenueGradient)"
                strokeWidth={0}
                fill="url(#revenueGradient)"
                isAnimationActive={false}
                connectNulls={true}
              />
              {showZoomNavigator ? (
                <Brush
                  dataKey="date"
                  height={24}
                  stroke="#6366f1"
                  travellerWidth={10}
                  tickFormatter={(d) => formatBackendCalendarDate(d as string, "MM/dd")}
                />
              ) : null}
            </LineChart>
          </ResponsiveContainer>
          {showZoomNavigator ? (
            <p className="mt-2 text-xs text-muted-foreground">
              {t("dashboard.revenueTrend.zoomHint")}
            </p>
          ) : null}
          {loadMoreContent()}
        </>
      )}
    </SectionCard>
  );
}
