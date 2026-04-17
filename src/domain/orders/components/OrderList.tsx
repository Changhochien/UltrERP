/** Paginated order list with multi-filter, search, sort, and URL sync. */

import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { useState } from "react";

import { ActiveFilterBar } from "../../../components/filters/ActiveFilterBar";
import { CustomerCombobox } from "../../../components/customers/CustomerCombobox";
import type { CustomerSummary } from "../../customers/types";
import { DataTable, DataTableToolbar, type DataTableSortState } from "../../../components/layout/DataTable";
import { DateRangeFilter } from "../../../components/filters/DateRangeFilter";
import { SearchInput } from "../../../components/filters/SearchInput";
import { StatusMultiSelect } from "../../../components/filters/StatusMultiSelect";
import { Badge } from "../../../components/ui/badge";
import { useOrders, statusBadgeVariant, statusLabel } from "../hooks/useOrders";
import type { OrderStatus } from "../types";

interface OrderListProps {
  onSelect: (orderId: string) => void;
}

const STATUS_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "pending", label: "Pending" },
  { value: "confirmed", label: "Confirmed" },
  { value: "shipped", label: "Shipped" },
  { value: "fulfilled", label: "Fulfilled" },
  { value: "cancelled", label: "Cancelled" },
];

const SORTABLE_COLUMNS = ["created_at", "order_number", "total_amount", "status"] as const;

