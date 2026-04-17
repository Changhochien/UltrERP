import { useDeferredValue, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { isFeatureDisabledError } from "../../../lib/featureGates";
import { buildProductDetailPath } from "../../../lib/routes";
import { useProductPerformance } from "../hooks/useIntelligence";
import type { ProductLifecycleStage, ProductPerformanceDataBasis } from "../types";

type LifecycleFilter = "all" | ProductLifecycleStage;

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

function formatDataBasis(
  value: ProductPerformanceDataBasis,
  t: ReturnType<typeof useTranslation>["t"],
): string {
  return t(`dataBasis.${value}`, {
    defaultValue: value === "aggregate_plus_live_current_month" ? "Aggregate + live current month" : "Aggregate only",
  });
}

function formatStageReason(
  reason: string | undefined,
  t: ReturnType<typeof useTranslation>["t"],
): string | null {
  if (!reason) {
    return null;
  }

  if (!reason.startsWith("rule:")) {
    return reason;
  }

  return t(`reason.${reason.slice(5)}`, { defaultValue: reason });
}

export function ProductPerformanceCard() {
  const { t, i18n } = useTranslation("common", { keyPrefix: "intelligence.productPerformance" });
  const [categoryInput, setCategoryInput] = useState("");
  const [lifecycleStage, setLifecycleStage] = useState<LifecycleFilter>("all");
  const [includeCurrentMonth, setIncludeCurrentMonth] = useState(false);
  const deferredCategory = useDeferredValue(categoryInput.trim() || undefined);
  const effectiveStage = lifecycleStage === "all" ? undefined : lifecycleStage;
  const { data, isLoading, error } = useProductPerformance(
    deferredCategory,
    effectiveStage,
    25,
    includeCurrentMonth,
  );

  if (!isLoading && isFeatureDisabledError(error)) {
    return null;
  }

  return (
    <SectionCard
      title={t("title", { defaultValue: "Product Performance" })}
      description={t("description", {
        defaultValue: "Rank products by current-versus-prior revenue and lifecycle stage.",
      })}
      actions={(
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={lifecycleStage}
            onChange={(event) => setLifecycleStage(event.target.value as LifecycleFilter)}
            aria-label={t("lifecycleLabel", { defaultValue: "Lifecycle stage" })}
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          >
            <option value="all">{t("allStages", { defaultValue: "All stages" })}</option>
            <option value="growing">{t("stage.growing", { defaultValue: "Growing" })}</option>
            <option value="mature">{t("stage.mature", { defaultValue: "Mature" })}</option>
            <option value="stable">{t("stage.stable", { defaultValue: "Stable" })}</option>
            <option value="declining">{t("stage.declining", { defaultValue: "Declining" })}</option>
            <option value="new">{t("stage.new", { defaultValue: "New" })}</option>
            <option value="end_of_life">{t("stage.end_of_life", { defaultValue: "End of Life" })}</option>
          </select>
          <Input
            value={categoryInput}
            onChange={(event) => setCategoryInput(event.target.value)}
            placeholder={t("categoryPlaceholder", { defaultValue: "Filter category" })}
            className="h-9 w-44"
            aria-label={t("categoryPlaceholder", { defaultValue: "Filter category" })}
          />
          <Button
            type="button"
            size="sm"
            variant={includeCurrentMonth ? "default" : "outline"}
            aria-pressed={includeCurrentMonth}
            onClick={() => setIncludeCurrentMonth((current) => !current)}
          >
            {t("includeCurrentMonth", { defaultValue: "Include current month" })}
          </Button>
        </div>
      )}
    >
      <div className="space-y-4">
        {isLoading ? (
          <div className="space-y-3" data-testid="product-performance-loading">
            <div className="h-10 rounded-xl bg-muted/60" />
            <div className="h-32 rounded-xl bg-muted/40" />
          </div>
        ) : null}

        {!isLoading && error ? (
          <SurfaceMessage tone="danger">
            {t("loadError", { defaultValue: "Failed to load product performance." })}
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
                <Badge variant="outline">{formatDataBasis(data.data_basis, t)}</Badge>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <article className="rounded-2xl border border-border/70 bg-background/60 p-4">
                <div className="text-sm text-muted-foreground">{t("summary.products", { defaultValue: "Products" })}</div>
                <div className="mt-2 text-2xl font-semibold">{data.total}</div>
                <div className="mt-1 text-sm text-muted-foreground">
                  {t("summary.windowNote", {
                    count: data.products.length,
                    defaultValue: `Showing top ${data.products.length} rows`,
                  })}
                </div>
              </article>
              <article className="rounded-2xl border border-border/70 bg-background/60 p-4">
                <div className="text-sm text-muted-foreground">{t("summary.currentWindow", { defaultValue: "Current Window" })}</div>
                <div className="mt-2 text-sm font-medium">{data.current_window.start_month} to {data.current_window.end_month}</div>
              </article>
              <article className="rounded-2xl border border-border/70 bg-background/60 p-4">
                <div className="text-sm text-muted-foreground">{t("summary.priorWindow", { defaultValue: "Prior Window" })}</div>
                <div className="mt-2 text-sm font-medium">{data.prior_window.start_month} to {data.prior_window.end_month}</div>
              </article>
            </div>

            {data.products.length === 0 ? (
              <SurfaceMessage>
                {t("empty", { defaultValue: "No qualifying products for this comparison window." })}
              </SurfaceMessage>
            ) : (
              <div className="overflow-x-auto rounded-2xl border border-border/70 bg-background/60">
                <table className="min-w-full divide-y divide-border/60 text-sm">
                  <thead className="bg-muted/40 text-left text-muted-foreground">
                    <tr>
                      <th className="px-4 py-3 font-medium">{t("table.product", { defaultValue: "Product" })}</th>
                      <th className="px-4 py-3 font-medium">{t("table.category", { defaultValue: "Category" })}</th>
                      <th className="px-4 py-3 font-medium">{t("table.lifecycle", { defaultValue: "Lifecycle" })}</th>
                      <th className="px-4 py-3 font-medium">{t("table.currentRevenue", { defaultValue: "Current Revenue" })}</th>
                      <th className="px-4 py-3 font-medium">{t("table.priorRevenue", { defaultValue: "Prior Revenue" })}</th>
                      <th className="px-4 py-3 font-medium">{t("table.delta", { defaultValue: "Delta" })}</th>
                      <th className="px-4 py-3 font-medium">{t("table.peakMonth", { defaultValue: "Peak Month Revenue" })}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/50">
                    {data.products.map((product) => (
                      <tr key={product.product_id}>
                        <td className="px-4 py-3 align-top">
                          <Link
                            to={buildProductDetailPath(product.product_id, "analytics")}
                            className="font-medium text-primary underline-offset-4 hover:underline"
                          >
                            {product.product_name}
                          </Link>
                          <div className="mt-1 text-xs text-muted-foreground">
                            {t("table.monthsOnSale", {
                              count: product.months_on_sale,
                              defaultValue: `${product.months_on_sale} months on sale`,
                            })}
                          </div>
                        </td>
                        <td className="px-4 py-3 align-top text-muted-foreground">{product.product_category_snapshot}</td>
                        <td className="px-4 py-3 align-top">
                          <Badge variant="outline">
                            {t(`stage.${product.lifecycle_stage}`, {
                              defaultValue: product.lifecycle_stage,
                            })}
                          </Badge>
                          {formatStageReason(product.stage_reasons[0], t) ? (
                            <div className="mt-2 max-w-xs text-xs text-muted-foreground">
                              {formatStageReason(product.stage_reasons[0], t)}
                            </div>
                          ) : null}
                        </td>
                        <td className="px-4 py-3 align-top">{formatTWD(product.current_period.revenue)}</td>
                        <td className="px-4 py-3 align-top">{formatTWD(product.prior_period.revenue)}</td>
                        <td className="px-4 py-3 align-top">
                          <div className="font-medium">{formatDelta(product.revenue_delta_pct)}</div>
                        </td>
                        <td className="px-4 py-3 align-top">{formatTWD(product.peak_month_revenue)}</td>
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