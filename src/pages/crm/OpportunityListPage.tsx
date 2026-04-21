import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import OpportunityDetailPage from "./OpportunityDetailPage";
import OpportunityPipelineSummary from "../../components/crm/OpportunityPipelineSummary";
import OpportunityResultsTable from "../../components/crm/OpportunityResultsTable";
import { PageHeader, SectionCard } from "../../components/layout/PageLayout";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import type { OpportunityListResponse, OpportunityStatus } from "../../domain/crm/types";
import { usePermissions } from "../../hooks/usePermissions";
import { listOpportunities } from "../../lib/api/crm";
import {
  buildOpportunityDetailPath,
  CRM_OPPORTUNITIES_ROUTE,
  CRM_OPPORTUNITY_CREATE_ROUTE,
} from "../../lib/routes";

const STATUS_OPTIONS: OpportunityStatus[] = [
  "open",
  "replied",
  "quotation",
  "converted",
  "closed",
  "lost",
];

export function OpportunityListPage() {
  const { opportunityId } = useParams<{ opportunityId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation("common");
  const { canWrite } = usePermissions();
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<OpportunityStatus | "">("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<OpportunityListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listOpportunities({
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
          setError(err instanceof Error ? err.message : t("crm.opportunities.listPage.loadError"));
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

  if (opportunityId) {
    return <OpportunityDetailPage onBack={() => navigate(CRM_OPPORTUNITIES_ROUTE)} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[{ label: t("routes.crmOpportunities.label") }]}
        eyebrow={t("crm.opportunities.listPage.eyebrow")}
        title={t("crm.opportunities.listPage.title")}
        description={t("crm.opportunities.listPage.description")}
        actions={canWrite("crm") ? (
          <Button type="button" onClick={() => navigate(CRM_OPPORTUNITY_CREATE_ROUTE)}>
            {t("crm.opportunities.listPage.createOpportunity")}
          </Button>
        ) : null}
      />

      <SectionCard title={t("crm.opportunities.listPage.pipelineTitle")} description={t("crm.opportunities.listPage.pipelineDescription")}>
        <OpportunityPipelineSummary items={data?.items ?? []} />
      </SectionCard>

      <SectionCard title={t("crm.opportunities.listPage.registryTitle")} description={t("crm.opportunities.listPage.registryDescription")}>
        <div className="space-y-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <label className="flex flex-col gap-2 text-sm font-medium text-foreground">
              <span>{t("crm.opportunities.listPage.searchLabel")}</span>
              <Input
                aria-label={t("crm.opportunities.listPage.searchLabel")}
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setPage(1);
                }}
                placeholder={t("crm.opportunities.listPage.searchPlaceholder")}
              />
            </label>
            <label className="flex flex-col gap-2 text-sm font-medium text-foreground">
              <span>{t("crm.opportunities.listPage.statusLabel")}</span>
              <select
                aria-label={t("crm.opportunities.listPage.statusLabel")}
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 lg:w-52"
                value={statusFilter}
                onChange={(event) => {
                  setStatusFilter(event.target.value as OpportunityStatus | "");
                  setPage(1);
                }}
              >
                <option value="">{t("crm.opportunities.listPage.allStatuses")}</option>
                {STATUS_OPTIONS.map((status) => (
                  <option key={status} value={status}>{t(`crm.opportunities.statusValues.${status}`)}</option>
                ))}
              </select>
            </label>
          </div>

          {activeFilterCount > 0 ? (
            <div className="flex flex-col gap-3 rounded-xl border border-border/70 bg-muted/20 px-3 py-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm text-muted-foreground">
                  {t("crm.opportunities.listPage.activeFilters", { count: activeFilterCount })}
                </span>
                {query ? <Badge variant="outline">{t("crm.opportunities.listPage.searchBadge", { query })}</Badge> : null}
                {statusFilter ? (
                  <Badge variant="outline">{t("crm.opportunities.listPage.statusBadge", { status: t(`crm.opportunities.statusValues.${statusFilter}`) })}</Badge>
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
                {t("crm.opportunities.listPage.clearFilters")}
              </Button>
            </div>
          ) : null}

          {data ? (
            <OpportunityResultsTable
              items={data.items}
              page={data.page}
              pageSize={data.page_size}
              totalCount={data.total_count}
              onPageChange={setPage}
              onSelect={(id) => navigate(buildOpportunityDetailPath(id))}
            />
          ) : null}

          {loading && !data ? <p>{t("crm.opportunities.listPage.loading")}</p> : null}
          {error && !loading ? <p className="text-sm text-muted-foreground">{error}</p> : null}
        </div>
      </SectionCard>
    </div>
  );
}

export default OpportunityListPage;