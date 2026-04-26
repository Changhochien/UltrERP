import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { WarehouseSelector } from "../domain/inventory/components/WarehouseSelector";
import { WarehouseProvider, useWarehouseContext } from "../domain/inventory/context/WarehouseContext";
import { AlertFeed } from "../domain/inventory/components/AlertFeed";
import { CommandBar } from "../domain/inventory/components/CommandBar";
import { ProductTable } from "../domain/inventory/components/ProductTable";
import { MetricCards } from "../domain/inventory/components/MetricCards";
import { PageHeader, PageTabs } from "../components/layout/PageLayout";
import { ProductDetailDrawer } from "../domain/inventory/components/ProductDetailDrawer";
import { CreateProductForm } from "../domain/inventory/components/CreateProductForm";
import { ReorderPointAdmin } from "../domain/inventory/components/ReorderPointAdmin";
import { StockAdjustmentForm } from "../domain/inventory/components/StockAdjustmentForm";
import { Button } from "../components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { usePermissions } from "../hooks/usePermissions";
import { buildInventoryTransfersPath, ORDER_CREATE_ROUTE } from "../lib/routes";
import { buildInventorySectionTabs, getInventorySectionRoute, type InventorySectionTabValue } from "./inventory/inventoryPageTabs";

function InventoryWorkspace() {
  const { t } = useTranslation("inventory");
  const { t: tRoutes } = useTranslation("routes");
  const navigate = useNavigate();
  const { selectedWarehouse, setSelectedWarehouse } = useWarehouseContext();
  const { canWrite } = usePermissions();
  const canManageInventory = canWrite("inventory");
  const canCreateOrders = canWrite("orders");
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [adjustProductId, setAdjustProductId] = useState("");
  const [showAdjustStock, setShowAdjustStock] = useState(false);
  const [stockAdjustmentDialogKey, setStockAdjustmentDialogKey] = useState(0);
  const [showCreateProduct, setShowCreateProduct] = useState(false);
  const [createProductDialogKey, setCreateProductDialogKey] = useState(0);
  const [createdProductKey, setCreatedProductKey] = useState(0);
  const [productSearch, setProductSearch] = useState("");
  const inventoryTabs = buildInventorySectionTabs(t);

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[{ label: tRoutes("inventory.label") }]}
        eyebrow={t("page.eyebrow")}
        title={t("page.title")}
        description={t("page.description")}
        actions={
          <div className="grid w-full gap-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end xl:w-[32rem]">
            <div className="space-y-2">
              <div className="text-[11px] font-semibold uppercase tracking-[0.28em] text-muted-foreground">
                {t("page.warehouseScope")}
              </div>
              <WarehouseSelector
                value={selectedWarehouse}
                onChange={setSelectedWarehouse}
              />
              <p className="text-xs text-muted-foreground">
                {t("page.warehouseScopeDescription")}
              </p>
            </div>
            {canWrite("inventory") && (
              <Button
                type="button"
                className="h-10 rounded-full px-5"
                onClick={() => {
                  setCreateProductDialogKey((current) => current + 1);
                  setShowCreateProduct(true);
                }}
              >
                {t("page.addProduct")}
              </Button>
            )}
          </div>
        }
        tabs={(
          <PageTabs
            items={inventoryTabs}
            value="overview"
            ariaLabel={t("page.title")}
            onValueChange={(next) => navigate(getInventorySectionRoute(next as InventorySectionTabValue))}
          />
        )}
      />

      <MetricCards warehouseId={selectedWarehouse?.id} />

      <CommandBar
        ariaLabel={t("page.commandBar.regionLabel")}
        searchValue={productSearch}
        onSearch={setProductSearch}
        searchPlaceholder={t("page.commandBar.searchPlaceholder")}
        searchAriaLabel={t("page.commandBar.searchPlaceholder")}
        adjustStockLabel={t("page.commandBar.adjustStock")}
        newTransferLabel={t("page.commandBar.newTransfer")}
        newOrderLabel={t("page.commandBar.newOrder")}
        onAdjustStock={canManageInventory ? () => {
          setSelectedProductId(null);
          setAdjustProductId("");
          setStockAdjustmentDialogKey((current) => current + 1);
          setShowAdjustStock(true);
        } : undefined}
        onNewTransfer={canManageInventory ? () => navigate(buildInventoryTransfersPath(undefined, selectedWarehouse?.id)) : undefined}
        onNewOrder={canCreateOrders ? () => navigate(ORDER_CREATE_ROUTE) : undefined}
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
        <ProductTable
          warehouseId={selectedWarehouse?.id}
          onProductClick={(id) => setSelectedProductId(id)}
          createdProductKey={createdProductKey}
          searchValue={productSearch}
          onSearchValueChange={setProductSearch}
          hideToolbarSearch
        />
        <AlertFeed />
      </div>

      {canManageInventory ? <ReorderPointAdmin /> : null}

      <ProductDetailDrawer
        productId={selectedProductId}
        onClose={() => setSelectedProductId(null)}
        onAdjustStock={(productId) => {
          setSelectedProductId(null);
          setAdjustProductId(productId);
          setStockAdjustmentDialogKey((current) => current + 1);
          setShowAdjustStock(true);
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

      <Dialog
        open={showAdjustStock}
        onOpenChange={(open) => {
          setShowAdjustStock(open);
          if (!open) {
            setAdjustProductId("");
            setStockAdjustmentDialogKey((current) => current + 1);
          }
        }}
      >
        <DialogContent className="max-w-3xl p-0 sm:max-w-3xl" showCloseButton>
          <DialogHeader className="px-6 pt-6">
            <DialogTitle>{t("page.stockAdjustmentDialog.title")}</DialogTitle>
            <DialogDescription>
              {t("page.stockAdjustmentDialog.description")}
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[80vh] overflow-y-auto px-6 pb-6">
            <StockAdjustmentForm
              key={stockAdjustmentDialogKey}
              defaultProductId={adjustProductId || undefined}
              defaultWarehouseId={selectedWarehouse?.id ?? ""}
              confirmBeforeSubmit={false}
            />
          </div>
        </DialogContent>
      </Dialog>

      <Dialog
        open={showCreateProduct}
        onOpenChange={(open) => {
          setShowCreateProduct(open);
          if (!open) {
            setCreateProductDialogKey((current) => current + 1);
          }
        }}
      >
        <DialogContent className="max-w-3xl p-0 sm:max-w-3xl" showCloseButton>
          <DialogHeader className="px-6 pt-6">
            <DialogTitle>{t("page.createProductDialog.title")}</DialogTitle>
            <DialogDescription>
              {t("page.createProductDialog.description")}
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[80vh] overflow-y-auto px-6 pb-6">
            <CreateProductForm
              key={createProductDialogKey}
              onSuccess={() => {
                setShowCreateProduct(false);
                setCreatedProductKey((k) => k + 1);
                setCreateProductDialogKey((current) => current + 1);
              }}
              onCancel={() => {
                setShowCreateProduct(false);
                setCreateProductDialogKey((current) => current + 1);
              }}
            />
          </div>
        </DialogContent>
      </Dialog>
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
