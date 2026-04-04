/** Read-only order detail view with line items and status actions. */

import { useState } from "react";

import { DataTable } from "../../../components/layout/DataTable";
import { SectionCard, SurfaceMessage } from "../../../components/layout/PageLayout";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { useOrderDetail, statusBadgeVariant, statusLabel } from "../hooks/useOrders";
import { updateOrderStatus } from "../../../lib/api/orders";
import type { OrderStatus } from "../types";

interface StatusAction {
  label: string;
  targetStatus: OrderStatus;
  confirmMessage: string;
}

const STATUS_ACTIONS: Record<string, StatusAction[]> = {
  pending: [
    { label: "Confirm Order", targetStatus: "confirmed" as OrderStatus, confirmMessage: "Confirming this order will auto-generate an invoice. Continue?" },
    { label: "Cancel Order", targetStatus: "cancelled" as OrderStatus, confirmMessage: "Are you sure you want to cancel this order?" },
  ],
  confirmed: [
    { label: "Mark Shipped", targetStatus: "shipped" as OrderStatus, confirmMessage: "Mark this order as shipped?" },
  ],
  shipped: [
    { label: "Mark Fulfilled", targetStatus: "fulfilled" as OrderStatus, confirmMessage: "Mark this order as fulfilled?" },
  ],
};

interface OrderDetailProps {
  orderId: string;
  onBack: () => void;
}

export function OrderDetail({ orderId, onBack }: OrderDetailProps) {
  const { order, loading, error, reload } = useOrderDetail(orderId);
  const [updating, setUpdating] = useState(false);
  const [updateError, setUpdateError] = useState<string | null>(null);
  const [activeAction, setActiveAction] = useState<StatusAction | null>(null);

  const handleStatusChange = async (targetStatus: OrderStatus) => {
    setUpdating(true);
    setUpdateError(null);
    const result = await updateOrderStatus(orderId, targetStatus);
    setUpdating(false);
    if (result.ok) {
      setActiveAction(null);
      reload();
    } else {
      setUpdateError(result.error);
    }
  };

  if (loading) return <p aria-busy="true">Loading…</p>;
  if (error) return <div role="alert" className="text-sm text-destructive">{error}</div>;
  if (!order) return <p>Order not found.</p>;

  const actions = STATUS_ACTIONS[order.status] ?? [];

  return (
    <section aria-label="Order detail" className="space-y-5">
      <Button type="button" variant="outline" onClick={onBack}>
        Back to list
      </Button>

      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-2">
          <h2 className="text-xl font-semibold tracking-tight">Order {order.order_number}</h2>
          <Badge variant={statusBadgeVariant(order.status as OrderStatus)} className="normal-case tracking-normal">
            {statusLabel(order.status as OrderStatus)}
          </Badge>
        </div>
        {actions.length > 0 && !activeAction ? (
          <div className="flex flex-wrap gap-2">
            {actions.map((action) => (
              <Button key={action.targetStatus} type="button" onClick={() => setActiveAction(action)}>
                {action.label}
              </Button>
            ))}
          </div>
        ) : null}
      </div>

      {activeAction ? (
        <SectionCard title="Confirm status change" description={activeAction.confirmMessage}>
          <div role="dialog" aria-label="Confirm status change" className="space-y-4">
            {updateError ? <SurfaceMessage tone="danger">{updateError}</SurfaceMessage> : null}
            <div className="flex gap-3">
              <Button type="button" onClick={() => handleStatusChange(activeAction.targetStatus)} disabled={updating}>
                {updating ? "Updating…" : `Yes, ${activeAction.label}`}
              </Button>
              <Button type="button" variant="outline" onClick={() => { setActiveAction(null); setUpdateError(null); }}>
                Cancel
              </Button>
            </div>
          </div>
        </SectionCard>
      ) : null}

      <SectionCard title="Order Summary" description="Customer, pricing, and operational timestamps.">
        <dl className="gap-y-4">
          <dt>Customer</dt>
          <dd>{order.customer_name ?? order.customer_id}</dd>
          <dt>Payment Terms</dt>
          <dd>{order.payment_terms_code} ({order.payment_terms_days} days)</dd>
          <dt>Subtotal</dt>
          <dd>${order.subtotal_amount}</dd>
          <dt>Tax</dt>
          <dd>${order.tax_amount}</dd>
          <dt>Total</dt>
          <dd><strong>${order.total_amount}</strong></dd>
          {order.invoice_id ? (
            <>
              <dt>Invoice</dt>
              <dd>{order.invoice_id}</dd>
            </>
          ) : null}
          {order.notes ? (
            <>
              <dt>Notes</dt>
              <dd>{order.notes}</dd>
            </>
          ) : null}
          <dt>Created</dt>
          <dd>{new Date(order.created_at).toLocaleString()}</dd>
          {order.confirmed_at ? (
            <>
              <dt>Confirmed</dt>
              <dd>{new Date(order.confirmed_at).toLocaleString()}</dd>
            </>
          ) : null}
        </dl>
      </SectionCard>

      <SectionCard title="Line Items" description="Commercial and stock detail for each order line.">
        <DataTable
          columns={[
            { id: "line_number", header: "#", sortable: true, getSortValue: (line) => line.line_number, cell: (line) => line.line_number },
            { id: "description", header: "Description", sortable: true, getSortValue: (line) => line.description, cell: (line) => line.description },
            { id: "quantity", header: "Qty", sortable: true, getSortValue: (line) => Number(line.quantity), cell: (line) => line.quantity },
            { id: "unit_price", header: "Unit Price", sortable: true, getSortValue: (line) => Number(line.unit_price), cell: (line) => `$${line.unit_price}` },
            { id: "tax_amount", header: "Tax", sortable: true, getSortValue: (line) => Number(line.tax_amount), cell: (line) => `$${line.tax_amount}` },
            { id: "subtotal_amount", header: "Subtotal", sortable: true, getSortValue: (line) => Number(line.subtotal_amount), cell: (line) => `$${line.subtotal_amount}` },
            { id: "total_amount", header: "Total", sortable: true, getSortValue: (line) => Number(line.total_amount), cell: (line) => `$${line.total_amount}` },
            {
              id: "stock",
              header: "Stock",
              cell: (line) => (
                <div className="text-sm">
                  {line.available_stock_snapshot != null ? <span>{line.available_stock_snapshot}</span> : null}
                  {line.backorder_note ? <span className="block text-destructive">{line.backorder_note}</span> : null}
                </div>
              ),
            },
          ]}
          data={order.lines}
          emptyTitle="No line items."
          emptyDescription="Order line items will appear here once the order is populated."
          getRowId={(line) => line.id}
        />
      </SectionCard>
    </section>
  );
}
