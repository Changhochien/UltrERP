/** Visitor statistics dashboard card with PostHog data. */

import { useTranslation } from "react-i18next";

import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Skeleton } from "../../../components/ui/skeleton";
import { useVisitorStats } from "../hooks/useDashboard";

export function VisitorStatsCard() {
  const { t } = useTranslation("dashboard");
  const { data, isLoading, error } = useVisitorStats();

  if (isLoading) {
    return (
      <Card data-testid="visitor-stats-card" className="h-full">
        <CardHeader>
          <CardTitle>{t("visitorStats.title")}</CardTitle>
        </CardHeader>
        <CardContent>
          <div data-testid="visitor-stats-loading" className="space-y-3">
            <Skeleton className="h-5 w-28" />
            <Skeleton className="h-24 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card data-testid="visitor-stats-card" className="h-full">
        <CardHeader>
          <CardTitle>{t("visitorStats.title")}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-destructive">{t("visitorStats.analyticsUnavailable")}</p>
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  if (!data.is_configured) {
    return (
      <Card data-testid="visitor-stats-card" className="h-full">
        <CardHeader>
          <CardTitle>{t("visitorStats.title")}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground" data-testid="visitor-not-configured">
            {t("visitorStats.analyticsNotConfigured")}
          </p>
        </CardContent>
      </Card>
    );
  }

  if (data.error) {
    return (
      <Card data-testid="visitor-stats-card" className="h-full">
        <CardHeader>
          <CardTitle>{t("visitorStats.title")}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-destructive">{t("visitorStats.analyticsUnavailable")}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="visitor-stats-card" className="h-full">
      <CardHeader>
        <CardTitle>{t("visitorStats.title")}</CardTitle>
        <p className="text-sm text-muted-foreground" data-testid="visitor-date">
          {t("visitorStats.yesterday", { date: data.date })}
        </p>
      </CardHeader>
      <CardContent className="grid gap-3 pt-0 sm:grid-cols-2 2xl:grid-cols-3">
        <div className="rounded-2xl border border-border/70 bg-muted/30 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{t("visitorStats.uniqueVisitors")}</p>
          <p className="mt-3 text-3xl font-semibold tracking-tight" data-testid="visitor-count" aria-label={`Unique visitors: ${data.visitor_count}`}>
            {data.visitor_count.toLocaleString()}
          </p>
        </div>
        <div className="rounded-2xl border border-border/70 bg-muted/30 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{t("visitorStats.inquiries")}</p>
          <p className="mt-3 text-3xl font-semibold tracking-tight" data-testid="inquiry-count" aria-label={`Inquiries: ${data.inquiry_count}`}>
            {data.inquiry_count.toLocaleString()}
          </p>
        </div>
        <div className="rounded-2xl border border-border/70 bg-muted/30 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{t("visitorStats.conversion")}</p>
          <p
            className="mt-3 text-3xl font-semibold tracking-tight"
            data-testid="conversion-rate"
            aria-label={`Conversion rate: ${data.conversion_rate != null ? `${data.conversion_rate}%` : "not available"}`}
          >
            {data.conversion_rate != null ? `${data.conversion_rate}%` : "—"}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
