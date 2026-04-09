/** Cash Flow dashboard card — weekly inflows vs outflows bar chart. */

import { useTranslation } from "react-i18next";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Skeleton } from "../../../components/ui/skeleton";
import { Button } from "../../../components/ui/button";
import { useCashFlow } from "../hooks/useDashboard";

function formatTWD(value: string | number): string {
  return `NT$ ${Number(value).toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })}`;
}

interface CashFlowCardProps {
  data: ReturnType<typeof useCashFlow>["data"];
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
}

export function CashFlowCard({ data, isLoading, error, onRetry }: CashFlowCardProps) {
  const { t } = useTranslation("common");

  if (isLoading) {
    return (
      <Card data-testid="cash-flow-card" className="h-full">
        <CardHeader className="pb-2">
          <Skeleton className="h-5 w-36" />
        </CardHeader>
        <CardContent>
          <div data-testid="cash-flow-loading">
            <Skeleton className="h-4 w-24 mb-4" />
            <Skeleton className="h-48 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card data-testid="cash-flow-card" className="h-full">
        <CardHeader className="pb-2">
          <CardTitle>{t("dashboard.cashFlow.title")}</CardTitle>
        </CardHeader>
        <CardContent>
          <div data-testid="cash-flow-error" className="flex flex-col gap-3">
            <p className="text-sm text-destructive">{error}</p>
            <Button variant="outline" size="sm" onClick={onRetry}>
              {t("common.retry")}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  // Merge inflows, outflows by date for the chart
  const periodMap: Record<string, { date: string; inflows: number; outflows: number; net: number }> = {};
  for (const item of data.cash_inflows) {
    periodMap[item.date] = { date: item.date, inflows: Number(item.amount), outflows: 0, net: 0 };
  }
  for (const item of data.cash_outflows) {
    if (!periodMap[item.date]) periodMap[item.date] = { date: item.date, inflows: 0, outflows: 0, net: 0 };
    periodMap[item.date].outflows = Number(item.amount);
  }

  const chartData = Object.values(periodMap);

  // Totals
  const totalInflows = data.cash_inflows.reduce((s, i) => s + Number(i.amount), 0);
  const totalOutflows = data.cash_outflows.reduce((s, i) => s + Number(i.amount), 0);
  const totalNet = totalInflows - totalOutflows;

  return (
    <Card data-testid="cash-flow-card" className="h-full">
      <CardHeader className="pb-2">
        <CardTitle>{t("dashboard.cashFlow.title")}</CardTitle>
        <p className="text-sm text-muted-foreground">{t("dashboard.cashFlow.description")}</p>
      </CardHeader>
      <CardContent className="space-y-4 pt-0">
        {/* Chart */}
        <div data-testid="cash-flow-chart" className="h-48 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                tickFormatter={(v) => `NT$ ${(v / 1000).toFixed(0)}k`}
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                width={60}
              />
              <Tooltip
                formatter={(value) => formatTWD(value as number)}
                contentStyle={{ fontSize: 12 }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="inflows" name={t("dashboard.cashFlow.inflows")} fill="#22c55e" radius={[2, 2, 0, 0]} />
              <Bar dataKey="outflows" name={t("dashboard.cashFlow.outflows")} fill="#ef4444" radius={[2, 2, 0, 0]} />
              {chartData.length <= 8 && (
                <Bar dataKey="net" name={t("dashboard.cashFlow.net")} fill="#3b82f6" radius={[2, 2, 0, 0]} />
              )}
              {chartData.length > 8 && (
                <ReferenceLine y={0} stroke="#94a3b8" />
              )}
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Summary row */}
        <div data-testid="cash-flow-summary" className="flex gap-6 pt-2 border-t">
          <div>
            <p className="text-xs text-muted-foreground">{t("dashboard.cashFlow.totalInflows")}</p>
            <p className="text-sm font-semibold text-[#22c55e]">{formatTWD(totalInflows)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t("dashboard.cashFlow.totalOutflows")}</p>
            <p className="text-sm font-semibold text-[#ef4444]">{formatTWD(totalOutflows)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t("dashboard.cashFlow.netCashFlow")}</p>
            <p className={`text-sm font-semibold ${totalNet >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"}`}>
              {formatTWD(Math.abs(totalNet))}
              {totalNet < 0 ? " ↓" : " ↑"}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
