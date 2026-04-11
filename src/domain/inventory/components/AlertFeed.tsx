import { Bell, Package, RefreshCw, Settings, Truck, AlertTriangle } from "lucide-react";
import { useState } from "react";

import {
  useAcknowledgeAlert,
  useReorderAlerts,
} from "../hooks/useReorderAlerts";
import { useWarehouseContext } from "../context/WarehouseContext";
import type { ReorderAlertItem } from "../types";
import { normalizeAlertSeverity } from "../../../lib/alertSeverity";

type AlertFilter = "all" | "low_stock" | "critical" | "transfer" | "adjustment";

const FILTER_OPTIONS: { value: AlertFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "low_stock", label: "Low Stock" },
  { value: "critical", label: "Critical" },
  { value: "transfer", label: "Transfers" },
  { value: "adjustment", label: "Adjustments" },
];

function getAlertIcon(type: AlertFilter) {
  switch (type) {
    case "low_stock":
    case "critical":
      return <AlertTriangle size={14} />;
    case "transfer":
      return <Truck size={14} />;
    case "adjustment":
      return <Settings size={14} />;
    default:
      return <Bell size={14} />;
  }
}

function getAlertIconClass(type: AlertFilter): string {
  switch (type) {
    case "low_stock": return "low-stock";
    case "critical": return "critical";
    case "transfer": return "transfer";
    case "adjustment": return "adjustment";
    default: return "reorder";
  }
}

function alertTypeFromItem(item: ReorderAlertItem): AlertFilter {
  if (item.status === "pending") {
    if (normalizeAlertSeverity(item.severity) === "CRITICAL") return "critical";
    return "low_stock";
  }
  if (item.status === "acknowledged") return "adjustment";
  return "all";
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);
  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

export function AlertFeed() {
  const [filter, setFilter] = useState<AlertFilter>("all");
  const { selectedWarehouse } = useWarehouseContext();
  const { alerts, loading, reload } = useReorderAlerts({
    warehouseId: selectedWarehouse?.id,
  });
  const { acknowledge, submitting } = useAcknowledgeAlert();

  const handleAcknowledge = async (alertId: string) => {
    const ok = await acknowledge(alertId);
    if (ok) void reload();
  };

  const pendingCount = alerts.filter((a) => a.status === "pending").length;

  const filteredAlerts = alerts.filter((alert) => {
    if (filter === "all") return true;
    const type = alertTypeFromItem(alert);
    return type === filter;
  });

  return (
    <div className="alert-sidebar">
      <div className="alert-sidebar-header">
        <div className="alert-sidebar-title">
          <Bell size={14} />
          Alert Feed
          {pendingCount > 0 && (
            <span className="alert-count-badge">{pendingCount}</span>
          )}
        </div>
      </div>

      <div className="alert-filters">
        {FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            className={`alert-filter-btn${filter === opt.value ? " active" : ""}`}
            onClick={() => setFilter(opt.value)}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <div className="alert-list">
        {loading ? (
          <div className="alert-empty">
            <RefreshCw size={20} className="animate-spin" />
            <p className="alert-empty-text">Loading alerts…</p>
          </div>
        ) : filteredAlerts.length === 0 ? (
          <div className="alert-empty">
            <Package size={32} />
            <p className="alert-empty-text">
              {filter === "all"
                ? "No alerts — inventory is healthy"
                : `No ${filter.replace("_", " ")} alerts`}
            </p>
          </div>
        ) : (
          filteredAlerts.map((alert, index) => {
            const type = alertTypeFromItem(alert);
            const severity = normalizeAlertSeverity(alert.severity);
            return (
              <div
                key={alert.id}
                className="alert-item"
                style={{ animationDelay: `${index * 30}ms` }}
              >
                <div className="alert-item-header">
                  <div className={`alert-icon ${getAlertIconClass(type)}`}>
                    {getAlertIcon(type)}
                  </div>
                  <div className="alert-body">
                    <div className="alert-product">{alert.product_name}</div>
                    <div className="alert-desc">
                      {type === "critical"
                        ? `Out of stock (${alert.current_stock} units)`
                        : type === "low_stock" && severity === "INFO"
                          ? `${alert.current_stock} at reorder point ${alert.reorder_point}`
                          : type === "low_stock"
                          ? `${alert.current_stock} below reorder point ${alert.reorder_point}`
                          : `${alert.status} — ${alert.warehouse_name}`}
                    </div>
                  </div>
                </div>
                <div className="alert-footer">
                  <span className="alert-meta">
                    {alert.warehouse_name} · {formatRelativeTime(alert.created_at)}
                  </span>
                  {alert.status === "pending" && (
                    <button
                      type="button"
                      className="alert-ack-btn"
                      onClick={() => void handleAcknowledge(alert.id)}
                      disabled={submitting}
                    >
                      Acknowledge
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
