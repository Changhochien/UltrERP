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

import { MetricCard } from "@/components/layout/PageLayout";
import { Badge } from "@/components/ui/badge";
import { SectionCard } from "@/components/layout/PageLayout";
import {
  getCustomerAnalyticsSummary,
  getCustomerRevenueTrend,
  type CustomerAnalyticsSummary,
  type CustomerRevenueTrend,
} from "@/lib/api/customers";

interface CustomerAnalyticsTabProps {
  customerId: string;
}

function formatTWD(value: string): string {
  const num = Number(value);
  if (isNaN(num)) return value;
  return `NT$ ${num.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

const SCORE_LABELS: Record<CustomerAnalyticsSummary["payment_score"], string> = {
  excellent: "Excellent",
  prompt: "Prompt",
  late: "Late",
  at_risk: "At Risk",
};

const SCORE_BADGE_VARIANT: Record<CustomerAnalyticsSummary["payment_score"], "success" | "warning" | "destructive" | "secondary"> = {
  excellent: "success",
  prompt: "warning",
  late: "destructive",
  at_risk: "destructive",
};

export function CustomerAnalyticsTab({ customerId }: CustomerAnalyticsTabProps) {
  const { t } = useTranslation("common");

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
        getCustomerRevenueTrend(customerId, 12),
      ]);
      setSummary(summaryData);
      setTrend(trendData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    void load();
  }, [load]);

  const chartData = trend?.trend.map((p) => ({ month: p.month, revenue: Number(p.revenue) })) ?? [];

  const scoreLabel = summary ? SCORE_LABELS[summary.payment_score] : "";
  const scoreVariant = summary ? SCORE_BADGE_VARIANT[summary.payment_score] : "secondary";

  return (
    <div className="space-y-6">
      {/* 2x2 metric cards grid */}
      <div className="grid gap-4 sm:grid-cols-2">
        <MetricCard
          title={t("customer.analytics.totalRevenue") ?? "Total Revenue (12m)"}
          value={loading ? "—" : (summary ? formatTWD(summary.total_revenue_12m) : "—")}
          description={t("customer.analytics.revenueDescription") ?? "Last 12 months"}
        />
        <MetricCard
          title={t("customer.analytics.invoiceCount") ?? "Invoice Count"}
          value={loading ? "—" : (summary ? String(summary.invoice_count_12m) : "—")}
          description={t("customer.analytics.invoiceCountDesc") ?? "Last 12 months"}
        />
        <MetricCard
          title={t("customer.analytics.avgInvoiceValue") ?? "Avg Invoice Value"}
          value={loading ? "—" : (summary ? formatTWD(summary.avg_invoice_value) : "—")}
          description={t("customer.analytics.avgInvoiceDesc") ?? "Per invoice"}
        />
        <MetricCard
          title={t("customer.analytics.outstandingBalance") ?? "Outstanding Balance"}
          value={loading ? "—" : (summary ? formatTWD(summary.outstanding_balance) : "—")}
          description={
            summary && !loading
              ? `${t("customer.analytics.creditUtilization") ?? "Credit utilization"}: ${summary.credit_utilization_pct}%`
              : (t("customer.analytics.outstandingBalance") ?? "Outstanding Balance")
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
        title={t("customer.analytics.revenueTrend") ?? "Revenue Trend"}
        description={t("customer.analytics.revenueTrendDesc") ?? "Last 12 months"}
      >
        {loading ? (
          <div className="h-[300px] w-full animate-pulse rounded-lg bg-muted" />
        ) : error ? (
          <p className="text-sm text-destructive">{error}</p>
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
                formatter={(val) => [formatTWD(String(val)), "Revenue"]}
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
            title={t("customer.analytics.avgDaysToPay") ?? "Avg Days to Pay"}
            value={summary.avg_days_to_pay != null ? String(summary.avg_days_to_pay) : "—"}
            description={t("customer.analytics.avgDaysDesc") ?? "From invoice date"}
          />
          <MetricCard
            title={t("customer.analytics.daysOverdueAvg") ?? "Avg Days Overdue"}
            value={summary.days_overdue_avg != null ? String(summary.days_overdue_avg) : "—"}
            description={t("customer.analytics.daysOverdueDesc") ?? "After due date"}
          />
          <MetricCard
            title={t("customer.analytics.creditLimit") ?? "Credit Limit"}
            value={formatTWD(summary.credit_limit)}
            description={t("customer.analytics.creditLimitDesc") ?? "Total available credit"}
          />
        </div>
      )}
    </div>
  );
}