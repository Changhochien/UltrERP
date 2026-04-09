/** AP Aging dashboard card. */

import { useTranslation } from "react-i18next";

import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Skeleton } from "../../../components/ui/skeleton";
import { Button } from "../../../components/ui/button";
import { useAPAging } from "../hooks/useDashboard";
import type { APAgingBucket } from "../types";

const BUCKET_COLORS: Record<string, string> = {
  "0-30": "#22c55e",   // green - healthy
  "31-60": "#eab308",  // amber - attention
  "61-90": "#f97316",  // orange - warning
  "90+": "#ef4444",    // red - critical
};

const BUCKET_LABELS: Record<string, string> = {
  "0-30": "0–30 days",
  "31-60": "31–60 days",
  "61-90": "61–90 days",
  "90+": "90+ days",
};

function formatTWD(value: string | number): string {
  return `NT$ ${Number(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

interface APAgingCardProps {
  data: ReturnType<typeof useAPAging>["data"];
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
}

export function APAgingCard({ data, isLoading, error, onRetry }: APAgingCardProps) {
  const { t } = useTranslation("common");

  if (isLoading) {
    return (
      <Card data-testid="ap-aging-card" className="h-full">
        <CardHeader className="pb-2">
          <Skeleton className="h-5 w-36" />
        </CardHeader>
        <CardContent>
          <div data-testid="ap-aging-loading">
            <Skeleton className="h-4 w-24 mb-4" />
            <Skeleton className="h-20 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card data-testid="ap-aging-card" className="h-full">
        <CardHeader className="pb-2">
          <CardTitle>{t("dashboard.apAging.title")}</CardTitle>
        </CardHeader>
        <CardContent>
          <div data-testid="ap-aging-error" className="flex flex-col gap-3">
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

  const buckets = data.buckets;

  return (
    <Card data-testid="ap-aging-card" className="h-full">
      <CardHeader className="pb-2">
        <CardTitle>{t("dashboard.apAging.title")}</CardTitle>
        <p className="text-sm text-muted-foreground">
          {t("dashboard.apAging.asOf", { date: data.as_of_date })}
        </p>
      </CardHeader>
      <CardContent className="space-y-4 pt-0">
        {/* 4-column bucket grid */}
        <div data-testid="ap-aging-buckets" className="grid grid-cols-4 gap-2">
          {buckets.map((bucket: APAgingBucket) => (
            <div
              key={bucket.bucket_label}
              data-testid={`ap-aging-bucket-${bucket.bucket_label}`}
              className="flex flex-col items-center rounded-2xl border p-3 text-center gap-1"
            >
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: BUCKET_COLORS[bucket.bucket_label] ?? "#6b7280" }}
                aria-label={BUCKET_LABELS[bucket.bucket_label]}
              />
              <span className="text-xs text-muted-foreground font-medium">
                {BUCKET_LABELS[bucket.bucket_label]}
              </span>
              <span className="text-sm font-semibold text-foreground">
                {formatTWD(bucket.amount)}
              </span>
              <span className="text-xs text-muted-foreground">
                {t("dashboard.apAging.invoices", { count: bucket.invoice_count })}
              </span>
            </div>
          ))}
        </div>

        {/* Summary row */}
        <div data-testid="ap-aging-summary" className="flex gap-6 pt-2 border-t">
          <div>
            <p className="text-xs text-muted-foreground">{t("dashboard.apAging.totalOutstanding")}</p>
            <p className="text-sm font-semibold text-foreground">{formatTWD(data.total_outstanding)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t("dashboard.apAging.totalOverdue")}</p>
            <p className="text-sm font-semibold text-destructive">{formatTWD(data.total_overdue)}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
