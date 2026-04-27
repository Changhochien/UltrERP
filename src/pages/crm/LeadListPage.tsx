import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import LeadDetailPage from "./LeadDetailPage";
import { LeadResultsTable } from "@/domain/crm/components/LeadResultsTable";
import { PageHeader, SectionCard } from "../../components/layout/PageLayout";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { usePermissions } from "../../hooks/usePermissions";
import { listLeads } from "../../lib/api/crm";
import type { LeadListResponse, LeadStatus } from "../../domain/crm/types";
import {
  buildLeadDetailPath,
  CRM_LEAD_CREATE_ROUTE,
  CRM_LEADS_ROUTE,
} from "../../lib/routes";

const STATUS_OPTIONS: LeadStatus[] = [
  "lead",
  "open",
  "replied",
  "opportunity",
  "quotation",
  "lost_quotation",
  "interested",
  "converted",
  "do_not_contact",
];

export function LeadListPage() {
  const { leadId } = useParams<{ leadId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation("common");
const { t: tRoutes } = useTranslation("routes");
  const { canWrite } = usePermissions();
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<LeadStatus | "">("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<LeadListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listLeads({
      q: query || undefined,
      status: statusFilter || undefined,
      page,
    })
      .then((response) => {
        if (!cancelled) {
          setData(response);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : t("crm.listPage.loadError"));
          setData({
            items: [],
            page,
            page_size: 20,
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

  if (leadId) {
    return <LeadDetailPage onBack={() => navigate(CRM_LEADS_ROUTE)} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[{ label: tRoutes("crmLeads.label") }]}
        eyebrow={t("crm.listPage.eyebrow")}
        title={t("crm.listPage.title")}
        description={t("crm.listPage.description")}
        actions={canWrite("crm") ? (
          <Button type="button" onClick={() => navigate(CRM_LEAD_CREATE_ROUTE)}>
            {t("crm.listPage.createLead")}
          </Button>
        ) : null}
      />

      <SectionCard title={t("crm.listPage.registryTitle")} description={t("crm.listPage.registryDescription")}>
        <div className="space-y-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <label className="flex flex-col gap-2 text-sm font-medium text-foreground">
              <span>{t("crm.listPage.searchLabel")}</span>
              <Input
                aria-label={t("crm.listPage.searchLabel")}
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setPage(1);
                }}
                placeholder={t("crm.listPage.searchPlaceholder")}
              />
            </label>
            <label className="flex flex-col gap-2 text-sm font-medium text-foreground">
              <span>{t("crm.listPage.statusLabel")}</span>
              <select
                aria-label={t("crm.listPage.statusLabel")}
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 lg:w-52"
                value={statusFilter}
                onChange={(event) => {
                  setStatusFilter(event.target.value as LeadStatus | "");
                  setPage(1);
                }}
              >
                <option value="">{t("crm.listPage.allStatuses")}</option>
                {STATUS_OPTIONS.map((status) => (
                  <option key={status} value={status}>{t(`crm.statusValues.${status}`)}</option>
                ))}
              </select>
            </label>
          </div>

          {activeFilterCount > 0 ? (
            <div className="flex flex-col gap-3 rounded-xl border border-border/70 bg-muted/20 px-3 py-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm text-muted-foreground">
                  {t("crm.listPage.activeFilters", { count: activeFilterCount })}
                </span>
                {query ? <Badge variant="outline">{t("crm.listPage.searchBadge", { query })}</Badge> : null}
                {statusFilter ? (
                  <Badge variant="outline">{t("crm.listPage.statusBadge", { status: t(`crm.statusValues.${statusFilter}`) })}</Badge>
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
                {t("crm.listPage.clearFilters")}
              </Button>
            </div>
          ) : null}

          {data ? (
            <LeadResultsTable
              items={data.items}
              page={data.page}
              pageSize={data.page_size}
              totalCount={data.total_count}
              onPageChange={setPage}
              onSelect={(id) => navigate(buildLeadDetailPath(id))}
            />
          ) : null}

          {loading && !data ? <p>{t("crm.listPage.loading")}</p> : null}
          {error && !loading ? <p className="text-sm text-muted-foreground">{error}</p> : null}
        </div>
      </SectionCard>
    </div>
  );
}

export default LeadListPage;
