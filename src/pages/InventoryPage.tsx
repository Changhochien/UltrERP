import { ProductSearch } from "../domain/inventory/components/ProductSearch";
import { ReorderAlerts } from "../domain/inventory/components/ReorderAlerts";
import { WarehouseSelector } from "../domain/inventory/components/WarehouseSelector";
import { PageHeader, SectionCard } from "../components/layout/PageLayout";
import {
  WarehouseProvider,
  useWarehouseContext,
} from "../domain/inventory/context/WarehouseContext";

function InventoryWorkspace() {
  const { selectedWarehouse, setSelectedWarehouse } = useWarehouseContext();

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Inventory"
        title="Inventory"
        description="Warehouse-scoped product search, low-stock monitoring, and exception handling for replenishment."
      />

      <SectionCard title="Warehouse Scope" description="Change warehouse context to narrow product search and alert results.">
        <WarehouseSelector
          value={selectedWarehouse}
          onChange={setSelectedWarehouse}
        />
      </SectionCard>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
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