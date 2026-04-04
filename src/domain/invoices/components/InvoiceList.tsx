/** Paginated invoice list with payment status columns, filter, and sort. */

import { useState } from "react";

import { DataTable, DataTableToolbar, type DataTableSortState } from "../../../components/layout/DataTable";
import { Badge } from "../../../components/ui/badge";
import { useInvoices, paymentStatusBadgeVariant, paymentStatusLabel } from "../hooks/useInvoices";

interface InvoiceListProps {
  onSelect: (invoiceId: string) => void;
}

const PAYMENT_STATUS_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "", label: "All" },
  { value: "unpaid", label: "Unpaid" },
  { value: "partial", label: "Partial" },
  { value: "paid", label: "Paid" },
  { value: "overdue", label: "Overdue" },
];

export function InvoiceList({ onSelect }: InvoiceListProps) {
  const [statusFilter, setStatusFilter] = useState("");
  const [sortState, setSortState] = useState<DataTableSortState>({
    columnId: "outstanding_balance",
    direction: "desc",
  });

  const { items, total, page, pageSize, loading, error, reload } = useInvoices({
    payment_status: statusFilter || undefined,
    sort_by: sortState.columnId,
    sort_order: sortState.direction,
  });

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
                <Badge variant={paymentStatusBadgeVariant(item.payment_status)} className="normal-case tracking-normal">
                  {paymentStatusLabel(item.payment_status)}
                </Badge>
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
            <label className="flex flex-col items-start gap-2 text-sm font-medium text-foreground sm:flex-row sm:items-center sm:gap-3">
              <span>Payment Status:</span>
              <select
                id="inv-payment-status"
                aria-label="Payment Status:"
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
                className="w-full sm:w-44"
              >
                {PAYMENT_STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
          </DataTableToolbar>
        )}
        summary={items.length > 0 ? `Showing ${items.length} invoices on this page.` : undefined}
        page={page}
        pageSize={pageSize}
        totalItems={total}
        onPageChange={(nextPage) => {
          void reload(nextPage);
        }}
        sortState={sortState}
        onSortChange={setSortState}
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
