/** Paginated order list with status filter. */

import { useState } from "react";
import { useOrders, statusLabel, statusColor } from "../hooks/useOrders";

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
  const { items, total, page, loading, error, reload } = useOrders({
    status: statusFilter || undefined,
  });

  return (
    <section aria-label="Order list">
      <h2>Orders</h2>

      <div style={{ marginBottom: 12, display: "flex", gap: 8 }}>
        <label htmlFor="ol-status">Status: </label>
        <select
          id="ol-status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div role="alert" style={{ color: "#dc2626" }}>
          {error}
        </div>
      )}

      {loading && <p aria-busy="true">Loading…</p>}

      {!loading && items.length === 0 && <p>No orders found.</p>}

      {!loading && items.length > 0 && (
        <>
          <table aria-label="Orders table">
            <thead>
              <tr>
                <th>Order #</th>
                <th>Status</th>
                <th>Total</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.id}
                  onClick={() => onSelect(item.id)}
                  style={{ cursor: "pointer" }}
                >
                  <td>{item.order_number}</td>
                  <td>
                    <span
                      style={{
                        color: statusColor(item.status),
                        fontWeight: 600,
                      }}
                    >
                      {statusLabel(item.status)}
                    </span>
                  </td>
                  <td>${item.total_amount}</td>
                  <td>{new Date(item.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ marginTop: 8 }}>
            <span>
              Page {page} · {total} total
            </span>
            {page > 1 && (
              <button
                type="button"
                onClick={() => void reload(page - 1)}
                style={{ marginLeft: 8 }}
              >
                ← Prev
              </button>
            )}
            {page * 20 < total && (
              <button
                type="button"
                onClick={() => void reload(page + 1)}
                style={{ marginLeft: 8 }}
              >
                Next →
              </button>
            )}
          </div>
        </>
      )}
    </section>
  );
}
