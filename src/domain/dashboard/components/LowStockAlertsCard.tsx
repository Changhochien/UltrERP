/** Low-stock alerts dashboard card. */

import { useLowStockAlerts } from "../hooks/useDashboard";

export function LowStockAlertsCard() {
  const { data, isLoading, error } = useLowStockAlerts();

  const alerts = data?.items ?? [];

  return (
    <div className="kpi-card" data-testid="low-stock-card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3>Low-Stock Alerts</h3>
        {!isLoading && !error && alerts.length > 0 && (
          <span className="badge badge--warning" data-testid="alert-badge">
            {alerts.length}
          </span>
        )}
      </div>

      {isLoading && (
        <div data-testid="low-stock-loading">
          <div className="skeleton" style={{ height: "4rem" }} />
        </div>
      )}

      {error && <p className="error-text">{error}</p>}

      {!isLoading && !error && alerts.length === 0 && (
        <p className="success-state" data-testid="low-stock-ok">
          All stock levels OK ✓
        </p>
      )}

      {!isLoading && !error && alerts.length > 0 && (
        <ul className="alert-list" data-testid="low-stock-list">
          {alerts.map((alert) => {
            const critical = alert.current_stock < alert.reorder_point * 0.5;
            return (
              <li
                key={alert.id}
                className={`alert-item ${critical ? "alert-item--critical" : "alert-item--warning"}`}
                aria-label={`${alert.product_name}. Stock: ${alert.current_stock}, Reorder point: ${alert.reorder_point}`}
              >
                <span className="alert-product">{alert.product_name}</span>
                <span className="alert-stock">
                  Stock: {alert.current_stock} / Reorder: {alert.reorder_point}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
