/** Supplier order list with status filtering. */

import { useState } from "react";

import { DataTable, DataTableToolbar } from "../../../components/layout/DataTable";
import { SectionCard } from "../../../components/layout/PageLayout";
import { Button } from "../../../components/ui/button";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import {
  useSupplierOrders,
  statusLabel,
} from "../hooks/useSupplierOrders";
import type { SupplierOrderStatus } from "../types";

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "All statuses" },
  { value: "pending", label: "Pending" },
  { value: "confirmed", label: "Confirmed" },
  { value: "shipped", label: "Shipped" },
  { value: "partially_received", label: "Partially Received" },
  { value: "received", label: "Received" },
  { value: "cancelled", label: "Cancelled" },
];

interface SupplierOrderListProps {
  onSelect: (orderId: string) => void;
  onCreateNew: () => void;
}

export function SupplierOrderList({
  onSelect,
  onCreateNew,
}: SupplierOrderListProps) {
  const [statusFilter, setStatusFilter] = useState("");

  const { items, total, loading, error, reload } = useSupplierOrders({
    status: statusFilter || undefined,
  });

  return (
    <SectionCard
      title="Supplier Orders"
      description="Track supplier purchase orders, shipment progress, and expected arrival timing."
      actions={(
        <Button type="button" onClick={onCreateNew}>
          New Order
        </Button>
      )}
    >
      <DataTable
        columns={[
          {
            id: "order_number",
            header: "Order #",
            sortable: true,
            getSortValue: (order) => order.order_number,
            cell: (order) => <span className="font-mono text-sm">{order.order_number}</span>,
          },
          {
            id: "supplier_name",
            header: "Supplier",
            sortable: true,
            getSortValue: (order) => order.supplier_name,
            cell: (order) => <span className="font-medium">{order.supplier_name}</span>,
          },
          {
            id: "status",
            header: "Status",
            sortable: true,
            getSortValue: (order) => order.status,
            cell: (order) => (
              <StatusBadge status={order.status} label={statusLabel(order.status as SupplierOrderStatus)} />
            ),
          },
          {
            id: "order_date",
            header: "Order Date",
            sortable: true,
            getSortValue: (order) => order.order_date,
            cell: (order) => new Date(order.order_date).toLocaleDateString(),
          },
          {
            id: "expected_arrival_date",
            header: "Expected Arrival",
            sortable: true,
            getSortValue: (order) => order.expected_arrival_date ?? "",
            cell: (order) => order.expected_arrival_date
              ? new Date(order.expected_arrival_date).toLocaleDateString()
              : "—",
          },
          {
            id: "line_count",
            header: "Lines",
            sortable: true,
            getSortValue: (order) => order.line_count,
            cell: (order) => order.line_count,
          },
          {
            id: "actions",
            header: "Action",
            cell: (order) => (
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={(event) => {
                  event.stopPropagation();
                  onSelect(order.id);
                }}
                aria-label={`View order ${order.order_number}`}
              >
                View
              </Button>
            ),
          },
        ]}
        data={items}
        loading={loading}
        error={error}
        emptyTitle="No supplier orders found."
        emptyDescription="Create a new supplier order or broaden the status filter."
        toolbar={(
          <DataTableToolbar>
            <div className="text-sm text-muted-foreground">
              {items.length > 0 ? `Showing ${items.length} of ${total} orders` : "Filter supplier orders by operational status."}
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <label className="flex flex-col items-start gap-2 text-sm font-medium text-foreground sm:flex-row sm:items-center sm:gap-3">
                <span>Status</span>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  aria-label="Filter by order status"
                  className="w-full sm:w-48"
                >
                  {STATUS_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <Button type="button" variant="outline" className="w-full sm:w-auto" onClick={() => void reload()}>
                Refresh
              </Button>
            </div>
          </DataTableToolbar>
        )}
        getRowId={(order) => order.id}
        rowLabel={(order) => `Supplier order ${order.order_number}`}
        onRowClick={(order) => onSelect(order.id)}
      />
    </SectionCard>
  );
}
