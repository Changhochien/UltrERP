import { useTranslation } from "react-i18next";

import { SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { isFeatureDisabledError } from "../../../lib/featureGates";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../../components/ui/table";
import { useCustomerBuyingBehavior } from "../hooks/useIntelligence";
import type { CustomerBuyingBehaviorCustomerType, CustomerBuyingBehaviorDataBasis, CustomerBuyingBehaviorPeriod } from "../types";
import { useState } from "react";

const customerTypeOptions: Array<{
  value: CustomerBuyingBehaviorCustomerType;
  labelKey: "filterDealers" | "filterEndUsers" | "filterUnknown" | "filterAll";
  defaultValue: string;
}> = [
  { value: "dealer", labelKey: "filterDealers", defaultValue: "Dealers" },
  { value: "end_user", labelKey: "filterEndUsers", defaultValue: "End Users" },
  { value: "unknown", labelKey: "filterUnknown", defaultValue: "Unknown" },
  { value: "all", labelKey: "filterAll", defaultValue: "All" },
];

const periods: CustomerBuyingBehaviorPeriod[] = ["3m", "6m", "12m"];

function formatTWD(value: string): string {
  return `NT$ ${Number(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatPercent(value: string): string {
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function formatLift(value: string | null): string {
  return value == null ? "—" : `${Number(value).toFixed(2)}x`;
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
  value: CustomerBuyingBehaviorDataBasis,
  t: ReturnType<typeof useTranslation>["t"],
): string {
  return t(`dataBasis.${value}`, {
    defaultValue: value === "transactional_fallback" ? "Transactional fallback" : value,
  });
}

export function CustomerBuyingBehaviorCard() {
  const { t, i18n } = useTranslation("common", { keyPrefix: "intelligence.customerBuyingBehavior" });
  const [customerType, setCustomerType] = useState<CustomerBuyingBehaviorCustomerType>("dealer");
  const [period, setPeriod] = useState<CustomerBuyingBehaviorPeriod>("12m");
  const [includeCurrentMonth, setIncludeCurrentMonth] = useState(false);
  const { data, isLoading, error } = useCustomerBuyingBehavior(customerType, period, 20, includeCurrentMonth);

  if (!isLoading && isFeatureDisabledError(error)) {
    return null;
  }

  return (
    <SectionCard
      title={t("title", { defaultValue: "Customer Buying Behavior" })}
      description={t("description", {
        defaultValue: "Compare segment-level category mix, cross-sell lift, and month-by-month buying patterns.",
      })}
      actions={(
        <div className="flex flex-wrap items-center gap-3">
          <div
            role="group"
            aria-label={t("customerTypeLabel", { defaultValue: "Customer Type" })}
            className="flex flex-wrap items-center gap-2"
          >
            {customerTypeOptions.map((option) => (
              <Button
                key={option.value}
                type="button"
                size="sm"
                variant={customerType === option.value ? "default" : "outline"}
                onClick={() => setCustomerType(option.value)}
              >
                {t(option.labelKey, { defaultValue: option.defaultValue })}
              </Button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Buying behavior period filters">
            {periods.map((periodOption) => (
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
          <div className="space-y-3" data-testid="customer-buying-behavior-loading">
            <div className="h-10 rounded-xl bg-muted/60" />
            <div className="h-40 rounded-xl bg-muted/40" />
          </div>
        ) : null}

        {!isLoading && error ? (
          <SurfaceMessage tone="danger">
            {t("loadError", { defaultValue: "Failed to load customer buying behavior." })}
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

            <div className="grid gap-3 md:grid-cols-4">
              <article className="rounded-2xl border border-border/70 bg-background/60 p-4">
                <div className="text-sm text-muted-foreground">{t("summary.customers", { defaultValue: "Customers" })}</div>
                <div className="mt-2 text-2xl font-semibold">{data.customer_count}</div>
              </article>
              <article className="rounded-2xl border border-border/70 bg-background/60 p-4">
                <div className="text-sm text-muted-foreground">{t("summary.avgRevenue", { defaultValue: "Avg Revenue / Customer" })}</div>
                <div className="mt-2 text-2xl font-semibold">{formatTWD(data.avg_revenue_per_customer)}</div>
              </article>
              <article className="rounded-2xl border border-border/70 bg-background/60 p-4">
                <div className="text-sm text-muted-foreground">{t("summary.avgOrders", { defaultValue: "Avg Orders / Customer" })}</div>
                <div className="mt-2 text-2xl font-semibold">{Number(data.avg_order_count_per_customer).toFixed(2)}</div>
              </article>
              <article className="rounded-2xl border border-border/70 bg-background/60 p-4">
                <div className="text-sm text-muted-foreground">{t("summary.avgCategories", { defaultValue: "Avg Categories / Customer" })}</div>
                <div className="mt-2 text-2xl font-semibold">{Number(data.avg_categories_per_customer).toFixed(2)}</div>
              </article>
            </div>

            {data.customer_count === 0 && data.top_categories.length === 0 && data.cross_sell_opportunities.length === 0 ? (
              <SurfaceMessage>
                {t("empty", { defaultValue: "No qualifying customer buying behavior for this segment yet." })}
              </SurfaceMessage>
            ) : null}

            <div className="grid gap-4 xl:grid-cols-2">
              <div className="space-y-2 rounded-2xl border border-border/70 bg-background/60 p-4">
                <div className="text-sm font-semibold">{t("topCategoriesTitle", { defaultValue: "Top Categories" })}</div>
                {data.top_categories.length === 0 ? (
                  <SurfaceMessage>
                    {t("emptyTopCategories", { defaultValue: "No category evidence yet." })}
                  </SurfaceMessage>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>{t("table.category", { defaultValue: "Category" })}</TableHead>
                        <TableHead className="text-right">{t("table.revenue", { defaultValue: "Revenue" })}</TableHead>
                        <TableHead className="text-right">{t("table.share", { defaultValue: "Share" })}</TableHead>
                        <TableHead className="text-right">{t("table.customers", { defaultValue: "Customers" })}</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.top_categories.map((category) => (
                        <TableRow key={category.category} data-testid="customer-buying-category-row">
                          <TableCell className="font-medium">{category.category}</TableCell>
                          <TableCell className="text-right">{formatTWD(category.revenue)}</TableCell>
                          <TableCell className="text-right">{formatPercent(category.revenue_share)}</TableCell>
                          <TableCell className="text-right">{category.customer_count}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </div>

              <div className="space-y-2 rounded-2xl border border-border/70 bg-background/60 p-4">
                <div className="text-sm font-semibold">{t("crossSellTitle", { defaultValue: "Cross-Sell Opportunities" })}</div>
                {data.cross_sell_opportunities.length === 0 ? (
                  <SurfaceMessage>
                    {t("emptyCrossSell", { defaultValue: "No cross-sell opportunities meet the support threshold yet." })}
                  </SurfaceMessage>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>{t("table.anchor", { defaultValue: "Anchor" })}</TableHead>
                        <TableHead>{t("table.recommended", { defaultValue: "Recommended" })}</TableHead>
                        <TableHead className="text-right">{t("table.shared", { defaultValue: "Shared" })}</TableHead>
                        <TableHead className="text-right">{t("table.segmentPenetration", { defaultValue: "Segment" })}</TableHead>
                        <TableHead className="text-right">{t("table.lift", { defaultValue: "Lift" })}</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.cross_sell_opportunities.map((opportunity) => (
                        <TableRow key={`${opportunity.anchor_category}-${opportunity.recommended_category}`} data-testid="customer-buying-cross-sell-row">
                          <TableCell className="font-medium">{opportunity.anchor_category}</TableCell>
                          <TableCell>{opportunity.recommended_category}</TableCell>
                          <TableCell className="text-right">{opportunity.shared_customer_count}</TableCell>
                          <TableCell className="text-right">{formatPercent(opportunity.segment_penetration)}</TableCell>
                          <TableCell className="text-right">{formatLift(opportunity.lift_score)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </div>
            </div>

            <div className="space-y-2 rounded-2xl border border-border/70 bg-background/60 p-4">
              <div className="text-sm font-semibold">{t("patternsTitle", { defaultValue: "Buying Patterns" })}</div>
              <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-4">
                {data.buying_patterns.map((pattern) => (
                  <article key={pattern.month_start} className="rounded-2xl border border-border/60 bg-background/70 p-3">
                    <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{pattern.month_start}</div>
                    <div className="mt-2 text-lg font-semibold">{formatTWD(pattern.revenue)}</div>
                    <div className="mt-2 text-sm text-muted-foreground">
                      {t("pattern.orders", { count: pattern.order_count, defaultValue: `${pattern.order_count} orders` })}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {t("pattern.customers", { count: pattern.customer_count, defaultValue: `${pattern.customer_count} customers` })}
                    </div>
                  </article>
                ))}
              </div>
            </div>
          </>
        ) : null}
      </div>
    </SectionCard>
  );
}