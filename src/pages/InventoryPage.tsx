import { useState } from "react";
import { useTranslation } from "react-i18next";

import { WarehouseSelector } from "../domain/inventory/components/WarehouseSelector";
import { WarehouseProvider, useWarehouseContext } from "../domain/inventory/context/WarehouseContext";
import { ProductTable } from "../domain/inventory/components/ProductTable";
import { AlertPanel } from "../domain/inventory/components/AlertPanel";
import { MetricCards } from "../domain/inventory/components/MetricCards";
import { PageHeader } from "../components/layout/PageLayout";
import { ProductDetailDrawer } from "../domain/inventory/components/ProductDetailDrawer";
import { CreateProductForm } from "../domain/inventory/components/CreateProductForm";
import { ReorderPointAdmin } from "../domain/inventory/components/ReorderPointAdmin";
import { StockAdjustmentForm } from "../domain/inventory/components/StockAdjustmentForm";
import { StockTransferForm } from "../domain/inventory/components/StockTransferForm";
import { usePermissions } from "../hooks/usePermissions";

function InventoryWorkspace() {
  const { t } = useTranslation("common");
  const { selectedWarehouse, setSelectedWarehouse } = useWarehouseContext();
  const { canWrite } = usePermissions();
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [adjustProductId, setAdjustProductId] = useState<string | null>(null);
  const [transferProductId, setTransferProductId] = useState<string | null>(null);
  const [showCreateProduct, setShowCreateProduct] = useState(false);
  const [createdProductKey, setCreatedProductKey] = useState(0);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("inventory.page.eyebrow")}
        title={t("inventory.page.title")}
        description={t("inventory.page.description")}
        actions={
          <>
            <WarehouseSelector
              value={selectedWarehouse}
              onChange={setSelectedWarehouse}
            />
            {canWrite("inventory") && (
              <button
                onClick={() => setShowCreateProduct(true)}
                className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                Add Product
              </button>
            )}
          </>
        }
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
        onTransfer={(productId) => {
          setSelectedProductId(null);
          setTransferProductId(productId);
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

      {transferProductId && (
        <div className="fixed inset-0 z-[9002] flex items-center justify-center bg-black/50">
          <div className="w-full max-w-lg rounded-xl border border-border bg-background p-6 shadow-lg">
            <StockTransferForm defaultProductId={transferProductId} />
            <button
              type="button"
              className="mt-4 text-sm text-muted-foreground underline"
              onClick={() => setTransferProductId(null)}
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
