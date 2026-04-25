/**
 * MonthlyDemandExplorerChart - Explorer-tier monthly demand chart.
 * 
 * This component uses the dense time-series API with:
 * - Range preset controls (3M, 6M, 1Y, 2Y, 4Y, All)
 * - Shared chart shell and state handling
 * - @visx rendering with explorer pattern
 */

import { useMemo, useState } from "react";
import { ParentSize } from "@visx/responsive";
import { scaleBand, scaleLinear } from "@visx/scale";
import { Bar, LinePath } from "@visx/shape";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { GridRows } from "@visx/grid";
import { Group } from "@visx/group";
import { curveMonotoneX } from "@visx/curve";
import { TooltipWithBounds, useTooltip } from "@visx/tooltip";
import { useTranslation } from "react-i18next";

import { ChartShell } from "../../../components/charts/ChartShell";
import { ChartModeToggle } from "../../../components/charts/controls/ChartModeToggle";
import { ExplorerChartFrame, useExplorerRange } from "../../../components/charts/explorer";
import { formatChartQuantityCompact } from "../../../components/charts/formatters";
import { useProductMonthlyDemandSeries, getMonthlyRangeFromPreset } from "../hooks/useProductMonthlyDemandSeries";

interface MonthlyDemandExplorerChartProps {
  productId: string;
  /** Chart title */
  title?: string;
}

export function MonthlyDemandExplorerChart({
  productId,
  title,
}: MonthlyDemandExplorerChartProps) {
  const { t, i18n } = useTranslation("common", {
    keyPrefix: "inventory.productDetail.analyticsTab.monthlyDemand",
  });

  // State
  const [chartMode, setChartMode] = useState<"bar" | "line">("bar");

  const loadedMonthRange = useMemo(() => getMonthlyRangeFromPreset("All"), []);
  const fallbackVisibleRange = useMemo(() => getMonthlyRangeFromPreset("1Y"), []);

  // Fetch dense series data
  const { points, range, loading, error, refetch } = useProductMonthlyDemandSeries(
    productId,
    loadedMonthRange
  );

  const loadedRange = useMemo(
    () => ({
      start: range?.requested_start ?? loadedMonthRange.startMonth,
      end: range?.requested_end ?? loadedMonthRange.endMonth,
    }),
    [range?.requested_start, range?.requested_end, loadedMonthRange.startMonth, loadedMonthRange.endMonth],
  );

  const defaultVisibleRange = useMemo(
    () => ({
      start: range?.default_visible_start ?? fallbackVisibleRange.startMonth,
      end: range?.default_visible_end ?? fallbackVisibleRange.endMonth,
    }),
    [range?.default_visible_start, range?.default_visible_end, fallbackVisibleRange.startMonth, fallbackVisibleRange.endMonth],
  );

  const { visibleRange, selectedPreset, applyPreset, updateVisibleRange } = useExplorerRange({
    availableRange: loadedRange,
    defaultVisibleRange,
  });

  // Convert to chart format
  const chartData = useMemo(
    () =>
      points.map((p) => ({
        month: p.bucket_label,
        total_qty: p.value,
      })),
    [points]
  );

  const visibleChartData = useMemo(
    () => chartData.filter((point) => point.month >= visibleRange.start && point.month <= visibleRange.end),
    [chartData, visibleRange.end, visibleRange.start],
  );

  // Controls
  const controls = (
    <ChartModeToggle
      value={chartMode}
      onChange={setChartMode}
      aria-label="Chart display mode"
      size="sm"
    />
  );

  return (
    <ChartShell title={title} useSectionCard>
      <ExplorerChartFrame
        loading={loading}
        error={error}
        empty={chartData.length === 0}
        emptyMessage={String(t("empty"))}
        onRetry={refetch}
        availableRange={loadedRange}
        defaultVisibleRange={defaultVisibleRange}
        visibleRange={visibleRange}
        onVisibleRangeChange={updateVisibleRange}
        selectedPreset={selectedPreset}
        onPresetChange={applyPreset}
        controls={controls}
        navigator={<MonthlyDemandOverview data={chartData} />}
      >
        <div className="space-y-2">
          {visibleChartData.length > 0 && (
            <ParentSize>
              {({ width }) => (
                <MonthlyDemandChartInner
                  data={visibleChartData}
                  variant={chartMode}
                  locale={i18n.resolvedLanguage ?? i18n.language ?? "en"}
                  width={width}
                  height={260}
                />
              )}
            </ParentSize>
          )}
        </div>
      </ExplorerChartFrame>
    </ChartShell>
  );
}

