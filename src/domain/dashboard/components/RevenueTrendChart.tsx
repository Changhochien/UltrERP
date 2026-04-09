/** Revenue trend line chart — configurable period (month/quarter/year) daily revenue using recharts. */

import { useTranslation } from "react-i18next";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { format } from "date-fns";
import { parseBackendDate } from "../../../lib/time";

import { SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { Button } from "../../../components/ui/button";
import { Skeleton } from "../../../components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "../../../components/ui/tabs";

interface RevenueTrendChartProps {
  data: Array<{ date: string; revenue: string }>;
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
  period: "month" | "quarter" | "year";
  onPeriodChange: (period: "month" | "quarter" | "year") => void;
}

function formatTWD(value: number): string {
  return `NT$ ${value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function RevenueTrendChart({ data, isLoading, error, onRetry, period, onPeriodChange }: RevenueTrendChartProps) {
  const { t } = useTranslation("common");

  const periodLabel =
    period === "month" ? t("dashboard.revenueTrend.30d")
    : period === "quarter" ? t("dashboard.revenueTrend.90d")
    : t("dashboard.revenueTrend.1y");

  const interval = period === "year" ? 29 : period === "quarter" ? 13 : 6;

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
            {t("common.retry")}
          </Button>
        </>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <XAxis
              dataKey="date"
              tickFormatter={(d) => format(parseBackendDate(d), "MM/dd")}
              interval={interval}
              fontSize={12}
            />
            <YAxis
              tickFormatter={(v) => `NT$ ${(v / 1000).toFixed(0)}k`}
              fontSize={12}
              width={60}
            />
            <Tooltip
              labelFormatter={(d) => format(parseBackendDate(d as string), "yyyy-MM-dd")}
              formatter={(val) => [formatTWD(Number(val)), "Revenue"]}
            />
            <Line
              type="monotone"
              dataKey="revenue"
              stroke="#6366f1"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </SectionCard>
  );
}
