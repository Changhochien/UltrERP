/** Supplier order detail with status update and receive actions. */

import { useState } from "react";

import { DataTable } from "../../../components/layout/DataTable";
import { SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import {
  useSupplierOrderDetail,
  useUpdateOrderStatus,
  useReceiveOrder,
  statusLabel,
} from "../hooks/useSupplierOrders";
import type { SupplierOrderStatus } from "../types";

const NEXT_STATUSES: Partial<
  Record<SupplierOrderStatus, SupplierOrderStatus[]>
> = {
  pending: ["confirmed", "cancelled"],
  confirmed: ["shipped", "cancelled"],
  shipped: ["cancelled"],
};

interface SupplierOrderDetailProps {
  orderId: string;
  onBack: () => void;
}

export function SupplierOrderDetail({
  orderId,
  onBack,
}: SupplierOrderDetailProps) {
  const { order, loading, error, reload } = useSupplierOrderDetail(orderId);
  const {
    updateStatus,
    submitting: statusSubmitting,
    error: statusError,
  } = useUpdateOrderStatus();
  const {
    receive,
    submitting: receiveSubmitting,
    error: receiveError,
  } = useReceiveOrder();

  const [receiveQty, setReceiveQty] = useState<Record<string, number>>({});
  const [showReceive, setShowReceive] = useState(false);

  if (loading) return <div aria-busy="true">Loading order…</div>;
  if (error)
    return (
      <div role="alert" className="space-y-3">
        <p className="text-sm text-destructive">Error: {error}</p>
        <Button type="button" variant="outline" onClick={onBack}>
          Back to list
        </Button>
      </div>
    );
  if (!order) return null;

  const status = order.status as SupplierOrderStatus;
  const allowedNext = NEXT_STATUSES[status] ?? [];
  const canReceive =
    status === "shipped" || status === "partially_received";

  const handleStatusChange = async (newStatus: SupplierOrderStatus) => {
    const result = await updateStatus(orderId, { status: newStatus });
    if (result) void reload();
  };

  const handleReceive = async () => {
    // Build received_quantities: { line_id: qty }
    const quantities: Record<string, number> = {};
    for (const line of order.lines) {
      const qty = receiveQty[line.id] ?? 0;
      if (qty > 0) quantities[line.id] = qty;
    }
    if (Object.keys(quantities).length === 0) return;

    const result = await receive(orderId, {
      received_quantities: quantities,
    });
    if (result) {
      setShowReceive(false);
      setReceiveQty({});
      void reload();
    }
  };

  return (
    <section aria-label={`Order ${order.order_number}`} className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <Button type="button" variant="outline" onClick={onBack}>
            Back
          </Button>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-xl font-semibold tracking-tight">Order {order.order_number}</h2>
            <StatusBadge status={status} label={statusLabel(status)} />
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {allowedNext.map((nextStatus) => (
            <Button
              key={nextStatus}
              type="button"
              variant="outline"
              onClick={() => void handleStatusChange(nextStatus)}
              disabled={statusSubmitting}
            >
              {statusLabel(nextStatus)}
            </Button>
          ))}
          {canReceive && !showReceive ? (
            <Button type="button" onClick={() => setShowReceive(true)}>
              Record Receipt
            </Button>
          ) : null}
        </div>
      </div>

      {statusError || receiveError ? (
        <SurfaceMessage tone="danger" className="max-w-3xl" role="alert">
          {statusError || receiveError}
        </SurfaceMessage>
      ) : null}

      <SectionCard title="Order Summary" description="Supplier, lifecycle dates, and current receiving posture.">
        <dl className="gap-y-4">
          <dt>Supplier</dt>
          <dd>{order.supplier_name}</dd>
          <dt>Order Date</dt>
          <dd>{new Date(order.order_date).toLocaleDateString()}</dd>
          <dt>Expected Arrival</dt>
          <dd>
            {order.expected_arrival_date
              ? new Date(order.expected_arrival_date).toLocaleDateString()
              : "—"}
          </dd>
          <dt>Created</dt>
          <dd>{new Date(order.created_at).toLocaleString()}</dd>
        </dl>
      </SectionCard>

      <SectionCard
        title="Line Items"
        description={showReceive ? "Enter received quantities for each remaining line." : "Ordered, received, and remaining quantities by line."}
      >
        <DataTable
          columns={[
            {
              id: "product_id",
              header: "Product",
              sortable: true,
              getSortValue: (line) => line.product_id,
              cell: (line) => <span className="font-mono text-sm">{line.product_id.slice(0, 8)}…</span>,
            },
            {
              id: "warehouse_id",
              header: "Warehouse",
              sortable: true,
              getSortValue: (line) => line.warehouse_id,
              cell: (line) => <span className="font-mono text-sm">{line.warehouse_id.slice(0, 8)}…</span>,
            },
            {
              id: "quantity_ordered",
              header: "Ordered",
              sortable: true,
              getSortValue: (line) => line.quantity_ordered,
              className: "text-right",
              headerClassName: "text-right",
              cell: (line) => line.quantity_ordered,
            },
            {
              id: "quantity_received",
              header: "Received",
              sortable: true,
              getSortValue: (line) => line.quantity_received,
              className: "text-right",
              headerClassName: "text-right",
              cell: (line) => line.quantity_received,
            },
            {
              id: "remaining",
              header: "Remaining",
              sortable: true,
              getSortValue: (line) => line.quantity_ordered - line.quantity_received,
              className: "text-right",
              headerClassName: "text-right",
              cell: (line) => {
                const remaining = line.quantity_ordered - line.quantity_received;
                return (
                  <span className={remaining > 0 ? "font-semibold text-warning-token" : "font-semibold text-success-token"}>
                    {remaining}
                  </span>
                );
              },
            },
            ...(showReceive
              ? [
                  {
                    id: "receive_now",
                    header: "Receive Now",
                    className: "text-right",
                    headerClassName: "text-right",
                    cell: (line: (typeof order.lines)[number]) => {
                      const remaining = line.quantity_ordered - line.quantity_received;
                      return (
                        <Input
                          type="number"
                          min={0}
                          max={remaining}
                          value={receiveQty[line.id] ?? 0}
                          onChange={(event) =>
                            setReceiveQty((prev) => ({
                              ...prev,
                              [line.id]: Number(event.target.value),
                            }))
                          }
                          aria-label={`Receive quantity for line ${line.product_id.slice(0, 8)}`}
                          disabled={remaining === 0}
                          className="ml-auto w-24"
                        />
                      );
                    },
                  },
                ]
              : []),
          ]}
          data={order.lines}
          emptyTitle="No line items found."
          emptyDescription="Supplier order lines will appear here once the order is populated."
          getRowId={(line) => line.id}
        />

        {showReceive ? (
          <div className="mt-4 flex flex-wrap gap-3">
            <Button
              type="button"
              onClick={() => void handleReceive()}
              disabled={
                receiveSubmitting
                || Object.values(receiveQty).every((qty) => !qty || qty <= 0)
              }
            >
              {receiveSubmitting ? "Processing…" : "Confirm Receipt"}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setShowReceive(false);
                setReceiveQty({});
              }}
            >
              Cancel
            </Button>
          </div>
        ) : null}
      </SectionCard>
    </section>
  );
}
