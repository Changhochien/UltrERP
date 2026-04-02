/** Supplier order list with status filtering. */

import { useState } from "react";
import {
  useSupplierOrders,
  statusLabel,
  statusColor,
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
    <section aria-label="Supplier orders">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <h2>Supplier Orders</h2>
        <button type="button" onClick={onCreateNew}>
          + New Order
        </button>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        <label>
          Status:{" "}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter by order status"
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>

        <button type="button" onClick={() => void reload()}>
          Refresh
        </button>
      </div>

      {error && (
        <div role="alert" style={{ color: "#dc2626", marginBottom: 12 }}>
          {error}
        </div>
      )}

      {loading && <p aria-busy="true">Loading orders…</p>}

      {!loading && items.length === 0 && <p>No supplier orders found.</p>}

      {items.length > 0 && (
        <>
          <p style={{ marginBottom: 8 }}>
            Showing {items.length} of {total} orders
          </p>
          <table aria-label="Supplier orders list">
            <thead>
              <tr>
                <th>Order #</th>
                <th>Supplier</th>
                <th>Status</th>
                <th>Order Date</th>
                <th>Expected Arrival</th>
                <th>Lines</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {items.map((order) => (
                <tr key={order.id}>
                  <td style={{ fontFamily: "monospace" }}>
                    {order.order_number}
                  </td>
                  <td>{order.supplier_name}</td>
                  <td>
                    <span
                      style={{
                        padding: "2px 8px",
                        borderRadius: 4,
                        fontSize: "0.85em",
                        color: "#fff",
                        backgroundColor: statusColor(
                          order.status as SupplierOrderStatus,
                        ),
                      }}
                    >
                      {statusLabel(order.status as SupplierOrderStatus)}
                    </span>
                  </td>
                  <td>
                    {new Date(order.order_date).toLocaleDateString()}
                  </td>
                  <td>
                    {order.expected_arrival_date
                      ? new Date(
                          order.expected_arrival_date,
                        ).toLocaleDateString()
                      : "—"}
                  </td>
                  <td style={{ textAlign: "center" }}>{order.line_count}</td>
                  <td>
                    <button
                      type="button"
                      onClick={() => onSelect(order.id)}
                      aria-label={`View order ${order.order_number}`}
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}
