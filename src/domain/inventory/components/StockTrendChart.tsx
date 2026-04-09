/** Stock trend line chart with reorder point reference line and stockout projection. */

import { useMemo, useState } from "react";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ReferenceArea,
  ResponsiveContainer,
  Dot,
} from "recharts";
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

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload?: StockHistoryPoint & { daysUntilStockout?: number } }> }) {
  if (!active || !payload || payload.length === 0) return null;
  const p = payload[0].payload ?? (payload[0] as unknown as StockHistoryPoint & { daysUntilStockout?: number });
  return (
    <div className="rounded-xl border border-border bg-background px-3 py-2 shadow-lg">
      <p className="text-xs font-medium text-muted-foreground">{formatDate(p.date)}</p>
      {p.quantity_change !== 0 && (
        <p className="text-sm">
          <span className={p.quantity_change > 0 ? "text-success" : "text-destructive"}>
            {p.quantity_change > 0 ? "+" : ""}
            {p.quantity_change}
          </span>
          <span className="ml-1 text-muted-foreground">{p.reason_code}</span>
        </p>
      )}
      <p className="mt-0.5 text-sm font-semibold">Stock: {p.running_stock}</p>
      {p.daysUntilStockout != null && p.daysUntilStockout > 0 && (
        <p className="text-xs text-muted-foreground">
          Stockout in ~{Math.round(p.daysUntilStockout)}d
        </p>
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
    const filtered = cutoff > 0 ? points.filter((p) => parseBackendDate(p.date).getTime() >= cutoff) : points;

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

  // When the selected range excludes all data (e.g. 90d range but latest data is older),
  // fall back to showing all available data instead of an error.
  const displayPoints = filtered.length < 2 && points.length >= 2 ? points : filtered;

  if (displayPoints.length === 0) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-muted-foreground">
        <p className="text-sm">No movements in selected period</p>
        <p className="mt-1 text-xs">Current stock: {currentStock}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Time range selector */}
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

      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={[...displayPoints, ...projectedLine]} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
            tickLine={false}
            axisLine={{ stroke: "var(--border)" }}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
            tickLine={false}
            axisLine={false}
            width={40}
          />
          <Tooltip content={<CustomTooltip />} />

          {/* Safety stock shaded area */}
          {safetyStock != null && safetyStock > 0 && (
            <ReferenceArea
              y1={0}
              y2={safetyStock}
              fill="#f97316"
              fillOpacity={0.1}
              strokeOpacity={0}
            />
          )}

          {/* Reorder point reference line */}
          <ReferenceLine
            y={reorderPoint}
            stroke="#ef4444"
            strokeDasharray="5 3"
            label={{
              value: "ROP",
              position: "insideTopRight",
              fill: "#ef4444",
              fontSize: 11,
            }}
          />

          {/* Actual stock line */}
          <Line
            data={filtered}
            type="monotone"
            dataKey="running_stock"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={(props: { cx?: number; cy?: number; payload?: StockHistoryPoint }) => {
              if (!props.cx || !props.cy || !props.payload) return <Dot {...props} />;
              const { cx, cy, payload } = props;
              return (
                <Dot
                  cx={cx}
                  cy={cy}
                  r={4}
                  fill={dotColor(payload.reason_code ?? "other")}
                  stroke="white"
                  strokeWidth={1.5}
                />
              );
            }}
            activeDot={{ r: 5, stroke: "white", strokeWidth: 1.5 }}
            connectNulls={false}
          />

          {/* Projected stockout line (dashed) */}
          {projectedLine.length > 0 && (
            <Line
              data={projectedLine}
              type="monotone"
              dataKey="running_stock"
              stroke="#94a3b8"
              strokeWidth={1.5}
              strokeDasharray="4 3"
              dot={false}
              activeDot={false}
              connectNulls={false}
            />
          )}
        </LineChart>
      </ResponsiveContainer>

      {/* Legend */}
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
    </div>
  );
}