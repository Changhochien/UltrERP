/** Browse / search customers page. */

import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { PageHeader, SectionCard } from "../../components/layout/PageLayout";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import type { CustomerListResponse } from "../../domain/customers/types";
import { listCustomers } from "../../lib/api/customers";
import { CustomerDetailDialog } from "@/domain/customers/components/CustomerDetailDialog";
import { EditCustomerDialog } from "@/domain/customers/components/EditCustomerDialog";
import { CustomerResultsTable } from "@/domain/customers/components/CustomerResultsTable";
import { CustomerSearchBar } from "@/domain/customers/components/CustomerSearchBar";
import { CustomerDetailPage } from "./CustomerDetailPage";
import { usePermissions } from "../../hooks/usePermissions";
import { CUSTOMER_CREATE_ROUTE, CUSTOMERS_ROUTE } from "../../lib/routes";

const CUSTOMER_STATUS_OPTIONS = [
  { value: "active", labelKey: "customer.listPage.active" },
  { value: "inactive", labelKey: "customer.listPage.inactive" },
  { value: "suspended", labelKey: "customer.listPage.suspended" },
] as const;

export function CustomerListPage() {
  const { customerId } = useParams<{ customerId: string }>();
  const { t } = useTranslation("common");
const { t: tRoutes } = useTranslation("routes");
  const { canWrite } = usePermissions();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<CustomerListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [filterResetKey, setFilterResetKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listCustomers({
      q: query || undefined,
      status: statusFilter || undefined,
      page,
    })
      .then((resp) => {
        if (!cancelled) {
          setData(resp);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load customers");
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
  }, [query, statusFilter, page, refreshKey]);

  const handleSearch = useCallback((q: string) => {
    setQuery(q);
    setPage(1);
  }, []);

  const handleCreateCustomer = useCallback(() => {
    if (typeof window === "undefined") {
      return;
    }

    window.location.hash = CUSTOMER_CREATE_ROUTE;
  }, []);

  const handleClearFilters = useCallback(() => {
    setQuery("");
    setStatusFilter("");
    setPage(1);
    setFilterResetKey((value) => value + 1);
  }, []);

  const activeFilterCount = Number(Boolean(query)) + Number(Boolean(statusFilter));
  const hasActiveFilters = activeFilterCount > 0;
  const activeStatusLabel = CUSTOMER_STATUS_OPTIONS.find((option) => option.value === statusFilter)?.labelKey;

  if (customerId) {
    return <CustomerDetailPage onBack={() => navigate(CUSTOMERS_ROUTE)} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[{ label: tRoutes("customers.label") }]}
        eyebrow={t("customer.listPage.eyebrow")}
        title={t("customer.listPage.title")}
        description={t("customer.listPage.description")}
        actions={canWrite("customers") ? (
          <Button type="button" onClick={handleCreateCustomer}>
            {t("customer.listPage.createCustomer")}
          </Button>
        ) : null}
      />

      <SectionCard
        title={t("customer.listPage.customerRegistry")}
        description={t("customer.listPage.customerRegistryDescription")}
      >
        <div className="space-y-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <CustomerSearchBar onSearch={handleSearch} resetSignal={filterResetKey} />
            <label className="flex flex-col items-start gap-2 text-sm font-medium text-foreground sm:flex-row sm:items-center sm:gap-3">
              <span>{t("customer.listPage.status")}</span>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                aria-label="Filter by status"
                className="w-full sm:w-44"
              >
                <option value="">{t("customer.listPage.allStatuses")}</option>
                {CUSTOMER_STATUS_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{t(option.labelKey)}</option>
                ))}
              </select>
            </label>
          </div>

          {(hasActiveFilters || (loading && Boolean(data))) ? (
            <div className="flex flex-col gap-3 rounded-xl border border-border/70 bg-muted/20 px-3 py-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex flex-wrap items-center gap-2">
                {hasActiveFilters ? (
                  <span className="text-sm text-muted-foreground">
                    {t("customer.listPage.activeFilters", { count: activeFilterCount })}
                  </span>
                ) : null}
                {query ? <Badge variant="outline">{t("customer.listPage.search", { query })}</Badge> : null}
                {activeStatusLabel ? <Badge variant="outline">{t("customer.listPage.statusFilter", { status: t(activeStatusLabel) })}</Badge> : null}
                {loading && data ? <span className="text-sm text-muted-foreground">{t("customer.listPage.updating")}</span> : null}
              </div>
              {hasActiveFilters ? (
                <Button type="button" variant="ghost" size="sm" onClick={handleClearFilters}>
                  {t("customer.listPage.clearFilters")}
                </Button>
              ) : null}
            </div>
          ) : null}

          {data ? (
            <CustomerResultsTable
              items={data.items}
              page={data.page}
              pageSize={data.page_size}
              totalCount={data.total_count}
              onPageChange={setPage}
              onSelect={(id) => navigate(`/customers/${id}`)}
            />
          ) : null}

          {loading && !data ? <p>{t("customer.listPage.loading")}</p> : null}
          {error && !loading ? <p className="text-sm text-muted-foreground">{error}</p> : null}
        </div>
      </SectionCard>

      {selectedId && (
        <CustomerDetailDialog
          customerId={selectedId}
          onClose={() => setSelectedId(null)}
          onEdit={() => {
            setEditingId(selectedId);
            setSelectedId(null);
          }}
        />
      )}
      {editingId && (
        <EditCustomerDialog
          customerId={editingId}
          onClose={() => setEditingId(null)}
          onSaved={() => {
            setEditingId(null);
            setRefreshKey((k) => k + 1);
          }}
          onViewCustomer={(id) => {
            setEditingId(null);
            setSelectedId(id);
          }}
        />
      )}
    </div>
  );
}
