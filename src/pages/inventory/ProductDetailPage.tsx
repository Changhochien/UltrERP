import { useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ArrowRightLeft, ArrowLeft, ShoppingCart, SlidersHorizontal } from "lucide-react";

import { PageTabs } from "@/components/layout/PageLayout";
import { Badge } from "@/components/ui/badge";
import { Breadcrumb } from "@/components/ui/Breadcrumb";
import { Button } from "@/components/ui/button";
import { SectionCard } from "@/components/layout/PageLayout";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent } from "@/components/ui/tabs";
import { EditProductForm } from "@/domain/inventory/components/EditProductForm";
import { useProductDetail } from "@/domain/inventory/hooks/useProductDetail";
import { useStockHistory } from "@/domain/inventory/hooks/useStockHistory";
import { WarehouseProvider, useWarehouseContext } from "@/domain/inventory/context/WarehouseContext";
import { AdjustmentTimeline } from "@/domain/inventory/components/AdjustmentTimeline";
import { StockTrendChart } from "@/domain/inventory/components/StockTrendChart";
import { AnalyticsTab } from "@/domain/inventory/components/AnalyticsTab";
import { SettingsTab } from "@/domain/inventory/components/SettingsTab";
import { AuditLogTable } from "@/domain/inventory/components/AuditLogTable";
import { useProductAuditLog } from "@/domain/inventory/hooks/useProductAuditLog";
import { setProductStatus } from "@/lib/api/inventory";
import { buildInventoryTransfersPath, INVENTORY_ROUTE } from "@/lib/routes";
import { parseBackendDate } from "@/lib/time";
import { getStatusVariant } from "@/domain/inventory/utils";
import type { WarehouseStockInfo } from "@/domain/inventory/types";

