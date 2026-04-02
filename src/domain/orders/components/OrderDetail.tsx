/** Read-only order detail view with line items and status actions. */

import { useState } from "react";
import { useOrderDetail, statusLabel, statusColor } from "../hooks/useOrders";
import { updateOrderStatus } from "../../../lib/api/orders";
import type { OrderStatus } from "../types";

interface StatusAction {
  label: string;
  targetStatus: string;
  confirmMessage: string;
  color: string;
}

const STATUS_ACTIONS: Record<string, StatusAction[]> = {
  pending: [
    { label: "Confirm Order", targetStatus: "confirmed", confirmMessage: "Confirming this order will auto-generate an invoice. Continue?", color: "#2563eb" },
    { label: "Cancel Order", targetStatus: "cancelled", confirmMessage: "Are you sure you want to cancel this order?", color: "#dc2626" },
  ],
  confirmed: [
    { label: "Mark Shipped", targetStatus: "shipped", confirmMessage: "Mark this order as shipped?", color: "#7c3aed" },
  ],
  shipped: [
    { label: "Mark Fulfilled", targetStatus: "fulfilled", confirmMessage: "Mark this order as fulfilled?", color: "#059669" },
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

  const handleStatusChange = async (targetStatus: string) => {
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
  if (error) return <div role="alert" style={{ color: "#dc2626" }}>{error}</div>;
  if (!order) return <p>Order not found.</p>;

  const actions = STATUS_ACTIONS[order.status] ?? [];

  return (
    <section aria-label="Order detail">
      <button type="button" onClick={onBack} style={{ marginBottom: 12 }}>
        ← Back to list
      </button>

      <h2>Order {order.order_number}</h2>

      {actions.length > 0 && !activeAction && (
        <div style={{ marginBottom: 12, display: "flex", gap: 8 }}>
          {actions.map((action) => (
            <button
              key={action.targetStatus}
              type="button"
              onClick={() => setActiveAction(action)}
              style={{ background: action.color, color: "#fff", padding: "6px 16px", border: "none", borderRadius: 4, cursor: "pointer" }}
            >
              {action.label}
            </button>
          ))}
        </div>
      )}

      {activeAction && (
        <div role="dialog" aria-label="Confirm status change" style={{ border: "1px solid #e5e7eb", padding: 16, marginBottom: 16, borderRadius: 8, background: "#f9fafb" }}>
          <p>{activeAction.confirmMessage}</p>
          {updateError && <p role="alert" style={{ color: "#dc2626" }}>{updateError}</p>}
          <button type="button" onClick={() => handleStatusChange(activeAction.targetStatus)} disabled={updating} style={{ marginRight: 8 }}>
            {updating ? "Updating…" : `Yes, ${activeAction.label}`}
          </button>
          <button type="button" onClick={() => { setActiveAction(null); setUpdateError(null); }}>
            Cancel
          </button>
        </div>
      )}

      <dl style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "4px 16px", marginBottom: 16 }}>
        <dt><strong>Status</strong></dt>
        <dd>
          <span style={{ color: statusColor(order.status as OrderStatus), fontWeight: 600 }}>
            {statusLabel(order.status as OrderStatus)}
          </span>
        </dd>
        <dt><strong>Customer</strong></dt>
        <dd>{order.customer_id}</dd>
        <dt><strong>Payment Terms</strong></dt>
        <dd>{order.payment_terms_code} ({order.payment_terms_days} days)</dd>
        <dt><strong>Subtotal</strong></dt>
        <dd>${order.subtotal_amount}</dd>
        <dt><strong>Tax</strong></dt>
        <dd>${order.tax_amount}</dd>
        <dt><strong>Total</strong></dt>
        <dd><strong>${order.total_amount}</strong></dd>
        {order.invoice_id && (
          <>
            <dt><strong>Invoice</strong></dt>
            <dd>{order.invoice_id}</dd>
          </>
        )}
        {order.notes && (
          <>
            <dt><strong>Notes</strong></dt>
            <dd>{order.notes}</dd>
          </>
        )}
        <dt><strong>Created</strong></dt>
        <dd>{new Date(order.created_at).toLocaleString()}</dd>
        {order.confirmed_at && (
          <>
            <dt><strong>Confirmed</strong></dt>
            <dd>{new Date(order.confirmed_at).toLocaleString()}</dd>
          </>
        )}
      </dl>

      <h3>Line Items</h3>
      <table aria-label="Order line items">
        <thead>
          <tr>
            <th>#</th>
            <th>Description</th>
            <th>Qty</th>
            <th>Unit Price</th>
            <th>Tax</th>
            <th>Subtotal</th>
            <th>Total</th>
            <th>Stock</th>
          </tr>
        </thead>
        <tbody>
          {order.lines.map((line) => (
            <tr key={line.id}>
              <td>{line.line_number}</td>
              <td>{line.description}</td>
              <td>{line.quantity}</td>
              <td>${line.unit_price}</td>
              <td>${line.tax_amount}</td>
              <td>${line.subtotal_amount}</td>
              <td>${line.total_amount}</td>
              <td>
                {line.available_stock_snapshot != null && (
                  <span>{line.available_stock_snapshot}</span>
                )}
                {line.backorder_note && (
                  <span style={{ color: "#dc2626", display: "block", fontSize: "0.85em" }}>
                    {line.backorder_note}
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