export function OrderList({ onSelect }: OrderListProps) {
  const { t } = useTranslation("common");
  const [searchParams, setSearchParams] = useSearchParams();
  const [customerSummaries, setCustomerSummaries] = useState<CustomerSummary[]>([]);

  // ── Derive filter state from URL ─────────────────────────────────────────
  const statusValues = searchParams.getAll("status") as OrderStatus[];
  const customerId = searchParams.get("customer_id") ?? "";
  const dateFrom = searchParams.get("date_from") ?? "";
  const dateTo = searchParams.get("date_to") ?? "";
  const search = searchParams.get("search") ?? "";
  const sortBy = SORTABLE_COLUMNS.includes(searchParams.get("sort_by") as typeof SORTABLE_COLUMNS[number])
    ? (searchParams.get("sort_by") as typeof SORTABLE_COLUMNS[number])
    : undefined;
  const sortOrder = searchParams.get("sort_order") === "asc" ? "asc" : "desc";

  // ── URL mutation helpers ────────────────────────────────────────────────
  function setStatus(values: string[]) {
    const next = new URLSearchParams(searchParams);
    next.delete("status");
    values.forEach((v) => next.append("status", v));
    setSearchParams(next);
  }

  function setCustomer(id: string) {
    const next = new URLSearchParams(searchParams);
    if (id) next.set("customer_id", id);
    else next.delete("customer_id");
    setSearchParams(next);
  }

  function setDateFrom(val: string) {
    const next = new URLSearchParams(searchParams);
    if (val) next.set("date_from", val);
    else next.delete("date_from");
    setSearchParams(next);
  }

  function setDateTo(val: string) {
    const next = new URLSearchParams(searchParams);
    if (val) next.set("date_to", val);
    else next.delete("date_to");
    setSearchParams(next);
  }

  function setSearch(val: string) {
    const next = new URLSearchParams(searchParams);
    if (val) next.set("search", val);
    else next.delete("search");
    setSearchParams(next);
  }

  function setSort(by: typeof SORTABLE_COLUMNS[number], order: "asc" | "desc") {
    const next = new URLSearchParams(searchParams);
    next.set("sort_by", by);
    next.set("sort_order", order);
    setSearchParams(next);
  }

  function removeFilter(id: string) {
    const next = new URLSearchParams(searchParams);
    if (id === "status") {
      next.delete("status");
    } else {
      next.delete(id);
    }
    setSearchParams(next);
  }

  function clearAll() {
    setSearchParams(new URLSearchParams());
  }

  // ── Sort state for DataTable ────────────────────────────────────────────
  const sortState: DataTableSortState = {
    columnId: sortBy ?? "created_at",
    direction: sortOrder,
  };

  function handleSortChange(next: DataTableSortState) {
    if (next.columnId === sortBy && next.direction === sortOrder) return;
    setSort(next.columnId as typeof SORTABLE_COLUMNS[number], next.direction);
  }

  // ── Active filter chips ─────────────────────────────────────────────────
  const activeFilters: Array<{ key: string; label: string }> = [];
  if (statusValues.length > 0) {
    activeFilters.push({
      key: "status",
      label:
        statusValues.length === 1
          ? `Status: ${STATUS_OPTIONS.find((o) => o.value === statusValues[0])?.label ?? statusValues[0]}`
          : `Status: ${statusValues.length} selected`,
    });
  }
  if (customerId) activeFilters.push({
    key: "customer_id",
    label: `Customer: ${customerSummaries.find((c) => c.id === customerId)?.company_name ?? customerId}`,
  });
  if (dateFrom) activeFilters.push({ key: "date_from", label: `From: ${dateFrom}` });
  if (dateTo) activeFilters.push({ key: "date_to", label: `To: ${dateTo}` });
  if (search) activeFilters.push({ key: "search", label: `Search: ${search}` });
  if (sortBy) activeFilters.push({ key: "sort_by", label: `Sort: ${sortBy} ${sortOrder}` });

  // ── Data fetch ──────────────────────────────────────────────────────────
  const { items, total, page, pageSize, loading, error, reload } = useOrders({
    status: statusValues.length > 0 ? statusValues : undefined,
    customerId: customerId || undefined,
    dateFrom,
    dateTo,
    search,
    sortBy: sortBy ?? "created_at",
    sortOrder,
  });

  return (
    <section aria-label="Order list">
      <DataTable
        columns={[
          {
            id: "order_number",
            header: t("orders.list.orderNumber"),
            sortable: true,
            getSortValue: (item) => item.order_number,
            cell: (item) => <span className="font-medium">{item.order_number}</span>,
          },
          {
            id: "status",
            header: t("orders.list.status"),
            sortable: true,
            getSortValue: (item) => item.status,
            cell: (item) => (
              <Badge variant={statusBadgeVariant(item.status)} className="normal-case tracking-normal">
                {statusLabel(item.status)}
              </Badge>
            ),
          },
          {
            id: "total_amount",
            header: t("orders.list.total"),
            sortable: true,
            getSortValue: (item) => Number(item.total_amount),
            cell: (item) => `$${item.total_amount}`,
          },
          {
            id: "created_at",
            header: t("orders.list.created"),
            sortable: true,
            getSortValue: (item) => new Date(item.created_at).getTime(),
            cell: (item) => new Date(item.created_at).toLocaleDateString(),
          },
        ]}
        data={items}
        loading={loading}
        error={error}
        emptyTitle={t("orders.list.noOrders")}
        emptyDescription={t("orders.list.adjustFilter")}
        toolbar={(
          <DataTableToolbar>
            <div className="space-y-1">
              <h2 className="text-lg font-semibold tracking-tight">{t("orders.list.title")}</h2>
              <p className="text-sm text-muted-foreground">{t("orders.list.description")}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <StatusMultiSelect
                options={STATUS_OPTIONS}
                selected={statusValues}
                onChange={setStatus}
              />
              <CustomerCombobox
                value={customerId}
                onChange={setCustomer}
                onClear={() => setCustomer("")}
                onCustomersLoaded={setCustomerSummaries}
                placeholder="Filter by customer…"
                searchPlaceholder="Search customer by name or BAN…"
              />
              <SearchInput
                value={search}
                onChange={setSearch}
                placeholder="Search order number…"
              />
              <DateRangeFilter
                dateFrom={dateFrom}
                dateTo={dateTo}
                onDateFromChange={setDateFrom}
                onDateToChange={setDateTo}
              />
            </div>
          </DataTableToolbar>
        )}
        summary={
          activeFilters.length > 0 ? (
            <ActiveFilterBar
              filters={activeFilters}
              onDismiss={removeFilter}
              onClearAll={clearAll}
            />
          ) : undefined
        }
        page={page}
        pageSize={pageSize}
        totalItems={total}
        onPageChange={(nextPage) => {
          void reload(nextPage);
        }}
        sortState={sortState}
        onSortChange={handleSortChange}
        getRowId={(item) => item.id}
        rowLabel={(item) => `Order ${item.order_number}`}
        onRowClick={(item) => onSelect(item.id)}
      />
    </section>
  );
}
