/** Customer analytics tab — summary metrics and revenue trend chart. */

import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { MetricCard, SectionCard, SurfaceMessage } from "@/components/layout/PageLayout";
import { Badge } from "@/components/ui/badge";
import { CustomerProductProfile } from "@/domain/intelligence/components/CustomerProductProfile";
import { usePermissions } from "@/hooks/usePermissions";
import {
  getCustomerAnalyticsSummary,
  getCustomerRevenueTrend,
  type CustomerAnalyticsSummary,
  type CustomerRevenueTrend,
} from "@/lib/api/customers";

interface CustomerAnalyticsTabProps {
  customerId: string;
}

const ANALYTICS_MONTH_WINDOW = 12;

function formatTWD(value: string): string {
  const num = Number(value);
  if (isNaN(num)) return value;
  return `NT$ ${num.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

const SCORE_BADGE_VARIANT: Record<CustomerAnalyticsSummary["payment_score"], "success" | "warning" | "destructive" | "secondary"> = {
  excellent: "success",
  prompt: "warning",
  late: "destructive",
  at_risk: "destructive",
};

function buildTrendChartData(trend: CustomerRevenueTrend | null, months: number) {
  const revenueByMonth = new Map(
    trend?.trend.map((point) => [point.month, Number(point.revenue)]) ?? [],
  );
  const points: Array<{ month: string; revenue: number }> = [];
  const now = new Date();

  for (let offset = months; offset >= 1; offset -= 1) {
    const date = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - offset, 1));
    const month = `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}`;
    points.push({ month, revenue: revenueByMonth.get(month) ?? 0 });
  }

  return points;
}

export function CustomerAnalyticsTab({ customerId }: CustomerAnalyticsTabProps) {
  const { t } = useTranslation("common", { keyPrefix: "customer.detail.analytics" });
  const { canAccess } = usePermissions();

  const [summary, setSummary] = useState<CustomerAnalyticsSummary | null>(null);
  const [trend, setTrend] = useState<CustomerRevenueTrend | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, trendData] = await Promise.all([
        getCustomerAnalyticsSummary(customerId),
        getCustomerRevenueTrend(customerId, ANALYTICS_MONTH_WINDOW),
      ]);
      setSummary(summaryData);
      setTrend(trendData);
    } catch (err) {
      setError(
        err instanceof Error && err.message
          ? err.message
          : t("loadError", { defaultValue: "Failed to load analytics." }),
      );
    } finally {
      setLoading(false);
    }
  }, [customerId, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const chartData = buildTrendChartData(trend, ANALYTICS_MONTH_WINDOW);
  const hasRevenueHistory = chartData.some((point) => point.revenue > 0);

  const scoreLabel = summary
    ? t(`paymentScoreLabels.${summary.payment_score}`, {
        defaultValue: summary.payment_score,
      })
    : "";
  const scoreVariant = summary ? SCORE_BADGE_VARIANT[summary.payment_score] : "secondary";

  return (
    <div className="space-y-6">
      {/* 2x2 metric cards grid */}
      <div className="grid gap-4 sm:grid-cols-2">
        <MetricCard
          title={t("totalRevenue", { defaultValue: "Total Revenue (12 months)" })}
          value={loading ? "—" : (summary ? formatTWD(summary.total_revenue_12m) : "—")}
          description={t("revenueDescription", { defaultValue: "Rolling 12-month revenue" })}
        />
        <MetricCard
          title={t("invoiceCount", { defaultValue: "Invoice Count" })}
          value={loading ? "—" : (summary ? String(summary.invoice_count_12m) : "—")}
          description={t("invoiceCountDesc", { defaultValue: "Invoices issued in the last 12 months" })}
        />
        <MetricCard
          title={t("avgInvoiceValue", { defaultValue: "Average Invoice Value" })}
          value={loading ? "—" : (summary ? formatTWD(summary.avg_invoice_value) : "—")}
          description={t("avgInvoiceDesc", { defaultValue: "Average value per invoice" })}
        />
        <MetricCard
          title={t("outstandingBalance", { defaultValue: "Outstanding Balance" })}
          value={loading ? "—" : (summary ? formatTWD(summary.outstanding_balance) : "—")}
          description={
            summary && !loading
              ? `${t("creditUtilization", { defaultValue: "Credit utilization" })}: ${summary.credit_utilization_pct}%`
              : t("outstandingBalance", { defaultValue: "Outstanding Balance" })
          }
          badge={
            summary && !loading ? (
              <Badge variant={scoreVariant} className="normal-case tracking-normal">
                {scoreLabel}
              </Badge>
            ) : undefined
          }
        />
      </div>

      {/* Revenue trend chart */}
      <SectionCard
        title={t("revenueTrend", { defaultValue: "Revenue Trend" })}
        description={t("revenueTrendDesc", { defaultValue: "Monthly revenue across the last 12 complete months" })}
      >
        {loading ? (
          <div className="h-[300px] w-full animate-pulse rounded-lg bg-muted" />
        ) : error ? (
          <SurfaceMessage tone="danger">{error}</SurfaceMessage>
        ) : !hasRevenueHistory ? (
          <SurfaceMessage>
            <p className="font-medium text-foreground">
              {t("emptyTitle", { defaultValue: "No revenue activity yet" })}
            </p>
            <p className="mt-1">
              {t("emptyDescription", { defaultValue: "This customer has no invoice revenue in the last 12 months." })}
            </p>
          </SurfaceMessage>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="analyticsGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="currentColor" opacity={0.2} />
              <XAxis
                dataKey="month"
                fontSize={12}
                tick={{ fill: "currentColor" }}
                axisLine={{ stroke: "currentColor" }}
              />
              <YAxis
                tickFormatter={(v) => `NT$ ${(v / 1000).toFixed(0)}k`}
                fontSize={12}
                width={60}
                domain={[0, "auto"]}
                padding={{ top: 2, bottom: 0 }}
                tick={{ fill: "currentColor" }}
                axisLine={{ stroke: "currentColor" }}
              />
              <Tooltip
                cursor={{ stroke: "#6366f1", strokeWidth: 1 }}
                contentStyle={{ color: "#000" }}
                formatter={(val) => [formatTWD(String(val)), t("tooltipRevenue", { defaultValue: "Revenue" })]}
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
                stroke="url(#analyticsGradient)"
                strokeWidth={0}
                fill="url(#analyticsGradient)"
                isAnimationActive={false}
                connectNulls={true}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </SectionCard>

      {/* Payment stats row */}
      {!loading && summary && (
        <div className="grid gap-4 sm:grid-cols-3">
          <MetricCard
            title={t("avgDaysToPay", { defaultValue: "Average Days to Pay" })}
            value={summary.avg_days_to_pay != null ? String(summary.avg_days_to_pay) : "—"}
            description={t("avgDaysDesc", { defaultValue: "Measured from invoice date to payment date" })}
          />
          <MetricCard
            title={t("daysOverdueAvg", { defaultValue: "Average Days Overdue" })}
            value={summary.days_overdue_avg != null ? String(summary.days_overdue_avg) : "—"}
            description={t("daysOverdueDesc", { defaultValue: "Average lateness beyond terms" })}
          />
          <MetricCard
            title={t("creditLimit", { defaultValue: "Credit Limit" })}
            value={formatTWD(summary.credit_limit)}
            description={t("creditLimitDesc", { defaultValue: "Configured customer credit line" })}
          />
        </div>
      )}

      {canAccess("intelligence") ? <CustomerProductProfile customerId={customerId} /> : null}
    </div>
  );
}