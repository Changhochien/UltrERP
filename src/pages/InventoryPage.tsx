import { useTranslation } from "react-i18next";

import { ProductSearch } from "../domain/inventory/components/ProductSearch";
import { ReorderAlerts } from "../domain/inventory/components/ReorderAlerts";
import { WarehouseSelector } from "../domain/inventory/components/WarehouseSelector";
import { PageHeader, SectionCard } from "../components/layout/PageLayout";
import {
  WarehouseProvider,
  useWarehouseContext,
} from "../domain/inventory/context/WarehouseContext";

function InventoryWorkspace() {
  const { t } = useTranslation("common");
  const { selectedWarehouse, setSelectedWarehouse } = useWarehouseContext();

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("inventory.page.eyebrow")}
        title={t("inventory.page.title")}
        description={t("inventory.page.description")}
      />

      <SectionCard
        title={t("inventory.page.warehouseScope")}
        description={t("inventory.page.warehouseScopeDescription")}
      >
        <WarehouseSelector
          value={selectedWarehouse}
          onChange={setSelectedWarehouse}
        />
      </SectionCard>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <ProductSearch />
        <ReorderAlerts />
      </div>
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