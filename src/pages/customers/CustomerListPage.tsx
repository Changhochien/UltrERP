/** Browse / search customers page. */

import { useCallback, useEffect, useState } from "react";
import type { CustomerListResponse } from "../../domain/customers/types";
import { listCustomers } from "../../lib/api/customers";
import { CustomerDetailDialog } from "../../components/customers/CustomerDetailDialog";
import { EditCustomerDialog } from "../../components/customers/EditCustomerDialog";
import { CustomerResultsTable } from "../../components/customers/CustomerResultsTable";
import { CustomerSearchBar } from "../../components/customers/CustomerSearchBar";

export function CustomerListPage() {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<CustomerListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listCustomers({
      q: query || undefined,
      status: statusFilter || undefined,
      page,
    }).then((resp) => {
      if (!cancelled) {
        setData(resp);
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

  return (
    <div>
      <h2>Customers</h2>
      <div style={{ display: "flex", gap: "1rem", alignItems: "center", marginBottom: "1rem" }}>
        <CustomerSearchBar onSearch={handleSearch} />
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          aria-label="Filter by status"
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="suspended">Suspended</option>
        </select>
      </div>
      {loading && !data ? (
        <p>Loading…</p>
      ) : data ? (
        <CustomerResultsTable
          items={data.items}
          page={data.page}
          totalPages={data.total_pages}
          onPageChange={setPage}
          onSelect={setSelectedId}
        />
      ) : null}
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
