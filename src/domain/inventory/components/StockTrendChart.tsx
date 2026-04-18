/** Stock trend line chart with reorder point reference line and stockout projection. */

import { useMemo, useState } from "react";
import { ParentSize } from "@visx/responsive";
import { scaleTime, scaleLinear } from "@visx/scale";
import { LinePath } from "@visx/shape";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { GridRows } from "@visx/grid";
import { Group } from "@visx/group";
import { curveMonotoneX } from "@visx/curve";
import { TooltipWithBounds, useTooltip } from "@visx/tooltip";
import { parseBackendDate } from "../../../lib/time";
import type { StockHistoryPoint } from "../types";

interface StockTrendChartProps {
  points: StockHistoryPoint[];
  reorderPoint: number;
  safetyStock?: number;
  avgDailyUsage?: number;
}

const TIME_RANGES = [
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
  { label: "180d", days: 180 },
  { label: "1yr", days: 365 },
  { label: "all", days: -1 },
] as const;

function formatDate(dateStr: string): string {
  const d = parseBackendDate(dateStr);
  return d.toLocaleDateString("zh-TW", { timeZone: "Asia/Taipei", month: "short", day: "numeric" });
}

function dotColor(reasonCode: string): string {
  switch (reasonCode) {
    case "sales_reservation":
      return "#ef4444";
    case "supplier_delivery":
      return "#22c55e";
    case "transfer_in":
    case "transfer_out":
      return "#3b82f6";
    default:
      return "#9ca3af";
  }
}

interface TooltipData {
  date: string;
  running_stock: number;
  quantity_change: number;
  reason_code: string;
  daysUntilStockout?: number;
}

