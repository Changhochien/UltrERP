/** Gross margin KPI card — shows margin % or unavailable state. */

import { useTranslation } from "react-i18next";
import { Info } from "lucide-react";

import { MetricCard, SectionCard } from "../../../components/layout/PageLayout";
import { Skeleton } from "../../../components/ui/skeleton";
import type { GrossMarginResponse } from "../types";

function formatTWD(value: string): string {
  return `NT$ ${Number(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

interface GrossMarginCardProps {
  data: GrossMarginResponse | null;
  isLoading: boolean;
  error: string | null;
}

export function GrossMarginCard({ data, isLoading, error }: GrossMarginCardProps) {
  const { t } = useTranslation("dashboard");

  if (isLoading) {
    return (
      <SectionCard
        title={t("grossMargin.title")}
        description={t("grossMargin.description")}
        className="h-full"
        contentClassName="space-y-4"
      >
        <div data-testid="gross-margin-card-loading" className="space-y-3">
          <Skeleton className="h-10 w-32" />
          <Skeleton className="h-20 w-full" />
        </div>
      </SectionCard>
    );
  }

  if (error) {
    return (
      <SectionCard
        title={t("grossMargin.title")}
        description={t("grossMargin.description")}
        className="h-full"
        contentClassName="space-y-4"
      >
        <p className="text-sm text-destructive">{error}</p>
      </SectionCard>
    );
  }

  if (!data) return null;

  // Unavailable state (unit_cost not populated)
  if (!data.available) {
    return (
      <SectionCard
        title={t("grossMargin.title")}
        description={t("grossMargin.description")}
        className="h-full"
        contentClassName="space-y-4"
      >
        <div
          data-testid="gross-margin-card-unavailable"
          className="flex items-center gap-2 text-sm text-muted-foreground"
        >
          <Info className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span>{t("grossMargin.unavailable")}</span>
        </div>
      </SectionCard>
    );
  }

  const marginPercent =
    data.gross_margin_percent != null ? Number(data.gross_margin_percent) : null;
  const hasMarginPercent = marginPercent != null && !Number.isNaN(marginPercent);
  const previousMarginPercent =
    data.previous_period.available && data.previous_period.gross_margin_percent != null
      ? Number(data.previous_period.gross_margin_percent)
      : null;
  const marginDelta =
    !hasMarginPercent || previousMarginPercent == null || Number.isNaN(previousMarginPercent)
      ? null
      : marginPercent - previousMarginPercent;

  let trendDisplay: string;
  let trendDirection: "up" | "down" | "flat" = "flat";

  if (marginDelta != null && !isNaN(marginDelta)) {
    if (marginDelta > 0) {
      trendDisplay = `+${marginDelta.toFixed(1)}pp`;
      trendDirection = "up";
    } else if (marginDelta < 0) {
      trendDisplay = `${marginDelta.toFixed(1)}pp`;
      trendDirection = "down";
    } else {
      trendDisplay = "0.0pp";
    }
  } else {
    trendDisplay = "—";
  }

  const sparkPoints =
    !hasMarginPercent
      ? [0, 0, 0, 0]
      : previousMarginPercent == null
      ? [marginPercent * 0.9, marginPercent, marginPercent, marginPercent]
      : [
          marginPercent * 0.9,
          marginPercent,
          (marginPercent + previousMarginPercent) / 2,
          marginPercent,
        ];

  return (
    <div data-testid="gross-margin-card">
      <MetricCard
        title={t("grossMargin.title")}
        value={hasMarginPercent ? `${marginPercent.toFixed(1)}%` : "—"}
        description={t("grossMargin.vsPreviousPeriod")}
        trendLabel={trendDisplay !== "—" ? trendDisplay : undefined}
        trendDirection={trendDisplay !== "—" ? trendDirection : undefined}
        points={sparkPoints}
      />
      <div className="mt-3 grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs text-muted-foreground">{t("grossMargin.revenue")}</p>
          <p className="text-sm font-semibold">{formatTWD(data.revenue)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{t("grossMargin.cogs")}</p>
          <p className="text-sm font-semibold">{formatTWD(data.cogs)}</p>
        </div>
      </div>
    </div>
  );
}
