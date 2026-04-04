/** Top selling products card with day/week toggle. */

import { useState } from "react";

import { useTopProducts } from "../hooks/useDashboard";

function formatTWD(value: string): string {
  return `NT$ ${Number(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function TopProductsCard() {
  const [period, setPeriod] = useState<"day" | "week">("day");
  const { data, isLoading, error } = useTopProducts(period);

  return (
    <div className="kpi-card" data-testid="top-products-card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3>Top Selling Products</h3>
        <div className="toggle-group" role="group" aria-label="Period toggle">
          <button
            type="button"
            className={period === "day" ? "toggle--active" : ""}
            onClick={() => setPeriod("day")}
            aria-pressed={period === "day"}
          >
            Today
          </button>
          <button
            type="button"
            className={period === "week" ? "toggle--active" : ""}
            onClick={() => setPeriod("week")}
            aria-pressed={period === "week"}
          >
            This Week
          </button>
        </div>
      </div>

      {isLoading && (
        <div data-testid="top-products-loading">
          <div className="skeleton" style={{ height: "4rem" }} />
        </div>
      )}

      {error && <p className="error-text">{error}</p>}

      {!isLoading && !error && data && data.items.length === 0 && (
        <p className="empty-state" data-testid="top-products-empty">
          No sales data for this period
        </p>
      )}

      {!isLoading && !error && data && data.items.length > 0 && (
        <table className="kpi-table" data-testid="top-products-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Product</th>
              <th>Qty Sold</th>
              <th>Revenue</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((item, idx) => (
              <tr key={item.product_id}>
                <td>{idx + 1}</td>
                <td>{item.product_name}</td>
                <td>{Number(item.quantity_sold).toLocaleString("en-US")}</td>
                <td>{formatTWD(item.revenue)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
