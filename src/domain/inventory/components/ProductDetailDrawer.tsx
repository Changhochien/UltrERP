import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { X, ArrowRightLeft, ExternalLink, ShoppingCart, SlidersHorizontal } from "lucide-react";

import "../inventory.css";

import { Badge } from "@/components/ui/badge";
import { useProductDetail } from "../hooks/useProductDetail";
import { useWarehouseContext } from "../context/WarehouseContext";
import type { AdjustmentHistoryItem, WarehouseStockInfo } from "../types";

interface ProductDetailDrawerProps {
  productId: string | null;
  onClose: () => void;
  onAdjustStock?: (productId: string, warehouseId: string) => void;
  onTransfer?: (productId: string) => void;
  onNewOrder?: (productId: string) => void;
}

function getStatusVariant(
  stock: number,
  reorderPoint: number,
  productStatus: string,
): "healthy" | "warning" | "critical" | "inactive" {
  if (productStatus !== "active") return "inactive";
  if (stock === 0) return "critical";
  if (stock < reorderPoint * 0.5) return "critical";
  if (stock < reorderPoint) return "warning";
  return "healthy";
}

function StockHealthBar({ warehouses }: { warehouses: WarehouseStockInfo[] }) {
  const totalStock = warehouses.reduce((sum, w) => sum + w.current_stock, 0);
  if (totalStock === 0) {
    return (
      <div>
        <div className="stock-health-bar">
          <div
            className="stock-health-segment critical"
            style={{ width: "100%" }}
          />
        </div>
        <div className="stock-health-legend">
          <div className="stock-health-legend-item">
            <div className="stock-health-dot critical" />
            <span>Out of stock</span>
          </div>
        </div>
      </div>
    );
  }

  const healthy = warehouses
    .filter((w) => {
      const status = getStatusVariant(w.current_stock, w.reorder_point, "active");
      return status === "healthy";
    })
    .reduce((sum, w) => sum + w.current_stock, 0);
  const warning = warehouses
    .filter((w) => {
      const status = getStatusVariant(w.current_stock, w.reorder_point, "active");
      return status === "warning";
    })
    .reduce((sum, w) => sum + w.current_stock, 0);
  const critical = warehouses
    .filter((w) => {
      const status = getStatusVariant(w.current_stock, w.reorder_point, "active");
      return status === "critical";
    })
    .reduce((sum, w) => sum + w.current_stock, 0);

  const pct = (n: number) => `${Math.round((n / totalStock) * 100)}%`;

  return (
    <div>
      <div className="stock-health-bar">
        {critical > 0 && (
          <div
            className="stock-health-segment critical"
            style={{ width: pct(critical) }}
          />
        )}
        {warning > 0 && (
          <div
            className="stock-health-segment warning"
            style={{ width: pct(warning) }}
          />
        )}
        {healthy > 0 && (
          <div
            className="stock-health-segment healthy"
            style={{ width: pct(healthy) }}
          />
        )}
      </div>
      <div className="stock-health-legend">
        {critical > 0 && (
          <div className="stock-health-legend-item">
            <div className="stock-health-dot critical" />
            <span>Critical {pct(critical)}</span>
          </div>
        )}
        {warning > 0 && (
          <div className="stock-health-legend-item">
            <div className="stock-health-dot warning" />
            <span>Low {pct(warning)}</span>
          </div>
        )}
        {healthy > 0 && (
          <div className="stock-health-legend-item">
            <div className="stock-health-dot healthy" />
            <span>Healthy {pct(healthy)}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function AdjustmentTimeline({
  history,
}: {
  history: AdjustmentHistoryItem[];
}) {
  if (history.length === 0) {
    return (
      <p style={{ fontSize: 13, color: "var(--inv-muted)" }}>
        No adjustment history available.
      </p>
    );
  }

  return (
    <div className="adjustment-timeline">
      {history.map((item) => {
        const isPositive = item.quantity_change > 0;
        const isNeutral = item.quantity_change === 0;
        return (
          <div
            key={item.id}
            className={`timeline-item ${isPositive ? "positive" : isNeutral ? "neutral" : "negative"}`}
          >
            <div className="timeline-item-header">
              <span
                className={`timeline-item-change ${isPositive ? "positive" : "negative"}`}
              >
                {isPositive ? "+" : ""}
                {item.quantity_change}
              </span>
              <span className="timeline-item-date">
                {new Date(item.created_at).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </span>
            </div>
            <div className="timeline-item-reason">{item.reason_code}</div>
          </div>
        );
      })}
    </div>
  );
}

export function ProductDetailDrawer({
  productId,
  onClose,
  onAdjustStock,
  onTransfer,
  onNewOrder,
}: ProductDetailDrawerProps) {
  const { product, loading, error } = useProductDetail(productId ?? "");
  const navigate = useNavigate();
  const { selectedWarehouse } = useWarehouseContext();

  // Close on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!productId) return null;

  return (
    <>
      <div
        className="inv-drawer-overlay"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        className="inv-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Product details"
      >
        {/* Header */}
        <div className="inv-drawer-header">
          <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 8 }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                background: "transparent",
                border: "none",
                cursor: "pointer",
                color: "var(--inv-muted)",
                padding: 4,
                borderRadius: 6,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              aria-label="Close drawer"
            >
              <X size={18} />
            </button>
          </div>

          {loading ? (
            <div style={{ padding: "20px 0" }}>
              <div
                style={{
                  height: 12,
                  width: 80,
                  background: "var(--inv-surface-hover)",
                  borderRadius: 4,
                  marginBottom: 12,
                  animation: "shimmer 1.5s infinite",
                }}
              />
              <div
                style={{
                  height: 24,
                  width: 200,
                  background: "var(--inv-surface-hover)",
                  borderRadius: 4,
                  animation: "shimmer 1.5s infinite",
                }}
              />
            </div>
          ) : error ? (
            <div>
              <p style={{ color: "var(--inv-critical)", fontSize: 14 }}>
                Failed to load product details
              </p>
              <p style={{ color: "var(--inv-muted)", fontSize: 12, marginTop: 4 }}>
                {error}
              </p>
            </div>
          ) : product ? (
            <>
              <div className="inv-drawer-code">{product.code}</div>
              <div className="inv-drawer-title">{product.name}</div>
              <div className="inv-drawer-tags">
                {product.category && (
                  <Badge
                    variant="outline"
                    style={{
                      borderColor: "var(--inv-border)",
                      color: "var(--inv-muted)",
                      background: "transparent",
                    }}
                  >
                    {product.category}
                  </Badge>
                )}
                <Badge
                  variant={product.status === "active" ? "success" : "destructive"}
                  style={{ textTransform: "capitalize" }}
                >
                  {product.status}
                </Badge>
              </div>
            </>
          ) : null}
        </div>

        {/* Body */}
        <div className="inv-drawer-body">
          {!loading && product && (
            <>
              {/* Stock Health */}
              <div className="drawer-section">
                <div className="drawer-section-title">Stock Health</div>
                <div
                  style={{
                    fontFamily: "var(--inv-font-mono)",
                    fontSize: 28,
                    fontWeight: 600,
                    marginBottom: 12,
                  }}
                >
                  {product.total_stock.toLocaleString()}{" "}
                  <span
                    style={{
                      fontSize: 14,
                      color: "var(--inv-muted)",
                      fontWeight: 400,
                    }}
                  >
                    total units
                  </span>
                </div>
                <StockHealthBar warehouses={product.warehouses} />
              </div>

              {/* Per-Warehouse */}
              <div className="drawer-section">
                <div className="drawer-section-title">
                  By Warehouse
                </div>
                <div className="warehouse-cards">
                  {product.warehouses.length === 0 ? (
                    <p style={{ fontSize: 13, color: "var(--inv-muted)" }}>
                      No warehouse data available.
                    </p>
                  ) : (
                    product.warehouses.map((wh) => {
                      const status = getStatusVariant(
                        wh.current_stock,
                        wh.reorder_point,
                        product.status,
                      );
                      return (
                        <div key={wh.warehouse_id} className="warehouse-card">
                          <div className="warehouse-card-header">
                            <span className="warehouse-card-name">
                              {wh.warehouse_name}
                            </span>
                            <span
                              className={`warehouse-card-stock ${status !== "healthy" ? status : ""}`}
                            >
                              {wh.current_stock}
                            </span>
                          </div>
                          <div className="warehouse-card-meta">
                            <span>
                              Reorder:{" "}
                              <strong style={{ color: "var(--inv-text)" }}>
                                {wh.reorder_point}
                              </strong>
                            </span>
                            {wh.last_adjusted && (
                              <span>
                                Updated:{" "}
                                <strong style={{ color: "var(--inv-text)" }}>
                                  {new Date(
                                    wh.last_adjusted,
                                  ).toLocaleDateString()}
                                </strong>
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              {/* Adjustment History */}
              <div className="drawer-section">
                <div className="drawer-section-title">
                  Recent Adjustments
                </div>
                <AdjustmentTimeline history={product.adjustment_history} />
              </div>
            </>
          )}
        </div>

        {/* Footer Actions */}
        {product && (
          <div className="inv-drawer-footer">
            <button
              type="button"
              className="drawer-action-btn primary"
              onClick={() =>
                onAdjustStock?.(
                  product.id,
                  selectedWarehouse?.id ?? product.warehouses[0]?.warehouse_id ?? "",
                )
              }
            >
              <SlidersHorizontal size={14} />
              Adjust Stock
            </button>
            <button
              type="button"
              className="drawer-action-btn"
              onClick={() => onTransfer?.(product.id)}
            >
              <ArrowRightLeft size={14} />
              Transfer
            </button>
            <button
              type="button"
              className="drawer-action-btn"
              onClick={() => onNewOrder?.(product.id)}
            >
              <ShoppingCart size={14} />
              Order
            </button>
            <button
              type="button"
              className="drawer-action-btn"
              onClick={() => navigate(`/inventory/${product.id}`)}
            >
              <ExternalLink size={14} />
              Open Full Page
            </button>
          </div>
        )}
      </div>
    </>
  );
}
