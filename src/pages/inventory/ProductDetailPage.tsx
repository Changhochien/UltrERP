import { useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ArrowRightLeft, ArrowLeft, ShoppingCart, SlidersHorizontal } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SectionCard } from "@/components/layout/PageLayout";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useProductDetail } from "@/domain/inventory/hooks/useProductDetail";
import { useStockHistory } from "@/domain/inventory/hooks/useStockHistory";
import { WarehouseProvider, useWarehouseContext } from "@/domain/inventory/context/WarehouseContext";
import { AdjustmentTimeline } from "@/domain/inventory/components/AdjustmentTimeline";
import { StockTrendChart } from "@/domain/inventory/components/StockTrendChart";
import { AnalyticsTab } from "@/domain/inventory/components/AnalyticsTab";
import { SettingsTab } from "@/domain/inventory/components/SettingsTab";
import { AuditLogTable } from "@/domain/inventory/components/AuditLogTable";
import { useProductAuditLog } from "@/domain/inventory/hooks/useProductAuditLog";
import { INVENTORY_ROUTE } from "@/lib/routes";
import { parseBackendDate } from "@/lib/time";
import type { WarehouseStockInfo } from "@/domain/inventory/types";

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
  const { t } = useTranslation("common", { keyPrefix: "inventory.productDetail" });
  const totalStock = warehouses.reduce((sum, w) => sum + w.current_stock, 0);
  if (totalStock === 0) {
    return (
      <div>
        <div className="stock-health-bar">
          <div className="stock-health-segment critical" style={{ width: "100%" }} />
        </div>
        <div className="stock-health-legend">
          <div className="stock-health-legend-item">
            <div className="stock-health-dot critical" />
            <span>{t("outOfStock")}</span>
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
          <div className="stock-health-segment critical" style={{ width: pct(critical) }} />
        )}
        {warning > 0 && (
          <div className="stock-health-segment warning" style={{ width: pct(warning) }} />
        )}
        {healthy > 0 && (
          <div className="stock-health-segment healthy" style={{ width: pct(healthy) }} />
        )}
      </div>
      <div className="stock-health-legend">
        {critical > 0 && (
          <div className="stock-health-legend-item">
            <div className="stock-health-dot critical" />
            <span>{t("critical")} {pct(critical)}</span>
          </div>
        )}
        {warning > 0 && (
          <div className="stock-health-legend-item">
            <div className="stock-health-dot warning" />
            <span>{t("low")} {pct(warning)}</span>
          </div>
        )}
        {healthy > 0 && (
          <div className="stock-health-legend-item">
            <div className="stock-health-dot healthy" />
            <span>{t("healthy")} {pct(healthy)}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function AuditLogTabContent({ productId }: { productId: string }) {
  const { t } = useTranslation("common", { keyPrefix: "inventory.productDetail" });
  const PAGE_SIZE = 50;
  const [offset, setOffset] = useState(0);
  const { items, total, loading, error } = useProductAuditLog(productId, {
    limit: PAGE_SIZE,
    offset,
  });

  const start = offset + 1;
  const end = Math.min(offset + PAGE_SIZE, total);

  return (
    <SectionCard title={t("auditLog")}>
      {error && <div className="mb-3 text-sm text-destructive">{error}</div>}
      <AuditLogTable items={items} loading={loading} error={error} />
      {total > 0 && (
        <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
          <span>
            {t("auditPagination.showing", { start, end, total })}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              {t("auditPagination.previous")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={end >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              {t("auditPagination.next")}
            </Button>
          </div>
        </div>
      )}
    </SectionCard>
  );
}

function ProductDetailContent({ productId }: { productId: string }) {
  const { t } = useTranslation("common", { keyPrefix: "inventory.productDetail" });
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { product, loading, error } = useProductDetail(productId);
  const { selectedWarehouse } = useWarehouseContext();
  const requestedTab = searchParams.get("tab");
  const defaultTab = requestedTab === "analytics"
    || requestedTab === "settings"
    || requestedTab === "audit"
    ? requestedTab
    : "overview";

  const stockId = selectedWarehouse?.id
    ? product?.warehouses.find((w) => w.warehouse_id === selectedWarehouse.id)?.stock_id
    : product?.warehouses[0]?.stock_id;
  const {
    history,
    reorderPoint,
    safetyStock,
    avgDailyUsage,
    loading: chartLoading,
    error: chartError,
  } = useStockHistory(stockId ?? "");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => navigate(INVENTORY_ROUTE)}>
          <ArrowLeft size={16} />
        </Button>
        <div className="flex-1">
          {loading ? (
            <div>
              <div
                style={{
                  height: 12,
                  width: 80,
                  background: "var(--inv-surface-hover)",
                  borderRadius: 4,
                  marginBottom: 8,
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
                {t("error", { message: error })}
              </p>
            </div>
          ) : product ? (
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {product.code}
              </div>
              <div className="text-xl font-semibold">{product.name}</div>
              <div className="mt-1 flex items-center gap-2">
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
                  {t(`statuses.${product.status}`, { defaultValue: product.status })}
                </Badge>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      <Tabs defaultValue={defaultTab}>
        <TabsList>
          <TabsTrigger value="overview">{t("overview")}</TabsTrigger>
          <TabsTrigger value="analytics">{t("analytics")}</TabsTrigger>
          <TabsTrigger value="settings">{t("settings")}</TabsTrigger>
          <TabsTrigger value="audit">{t("auditLog")}</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          {!loading && product && (
            <div className="space-y-6">
              {/* Stock Health */}
              <SectionCard title={t("stockHealth")}>
                <div
                  style={{
                    fontFamily: "var(--inv-font-mono)",
                    fontSize: 28,
                    fontWeight: 600,
                    marginBottom: 12,
                  }}
                >
                  {product.total_stock.toLocaleString()}{" "}
                  <span style={{ fontSize: 14, color: "var(--inv-muted)", fontWeight: 400 }}>
                    {t("totalUnits")}
                  </span>
                </div>
                <StockHealthBar warehouses={product.warehouses} />
              </SectionCard>

              {/* By Warehouse */}
              <SectionCard title={t("byWarehouse")}>
                {product.warehouses.length === 0 ? (
                  <p style={{ fontSize: 13, color: "var(--inv-muted)" }}>
                    {t("stockByWarehouse.noRecords")}
                  </p>
                ) : (
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {product.warehouses.map((wh) => {
                      const status = getStatusVariant(
                        wh.current_stock,
                        wh.reorder_point,
                        product.status,
                      );
                      return (
                        <div key={wh.warehouse_id} className="warehouse-card">
                          <div className="warehouse-card-header">
                            <span className="warehouse-card-name">{wh.warehouse_name}</span>
                            <span
                              className={`warehouse-card-stock ${status !== "healthy" ? status : ""}`}
                            >
                              {wh.current_stock}
                            </span>
                          </div>
                          <div className="warehouse-card-meta">
                            <span>
                              {t("reorder")}:{" "}
                              <strong style={{ color: "var(--inv-text)" }}>
                                {wh.reorder_point}
                              </strong>
                            </span>
                            {wh.last_adjusted && (
                              <span>
                                {t("updated")}:{" "}
                                <strong style={{ color: "var(--inv-text)" }}>
                                  {parseBackendDate(wh.last_adjusted).toLocaleDateString()}
                                </strong>
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </SectionCard>

              {/* Stock Trend Chart */}
              {(stockId || chartLoading) && (
                <SectionCard title={t("stockTrend")}>
                  {chartLoading ? (
                    <div
                      style={{
                        height: 260,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <span style={{ color: "var(--inv-muted)", fontSize: 13 }}>
                        {t("loading")}
                      </span>
                    </div>
                  ) : chartError ? (
                    <p style={{ fontSize: 13, color: "var(--inv-muted)" }}>{chartError}</p>
                  ) : (
                    <StockTrendChart
                      points={history}
                      reorderPoint={reorderPoint}
                      safetyStock={safetyStock ?? undefined}
                      avgDailyUsage={avgDailyUsage ?? undefined}
                    />
                  )}
                </SectionCard>
              )}

              {/* Recent Adjustments */}
              <SectionCard title={t("recentAdjustments")}>
                <AdjustmentTimeline history={product.adjustment_history} />
              </SectionCard>

              {/* Footer Actions */}
              {product && (
                <div className="flex flex-wrap gap-3">
                  <Button variant="default" size="sm">
                    <SlidersHorizontal size={14} />
                    {t("adjustStock")}
                  </Button>
                  <Button variant="outline" size="sm">
                    <ArrowRightLeft size={14} />
                    {t("transfer")}
                  </Button>
                  <Button variant="outline" size="sm">
                    <ShoppingCart size={14} />
                    {t("order")}
                  </Button>
                </div>
              )}
            </div>
          )}
        </TabsContent>

        <TabsContent value="analytics">
          {product && (
            <AnalyticsTab productId={productId} warehouses={product.warehouses} />
          )}
        </TabsContent>

        <TabsContent value="settings">
          {product && <SettingsTab productId={productId} />}
        </TabsContent>

        <TabsContent value="audit">
          <AuditLogTabContent productId={productId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export function ProductDetailPage() {
  const params = useParams<{ productId: string }>();
  const productId = params.productId;

  if (!productId) {
    return (
      <WarehouseProvider>
        <ProductDetailContent productId="" />
      </WarehouseProvider>
    );
  }

  return (
    <WarehouseProvider>
      <ProductDetailContent productId={productId} />
    </WarehouseProvider>
  );
}
