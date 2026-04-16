import { useDeferredValue, useState } from "react";
import { useTranslation } from "react-i18next";

import { SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { isFeatureDisabledError } from "../../../lib/featureGates";
import { useRevenueDiagnosis } from "../hooks/useIntelligence";
import type { RevenueDiagnosisDataBasis, RevenueDiagnosisPeriod } from "../types";

const PERIODS: RevenueDiagnosisPeriod[] = ["1m", "3m", "6m", "12m"];

function formatTWD(value: string): string {
  return `NT$ ${Number(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatDelta(value: number | null): string {
  if (value == null) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
}

function formatGeneratedAt(value: string, language: string): string {
  const locale = language === "zh-Hant" ? "zh-TW" : "en-US";
  return new Date(value).toLocaleString(locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatDataBasis(value: RevenueDiagnosisDataBasis): string {
  return value === "aggregate_plus_live_current_month" ? "Aggregate + live current month" : "Aggregate only";
}

export function RevenueDiagnosisCard() {
  const { t, i18n } = useTranslation("common", { keyPrefix: "intelligence.revenueDiagnosis" });
  const [period, setPeriod] = useState<RevenueDiagnosisPeriod>("1m");
  const [categoryInput, setCategoryInput] = useState("");
  const deferredCategory = useDeferredValue(categoryInput.trim() || undefined);
  const { data, isLoading, error } = useRevenueDiagnosis(period, undefined, deferredCategory, 10);

  if (!isLoading && isFeatureDisabledError(error)) {
    return null;
  }

  return (
    <SectionCard
      title={t("title", { defaultValue: "Revenue Diagnosis" })}
      description={t("description", {
        defaultValue: "Break revenue change into price, volume, and mix with snapshot-correct historical evidence.",
      })}
      actions={(
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex flex-wrap gap-2" role="group" aria-label="Revenue diagnosis period filters">
            {PERIODS.map((periodOption) => (
              <Button
                key={periodOption}
                type="button"
                size="sm"
                variant={period === periodOption ? "default" : "outline"}
                onClick={() => setPeriod(periodOption)}
                aria-pressed={period === periodOption}
              >
                {periodOption}
              </Button>
            ))}
          </div>
          <Input
            value={categoryInput}
            onChange={(event) => setCategoryInput(event.target.value)}
            placeholder={t("categoryPlaceholder", { defaultValue: "Filter category" })}
            className="h-9 w-44"
            aria-label={t("categoryPlaceholder", { defaultValue: "Filter category" })}
          />
        </div>
      )}
    >
      <div className="space-y-4">
        {isLoading ? (
          <div className="space-y-3" data-testid="revenue-diagnosis-loading">
            <div className="h-10 rounded-xl bg-muted/60" />
            <div className="h-32 rounded-xl bg-muted/40" />
          </div>
        ) : null}

        {!isLoading && error ? (
          <SurfaceMessage tone="danger">
            {t("loadError", { defaultValue: "Failed to load revenue diagnosis." })}
          </SurfaceMessage>
        ) : null}

        {!isLoading && !error && data ? (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground">
              <span>
                {t("generatedAt", {
                  value: formatGeneratedAt(data.computed_at, i18n.resolvedLanguage ?? i18n.language),
                  defaultValue: `Generated ${formatGeneratedAt(data.computed_at, i18n.resolvedLanguage ?? i18n.language)}`,
                })}
              </span>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={data.window_is_partial ? "warning" : "secondary"}>
                  {data.window_is_partial
                    ? t("partial", { defaultValue: "Includes live current month" })
                    : t("historical", { defaultValue: "Closed months only" })}
                </Badge>
                <Badge variant="outline">{formatDataBasis(data.data_basis)}</Badge>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-4">
              <article className="rounded-2xl border border-border/70 bg-background/60 p-4">
                <div className="text-sm text-muted-foreground">{t("summary.currentRevenue", { defaultValue: "Current Revenue" })}</div>
                <div className="mt-2 text-2xl font-semibold">{formatTWD(data.summary.current_revenue)}</div>
              </article>
              <article className="rounded-2xl border border-border/70 bg-background/60 p-4">
                <div className="text-sm text-muted-foreground">{t("summary.priorRevenue", { defaultValue: "Prior Revenue" })}</div>
                <div className="mt-2 text-2xl font-semibold">{formatTWD(data.summary.prior_revenue)}</div>
              </article>
              <article className="rounded-2xl border border-border/70 bg-background/60 p-4">
                <div className="text-sm text-muted-foreground">{t("summary.delta", { defaultValue: "Revenue Delta" })}</div>
                <div className="mt-2 text-2xl font-semibold">{formatTWD(data.summary.revenue_delta)}</div>
                <div className="mt-1 text-sm text-muted-foreground">{formatDelta(data.summary.revenue_delta_pct)}</div>
              </article>
              <article className="rounded-2xl border border-border/70 bg-background/60 p-4">
                <div className="text-sm text-muted-foreground">{t("summary.currentWindow", { defaultValue: "Current Window" })}</div>
                <div className="mt-2 text-sm font-medium">{data.current_window.start_month} to {data.current_window.end_month}</div>
                <div className="mt-1 text-sm text-muted-foreground">{t("summary.priorWindow", { defaultValue: "Prior" })}: {data.prior_window.start_month} to {data.prior_window.end_month}</div>
              </article>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <article className="rounded-2xl border border-border/70 bg-background/60 p-4">
                <div className="text-sm text-muted-foreground">{t("components.price", { defaultValue: "Price Effect" })}</div>
                <div className="mt-2 text-xl font-semibold">{formatTWD(data.components.price_effect_total)}</div>
              </article>
              <article className="rounded-2xl border border-border/70 bg-background/60 p-4">
                <div className="text-sm text-muted-foreground">{t("components.volume", { defaultValue: "Volume Effect" })}</div>
                <div className="mt-2 text-xl font-semibold">{formatTWD(data.components.volume_effect_total)}</div>
              </article>
              <article className="rounded-2xl border border-border/70 bg-background/60 p-4">
                <div className="text-sm text-muted-foreground">{t("components.mix", { defaultValue: "Mix Effect" })}</div>
                <div className="mt-2 text-xl font-semibold">{formatTWD(data.components.mix_effect_total)}</div>
              </article>
            </div>

            {data.drivers.length === 0 ? (
              <SurfaceMessage>
                {t("empty", { defaultValue: "No qualifying revenue drivers for this comparison window." })}
              </SurfaceMessage>
            ) : (
              <div className="overflow-x-auto rounded-2xl border border-border/70 bg-background/60">
                <table className="min-w-full divide-y divide-border/60 text-sm">
                  <thead className="bg-muted/40 text-left text-muted-foreground">
                    <tr>
                      <th className="px-4 py-3 font-medium">{t("table.product", { defaultValue: "Product" })}</th>
                      <th className="px-4 py-3 font-medium">{t("table.category", { defaultValue: "Category" })}</th>
                      <th className="px-4 py-3 font-medium">{t("table.delta", { defaultValue: "Delta" })}</th>
                      <th className="px-4 py-3 font-medium">{t("table.price", { defaultValue: "Price" })}</th>
                      <th className="px-4 py-3 font-medium">{t("table.volume", { defaultValue: "Volume" })}</th>
                      <th className="px-4 py-3 font-medium">{t("table.mix", { defaultValue: "Mix" })}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/50">
                    {data.drivers.map((driver) => (
                      <tr key={driver.product_id}>
                        <td className="px-4 py-3 align-top">
                          <div className="font-medium">{driver.product_name}</div>
                          <div className="text-xs text-muted-foreground">{formatDelta(driver.revenue_delta_pct)}</div>
                        </td>
                        <td className="px-4 py-3 align-top text-muted-foreground">{driver.product_category_snapshot}</td>
                        <td className="px-4 py-3 align-top">{formatTWD(driver.revenue_delta)}</td>
                        <td className="px-4 py-3 align-top">{formatTWD(driver.price_effect)}</td>
                        <td className="px-4 py-3 align-top">{formatTWD(driver.volume_effect)}</td>
                        <td className="px-4 py-3 align-top">{formatTWD(driver.mix_effect)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        ) : null}
      </div>
    </SectionCard>
  );
}