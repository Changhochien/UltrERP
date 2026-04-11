/** Revenue trend line chart — configurable period (month/quarter/year) daily revenue using @visx. */

import { useTranslation } from "react-i18next";
import { format } from "date-fns";
import { ParentSize } from "@visx/responsive";
import { scaleTime, scaleLinear } from "@visx/scale";
import { LinePath } from "@visx/shape";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { GridRows } from "@visx/grid";
import { Group } from "@visx/group";
import { curveMonotoneX } from "@visx/curve";
import { TooltipWithBounds, useTooltip } from "@visx/tooltip";
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

interface TooltipData {
  date: string;
  revenue: number;
}

function ChartInner({ data, width, height }: { data: Array<{ date: string; revenue: string }>; width: number; height: number }) {
  const {
    showTooltip,
    hideTooltip,
    tooltipOpen,
    tooltipData,
    tooltipLeft,
    tooltipTop,
  } = useTooltip<TooltipData>();

  const margin = { top: 10, right: 10, left: 60, bottom: 40 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const parsedData = data.map((d) => ({
    date: parseBackendDate(d.date),
    revenue: Number(d.revenue),
  }));

  const xScale = scaleTime({
    domain: [parsedData[0]?.date ?? new Date(), parsedData[parsedData.length - 1]?.date ?? new Date()],
    range: [0, innerWidth],
  });

  const yScale = scaleLinear({
    domain: [0, Math.max(...parsedData.map((d) => d.revenue)) * 1.1],
    range: [innerHeight, 0],
  });

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
            numTicks={innerWidth > 400 ? 8 : 4}
            tickFormat={(d) => format(d as Date, "MM/dd")}
            tickLabelProps={() => ({
              fill: "var(--muted-foreground)",
              fontSize: 12,
              textAnchor: "middle",
            })}
            stroke="var(--border)"
          />
          <AxisLeft
            scale={yScale}
            tickFormat={(d) => `NT$ ${((d as number) / 1000).toFixed(0)}k`}
            tickLabelProps={() => ({
              fill: "var(--muted-foreground)",
              fontSize: 12,
              textAnchor: "end",
            })}
            stroke="var(--border)"
          />
          <LinePath
            data={parsedData}
            x={(d) => xScale(d.date) ?? 0}
            y={(d) => yScale(d.revenue) ?? 0}
            stroke="#6366f1"
            strokeWidth={2}
            curve={curveMonotoneX}
          />
          {parsedData.map((d, i) => (
            <rect
              key={i}
              x={(xScale(d.date) ?? 0) - innerWidth / parsedData.length / 2}
              y={0}
              width={innerWidth / parsedData.length}
              height={innerHeight}
              fill="transparent"
              onMouseEnter={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                showTooltip({
                  tooltipData: { date: data[i].date, revenue: d.revenue },
                  tooltipLeft: rect.left + rect.width / 2,
                  tooltipTop: rect.top,
                });
              }}
              onMouseLeave={hideTooltip}
            />
          ))}
        </Group>
      </svg>
      {tooltipOpen && tooltipData && (
        <TooltipWithBounds
          left={tooltipLeft}
          top={tooltipTop}
          style={{ background: "var(--background)", border: "1px solid var(--border)", borderRadius: 8, padding: "8px 12px", fontSize: 12 }}
        >
          <div style={{ color: "var(--muted-foreground)", marginBottom: 4 }}>
            {format(parseBackendDate(tooltipData.date), "yyyy-MM-dd")}
          </div>
          <div style={{ fontWeight: 600 }}>{formatTWD(tooltipData.revenue)}</div>
        </TooltipWithBounds>
      )}
    </div>
  );
}

export function RevenueTrendChart({ data, isLoading, error, onRetry, period, onPeriodChange }: RevenueTrendChartProps) {
  const { t } = useTranslation("common");

  const periodLabel =
    period === "month" ? t("dashboard.revenueTrend.30d")
    : period === "quarter" ? t("dashboard.revenueTrend.90d")
    : t("dashboard.revenueTrend.1y");

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
        <ParentSize>
          {({ width }) => (
            <ChartInner data={data} width={width} height={300} />
          )}
        </ParentSize>
      )}
    </SectionCard>
  );
}
