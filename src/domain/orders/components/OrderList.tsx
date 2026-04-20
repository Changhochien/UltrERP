/** Paginated order list with multi-filter, search, sort, and URL sync. */

import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { useState } from "react";

import { ActiveFilterBar } from "../../../components/filters/ActiveFilterBar";
import { CustomerCombobox } from "../../../components/customers/CustomerCombobox";
import type { CustomerSummary } from "../../customers/types";
import { DataTableToolbar, type DataTableSortState } from "../../../components/layout/DataTable";
import { DateRangeFilter } from "../../../components/filters/DateRangeFilter";
import { SearchInput } from "../../../components/filters/SearchInput";
import { StatusMultiSelect } from "../../../components/filters/StatusMultiSelect";
import { TanStackDataTable } from "../../../components/layout/TanStackDataTable";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { useOrders, statusBadgeVariant, statusLabel } from "../hooks/useOrders";
import type { OrderBillingStatus, OrderStatus, OrderWorkflowView } from "../types";
import { BILLING_STATUS_META, COMMERCIAL_STATUS_META, FULFILLMENT_STATUS_META, RESERVATION_STATUS_META } from "../workflowMeta";

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

const VIEW_OPTIONS: Array<{ value: OrderWorkflowView; labelKey: string }> = [
  { value: "pending_intake", labelKey: "orders.list.pendingIntake" },
  { value: "ready_to_ship", labelKey: "orders.list.readyToShipView" },
  { value: "shipped_not_completed", labelKey: "orders.list.shippedNotCompleted" },
  { value: "invoiced_not_paid", labelKey: "orders.list.invoicedNotPaid" },
];

function billingMeta(status: OrderBillingStatus | null | undefined) {
  return BILLING_STATUS_META[status ?? "not_invoiced"];
}

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
  const workflowView = (searchParams.get("view") ?? "") as OrderWorkflowView | "";
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

  function setWorkflowView(value: OrderWorkflowView | "") {
    const next = new URLSearchParams(searchParams);
    if (value) next.set("view", value);
    else next.delete("view");
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
    } else if (id === "sort_by") {
      next.delete("sort_by");
      next.delete("sort_order");
    } else {
      next.delete(id);
    }
    setSearchParams(next);
  }

  function clearAll() {
    setSearchParams(new URLSearchParams());
  }

  // ── Sort state for DataTable ────────────────────────────────────────────
  const sortState = sortBy
    ? {
        columnId: sortBy,
        direction: sortOrder,
      }
    : null;

  function handleSortChange(next: DataTableSortState | null) {
    if (!next) {
      const current = new URLSearchParams(searchParams);
      current.delete("sort_by");
      current.delete("sort_order");
      setSearchParams(current);
      return;
    }

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
  if (workflowView) activeFilters.push({
    key: "view",
    label: `View: ${t(VIEW_OPTIONS.find((option) => option.value === workflowView)?.labelKey ?? workflowView)}`,
  });
  if (sortBy) activeFilters.push({ key: "sort_by", label: `Sort: ${sortBy} ${sortOrder}` });

  // ── Data fetch ──────────────────────────────────────────────────────────
  const { items, total, page, pageSize, loading, error, reload } = useOrders({
    status: statusValues.length > 0 ? statusValues : undefined,
    workflowView: workflowView || undefined,
    customerId: customerId || undefined,
    dateFrom,
    dateTo,
    search,
    sortBy,
    sortOrder: sortBy ? sortOrder : undefined,
  });

  return (
    <section aria-label="Order list">
      <TanStackDataTable
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
              <div className="space-y-2">
                <Badge variant={statusBadgeVariant(item.status)} className="normal-case tracking-normal">
                  {statusLabel(item.status)}
                </Badge>
                <Badge
                  variant={COMMERCIAL_STATUS_META[item.execution.commercial_status].variant}
                  className="normal-case tracking-normal"
                >
                  {t(COMMERCIAL_STATUS_META[item.execution.commercial_status].labelKey)}
                </Badge>
              </div>
            ),
          },
          {
            id: "fulfillment",
            header: t("orders.list.fulfillment"),
            cell: (item) => (
              <div className="flex flex-wrap gap-2">
                <Badge
                  variant={FULFILLMENT_STATUS_META[item.execution.fulfillment_status].variant}
                  className="normal-case tracking-normal"
                >
                  {t(FULFILLMENT_STATUS_META[item.execution.fulfillment_status].labelKey)}
                </Badge>
                <Badge
                  variant={RESERVATION_STATUS_META[item.execution.reservation_status].variant}
                  className="normal-case tracking-normal"
                >
                  {t(RESERVATION_STATUS_META[item.execution.reservation_status].labelKey)}
                </Badge>
                {item.execution.has_backorder ? (
                  <Badge variant="warning" className="normal-case tracking-normal">
                    {t(
                      item.execution.backorder_line_count === 1
                        ? "orders.list.backorderLines_one"
                        : "orders.list.backorderLines_other",
                      { count: item.execution.backorder_line_count },
                    )}
                  </Badge>
                ) : null}
              </div>
            ),
          },
          {
            id: "billing",
            header: t("orders.list.billing"),
            cell: (item) => {
              const paymentMeta = billingMeta(item.invoice_payment_status);
              return (
                <div className="space-y-2">
                  <div className="text-sm font-medium text-foreground">
                    {item.invoice_number ?? t("orders.list.invoiceOnConfirmation")}
                  </div>
                  <Badge variant={paymentMeta.variant} className="normal-case tracking-normal">
                    {t(paymentMeta.labelKey)}
                  </Badge>
                </div>
              );
            },
          },
          {
            id: "total_amount",
            header: t("orders.list.total"),
            sortable: true,
            getSortValue: (item) => Number(item.total_amount),
            cell: (item) => `$${item.total_amount}`,
          },
          {
            id: "commission",
            header: t("orders.list.commission"),
            cell: (item) => {
              const salesTeam = item.sales_team ?? [];
              if (salesTeam.length === 0) {
                return <span className="text-sm text-muted-foreground">{t("orders.list.noCommission")}</span>;
              }

              return (
                <div className="space-y-1">
                  <div className="text-sm font-medium text-foreground">${item.total_commission}</div>
                  <div className="text-xs text-muted-foreground">
                    {salesTeam.length === 1
                      ? salesTeam[0].sales_person
                      : t(
                        salesTeam.length === 2
                          ? "orders.list.salesTeamCount_two"
                          : "orders.list.salesTeamCount_other",
                        { count: salesTeam.length },
                      )}
                  </div>
                </div>
              );
            },
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
          <DataTableToolbar className="items-start">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold tracking-tight">{t("orders.list.title")}</h2>
              <p className="text-sm text-muted-foreground">{t("orders.list.description")}</p>
            </div>
            <div className="flex max-w-full flex-col gap-3 md:items-end">
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  type="button"
                  variant={workflowView ? "outline" : "secondary"}
                  onClick={() => setWorkflowView("")}
                >
                  {t("orders.list.allOrders")}
                </Button>
                {VIEW_OPTIONS.map((option) => (
                  <Button
                    key={option.value}
                    type="button"
                    variant={workflowView === option.value ? "secondary" : "outline"}
                    onClick={() => setWorkflowView(option.value)}
                  >
                    {t(option.labelKey)}
                  </Button>
                ))}
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
        stickyHeader
        enableColumnResizing
      />
    </section>
  );
}
