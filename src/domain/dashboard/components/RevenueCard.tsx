/** Revenue comparison card — today vs yesterday. */

import { MetricCard, SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { Badge } from "../../../components/ui/badge";
import { Skeleton } from "../../../components/ui/skeleton";
import { cn } from "../../../lib/utils";
import type { RevenueSummary } from "../types";

function formatTWD(value: string): string {
  return `NT$ ${Number(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

interface RevenueCardProps {
  data: RevenueSummary | null;
  isLoading: boolean;
  error: string | null;
}

export function RevenueCard({ data, isLoading, error }: RevenueCardProps) {
  if (isLoading) {
    return (
      <SectionCard title="Revenue Comparison" description="Today versus yesterday" className="h-full" contentClassName="space-y-4">
        <div data-testid="revenue-card-loading" className="space-y-3">
          <Skeleton className="h-10 w-32" />
          <Skeleton className="h-20 w-full" />
        </div>
      </SectionCard>
    );
  }

  if (error) {
    return (
      <SectionCard title="Revenue Comparison" description="Today versus yesterday" className="h-full" contentClassName="space-y-4">
        <div data-testid="revenue-card-error">
          <SurfaceMessage tone="danger">{error}</SurfaceMessage>
        </div>
      </SectionCard>
    );
  }

  if (!data) return null;

  const todayRevenue = Number(data.today_revenue);
  const yesterdayRevenue = Number(data.yesterday_revenue);
  const changePercent = data.change_percent;
  let changeDisplay: string;
  let changeClass = "";
  let changeVariant: "outline" | "success" | "destructive" = "outline";

  if (changePercent === null) {
    changeDisplay = "—";
  } else {
    const pct = Number(changePercent);
    if (pct > 0) {
      changeDisplay = `▲ +${pct.toFixed(1)}%`;
      changeClass = "change--positive";
      changeVariant = "success";
    } else if (pct < 0) {
      changeDisplay = `▼ ${pct.toFixed(1)}%`;
      changeClass = "change--negative";
      changeVariant = "destructive";
    } else {
      changeDisplay = "0.0%";
    }
  }

  return (
    <div data-testid="revenue-card">
      <MetricCard
        title="Revenue Comparison"
        value={formatTWD(data.today_revenue)}
        description={`Yesterday (${data.yesterday_date}) ${formatTWD(data.yesterday_revenue)}`}
        points={[yesterdayRevenue * 0.88, yesterdayRevenue, (yesterdayRevenue + todayRevenue) / 2, todayRevenue]}
        badge={(
          <Badge
            data-testid="change-indicator"
            variant={changeVariant}
            className={cn("normal-case tracking-normal", changeClass)}
            aria-label={
              changePercent === null
                ? "No change data available"
                : `Revenue change: ${changeDisplay}`
            }
          >
            {changeDisplay}
          </Badge>
        )}
      />
    </div>
  );
}
