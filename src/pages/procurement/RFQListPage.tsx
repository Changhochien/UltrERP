/** RFQ list page - sourcing workspace entry. */

import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { PageHeader, SectionCard } from "../../components/layout/PageLayout";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { useRFQList } from "../../domain/procurement/hooks/useRFQ";
import {
  getProcurementSummary,
  getQuoteTurnaroundStats,
  getSupplierPerformanceStats,
} from "../../lib/api/procurement";
import { RFQ_LIST_ROUTE, RFQ_CREATE_ROUTE } from "../../lib/routes";
import type {
  ProcurementSummary,
  QuoteTurnaroundStats,
  RFQStatus,
  SupplierPerformanceStats,
} from "../../domain/procurement/types";

const STATUS_OPTIONS: (RFQStatus | "")[] = [
  "",
  "draft",
  "submitted",
  "closed",
  "cancelled",
];

function formatMetric(value: number): string {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value);
}

function formatNullableMetric(value: number | null): string {
  return value == null ? "—" : formatMetric(value);
}

function formatPercent(value: number): string {
  return `${formatMetric(value)}%`;
}

function InsightTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-background p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>
    </div>
  );
}

export function RFQListPage() {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  const [statusFilter, setStatusFilter] = useState<RFQStatus | "">(
    (searchParams.get("status") as RFQStatus) ?? "",
  );
  const [page, setPage] = useState(Number(searchParams.get("page") ?? 1));
  const [summary, setSummary] = useState<ProcurementSummary | null>(null);
  const [turnaroundStats, setTurnaroundStats] = useState<QuoteTurnaroundStats | null>(null);
  const [supplierPerformance, setSupplierPerformance] = useState<SupplierPerformanceStats | null>(null);
  const [insightsLoading, setInsightsLoading] = useState(true);
  const [insightsError, setInsightsError] = useState<string | null>(null);

  const { data, loading, error } = useRFQList({
    q: query || undefined,
    status: statusFilter || undefined,
    page,
  });

  useEffect(() => {
    let isActive = true;

    setInsightsLoading(true);
    setInsightsError(null);

    Promise.all([
      getProcurementSummary(),
      getQuoteTurnaroundStats(),
      getSupplierPerformanceStats(),
    ])
      .then(([nextSummary, nextTurnaroundStats, nextSupplierPerformance]) => {
        if (!isActive) {
          return;
        }
        setSummary(nextSummary);
        setTurnaroundStats(nextTurnaroundStats);
        setSupplierPerformance(nextSupplierPerformance);
      })
      .catch((err) => {
        if (!isActive) {
          return;
        }
        setInsightsError(
          err instanceof Error ? err.message : t("procurement.reporting.loadError"),
        );
      })
      .finally(() => {
        if (isActive) {
          setInsightsLoading(false);
        }
      });

    return () => {
      isActive = false;
    };
  }, [t]);

  function applyFilters(q: string, status: RFQStatus | "", p: number) {
    const params: Record<string, string> = {};
    if (q) params.q = q;
    if (status) params.status = status;
    if (p > 1) params.page = String(p);
    setSearchParams(params, { replace: true });
    setQuery(q);
    setStatusFilter(status);
    setPage(p);
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    applyFilters(query, statusFilter, 1);
  }

  const topSuppliers = [...(supplierPerformance?.by_supplier ?? [])]
    .sort((left, right) => {
      if (right.total_quotes !== left.total_quotes) {
        return right.total_quotes - left.total_quotes;
      }
      return right.award_rate - left.award_rate;
    })
    .slice(0, 3);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <PageHeader
          title={t("procurement.rfq.title")}
          description={t("procurement.rfq.description")}
        />
        <Button onClick={() => navigate(RFQ_CREATE_ROUTE)}>
          {t("procurement.rfq.create")}
        </Button>
      </div>

      <SectionCard>
        <div className="space-y-6">
          <div>
            <h2 className="text-lg font-semibold">{t("procurement.reporting.title")}</h2>
            <p className="text-sm text-muted-foreground">{t("procurement.reporting.description")}</p>
            {summary ? (
              <p className="mt-1 text-xs text-muted-foreground">
                {summary.period.from} - {summary.period.to}
              </p>
            ) : null}
          </div>

          {insightsLoading ? (
            <p className="text-muted-foreground">{t("common.status.loading")}</p>
          ) : insightsError ? (
            <p className="text-destructive">{insightsError}</p>
          ) : summary && turnaroundStats && supplierPerformance ? (
            <div className="space-y-6">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <InsightTile
                  label={t("procurement.reporting.rfqsSubmitted")}
                  value={`${formatMetric(summary.rfqs.submitted)} / ${formatMetric(summary.rfqs.total)}`}
                />
                <InsightTile
                  label={t("procurement.reporting.quotationsSubmitted")}
                  value={`${formatMetric(summary.supplier_quotations.submitted)} / ${formatMetric(summary.supplier_quotations.total)}`}
                />
                <InsightTile
                  label={t("procurement.reporting.activePurchaseOrders")}
                  value={`${formatMetric(summary.purchase_orders.active)} / ${formatMetric(summary.purchase_orders.total)}`}
                />
                <InsightTile
                  label={t("procurement.reporting.blockedWarnedSuppliers")}
                  value={`${formatMetric(summary.supplier_controls.blocked_suppliers)} / ${formatMetric(summary.supplier_controls.warned_suppliers)}`}
                />
              </div>

              <div className="grid gap-4 xl:grid-cols-2">
                <div className="rounded-lg border bg-background p-4 space-y-4">
                  <div>
                    <h3 className="font-semibold">{t("procurement.reporting.quoteTurnaround")}</h3>
                    <p className="text-sm text-muted-foreground">
                      {t("procurement.reporting.quotesAnalysed")}: {formatMetric(turnaroundStats.total_quotes)}
                    </p>
                  </div>

                  {turnaroundStats.total_quotes === 0 ? (
                    <p className="text-sm text-muted-foreground">{t("procurement.reporting.noQuoteData")}</p>
                  ) : (
                    <div className="grid gap-4 sm:grid-cols-3">
                      <InsightTile
                        label={t("procurement.reporting.averageResponseTime")}
                        value={formatNullableMetric(turnaroundStats.avg_turnaround_days)}
                      />
                      <InsightTile
                        label={t("procurement.reporting.fastestResponse")}
                        value={formatNullableMetric(turnaroundStats.min_turnaround_days)}
                      />
                      <InsightTile
                        label={t("procurement.reporting.slowestResponse")}
                        value={formatNullableMetric(turnaroundStats.max_turnaround_days)}
                      />
                    </div>
                  )}
                </div>

                <div className="rounded-lg border bg-background p-4 space-y-4">
                  <div>
                    <h3 className="font-semibold">{t("procurement.reporting.supplierPerformance")}</h3>
                    <p className="text-sm text-muted-foreground">
                      {t("procurement.reporting.topSuppliers")}
                    </p>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    <InsightTile
                      label={t("procurement.reporting.overallAwardRate")}
                      value={formatPercent(supplierPerformance.overall.award_rate)}
                    />
                    <InsightTile
                      label={t("procurement.reporting.awardedQuotes")}
                      value={`${formatMetric(supplierPerformance.overall.awarded_quotes)} / ${formatMetric(supplierPerformance.overall.total_quotes)}`}
                    />
                    <InsightTile
                      label={t("procurement.reporting.monitoredSuppliers")}
                      value={formatMetric(supplierPerformance.supplier_controls.total_suppliers)}
                    />
                    <InsightTile
                      label={t("procurement.reporting.blockedSuppliers")}
                      value={formatMetric(supplierPerformance.supplier_controls.blocked_count)}
                    />
                  </div>

                  {topSuppliers.length === 0 ? (
                    <p className="text-sm text-muted-foreground">{t("procurement.reporting.noSupplierData")}</p>
                  ) : (
                    <div className="overflow-x-auto rounded-md border">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b text-left text-muted-foreground">
                            <th className="px-3 py-2 font-medium">{t("procurement.reporting.supplier")}</th>
                            <th className="px-3 py-2 font-medium">{t("procurement.reporting.totalQuotes")}</th>
                            <th className="px-3 py-2 font-medium">{t("procurement.reporting.awardRate")}</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {topSuppliers.map((supplier) => (
                            <tr key={supplier.supplier_id ?? supplier.supplier_name}>
                              <td className="px-3 py-2 font-medium">{supplier.supplier_name}</td>
                              <td className="px-3 py-2">{formatMetric(supplier.total_quotes)}</td>
                              <td className="px-3 py-2">{formatPercent(supplier.award_rate)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </SectionCard>

      <form onSubmit={handleSearch} className="flex gap-3 flex-wrap">
        <Input
          placeholder={t("procurement.rfq.searchPlaceholder")}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="max-w-xs"
        />
        <select
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
          value={statusFilter}
          onChange={(e) => applyFilters(query, e.target.value as RFQStatus | "", 1)}
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s || "all"} value={s}>
              {s ? t(`procurement.rfq.status.${s}`) : t("common.filters.allStatuses")}
            </option>
          ))}
        </select>
        <Button type="submit" variant="outline">
          {t("common.actions.search")}
        </Button>
      </form>

      {loading && <p className="text-muted-foreground">{t("common.status.loading")}</p>}
      {error && (
        <p className="text-destructive">{error}</p>
      )}

      {data && (
        <SectionCard>
          {data.items.length === 0 ? (
            <p className="text-muted-foreground py-8 text-center">
              {t("procurement.rfq.empty")}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-2 font-medium">{t("procurement.rfq.fields.name")}</th>
                    <th className="pb-2 font-medium">{t("procurement.rfq.fields.status")}</th>
                    <th className="pb-2 font-medium">{t("procurement.rfq.fields.company")}</th>
                    <th className="pb-2 font-medium">{t("procurement.rfq.fields.transactionDate")}</th>
                    <th className="pb-2 font-medium">{t("procurement.rfq.fields.suppliers")}</th>
                    <th className="pb-2 font-medium">{t("procurement.rfq.fields.quotesReceived")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data.items.map((rfq) => (
                    <tr
                      key={rfq.id}
                      className="cursor-pointer hover:bg-muted/40"
                      onClick={() => navigate(`${RFQ_LIST_ROUTE}/${rfq.id}`)}
                    >
                      <td className="py-3 font-medium">{rfq.name}</td>
                      <td className="py-3">
                        <StatusBadge status={rfq.status} />
                      </td>
                      <td className="py-3">{rfq.company || "—"}</td>
                      <td className="py-3">{rfq.transaction_date}</td>
                      <td className="py-3">{rfq.supplier_count}</td>
                      <td className="py-3">
                        {rfq.quotes_received > 0 ? (
                          <span className="text-emerald-600 font-medium">
                            {rfq.quotes_received}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">0</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {data && data.pages > 1 && (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                {t("common.pagination.pageInfo", {
                  page: data.page,
                  pages: data.pages,
                  total: data.total,
                })}
              </p>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page <= 1}
                  onClick={() => applyFilters(query, statusFilter, page - 1)}
                >
                  {t("common.pagination.previous")}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page >= data.pages}
                  onClick={() => applyFilters(query, statusFilter, page + 1)}
                >
                  {t("common.pagination.next")}
                </Button>
              </div>
            </div>
          )}
        </SectionCard>
      )}
    </div>
  );
}