function StockHealthBar({ warehouses }: { warehouses: WarehouseStockInfo[] }) {
  const { t } = useTranslation("inventory");
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
            <span>{t("inventory.productDetail.outOfStock")}</span>
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
            <span>{t("inventory.productDetail.critical")} {pct(critical)}</span>
          </div>
        )}
        {warning > 0 && (
          <div className="stock-health-legend-item">
            <div className="stock-health-dot warning" />
            <span>{t("inventory.productDetail.low")} {pct(warning)}</span>
          </div>
        )}
        {healthy > 0 && (
          <div className="stock-health-legend-item">
            <div className="stock-health-dot healthy" />
            <span>{t("inventory.productDetail.healthy")} {pct(healthy)}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function AuditLogTabContent({ productId }: { productId: string }) {
  const { t } = useTranslation("inventory");
  const PAGE_SIZE = 50;
  const [offset, setOffset] = useState(0);
  const { items, total, loading, error } = useProductAuditLog(productId, {
    limit: PAGE_SIZE,
    offset,
  });

  const start = offset + 1;
  const end = Math.min(offset + PAGE_SIZE, total);

  return (
    <SectionCard title={t("inventory.productDetail.auditLog")}>
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
              {t("inventory.productDetail.auditPagination.previous")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={end >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              {t("inventory.productDetail.auditPagination.next")}
            </Button>
          </div>
        </div>
      )}
    </SectionCard>
  );
}

function ProductDetailContent({ productId }: { productId: string }) {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showDeactivateDialog, setShowDeactivateDialog] = useState(false);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [statusSubmitting, setStatusSubmitting] = useState(false);
  const { product, loading, error, reload, applyLocalUpdate } = useProductDetail(productId);
  const { selectedWarehouse } = useWarehouseContext();
  const requestedTab = searchParams.get("inventory.productDetail.tab");
  const activeTab = requestedTab === "analytics"
    || requestedTab === "settings"
    || requestedTab === "audit"
    ? requestedTab
    : "overview";
  const detailTabs = [
    { value: "overview", label: t("inventory.productDetail.overview") },
    { value: "analytics", label: t("inventory.productDetail.analytics") },
    { value: "settings", label: t("inventory.productDetail.settings") },
    { value: "audit", label: t("inventory.productDetail.auditLog") },
  ];

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

  async function handleStatusChange(nextStatus: "active" | "inactive") {
    setStatusSubmitting(true);
    setStatusError(null);
    const result = await setProductStatus(productId, nextStatus);
    if (!result.ok) {
      setStatusError(result.error);
      setStatusSubmitting(false);
      return;
    }

    applyLocalUpdate(result.data);
    if (nextStatus === "inactive") {
      setShowDeactivateDialog(false);
    }
    await reload();
    setStatusSubmitting(false);
  }

  function handleTabChange(nextTab: string) {
    const nextParams = new URLSearchParams(searchParams);
    if (nextTab === "overview") {
      nextParams.delete("tab");
    } else {
      nextParams.set("tab", nextTab);
    }
    setSearchParams(nextParams, { replace: true });
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Button variant="ghost" size="sm" onClick={() => navigate(INVENTORY_ROUTE)}>
          <ArrowLeft size={16} />
        </Button>
        <div className="flex-1">
          {product ? (
            <Breadcrumb
              items={[
                { label: t("routes.inventory.label"), href: INVENTORY_ROUTE },
                { label: product.name },
              ]}
            />
          ) : null}
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
                  variant="outline"
                  style={{
                    borderColor: "var(--inv-border)",
                    color: "var(--inv-muted)",
                    background: "transparent",
                  }}
                >
                  {product.unit}
                </Badge>
                <Badge
                  variant={product.status === "active" ? "success" : "destructive"}
                  style={{ textTransform: "capitalize" }}
                >
                  {t(`statuses.${product.status}`, { defaultValue: product.status })}
                </Badge>
                <Badge
                  variant="outline"
                  style={{
                    borderColor: "var(--inv-border)",
                    color: "var(--inv-muted)",
                    background: "transparent",
                  }}
                >
                  {product.standard_cost
                    ? t("standardCost", { amount: product.standard_cost })
                    : t("inventory.productDetail.missingStandardCost")}
                </Badge>
              </div>
              {product.description && (
                <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
                  {product.description}
                </p>
              )}
            </div>
          ) : null}
        </div>
        {!loading && !error && product && (
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowEditDialog(true)}
              disabled={statusSubmitting}
            >
              {t("inventory.productDetail.edit")}
            </Button>
            {product.status === "active" ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setStatusError(null);
                  setShowDeactivateDialog(true);
                }}
                disabled={statusSubmitting}
              >
                {t("inventory.productDetail.deactivate")}
              </Button>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={() => void handleStatusChange("active")}
                disabled={statusSubmitting}
              >
                {t("inventory.productDetail.activate")}
              </Button>
            )}
          </div>
        )}
      </div>

      {statusError && (
        <div className="rounded-md border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {t("error", { message: statusError })}
        </div>
      )}

      <PageTabs
        items={detailTabs}
        value={activeTab}
        ariaLabel={t("title")}
        onValueChange={handleTabChange}
      />

      <Tabs value={activeTab}>
        <TabsContent value="overview">
          {!loading && product && (
            <div className="space-y-6">
              {/* Stock Health */}
              <SectionCard title={t("inventory.productDetail.stockHealth")}>
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
                    {t("inventory.productDetail.totalUnits")}
                  </span>
                </div>
                <StockHealthBar warehouses={product.warehouses} />
              </SectionCard>

              <SectionCard title={t("inventory.productDetail.masterData")}>
                <dl className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      {t("inventory.productDetail.unitLabel")}
                    </dt>
                    <dd className="mt-1 text-sm font-medium text-foreground">{product.unit}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      {t("inventory.productDetail.standardCostLabel")}
                    </dt>
                    <dd className="mt-1 text-sm font-medium text-foreground">
                      {product.standard_cost ?? t("inventory.productDetail.missingStandardCost")}
                    </dd>
                  </div>
                  <div className="sm:col-span-2">
                    <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      {t("inventory.productDetail.productDescription")}
                    </dt>
                    <dd className="mt-1 text-sm text-foreground">{product.description || "—"}</dd>
                  </div>
                </dl>
              </SectionCard>

              {/* By Warehouse */}
              <SectionCard title={t("inventory.productDetail.byWarehouse")}>
                {product.warehouses.length === 0 ? (
                  <p style={{ fontSize: 13, color: "var(--inv-muted)" }}>
                    {t("inventory.productDetail.stockByWarehouse.noRecords")}
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
                              {t("inventory.productDetail.reorder")}:{" "}
                              <strong style={{ color: "var(--inv-text)" }}>
                                {wh.reorder_point}
                              </strong>
                            </span>
                            {wh.last_adjusted && (
                              <span>
                                {t("inventory.productDetail.updated")}:{" "}
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
                <SectionCard title={t("inventory.productDetail.stockTrend")}>
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
                        {t("inventory.productDetail.loading")}
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
              <SectionCard title={t("inventory.productDetail.recentAdjustments")}>
                <AdjustmentTimeline history={product.adjustment_history} />
              </SectionCard>

              {/* Footer Actions */}
              {product && (
                <div className="flex flex-wrap gap-3">
                  <Button variant="default" size="sm">
                    <SlidersHorizontal size={14} />
                    {t("inventory.productDetail.adjustStock")}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate(
                      buildInventoryTransfersPath(
                        product.id,
                        selectedWarehouse?.id ?? product.warehouses[0]?.warehouse_id,
                      ),
                    )}
                  >
                    <ArrowRightLeft size={14} />
                    {t("inventory.productDetail.transfer")}
                  </Button>
                  <Button variant="outline" size="sm">
                    <ShoppingCart size={14} />
                    {t("inventory.productDetail.order")}
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

      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent aria-label={t("inventory.productDetail.edit")} className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{t("inventory.productDetail.edit")}</DialogTitle>
            <DialogDescription>{t("inventory.productDetail.editDescription")}</DialogDescription>
          </DialogHeader>
          {product && (
            <EditProductForm
              product={product}
              onSuccess={(updatedProduct) => {
                applyLocalUpdate(updatedProduct);
                setShowEditDialog(false);
                void reload();
              }}
              onCancel={() => setShowEditDialog(false)}
            />
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={showDeactivateDialog} onOpenChange={setShowDeactivateDialog}>
        <DialogContent aria-label={t("inventory.productDetail.deactivate")} className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{t("inventory.productDetail.deactivate")}</DialogTitle>
            <DialogDescription>{t("inventory.productDetail.deactivateDescription")}</DialogDescription>
          </DialogHeader>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setShowDeactivateDialog(false)}
              disabled={statusSubmitting}
            >
              {t("inventory.productDetail.cancel")}
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={() => void handleStatusChange("inactive")}
              disabled={statusSubmitting}
            >
              {t("inventory.productDetail.confirmDeactivate")}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
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
