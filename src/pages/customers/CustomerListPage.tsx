/** Browse / search customers page. */

import { useCallback, useEffect, useState } from "react";

import { PageHeader, SectionCard } from "../../components/layout/PageLayout";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import type { CustomerListResponse } from "../../domain/customers/types";
import { listCustomers } from "../../lib/api/customers";
import { CustomerDetailDialog } from "../../components/customers/CustomerDetailDialog";
import { EditCustomerDialog } from "../../components/customers/EditCustomerDialog";
import { CustomerResultsTable } from "../../components/customers/CustomerResultsTable";
import { CustomerSearchBar } from "../../components/customers/CustomerSearchBar";
import { usePermissions } from "../../hooks/usePermissions";
import { CUSTOMER_CREATE_ROUTE } from "../../lib/routes";

const CUSTOMER_STATUS_OPTIONS = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
  { value: "suspended", label: "Suspended" },
] as const;

export function CustomerListPage() {
  const { canWrite } = usePermissions();
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
  const activeStatusLabel = CUSTOMER_STATUS_OPTIONS.find((option) => option.value === statusFilter)?.label;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Directory"
        title="Customers"
        description="Search account records, review current status, and drill into individual customer details."
        actions={canWrite("customers") ? (
          <Button type="button" onClick={handleCreateCustomer}>
            Create Customer
          </Button>
        ) : null}
      />

      <SectionCard title="Customer Registry" description="Live customer list with debounced search and status filtering.">
        <div className="space-y-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <CustomerSearchBar onSearch={handleSearch} resetSignal={filterResetKey} />
            <label className="flex flex-col items-start gap-2 text-sm font-medium text-foreground sm:flex-row sm:items-center sm:gap-3">
              <span>Status</span>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                aria-label="Filter by status"
                className="w-full sm:w-44"
              >
                <option value="">All statuses</option>
                {CUSTOMER_STATUS_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </label>
          </div>

          {(hasActiveFilters || (loading && Boolean(data))) ? (
            <div className="flex flex-col gap-3 rounded-xl border border-border/70 bg-muted/20 px-3 py-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex flex-wrap items-center gap-2">
                {hasActiveFilters ? (
                  <span className="text-sm text-muted-foreground">
                    {activeFilterCount} active filter{activeFilterCount === 1 ? "" : "s"} applied
                  </span>
                ) : null}
                {query ? <Badge variant="outline">Search: {query}</Badge> : null}
                {activeStatusLabel ? <Badge variant="outline">Status: {activeStatusLabel}</Badge> : null}
                {loading && data ? <span className="text-sm text-muted-foreground">Updating results…</span> : null}
              </div>
              {hasActiveFilters ? (
                <Button type="button" variant="ghost" size="sm" onClick={handleClearFilters}>
                  Clear filters
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
              onSelect={setSelectedId}
            />
          ) : null}

          {loading && !data ? <p>Loading…</p> : null}
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
