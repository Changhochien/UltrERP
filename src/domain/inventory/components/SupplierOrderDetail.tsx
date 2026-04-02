/** Supplier order detail with status update and receive actions. */

import { useState } from "react";
import {
  useSupplierOrderDetail,
  useUpdateOrderStatus,
  useReceiveOrder,
  statusLabel,
  statusColor,
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
      <div role="alert">
        <p>Error: {error}</p>
        <button type="button" onClick={onBack}>
          Back to list
        </button>
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
    <section aria-label={`Order ${order.order_number}`}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <h2>
          Order {order.order_number}
          <span
            style={{
              marginLeft: 12,
              padding: "2px 10px",
              borderRadius: 4,
              fontSize: "0.8em",
              color: "#fff",
              backgroundColor: statusColor(status),
            }}
          >
            {statusLabel(status)}
          </span>
        </h2>
        <button type="button" onClick={onBack}>
          ← Back
        </button>
      </div>

      {(statusError || receiveError) && (
        <div role="alert" style={{ color: "#dc2626", marginBottom: 12 }}>
          {statusError || receiveError}
        </div>
      )}

      {/* Order metadata */}
      <dl
        style={{
          display: "grid",
          gridTemplateColumns: "auto 1fr",
          gap: "4px 16px",
          marginBottom: 16,
        }}
      >
        <dt style={{ fontWeight: 600 }}>Supplier</dt>
        <dd>{order.supplier_name}</dd>
        <dt style={{ fontWeight: 600 }}>Order Date</dt>
        <dd>{new Date(order.order_date).toLocaleDateString()}</dd>
        <dt style={{ fontWeight: 600 }}>Expected Arrival</dt>
        <dd>
          {order.expected_arrival_date
            ? new Date(order.expected_arrival_date).toLocaleDateString()
            : "—"}
        </dd>
        <dt style={{ fontWeight: 600 }}>Created</dt>
        <dd>{new Date(order.created_at).toLocaleString()}</dd>
      </dl>

      {/* Status actions */}
      {allowedNext.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <strong>Update status: </strong>
          {allowedNext.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => void handleStatusChange(s)}
              disabled={statusSubmitting}
              style={{ marginRight: 8 }}
            >
              {statusLabel(s)}
            </button>
          ))}
        </div>
      )}

      {/* Receive toggle */}
      {canReceive && !showReceive && (
        <button
          type="button"
          onClick={() => setShowReceive(true)}
          style={{ marginBottom: 16 }}
        >
          Record Receipt
        </button>
      )}

      {/* Order lines */}
      <h3>Line Items</h3>
      <table aria-label="Order line items">
        <thead>
          <tr>
            <th>Product</th>
            <th>Warehouse</th>
            <th style={{ textAlign: "right" }}>Ordered</th>
            <th style={{ textAlign: "right" }}>Received</th>
            <th style={{ textAlign: "right" }}>Remaining</th>
            {showReceive && <th style={{ textAlign: "right" }}>Receive Now</th>}
          </tr>
        </thead>
        <tbody>
          {order.lines.map((line) => {
            const remaining =
              line.quantity_ordered - line.quantity_received;
            return (
              <tr key={line.id}>
                <td style={{ fontFamily: "monospace", fontSize: "0.9em" }}>
                  {line.product_id.slice(0, 8)}…
                </td>
                <td style={{ fontFamily: "monospace", fontSize: "0.9em" }}>
                  {line.warehouse_id.slice(0, 8)}…
                </td>
                <td style={{ textAlign: "right" }}>
                  {line.quantity_ordered}
                </td>
                <td style={{ textAlign: "right" }}>
                  {line.quantity_received}
                </td>
                <td
                  style={{
                    textAlign: "right",
                    color: remaining > 0 ? "#d97706" : "#16a34a",
                    fontWeight: 600,
                  }}
                >
                  {remaining}
                </td>
                {showReceive && (
                  <td style={{ textAlign: "right" }}>
                    <input
                      type="number"
                      min={0}
                      max={remaining}
                      value={receiveQty[line.id] ?? 0}
                      onChange={(e) =>
                        setReceiveQty((prev) => ({
                          ...prev,
                          [line.id]: Number(e.target.value),
                        }))
                      }
                      style={{ width: 80 }}
                      aria-label={`Receive quantity for line ${line.product_id.slice(0, 8)}`}
                      disabled={remaining === 0}
                    />
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Receive actions */}
      {showReceive && (
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button
            type="button"
            onClick={() => void handleReceive()}
            disabled={
              receiveSubmitting ||
              Object.values(receiveQty).every((q) => !q || q <= 0)
            }
          >
            {receiveSubmitting ? "Processing…" : "Confirm Receipt"}
          </button>
          <button
            type="button"
            onClick={() => {
              setShowReceive(false);
              setReceiveQty({});
            }}
          >
            Cancel
          </button>
        </div>
      )}
    </section>
  );
}
