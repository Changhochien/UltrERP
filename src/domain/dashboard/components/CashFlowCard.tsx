/** Cash Flow dashboard card — weekly inflows vs outflows bar chart using @visx. */

import { useTranslation } from "react-i18next";
import { ParentSize } from "@visx/responsive";
import { scaleBand, scaleLinear } from "@visx/scale";
import { Bar } from "@visx/shape";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { GridRows } from "@visx/grid";
import { Group } from "@visx/group";
import { TooltipWithBounds, useTooltip } from "@visx/tooltip";

import { formatChartCurrency, formatCurrencyAxis } from "../../../components/charts/formatters";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Skeleton } from "../../../components/ui/skeleton";
import { Button } from "../../../components/ui/button";
import { useCashFlow } from "../hooks/useDashboard";

function formatTWD(value: string | number, locale: string): string {
  return formatChartCurrency(Number(value), locale, "TWD", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

interface CashFlowCardProps {
  data: ReturnType<typeof useCashFlow>["data"];
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
}

interface ChartData {
  date: string;
  inflows: number;
  outflows: number;
  net: number;
}

function ChartInner({
  chartData,
  width,
  height,
  t,
  locale,
}: {
  chartData: ChartData[];
  width: number;
  height: number;
  t: (key: string) => string;
  locale: string;
}) {
  const { showTooltip, hideTooltip, tooltipOpen, tooltipData, tooltipLeft, tooltipTop } =
    useTooltip<ChartData>();

  const margin = { top: 10, right: 10, left: 60, bottom: 40 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const xScale = scaleBand({
    domain: chartData.map((d) => d.date),
    range: [0, innerWidth],
    padding: 0.3,
  });

  const allValues = chartData.flatMap((d) => [d.inflows, d.outflows, d.net]);
  const yMax = Math.max(...allValues, 1);

  const yScale = scaleLinear({
    domain: [0, yMax * 1.1],
    range: [innerHeight, 0],
  });

  const barWidth = xScale.bandwidth();
  const netBarWidth = barWidth * 0.4;
  const inflowsWidth = (barWidth - netBarWidth) / 2 - 1;
  const outflowsWidth = inflowsWidth;

  return (
    <div style={{ position: "relative" }}>
      <svg width={width} height={height}>
        <Group left={margin.left} top={margin.top}>
          <GridRows
            scale={yScale}
            width={innerWidth}
            stroke="var(--border)"
            strokeDasharray="3 3"
          />
          <AxisBottom
            top={innerHeight}
            scale={xScale}
            tickLabelProps={() => ({
              fill: "var(--muted-foreground)",
              fontSize: 11,
              textAnchor: "middle",
            })}
            stroke="var(--border)"
          />
          <AxisLeft
            scale={yScale}
            tickFormat={(d) => formatCurrencyAxis(Number(d), locale, "NT$")}
            tickLabelProps={() => ({
              fill: "var(--muted-foreground)",
              fontSize: 11,
              textAnchor: "end",
            })}
            stroke="var(--border)"
          />

          {chartData.map((d, i) => {
            const x = xScale(d.date) ?? 0;
            const inflowsY = yScale(d.inflows);
            const outflowsY = yScale(d.outflows);
            const netY = yScale(Math.max(0, d.net));
            const netHeight = Math.abs(yScale(0) - netY);
            const netBarX = x + inflowsWidth + 2;

            return (
              <g key={i}>
                <Bar
                  x={x}
                  y={inflowsY}
                  width={inflowsWidth}
                  height={innerHeight - inflowsY}
                  fill="#22c55e"
                  rx={2}
                  onMouseEnter={(e) => {
                    showTooltip({ tooltipData: d, tooltipLeft: e.clientX, tooltipTop: e.clientY });
                  }}
                  onMouseLeave={hideTooltip}
                />
                <Bar
                  x={x + inflowsWidth + 2}
                  y={outflowsY}
                  width={outflowsWidth}
                  height={innerHeight - outflowsY}
                  fill="#ef4444"
                  rx={2}
                  onMouseEnter={(e) => {
                    showTooltip({ tooltipData: d, tooltipLeft: e.clientX, tooltipTop: e.clientY });
                  }}
                  onMouseLeave={hideTooltip}
                />
                <Bar
                  x={netBarX}
                  y={d.net >= 0 ? netY : yScale(0)}
                  width={netBarWidth}
                  height={netHeight}
                  fill="#3b82f6"
                  rx={2}
                  onMouseEnter={(e) => {
                    showTooltip({ tooltipData: d, tooltipLeft: e.clientX, tooltipTop: e.clientY });
                  }}
                  onMouseLeave={hideTooltip}
                />
              </g>
            );
          })}
        </Group>
      </svg>
      <div className="flex gap-4 pt-1 text-xs" style={{ paddingLeft: margin.left }}>
        <span className="flex items-center gap-1">
          <span className="size-2 rounded-full bg-green-500" /> {t("dashboard.cashFlow.inflows")}
        </span>
        <span className="flex items-center gap-1">
          <span className="size-2 rounded-full bg-red-500" /> {t("dashboard.cashFlow.outflows")}
        </span>
        {chartData.length <= 8 && (
          <span className="flex items-center gap-1">
            <span className="size-2 rounded-full bg-blue-500" /> {t("dashboard.cashFlow.net")}
          </span>
        )}
      </div>
      {tooltipOpen && tooltipData && (
        <TooltipWithBounds
          left={tooltipLeft ?? 0}
          top={tooltipTop ?? 0}
          style={{
            background: "var(--background)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            padding: "8px 12px",
            fontSize: 12,
            position: "fixed",
          }}
        >
          <div style={{ color: "var(--muted-foreground)", marginBottom: 4 }}>
            {tooltipData.date}
          </div>
          <div style={{ color: "#22c55e" }}>Inflows: {formatTWD(tooltipData.inflows, locale)}</div>
          <div style={{ color: "#ef4444" }}>Outflows: {formatTWD(tooltipData.outflows, locale)}</div>
          <div style={{ color: "#3b82f6" }}>Net: {formatTWD(tooltipData.net, locale)}</div>
        </TooltipWithBounds>
      )}
    </div>
  );
}

export function CashFlowCard({ data, isLoading, error, onRetry }: CashFlowCardProps) {
  const { t, i18n } = useTranslation("common");
  const locale = i18n.resolvedLanguage ?? i18n.language ?? "en";

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
              {t("retry")}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  const periodMap: Record<
    string,
    { date: string; inflows: number; outflows: number; net: number }
  > = {};
  for (const item of data.cash_inflows) {
    periodMap[item.date] = {
      date: item.date,
      inflows: Number(item.amount),
      outflows: 0,
      net: 0,
    };
  }
  for (const item of data.cash_outflows) {
    if (!periodMap[item.date])
      periodMap[item.date] = { date: item.date, inflows: 0, outflows: 0, net: 0 };
    periodMap[item.date].outflows = Number(item.amount);
  }

  const chartData = Object.values(periodMap).map((d) => ({
    ...d,
    net: d.inflows - d.outflows,
  }));

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
        <div data-testid="cash-flow-chart" className="h-48 w-full">
          <ParentSize>
            {({ width }) => (
              <ChartInner chartData={chartData} width={width} height={192} t={(key) => t(key)} locale={locale} />
            )}
          </ParentSize>
        </div>

        <div data-testid="cash-flow-summary" className="flex gap-6 pt-2 border-t">
          <div>
            <p className="text-xs text-muted-foreground">
              {t("dashboard.cashFlow.totalInflows")}
            </p>
            <p className="text-sm font-semibold text-[#22c55e]">{formatTWD(totalInflows, locale)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">
              {t("dashboard.cashFlow.totalOutflows")}
            </p>
            <p className="text-sm font-semibold text-[#ef4444]">{formatTWD(totalOutflows, locale)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t("dashboard.cashFlow.netCashFlow")}</p>
            <p
              className={`text-sm font-semibold ${totalNet >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"}`}
            >
              {formatTWD(Math.abs(totalNet), locale)}
              {totalNet < 0 ? " ↓" : " ↑"}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
