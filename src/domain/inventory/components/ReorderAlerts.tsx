/** Reorder alerts list with filtering and acknowledge action. */

import { useMemo, useState } from "react";
import { useWarehouses } from "../hooks/useWarehouses";
import {
  useReorderAlerts,
  useAcknowledgeAlert,
} from "../hooks/useReorderAlerts";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "pending", label: "Pending" },
  { value: "acknowledged", label: "Acknowledged" },
  { value: "resolved", label: "Resolved" },
] as const;

export function ReorderAlerts() {
  const [statusFilter, setStatusFilter] = useState("");
  const [warehouseFilter, setWarehouseFilter] = useState("");

  const filters = useMemo(
    () => ({
      status: statusFilter || undefined,
      warehouseId: warehouseFilter || undefined,
    }),
    [statusFilter, warehouseFilter],
  );

  const { alerts, total, loading, error, reload } = useReorderAlerts(filters);
  const { warehouses, loading: whLoading } = useWarehouses();
  const { acknowledge, submitting, error: ackError } = useAcknowledgeAlert();

  const handleAcknowledge = async (alertId: string) => {
    const ok = await acknowledge(alertId);
    if (ok) void reload();
  };

  return (
    <section aria-label="Reorder alerts">
      <h2>Reorder Alerts</h2>

      {/* Filters */}
      <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        <label>
          Status:{" "}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter by status"
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>

        <label>
          Warehouse:{" "}
          <select
            value={warehouseFilter}
            onChange={(e) => setWarehouseFilter(e.target.value)}
            aria-label="Filter by warehouse"
            disabled={whLoading}
          >
            <option value="">All warehouses</option>
            {warehouses.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* Error display */}
      {(error || ackError) && (
        <div role="alert" style={{ color: "#dc2626", marginBottom: 12 }}>
          {error || ackError}
        </div>
      )}

      {/* Loading */}
      {loading && <p aria-busy="true">Loading alerts…</p>}

      {/* Empty state */}
      {!loading && alerts.length === 0 && (
        <p>No reorder alerts found.</p>
      )}

      {/* Alert table */}
      {alerts.length > 0 && (
        <>
          <p style={{ marginBottom: 8 }}>
            Showing {alerts.length} of {total} alerts
          </p>
          <table aria-label="Reorder alerts list">
            <thead>
              <tr>
                <th>Product</th>
                <th>Warehouse</th>
                <th>Current Stock</th>
                <th>Reorder Point</th>
                <th>Status</th>
                <th>Created</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a) => (
                <tr key={a.id}>
                  <td>{a.product_name}</td>
                  <td>{a.warehouse_name}</td>
                  <td
                    style={{
                      color: a.current_stock < a.reorder_point ? "#dc2626" : undefined,
                      fontWeight: a.current_stock < a.reorder_point ? 600 : undefined,
                    }}
                  >
                    {a.current_stock}
                  </td>
                  <td>{a.reorder_point}</td>
                  <td>
                    <span
                      style={{
                        padding: "2px 8px",
                        borderRadius: 4,
                        fontSize: "0.85em",
                        background:
                          a.status === "pending"
                            ? "#fef3c7"
                            : a.status === "acknowledged"
                              ? "#dbeafe"
                              : "#d1fae5",
                        color:
                          a.status === "pending"
                            ? "#92400e"
                            : a.status === "acknowledged"
                              ? "#1e40af"
                              : "#065f46",
                      }}
                    >
                      {a.status}
                    </span>
                  </td>
                  <td>{new Date(a.created_at).toLocaleDateString()}</td>
                  <td>
                    {a.status === "pending" && (
                      <button
                        type="button"
                        onClick={() => void handleAcknowledge(a.id)}
                        disabled={submitting}
                        aria-label={`Acknowledge alert for ${a.product_name}`}
                      >
                        Acknowledge
                      </button>
                    )}
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
