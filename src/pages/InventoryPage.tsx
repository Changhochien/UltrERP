import { ProductSearch } from "../domain/inventory/components/ProductSearch";
import { ReorderAlerts } from "../domain/inventory/components/ReorderAlerts";
import { WarehouseSelector } from "../domain/inventory/components/WarehouseSelector";
import {
  WarehouseProvider,
  useWarehouseContext,
} from "../domain/inventory/context/WarehouseContext";

function InventoryWorkspace() {
  const { selectedWarehouse, setSelectedWarehouse } = useWarehouseContext();

  return (
    <section className="hero-card" style={{ width: "min(72rem, 100%)" }}>
      <h1 style={{ fontSize: "2rem", lineHeight: 1.1 }}>Inventory</h1>
      <p className="caption">Read-heavy inventory workspace with warehouse filtering and reorder visibility.</p>

      <div style={{ margin: "1rem 0 1.5rem" }}>
        <WarehouseSelector
          value={selectedWarehouse}
          onChange={setSelectedWarehouse}
        />
      </div>

      <div style={{ display: "grid", gap: "2rem" }}>
        <ProductSearch />
        <ReorderAlerts />
      </div>
    </section>
  );
}

export function InventoryPage() {
  return (
    <WarehouseProvider>
      <InventoryWorkspace />
    </WarehouseProvider>
  );
}