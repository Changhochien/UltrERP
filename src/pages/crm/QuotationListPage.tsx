import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import QuotationDetailPage from "./QuotationDetailPage";
import QuotationResultsTable from "@/domain/crm/components/QuotationResultsTable";
import { PageHeader, SectionCard } from "../../components/layout/PageLayout";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import type { QuotationListResponse, QuotationStatus } from "../../domain/crm/types";
import { usePermissions } from "../../hooks/usePermissions";
import { listQuotations } from "../../lib/api/crm";
import {
  buildQuotationDetailPath,
  CRM_QUOTATION_CREATE_ROUTE,
  CRM_QUOTATIONS_ROUTE,
} from "../../lib/routes";

const STATUS_OPTIONS: QuotationStatus[] = [
  "draft",
  "open",
  "replied",
  "partially_ordered",
  "ordered",
  "lost",
  "cancelled",
  "expired",
];

export function QuotationListPage() {
  const { quotationId } = useParams<{ quotationId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation("crm");
const { t: tRoutes } = useTranslation("routes");
  const { canWrite } = usePermissions();
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<QuotationStatus | "">("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<QuotationListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listQuotations({
      q: query || undefined,
      status: statusFilter || undefined,
      page,
      page_size: 50,
    })
      .then((response) => {
        if (!cancelled) {
          setData(response);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : t("quotations.listPage.loadError"));
          setData({
            items: [],
            page,
            page_size: 50,
            total_count: 0,
            total_pages: 1,
          });
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [page, query, statusFilter, t]);

  const activeFilterCount = useMemo(
    () => Number(Boolean(query)) + Number(Boolean(statusFilter)),
    [query, statusFilter],
  );

  if (quotationId) {
    return <QuotationDetailPage onBack={() => navigate(CRM_QUOTATIONS_ROUTE)} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[{ label: tRoutes("crmQuotations.label") }]}
        eyebrow={t("quotations.listPage.eyebrow")}
        title={t("quotations.listPage.title")}
        description={t("quotations.listPage.description")}
        actions={canWrite("crm") ? (
          <Button type="button" onClick={() => navigate(CRM_QUOTATION_CREATE_ROUTE)}>
            {t("quotations.listPage.createQuotation")}
          </Button>
        ) : null}
      />

      <SectionCard title={t("quotations.listPage.registryTitle")} description={t("quotations.listPage.registryDescription")}>
        <div className="space-y-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <label className="flex flex-col gap-2 text-sm font-medium text-foreground">
              <span>{t("quotations.listPage.searchLabel")}</span>
              <Input
                aria-label={t("quotations.listPage.searchLabel")}
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setPage(1);
                }}
                placeholder={t("quotations.listPage.searchPlaceholder")}
              />
            </label>
            <label className="flex flex-col gap-2 text-sm font-medium text-foreground">
              <span>{t("quotations.listPage.statusLabel")}</span>
              <select
                aria-label={t("quotations.listPage.statusLabel")}
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 lg:w-52"
                value={statusFilter}
                onChange={(event) => {
                  setStatusFilter(event.target.value as QuotationStatus | "");
                  setPage(1);
                }}
              >
                <option value="">{t("quotations.listPage.allStatuses")}</option>
                {STATUS_OPTIONS.map((status) => (
                  <option key={status} value={status}>{t(`crm.quotations.statusValues.${status}`)}</option>
                ))}
              </select>
            </label>
          </div>

          {activeFilterCount > 0 ? (
            <div className="flex flex-col gap-3 rounded-xl border border-border/70 bg-muted/20 px-3 py-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm text-muted-foreground">
                  {t("quotations.listPage.activeFilters", { count: activeFilterCount })}
                </span>
                {query ? <Badge variant="outline">{t("quotations.listPage.searchBadge", { query })}</Badge> : null}
                {statusFilter ? (
                  <Badge variant="outline">{t("quotations.listPage.statusBadge", { status: t(`crm.quotations.statusValues.${statusFilter}`) })}</Badge>
                ) : null}
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setQuery("");
                  setStatusFilter("");
                  setPage(1);
                }}
              >
                {t("quotations.listPage.clearFilters")}
              </Button>
            </div>
          ) : null}

          {data ? (
            <QuotationResultsTable
              items={data.items}
              page={data.page}
              pageSize={data.page_size}
              totalCount={data.total_count}
              onPageChange={setPage}
              onSelect={(id) => navigate(buildQuotationDetailPath(id))}
            />
          ) : null}

          {loading && !data ? <p>{t("quotations.listPage.loading")}</p> : null}
          {error && !loading ? <p className="text-sm text-muted-foreground">{error}</p> : null}
        </div>
      </SectionCard>
    </div>
  );
}

export default QuotationListPage;