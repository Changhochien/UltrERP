/** Analytics summary card — displays avg_daily, lead_time, ROP, safety_stock. */

import { SectionCard } from "@/components/layout/PageLayout";

interface AnalyticsSummaryCardProps {
  avgDailyUsage: number | null;
  leadTimeDays: number | null;
  reorderPoint: number;
  safetyStock: number | null;
  loading?: boolean;
}

function num(value: number | null | undefined, fallback = "—"): string {
  if (value == null) return fallback;
  return value.toFixed(1);
}

export function AnalyticsSummaryCard({
  avgDailyUsage,
  leadTimeDays,
  reorderPoint,
  safetyStock,
  loading,
}: AnalyticsSummaryCardProps) {
  if (loading) {
    return (
      <SectionCard title="Analytics Summary">
        <div className="flex gap-8">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-12 w-24 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      </SectionCard>
    );
  }

  return (
    <SectionCard title="Analytics Summary">
      <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Avg Daily Usage</p>
          <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">{num(avgDailyUsage)}</p>
          <p className="text-xs text-muted-foreground">units / day</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Lead Time</p>
          <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">{num(leadTimeDays)}</p>
          <p className="text-xs text-muted-foreground">days</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">ROP</p>
          <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">{reorderPoint.toLocaleString()}</p>
          <p className="text-xs text-muted-foreground">reorder point</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Safety Stock</p>
          <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">{num(safetyStock)}</p>
          <p className="text-xs text-muted-foreground">units</p>
        </div>
      </div>
    </SectionCard>
  );
}
