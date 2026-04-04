/** Paginated order list with status filter. */

import { useState } from "react";

import { DataTable, DataTableToolbar } from "../../../components/layout/DataTable";
import { Badge } from "../../../components/ui/badge";
import { useOrders, statusBadgeVariant, statusLabel } from "../hooks/useOrders";

interface OrderListProps {
  onSelect: (orderId: string) => void;
}

const STATUS_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "", label: "All statuses" },
  { value: "pending", label: "Pending" },
  { value: "confirmed", label: "Confirmed" },
  { value: "shipped", label: "Shipped" },
  { value: "fulfilled", label: "Fulfilled" },
  { value: "cancelled", label: "Cancelled" },
];

export function OrderList({ onSelect }: OrderListProps) {
  const [statusFilter, setStatusFilter] = useState("");
  const { items, total, page, pageSize, loading, error, reload } = useOrders({
    status: statusFilter || undefined,
  });

  return (
    <section aria-label="Order list">
      <DataTable
        columns={[
          {
            id: "order_number",
            header: "Order #",
            sortable: true,
            getSortValue: (item) => item.order_number,
            cell: (item) => <span className="font-medium">{item.order_number}</span>,
          },
          {
            id: "status",
            header: "Status",
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
            header: "Total",
            sortable: true,
            getSortValue: (item) => Number(item.total_amount),
            cell: (item) => `$${item.total_amount}`,
          },
          {
            id: "created_at",
            header: "Created",
            sortable: true,
            getSortValue: (item) => new Date(item.created_at).getTime(),
            cell: (item) => new Date(item.created_at).toLocaleDateString(),
          },
        ]}
        data={items}
        loading={loading}
        error={error}
        emptyTitle="No orders found."
        emptyDescription="Adjust the status filter or create a new order."
        toolbar={(
          <DataTableToolbar>
            <div className="space-y-1">
              <h2 className="text-lg font-semibold tracking-tight">Orders</h2>
              <p className="text-sm text-muted-foreground">Current order pipeline and fulfillment status.</p>
            </div>
            <label className="flex flex-col items-start gap-2 text-sm font-medium text-foreground sm:flex-row sm:items-center sm:gap-3">
              <span>Status:</span>
              <select
                id="ol-status"
                aria-label="Status:"
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
                className="w-full sm:w-44"
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
          </DataTableToolbar>
        )}
        page={page}
        pageSize={pageSize}
        totalItems={total}
        onPageChange={(nextPage) => {
          void reload(nextPage);
        }}
        getRowId={(item) => item.id}
        rowLabel={(item) => `Order ${item.order_number}`}
        onRowClick={(item) => onSelect(item.id)}
      />
    </section>
  );
}