function MonthlyDemandOverview({ data }: { data: { month: string; total_qty: number }[] }) {
  const maxValue = Math.max(...data.map((point) => point.total_qty), 1);

  return (
    <div className="flex h-full items-end gap-px px-2 py-1">
      {data.map((point) => (
        <div
          key={point.month}
          className="min-w-1 flex-1 rounded-sm bg-primary/60"
          style={{ height: `${Math.max(8, (point.total_qty / maxValue) * 100)}%` }}
          aria-hidden="true"
        />
      ))}
    </div>
  );
}

// Inner chart component
function MonthlyDemandChartInner({
  data,
  variant,
  locale,
  width,
  height,
}: {
  data: { month: string; total_qty: number }[];
  variant: "bar" | "line";
  locale: string;
  width: number;
  height: number;
}) {
  const { showTooltip, hideTooltip, tooltipOpen, tooltipData, tooltipLeft, tooltipTop } =
    useTooltip<{ month: string; total_qty: number }>();

  const margin = { top: 10, right: 10, left: 50, bottom: 40 };
  const innerWidth = Math.max(0, width - margin.left - margin.right);
  const innerHeight = Math.max(0, height - margin.top - margin.bottom);

  const xScale = scaleBand({
    domain: data.map((d) => d.month),
    range: [0, innerWidth],
    padding: 0.3,
  });

  const maxTickCount = Math.max(2, Math.floor(innerWidth / 72));
  const tickStep = Math.max(1, Math.ceil(data.length / maxTickCount));
  const visibleMonths = data.filter((_, i) => i % tickStep === 0 || i === data.length - 1);

  const yMax = Math.max(...data.map((d) => d.total_qty), 1);
  const yScale = scaleLinear({
    domain: [0, yMax * 1.1],
    range: [innerHeight, 0],
  });

  const tooltipStyle = {
    background: "var(--background)",
    border: "1px solid var(--border)",
    borderRadius: 12,
    padding: "8px 12px",
    fontSize: 12,
    position: "fixed" as const,
  };

  return (
    <div style={{ position: "relative" }}>
      <svg width={width} height={height}>
        <Group left={margin.left} top={margin.top}>
          <GridRows scale={yScale} width={innerWidth} stroke="var(--border)" strokeDasharray="3 3" />
          <AxisBottom
            top={innerHeight}
            scale={xScale}
            tickValues={visibleMonths.map((d) => d.month)}
            tickLabelProps={() => ({ fill: "var(--muted-foreground)", fontSize: 11, textAnchor: "middle" })}
            stroke="var(--border)"
          />
          <AxisLeft
            scale={yScale}
            tickFormat={(v) => formatChartQuantityCompact(Number(v), locale)}
            tickLabelProps={() => ({ fill: "var(--muted-foreground)", fontSize: 11, textAnchor: "end" })}
            stroke="var(--border)"
          />
          {variant === "line" ? (
            <LinePath
              data={data}
              x={(d) => (xScale(d.month) ?? 0) + xScale.bandwidth() / 2}
              y={(d) => yScale(d.total_qty) ?? 0}
              stroke="#3b82f6"
              strokeWidth={2.5}
              curve={curveMonotoneX}
            />
          ) : null}
          {data.map((d, i) => {
            const x = xScale(d.month) ?? 0;
            const y = yScale(d.total_qty) ?? 0;
            const bandwidth = xScale.bandwidth();

            if (variant === "line") {
              return (
                <circle
                  key={i}
                  cx={x + bandwidth / 2}
                  cy={y}
                  r={4}
                  fill="#3b82f6"
                  stroke="white"
                  strokeWidth={1.5}
                  onMouseEnter={(e) => showTooltip({ tooltipData: d, tooltipLeft: e.pageX, tooltipTop: e.pageY })}
                  onMouseLeave={hideTooltip}
                />
              );
            }
            return (
              <Bar
                key={i}
                x={x}
                y={y}
                width={bandwidth}
                height={innerHeight - y}
                fill="#3b82f6"
                rx={4}
                onMouseEnter={(e) => showTooltip({ tooltipData: d, tooltipLeft: e.pageX, tooltipTop: e.pageY })}
                onMouseLeave={hideTooltip}
              />
            );
          })}
        </Group>
      </svg>
      {tooltipOpen && tooltipData && (
        <TooltipWithBounds left={tooltipLeft ?? 0} top={tooltipTop ?? 0} style={tooltipStyle}>
          <p className="text-xs font-medium text-muted-foreground">{tooltipData.month}</p>
          <p className="text-sm font-semibold">{formatChartQuantityCompact(tooltipData.total_qty, locale)} units</p>
        </TooltipWithBounds>
      )}
    </div>
  );
}
