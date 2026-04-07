import { Boxes, AlertTriangle, Bell, DollarSign } from "lucide-react";

import { useProductSearch } from "../hooks/useProductSearch";
import { useReorderAlerts } from "../hooks/useReorderAlerts";

interface InventoryMetricsProps {
  warehouseId?: string;
}

export function InventoryMetrics({ warehouseId }: InventoryMetricsProps) {
  const { results, loading: productsLoading } = useProductSearch();
  const { alerts, total: alertsTotal, loading: alertsLoading } = useReorderAlerts({
    warehouseId,
  });

  const totalProducts = results.length;
  const pendingAlerts = alerts.filter((a) => a.status === "pending").length;
  const lowStockCount = alerts.filter((a) => a.status === "pending").length;

  // Calculate total stock value (sum of all product stock)
  const totalStockValue = results.reduce(
    (sum, p) => sum + p.current_stock,
    0,
  );

  const loading = productsLoading || alertsLoading;

  return (
    <div className="metrics-strip">
      {/* Total Products */}
      <div className="metric-card">
        <div className="metric-icon-wrap">
          <Boxes />
        </div>
        <div className="metric-body">
          <div className="metric-label">Total SKUs</div>
          <div className="metric-value">
            {loading ? "—" : totalProducts.toLocaleString()}
          </div>
          <div className="metric-sub">
            {warehouseId ? "Filtered scope" : "All warehouses"}
          </div>
        </div>
      </div>

      {/* Low Stock */}
      <div
        className={`metric-card${lowStockCount > 0 && !loading ? " glow-warning" : ""}`}
      >
        <div className="metric-icon-wrap">
          <AlertTriangle
            style={{ color: lowStockCount > 0 ? "#F59E0B" : undefined }}
          />
        </div>
        <div className="metric-body">
          <div className="metric-label">Low Stock</div>
          <div
            className="metric-value"
            style={{
              color: lowStockCount > 0 ? "#F59E0B" : undefined,
            }}
          >
            {loading ? "—" : lowStockCount}
          </div>
          <div className="metric-sub">
            {loading ? "—" : `${alertsTotal} total alerts`}
          </div>
        </div>
      </div>

      {/* Pending Alerts */}
      <div
        className={`metric-card${pendingAlerts > 0 && !loading ? " glow-critical" : ""}`}
      >
        <div className="metric-icon-wrap">
          <Bell
            style={{ color: pendingAlerts > 0 ? "#EF4444" : undefined }}
          />
        </div>
        <div className="metric-body">
          <div className="metric-label">Pending Alerts</div>
          <div
            className="metric-value"
            style={{
              color: pendingAlerts > 0 ? "#EF4444" : undefined,
            }}
          >
            {loading ? "—" : pendingAlerts}
          </div>
          <div className="metric-sub">
            {loading ? "—" : "Require attention"}
          </div>
        </div>
      </div>

      {/* Total Stock */}
      <div className="metric-card">
        <div className="metric-icon-wrap">
          <DollarSign />
        </div>
        <div className="metric-body">
          <div className="metric-label">Total Units</div>
          <div className="metric-value">
            {loading ? "—" : totalStockValue.toLocaleString()}
          </div>
          <div className="metric-sub">All warehouses combined</div>
        </div>
      </div>
    </div>
  );
}