function ChartInner({
  filtered,
  projectedLine,
  reorderPoint,
  safetyStock,
  width,
  height,
  daysUntilStockout,
}: {
  filtered: StockHistoryPoint[];
  projectedLine: Array<{ date: string; running_stock: number }>;
  reorderPoint: number;
  safetyStock?: number;
  width: number;
  height: number;
  daysUntilStockout: number | null;
}) {
  const { showTooltip, hideTooltip, tooltipOpen, tooltipData, tooltipLeft, tooltipTop } =
    useTooltip<TooltipData>();

  const margin = { top: 10, right: 10, left: 40, bottom: 40 };
  const innerWidth = Math.max(0, width - margin.left - margin.right);
  const innerHeight = Math.max(0, height - margin.top - margin.bottom);

  const allPoints = [...filtered, ...projectedLine];
  if (allPoints.length === 0 || innerWidth <= 0 || innerHeight <= 0) return null;

  const parsedActual = filtered.map((d) => ({
    date: parseBackendDate(d.date),
    running_stock: d.running_stock,
    quantity_change: d.quantity_change,
    reason_code: d.reason_code ?? "other",
  }));

  const parsedProjected = projectedLine.map((d) => ({
    date: parseBackendDate(d.date),
    running_stock: d.running_stock,
  }));

  const xDomain: [Date, Date] = [
    parseBackendDate(allPoints[0]?.date ?? ""),
    parseBackendDate(allPoints[allPoints.length - 1]?.date ?? ""),
  ];
  const yMax = Math.max(...allPoints.map((d) => d.running_stock), reorderPoint) * 1.1;

  const xScale = scaleTime({ domain: xDomain, range: [0, innerWidth] });
  const yScale = scaleLinear({ domain: [0, yMax], range: [innerHeight, 0] });

  const safetyStockY1 = safetyStock != null ? yScale(safetyStock) : null;
  const safetyStockY2 = yScale(0);

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

          {safetyStock != null && safetyStockY1 != null && (
            <rect
              x={0}
              y={Math.min(safetyStockY1, safetyStockY2 ?? 0)}
              width={Math.max(0, innerWidth)}
              height={Math.max(0, Math.abs((safetyStockY2 ?? 0) - safetyStockY1))}
              fill="#f97316"
              fillOpacity={0.1}
            />
          )}

          {reorderPoint > 0 && (
            <>
              <line
                x1={0}
                x2={innerWidth}
                y1={yScale(reorderPoint)}
                y2={yScale(reorderPoint)}
                stroke="#ef4444"
                strokeDasharray="5 3"
              />
              <text
                x={innerWidth - 4}
                y={yScale(reorderPoint) - 4}
                fill="#ef4444"
                fontSize={11}
                textAnchor="end"
              >
                ROP
              </text>
            </>
          )}

          <AxisBottom
            top={innerHeight}
            scale={xScale}
            numTicks={innerWidth > 400 ? 8 : 4}
            tickFormat={(d) => formatDate((d as Date).toISOString().slice(0, 10))}
            tickLabelProps={() => ({
              fill: "var(--muted-foreground)",
              fontSize: 11,
              textAnchor: "middle",
            })}
            stroke="var(--border)"
          />
          <AxisLeft
            scale={yScale}
            tickLabelProps={() => ({
              fill: "var(--muted-foreground)",
              fontSize: 11,
              textAnchor: "end",
            })}
            stroke="var(--border)"
          />

          {parsedActual.length > 0 && (
            <LinePath
              data={parsedActual}
              x={(d) => xScale(d.date) ?? 0}
              y={(d) => yScale(d.running_stock) ?? 0}
              stroke="#3b82f6"
              strokeWidth={2}
              curve={curveMonotoneX}
            />
          )}

          {parsedActual.map((d, i) => {
            const cx = xScale(d.date) ?? 0;
            const cy = yScale(d.running_stock) ?? 0;
            return (
              <circle
                key={i}
                cx={cx}
                cy={cy}
                r={4}
                fill={dotColor(d.reason_code)}
                stroke="white"
                strokeWidth={1.5}
                onMouseEnter={(e) => {
                  showTooltip({
                    tooltipData: {
                      ...d,
                      date: filtered[i].date,
                      daysUntilStockout: daysUntilStockout ?? undefined,
                    },
                    tooltipLeft: e.pageX,
                    tooltipTop: e.pageY,
                  });
                }}
                onMouseLeave={hideTooltip}
              />
            );
          })}

          {parsedProjected.length > 0 && (
            <LinePath
              data={parsedProjected}
              x={(d) => xScale(d.date) ?? 0}
              y={(d) => yScale(d.running_stock) ?? 0}
              stroke="#94a3b8"
              strokeWidth={1.5}
              strokeDasharray="4 3"
              curve={curveMonotoneX}
            />
          )}
        </Group>
      </svg>
      {tooltipOpen && tooltipData && (
        <TooltipWithBounds
          left={tooltipLeft ?? 0}
          top={tooltipTop ?? 0}
          style={{
            background: "var(--background)",
            border: "1px solid var(--border)",
            borderRadius: 12,
            padding: "8px 12px",
            fontSize: 12,
            position: "fixed",
          }}
        >
          <p className="text-xs font-medium text-muted-foreground">
            {formatDate(tooltipData.date)}
          </p>
          {tooltipData.quantity_change !== 0 && (
            <p className="text-sm">
              <span className={tooltipData.quantity_change > 0 ? "text-success" : "text-destructive"}>
                {tooltipData.quantity_change > 0 ? "+" : ""}
                {tooltipData.quantity_change}
              </span>
              <span className="ml-1 text-muted-foreground">{tooltipData.reason_code}</span>
            </p>
          )}
          <p className="mt-0.5 text-sm font-semibold">Stock: {tooltipData.running_stock}</p>
          {tooltipData.daysUntilStockout != null && tooltipData.daysUntilStockout > 0 && (
            <p className="text-xs text-muted-foreground">
              Stockout in ~{Math.round(tooltipData.daysUntilStockout)}d
            </p>
          )}
        </TooltipWithBounds>
      )}
    </div>
  );
}

