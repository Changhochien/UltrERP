import { useState } from "react";
import { useProductDetail } from "../hooks/useProductDetail";
import type { WarehouseStockInfo, AdjustmentHistoryItem } from "../types";

interface ProductDetailProps {
  productId: string;
}

function ReorderBadge({ below }: { below: boolean }) {
  if (!below) return null;
  return (
    <span
      role="status"
      aria-label="Below reorder point"
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 4,
        backgroundColor: "#dc2626",
        color: "#fff",
        fontSize: "0.75rem",
        fontWeight: 600,
      }}
    >
      Below reorder point
    </span>
  );
}

function WarehouseStockRow({ wh }: { wh: WarehouseStockInfo }) {
  return (
    <tr>
      <td>{wh.warehouse_name}</td>
      <td style={{ textAlign: "right" }}>{wh.current_stock}</td>
      <td style={{ textAlign: "right" }}>{wh.reorder_point}</td>
      <td>
        <ReorderBadge below={wh.is_below_reorder} />
      </td>
      <td>
        {wh.last_adjusted
          ? new Date(wh.last_adjusted).toLocaleDateString()
          : "—"}
      </td>
    </tr>
  );
}

function AdjustmentRow({ item }: { item: AdjustmentHistoryItem }) {
  return (
    <tr>
      <td>{new Date(item.created_at).toLocaleString()}</td>
      <td
        style={{
          textAlign: "right",
          color: item.quantity_change < 0 ? "#dc2626" : "#16a34a",
        }}
      >
        {item.quantity_change > 0 ? "+" : ""}
        {item.quantity_change}
      </td>
      <td>{item.reason_code}</td>
      <td>{item.actor_id}</td>
      <td>{item.notes ?? "—"}</td>
    </tr>
  );
}

export function ProductDetail({ productId }: ProductDetailProps) {
  const { product, loading, error, reload } = useProductDetail(productId);
  const [selectedWarehouse, setSelectedWarehouse] = useState<string | null>(
    null,
  );

  if (loading) return <div aria-busy="true">Loading product details…</div>;
  if (error)
    return (
      <div role="alert">
        <p>Error: {error}</p>
        <button type="button" onClick={() => void reload()}>
          Retry
        </button>
      </div>
    );
  if (!product) return null;

  const filteredWarehouses = selectedWarehouse
    ? product.warehouses.filter((w) => w.warehouse_id === selectedWarehouse)
    : product.warehouses;

  return (
    <article aria-label={`Product detail: ${product.name}`}>
      <header>
        <h2>
          {product.name}{" "}
          <small style={{ color: "#6b7280" }}>({product.code})</small>
        </h2>
        {product.category && <p>Category: {product.category}</p>}
        <p>
          Status: {product.status} | Total stock: {product.total_stock}
        </p>
      </header>

      {product.warehouses.length > 1 && (
        <nav aria-label="Warehouse filter">
          <label htmlFor="wh-toggle">Warehouse: </label>
          <select
            id="wh-toggle"
            value={selectedWarehouse ?? ""}
            onChange={(e) =>
              setSelectedWarehouse(e.target.value || null)
            }
          >
            <option value="">All warehouses</option>
            {product.warehouses.map((wh) => (
              <option key={wh.warehouse_id} value={wh.warehouse_id}>
                {wh.warehouse_name}
              </option>
            ))}
          </select>
        </nav>
      )}

      <section aria-label="Warehouse stock levels">
        <h3>Stock by Warehouse</h3>
        {filteredWarehouses.length === 0 ? (
          <p>No stock records</p>
        ) : (
        <table role="grid" style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th scope="col" style={{ textAlign: "left" }}>Warehouse</th>
              <th scope="col" style={{ textAlign: "right" }}>Quantity</th>
              <th scope="col" style={{ textAlign: "right" }}>Reorder Point</th>
              <th scope="col">Status</th>
              <th scope="col">Last Adjusted</th>
            </tr>
          </thead>
          <tbody>
            {filteredWarehouses.map((wh) => (
              <WarehouseStockRow key={wh.warehouse_id} wh={wh} />
            ))}
          </tbody>
        </table>
        )}
      </section>

      <section aria-label="Adjustment history">
        <h3>Adjustment History</h3>
        {product.adjustment_history.length === 0 ? (
          <p>No adjustment history available.</p>
        ) : (
          <table
            role="grid"
            style={{ width: "100%", borderCollapse: "collapse" }}
          >
            <thead>
              <tr>
                <th scope="col" style={{ textAlign: "left" }}>Date</th>
                <th scope="col" style={{ textAlign: "right" }}>Change</th>
                <th scope="col">Reason</th>
                <th scope="col">Actor</th>
                <th scope="col">Notes</th>
              </tr>
            </thead>
            <tbody>
              {product.adjustment_history.map((item) => (
                <AdjustmentRow key={item.id} item={item} />
              ))}
            </tbody>
          </table>
        )}
      </section>
    </article>
  );
}
