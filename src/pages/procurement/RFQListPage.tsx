/** RFQ list page - sourcing workspace entry. */

import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { PageHeader, SectionCard } from "../../components/layout/PageLayout";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { useRFQList } from "../../domain/procurement/hooks/useRFQ";
import { RFQ_LIST_ROUTE, RFQ_CREATE_ROUTE } from "../../lib/routes";
import type { RFQStatus } from "../../domain/procurement/types";

const STATUS_OPTIONS: (RFQStatus | "")[] = [
  "",
  "draft",
  "submitted",
  "closed",
  "cancelled",
];

export function RFQListPage() {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  const [statusFilter, setStatusFilter] = useState<RFQStatus | "">(
    (searchParams.get("status") as RFQStatus) ?? "",
  );
  const [page, setPage] = useState(Number(searchParams.get("page") ?? 1));

  const { data, loading, error } = useRFQList({
    q: query || undefined,
    status: statusFilter || undefined,
    page,
  });

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