export function StockTrendChart({
  points,
  reorderPoint,
  safetyStock,
  avgDailyUsage,
}: StockTrendChartProps) {
  const [range, setRange] = useState<30 | 90 | 180 | 365 | -1>(90);

  const { filtered, currentStock, daysUntilStockout, projectedLine } = useMemo(() => {
    if (points.length === 0) {
      return { filtered: [], currentStock: 0, daysUntilStockout: null, projectedLine: [] };
    }

    const now = Date.now();
    const cutoff = range === -1 ? 0 : now - range * 24 * 60 * 60 * 1000;
    const filtered =
      cutoff > 0
        ? points.filter((p) => parseBackendDate(p.date).getTime() >= cutoff)
        : points;

    const last = points[points.length - 1];
    const currentStock = last?.running_stock ?? 0;

    let daysUntilStockout: number | null = null;
    let projectedLine: Array<{ date: string; running_stock: number }> = [];

    if (avgDailyUsage && avgDailyUsage > 0 && currentStock > 0) {
      daysUntilStockout = currentStock / avgDailyUsage;
      const daysToProject = Math.min(Math.ceil(daysUntilStockout) + 5, 90);
      projectedLine = [];
      for (let i = 1; i <= daysToProject; i++) {
        const projectedStock = Math.max(0, currentStock - avgDailyUsage * i);
        const date = new Date(now + i * 24 * 60 * 60 * 1000);
        projectedLine.push({
          date: date.toISOString().slice(0, 10),
          running_stock: projectedStock,
        });
      }
    }

    return { filtered, currentStock, daysUntilStockout, projectedLine };
  }, [points, range, avgDailyUsage]);

  const displayPoints = filtered;

  // Debug logging
  if (points.length > 0) {
    const now = Date.now();
    const cutoff = range === -1 ? 0 : now - range * 24 * 60 * 60 * 1000;
    const cutoffDate = new Date(cutoff).toISOString();
    console.log("[StockTrendChart]", {
      range,
      cutoffDate,
      now: new Date(now).toISOString(),
      pointsCount: points.length,
      filteredCount: filtered.length,
      firstPoint: points[0]?.date,
      lastPoint: points[points.length - 1]?.date,
    });
  }

  return (
    <div className="space-y-3">
      {/* Time range buttons - always visible */}
      <div className="flex items-center gap-1">
        {TIME_RANGES.map((r) => (
          <button
            key={r.label}
            type="button"
            onClick={() => setRange(r.days as typeof range)}
            className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              range === r.days
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {r.label}
          </button>
        ))}
        {daysUntilStockout != null && daysUntilStockout > 0 && (
          <span className="ml-3 text-xs text-muted-foreground">
            Stockout ~{Math.round(daysUntilStockout)}d
          </span>
        )}
      </div>

      {/* Chart or empty state */}
      {displayPoints.length === 0 ? (
        <div className="flex h-64 flex-col items-center justify-center text-muted-foreground">
          <p className="text-sm">No movements in selected period</p>
          <p className="mt-1 text-xs">Current stock: {currentStock}</p>
        </div>
      ) : (
        <>
          <ParentSize>
            {({ width }) => (
              <ChartInner
                filtered={displayPoints}
                projectedLine={projectedLine}
                reorderPoint={reorderPoint}
                safetyStock={safetyStock}
                width={width}
                height={260}
                daysUntilStockout={daysUntilStockout}
              />
            )}
          </ParentSize>

          <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="size-2 rounded-full bg-blue-500" /> Stock
            </span>
            <span className="flex items-center gap-1">
              <span className="size-2 rounded-full bg-red-400" /> Sales/Reservation
            </span>
            <span className="flex items-center gap-1">
              <span className="size-2 rounded-full bg-green-500" /> Supplier Delivery
            </span>
            <span className="flex items-center gap-1">
              <span className="size-2 rounded-full bg-slate-400" /> Other
            </span>
            {safetyStock != null && (
              <span className="flex items-center gap-1">
                <span className="size-2 rounded-full bg-orange-400 opacity-50" /> Safety Stock
              </span>
            )}
          </div>
        </>
      )}
    </div>
  );
}
