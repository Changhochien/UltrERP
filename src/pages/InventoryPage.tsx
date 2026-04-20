import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { WarehouseSelector } from "../domain/inventory/components/WarehouseSelector";
import { WarehouseProvider, useWarehouseContext } from "../domain/inventory/context/WarehouseContext";
import { ProductTable } from "../domain/inventory/components/ProductTable";
import { AlertPanel } from "../domain/inventory/components/AlertPanel";
import { MetricCards } from "../domain/inventory/components/MetricCards";
import { PageHeader, PageTabs } from "../components/layout/PageLayout";
import { ProductDetailDrawer } from "../domain/inventory/components/ProductDetailDrawer";
import { CreateProductForm } from "../domain/inventory/components/CreateProductForm";
import { ReorderPointAdmin } from "../domain/inventory/components/ReorderPointAdmin";
import { StockAdjustmentForm } from "../domain/inventory/components/StockAdjustmentForm";
import { Button } from "../components/ui/button";
import { usePermissions } from "../hooks/usePermissions";
import { buildInventoryTransfersPath } from "../lib/routes";
import { buildInventorySectionTabs, getInventorySectionRoute, type InventorySectionTabValue } from "./inventory/inventoryPageTabs";

function InventoryWorkspace() {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const { selectedWarehouse, setSelectedWarehouse } = useWarehouseContext();
  const { canWrite } = usePermissions();
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [adjustProductId, setAdjustProductId] = useState<string | null>(null);
  const [showCreateProduct, setShowCreateProduct] = useState(false);
  const [createdProductKey, setCreatedProductKey] = useState(0);
  const inventoryTabs = buildInventorySectionTabs(t);

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[{ label: t("routes.inventory.label") }]}
        eyebrow={t("inventory.page.eyebrow")}
        title={t("inventory.page.title")}
        description={t("inventory.page.description")}
        actions={
          <div className="grid w-full gap-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end xl:w-[32rem]">
            <div className="space-y-2">
              <div className="text-[11px] font-semibold uppercase tracking-[0.28em] text-muted-foreground">
                {t("inventory.page.warehouseScope")}
              </div>
              <WarehouseSelector
                value={selectedWarehouse}
                onChange={setSelectedWarehouse}
              />
              <p className="text-xs text-muted-foreground">
                {t("inventory.page.warehouseScopeDescription")}
              </p>
            </div>
            {canWrite("inventory") && (
              <Button type="button" className="h-10 rounded-full px-5" onClick={() => setShowCreateProduct(true)}>
                {t("inventory.page.addProduct")}
              </Button>
            )}
          </div>
        }
        tabs={(
          <PageTabs
            items={inventoryTabs}
            value="overview"
            ariaLabel={t("inventory.page.title")}
            onValueChange={(next) => navigate(getInventorySectionRoute(next as InventorySectionTabValue))}
          />
        )}
      />

      <MetricCards warehouseId={selectedWarehouse?.id} />

      <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
        <ProductTable
          warehouseId={selectedWarehouse?.id}
          onProductClick={(id) => setSelectedProductId(id)}
          createdProductKey={createdProductKey}
        />
        <AlertPanel />
      </div>

      {canWrite("inventory") ? <ReorderPointAdmin /> : null}

      <ProductDetailDrawer
        productId={selectedProductId}
        onClose={() => setSelectedProductId(null)}
        onAdjustStock={(productId) => {
          setSelectedProductId(null);
          setAdjustProductId(productId);
        }}
        onTransfer={(productId, warehouseId) => {
          setSelectedProductId(null);
          navigate(buildInventoryTransfersPath(productId, warehouseId || selectedWarehouse?.id));
        }}
        onNewOrder={(_productId) => {
          // TODO: wire up supplier order form
          setSelectedProductId(null);
        }}
      />

      {adjustProductId && (
        <div className="fixed inset-0 z-[9002] flex items-center justify-center bg-black/50">
          <div className="w-full max-w-lg rounded-xl border border-border bg-background p-6 shadow-lg">
            <StockAdjustmentForm
              defaultProductId={adjustProductId}
              defaultWarehouseId={selectedWarehouse?.id ?? ""}
            />
            <button
              type="button"
              className="mt-4 text-sm text-muted-foreground underline"
              onClick={() => setAdjustProductId(null)}
            >
              Close
            </button>
          </div>
        </div>
      )}

      {showCreateProduct && (
        <div className="fixed inset-0 z-[9002] flex items-center justify-center bg-black/50">
          <div className="w-full max-w-lg rounded-xl border border-border bg-background p-6 shadow-lg">
            <CreateProductForm
              onSuccess={() => {
                setShowCreateProduct(false);
                setCreatedProductKey((k) => k + 1);
              }}
              onCancel={() => setShowCreateProduct(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export function InventoryPage() {
  return (
    <WarehouseProvider>
      <InventoryWorkspace />
    </WarehouseProvider>
  );
}
