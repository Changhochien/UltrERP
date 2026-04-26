import { useTranslation } from "react-i18next";

import { MetricCard, SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { Badge } from "../../../components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../../components/ui/table";
import { useCustomerProductProfile } from "../hooks/useIntelligence";

interface CustomerProductProfileProps {
  customerId: string;
}

const CONFIDENCE_VARIANTS = {
  high: "success",
  medium: "warning",
  low: "secondary",
} as const;

function formatTWD(value: string): string {
  return `NT$ ${Number(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatPercent(value: string): string {
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(`${value}T00:00:00Z`).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function metricTrendDirection(trend: "increasing" | "declining" | "stable") {
  if (trend === "increasing") return "up" as const;
  if (trend === "declining") return "down" as const;
  return "flat" as const;
}

export function CustomerProductProfile({ customerId }: CustomerProductProfileProps) {
  const { t } = useTranslation("intelligence", { keyPrefix: "customerProfile" });
  const { data, isLoading, error } = useCustomerProductProfile(customerId);

  if (isLoading) {
    return (
      <SectionCard
        title={t("title", { defaultValue: "Product Profile" })}
        description={t("description", {
          defaultValue: "What this customer buys, how often they order, and which categories are newly active.",
        })}
      >
        <div className="space-y-3" data-testid="customer-product-profile-loading">
          <div className="h-10 rounded-xl bg-muted/60" />
          <div className="h-28 rounded-xl bg-muted/50" />
          <div className="h-44 rounded-xl bg-muted/40" />
        </div>
      </SectionCard>
    );
  }

  if (error) {
    return (
      <SectionCard
        title={t("title", { defaultValue: "Product Profile" })}
        description={t("description", {
          defaultValue: "What this customer buys, how often they order, and which categories are newly active.",
        })}
      >
        <SurfaceMessage tone="danger">
          {t("loadError", { defaultValue: "Failed to load product profile." })}
        </SurfaceMessage>
      </SectionCard>
    );
  }

  if (!data) return null;

  const maxCategoryRevenue = Math.max(
    ...data.top_categories.map((category) => Number(category.revenue)),
    0,
  );
  const frequencyLabel = t(`trend.${data.frequency_trend}`, { defaultValue: data.frequency_trend });
  const aovLabel = t(`trend.${data.aov_trend}`, { defaultValue: data.aov_trend });

  return (
    <SectionCard
      title={t("title", { defaultValue: "Product Profile" })}
      description={t("description", {
        defaultValue: "What this customer buys, how often they order, and which categories are newly active.",
      })}
    >
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            title={t("totalRevenue12m", { defaultValue: "Revenue (12 months)" })}
            value={formatTWD(data.total_revenue_12m)}
            description={t("activityBasis", {
              defaultValue: "Based on confirmed, shipped, and fulfilled orders.",
            })}
          />
          <MetricCard
            title={t("orders12m", { defaultValue: "Orders (12 months)" })}
            value={String(data.order_count_12m)}
            description={t("frequencyTrend", { defaultValue: "Ordering frequency trend" })}
            trendLabel={frequencyLabel}
            trendDirection={metricTrendDirection(data.frequency_trend)}
          />
          <MetricCard
            title={t("averageOrderValue", { defaultValue: "Average Order Value" })}
            value={formatTWD(data.avg_order_value)}
            description={t("aovTrend", { defaultValue: "Average order value trend" })}
            trendLabel={aovLabel}
            trendDirection={metricTrendDirection(data.aov_trend)}
          />
          <MetricCard
            title={t("lastOrder", { defaultValue: "Last Order" })}
            value={formatDate(data.last_order_date)}
            description={
              data.days_since_last_order == null
                ? t("noOrdersYet", { defaultValue: "No qualifying orders yet" })
                : t("daysSinceLastOrder", {
                    count: data.days_since_last_order,
                    defaultValue: `${data.days_since_last_order} days since last order`,
                  })
            }
            badge={
              data.is_dormant ? (
                <Badge variant="destructive">
                  {t("dormant", { defaultValue: "Dormant" })}
                </Badge>
              ) : undefined
            }
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <Badge variant={CONFIDENCE_VARIANTS[data.confidence]}>
            {t(`confidence.${data.confidence}`, { defaultValue: data.confidence })}
          </Badge>
          <span>
            {t("activityBasis", {
              defaultValue: "Based on confirmed, shipped, and fulfilled orders.",
            })}
          </span>
        </div>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
          <div className="rounded-2xl border border-border/70 bg-background/60 p-4">
            <div className="mb-4 space-y-1">
              <h3 className="text-lg font-semibold">
                {t("topCategories", { defaultValue: "Top Categories" })}
              </h3>
              <p className="text-sm text-muted-foreground">
                {t("topCategoriesDescription", {
                  defaultValue: "Revenue mix across the last 12 months.",
                })}
              </p>
            </div>

            {data.top_categories.length === 0 ? (
              <SurfaceMessage>
                {t("noCategoryData", { defaultValue: "No category activity yet." })}
              </SurfaceMessage>
            ) : (
              <div className="space-y-4">
                {data.top_categories.map((category) => {
                  const width = maxCategoryRevenue > 0
                    ? `${(Number(category.revenue) / maxCategoryRevenue) * 100}%`
                    : "0%";
                  const isNewCategory = data.new_categories.includes(category.category);

                  return (
                    <div key={category.category} className="space-y-2">
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-foreground">{category.category}</span>
                          {isNewCategory ? (
                            <Badge variant="success">
                              {t("new", { defaultValue: "New" })}
                            </Badge>
                          ) : null}
                        </div>
                        <span className="text-sm text-muted-foreground">{formatTWD(category.revenue)}</span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-muted/60">
                        <div className="h-full rounded-full bg-primary" style={{ width }} />
                      </div>
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>
                          {category.order_count} {t("orders", { defaultValue: "Orders" }).toLowerCase()}
                        </span>
                        <span>{formatPercent(category.revenue_pct_of_total)}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-border/70 bg-background/60 p-4">
            <div className="mb-4 space-y-1">
              <h3 className="text-lg font-semibold">
                {t("topProducts", { defaultValue: "Top Products" })}
              </h3>
              <p className="text-sm text-muted-foreground">
                {t("topProductsDescription", {
                  defaultValue: "Products ranked by order count in the last 12 months.",
                })}
              </p>
            </div>

            {data.top_products.length === 0 ? (
              <SurfaceMessage>
                {t("noProductData", { defaultValue: "No product activity yet." })}
              </SurfaceMessage>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("product", { defaultValue: "Product" })}</TableHead>
                    <TableHead>{t("category", { defaultValue: "Category" })}</TableHead>
                    <TableHead className="text-right">{t("orders", { defaultValue: "Orders" })}</TableHead>
                    <TableHead className="text-right">{t("revenue", { defaultValue: "Revenue" })}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.top_products.map((product) => (
                    <TableRow key={product.product_id}>
                      <TableCell className="font-medium">{product.product_name}</TableCell>
                      <TableCell>{product.category ?? "—"}</TableCell>
                      <TableCell className="text-right">{product.order_count}</TableCell>
                      <TableCell className="text-right">{formatTWD(product.total_revenue)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </div>
      </div>
    </SectionCard>
  );
}