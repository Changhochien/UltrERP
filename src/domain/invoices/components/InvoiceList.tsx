/** Paginated invoice list with payment status columns, filter, and sort. */

import { useCallback, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { DataTable, DataTableToolbar, type DataTableSortState } from "../../../components/layout/DataTable";
import { Badge } from "../../../components/ui/badge";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { ActiveFilterBar } from "../../../components/filters/ActiveFilterBar";
import { CustomerCombobox } from "../../../components/customers/CustomerCombobox";
import type { CustomerSummary } from "../../customers/types";
import { DateRangeFilter } from "../../../components/filters/DateRangeFilter";
import { SearchInput } from "../../../components/filters/SearchInput";
import { StatusMultiSelect } from "../../../components/filters/StatusMultiSelect";
import { useInvoices, paymentStatusLabel } from "../hooks/useInvoices";

interface InvoiceListProps {
  onSelect: (invoiceId: string) => void;
}

const PAYMENT_STATUS_OPTIONS = [
  { value: "unpaid", label: "Unpaid" },
  { value: "partial", label: "Partial" },
  { value: "paid", label: "Paid" },
  { value: "overdue", label: "Overdue" },
];

export function InvoiceList({ onSelect }: InvoiceListProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [customerSummaries, setCustomerSummaries] = useState<CustomerSummary[]>([]);
  const sortableColumns = ["invoice_date", "outstanding_balance", "created_at"] as const;

  // Derive filter state from URL params
  const statusValues = searchParams.getAll("payment_status") as string[];
  const customerId = searchParams.get("customer_id") ?? "";
  const dateFrom = searchParams.get("date_from") ?? "";
  const dateTo = searchParams.get("date_to") ?? "";
  const search = searchParams.get("search") ?? "";
  const sortBy = sortableColumns.includes(searchParams.get("sort_by") as (typeof sortableColumns)[number])
    ? (searchParams.get("sort_by") as (typeof sortableColumns)[number])
    : undefined;
  const sortOrder = (searchParams.get("sort_order") as "asc" | "desc" | null) ?? "desc";

  // Build sort state for DataTable
  const sortState: DataTableSortState | null = sortBy
    ? {
        columnId: sortBy,
        direction: sortOrder,
      }
    : null;

  // Build active filter list for ActiveFilterBar
  const activeFilters: { key: string; label: string }[] = [
    ...statusValues.map((v) => ({
      key: `payment_status:${v}`,
      label: `${PAYMENT_STATUS_OPTIONS.find((o) => o.value === v)?.label ?? v}`,
    })),
    ...(customerId
      ? [
          {
            key: "customer_id",
            label: `Customer: ${customerSummaries.find((customer) => customer.id === customerId)?.company_name ?? customerId}`,
          },
        ]
      : []),
    ...(dateFrom ? [{ key: "date_from", label: `From: ${dateFrom}` }] : []),
    ...(dateTo ? [{ key: "date_to", label: `To: ${dateTo}` }] : []),
    ...(search ? [{ key: "search", label: `Search: ${search}` }] : []),
  ];

  const { items, total, page, pageSize, loading, error, reload } = useInvoices({
    customer_id: customerId || undefined,
    payment_status: statusValues.length > 0 ? statusValues : undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    search: search || undefined,
    sort_by: sortBy,
    sort_order: sortBy ? sortOrder : undefined,
  });

  function updateParam(key: string, value: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) {
        next.set(key, value);
      } else {
        next.delete(key);
      }
      return next;
    });
  }

  function updateStatusParam(values: string[]) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete("payment_status");
      values.forEach((v) => next.append("payment_status", v));
      return next;
    });
  }

  function dismissFilter(key: string) {
    if (key.startsWith("payment_status:")) {
      const value = key.replace("payment_status:", "");
      updateStatusParam(statusValues.filter((v) => v !== value));
    } else if (key === "customer_id") {
      updateParam("customer_id", "");
    } else if (key === "date_from") {
      updateParam("date_from", "");
    } else if (key === "date_to") {
      updateParam("date_to", "");
    } else if (key === "search") {
      updateParam("search", "");
    }
  }

  function clearAllFilters() {
    setSearchParams(() => new URLSearchParams());
  }

  const handleSortChange = useCallback(
    (newSortState: DataTableSortState | null) => {
      if (!newSortState) {
        setSearchParams((prev) => {
          const next = new URLSearchParams(prev);
          next.delete("sort_by");
          next.delete("sort_order");
          return next;
        });
        return;
      }

      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set("sort_by", newSortState.columnId);
        next.set("sort_order", newSortState.direction);
        return next;
      });
    },
    [],
  );

  return (
    <section aria-label="Invoice list">
      <DataTable
        columns={[
          {
            id: "invoice_number",
            header: "Invoice #",
            sortable: true,
            cell: (item) => <span className="font-medium">{item.invoice_number}</span>,
          },
          {
            id: "invoice_date",
            header: "Date",
            sortable: true,
            cell: (item) => item.invoice_date,
          },
          {
            id: "total_amount",
            header: "Total",
            cell: (item) => `${item.currency_code} ${item.total_amount}`,
          },
          {
            id: "amount_paid",
            header: "Paid",
            cell: (item) => `${item.currency_code} ${item.amount_paid}`,
          },
          {
            id: "outstanding_balance",
            header: "Outstanding",
            sortable: true,
            cell: (item) => `${item.currency_code} ${item.outstanding_balance}`,
          },
          {
            id: "payment_status",
            header: "Status",
            cell: (item) => (
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={item.payment_status} label={paymentStatusLabel(item.payment_status)} />
                {item.payment_status === "overdue" && item.days_overdue > 0 ? (
                  <Badge variant="destructive" className="normal-case tracking-normal">
                    {item.days_overdue}d
                  </Badge>
                ) : null}
              </div>
            ),
          },
        ]}
        data={items}
        loading={loading}
        error={error}
        emptyTitle="No invoices found."
        emptyDescription="Adjust the payment filter or try again later."
        toolbar={(
          <DataTableToolbar>
            <div className="space-y-1">
              <h2 className="text-lg font-semibold tracking-tight">Invoices</h2>
              <p className="text-sm text-muted-foreground">Browse invoice status and payment progress.</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <SearchInput
                value={search}
                onChange={(v) => updateParam("search", v)}
                placeholder="Search invoice #…"
              />
              <CustomerCombobox
                value={customerId}
                onChange={(id) => updateParam("customer_id", id)}
                onClear={() => updateParam("customer_id", "")}
                onCustomersLoaded={setCustomerSummaries}
              />
              <DateRangeFilter
                dateFrom={dateFrom}
                dateTo={dateTo}
                onDateFromChange={(v) => updateParam("date_from", v)}
                onDateToChange={(v) => updateParam("date_to", v)}
              />
              <StatusMultiSelect
                options={PAYMENT_STATUS_OPTIONS}
                selected={statusValues}
                onChange={updateStatusParam}
              />
            </div>
          </DataTableToolbar>
        )}
        filterBar={
          activeFilters.length > 0 ? (
            <ActiveFilterBar
              filters={activeFilters}
              onDismiss={dismissFilter}
              onClearAll={clearAllFilters}
            />
          ) : undefined
        }
        summary={items.length > 0 ? `Showing ${items.length} invoices on this page.` : undefined}
        page={page}
        pageSize={pageSize}
        totalItems={total}
        onPageChange={(nextPage) => {
          void reload(nextPage);
        }}
        sortState={sortState}
        onSortChange={handleSortChange}
        getRowId={(item) => item.id}
        rowLabel={(item) => `Invoice ${item.invoice_number}`}
        onRowClick={(item) => onSelect(item.id)}
        getRowClassName={(item) =>
          item.payment_status === "overdue"
            ? "border-l-4 border-destructive bg-destructive/5 hover:bg-destructive/10"
            : undefined
        }
      />
    </section>
  );
}
