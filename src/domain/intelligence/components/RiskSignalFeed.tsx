import { useState } from "react";
import { useTranslation } from "react-i18next";

import { SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { useCustomerRiskSignals } from "../hooks/useIntelligence";

const STATUS_VARIANTS = {
  growing: "success",
  at_risk: "destructive",
  dormant: "warning",
  new: "info",
  stable: "secondary",
} as const;

const FILTERS = ["all", "growing", "at_risk", "dormant", "new", "stable"] as const;

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

export function RiskSignalFeed() {
  const { t, i18n } = useTranslation("common", { keyPrefix: "intelligence.riskSignals" });
  const [status, setStatus] = useState<"all" | "growing" | "at_risk" | "dormant" | "new" | "stable">("all");
  const { data, isLoading, error } = useCustomerRiskSignals(status, 50);

  return (
    <SectionCard
      title={t("title", { defaultValue: "Customer Risk Signals" })}
      description={t("description", {
        defaultValue: "A ranked outreach queue across dormant, at-risk, growing, stable, and new accounts.",
      })}
      actions={(
        <div className="flex flex-wrap gap-2" role="group" aria-label="Risk signal filter bar">
          {FILTERS.map((filter) => (
            <Button
              key={filter}
              type="button"
              size="sm"
              variant={status === filter ? "default" : "outline"}
              onClick={() => setStatus(filter)}
              aria-pressed={status === filter}
            >
              {t(`filters.${filter}`, { defaultValue: filter })}
            </Button>
          ))}
        </div>
      )}
    >
      <div className="space-y-4">
        {isLoading ? (
          <div className="space-y-3" data-testid="risk-signal-loading">
            <div className="h-10 rounded-xl bg-muted/60" />
            <div className="h-32 rounded-xl bg-muted/40" />
          </div>
        ) : null}

        {!isLoading && error ? (
          <SurfaceMessage tone="danger">
            {t("loadError", { defaultValue: "Failed to load customer risk signals." })}
          </SurfaceMessage>
        ) : null}

        {!isLoading && !error && data ? (
          <>
            <div className="text-sm text-muted-foreground">
              {t("generatedAt", {
                value: formatGeneratedAt(data.generated_at, i18n.resolvedLanguage ?? i18n.language),
                defaultValue: `Generated ${formatGeneratedAt(data.generated_at, i18n.resolvedLanguage ?? i18n.language)}`,
              })}
            </div>

            {data.customers.length === 0 ? (
              <SurfaceMessage>
                {t("empty", { defaultValue: "No customer risk signals yet." })}
              </SurfaceMessage>
            ) : (
              <div className="max-h-[520px] space-y-3 overflow-y-auto pr-1">
                {data.customers.map((customer) => (
                  <article
                    key={customer.customer_id}
                    data-testid="risk-signal-card"
                    className="rounded-2xl border border-border/70 bg-background/60 p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="space-y-1">
                        <h3 className="text-lg font-semibold">{customer.company_name}</h3>
                        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                          <span>{t("revenueCurrent", { defaultValue: "Current Revenue" })}: {formatTWD(customer.revenue_current)}</span>
                          <span>{t("revenuePrior", { defaultValue: "Prior Revenue" })}: {formatTWD(customer.revenue_prior)}</span>
                          <span>{t("delta", { defaultValue: "Delta" })}: {formatDelta(customer.revenue_delta_pct)}</span>
                        </div>
                      </div>
                      <Badge
                        data-testid={`risk-badge-${customer.status}`}
                        variant={STATUS_VARIANTS[customer.status]}
                      >
                        {t(`status.${customer.status}`, { defaultValue: customer.status })}
                      </Badge>
                    </div>

                    <div className="mt-3 flex flex-wrap gap-4 text-sm text-muted-foreground">
                      {customer.days_since_last_order != null ? (
                        <span>
                          {t("daysSinceLastOrder", {
                            count: customer.days_since_last_order,
                            defaultValue: `${customer.days_since_last_order} days since last order`,
                          })}
                        </span>
                      ) : null}
                      {customer.products_expanded_into.length > 0 ? (
                        <span>
                          {t("expanded", {
                            value: customer.products_expanded_into.join(", "),
                            defaultValue: `Expanded: ${customer.products_expanded_into.join(", ")}`,
                          })}
                        </span>
                      ) : null}
                      {customer.products_contracted_from.length > 0 ? (
                        <span>
                          {t("contracted", {
                            value: customer.products_contracted_from.join(", "),
                            defaultValue: `Contracted: ${customer.products_contracted_from.join(", ")}`,
                          })}
                        </span>
                      ) : null}
                    </div>

                    <div className="mt-3 flex flex-wrap gap-2">
                      {customer.signals.length > 0 ? (
                        customer.signals.map((signal) => (
                          <Badge key={signal} variant="outline">
                            {signal}
                          </Badge>
                        ))
                      ) : (
                        <p className="text-sm text-muted-foreground">
                          {t("noSignals", { defaultValue: "No secondary signals for this account." })}
                        </p>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </>
        ) : null}
      </div>
    </SectionCard>
  );
}