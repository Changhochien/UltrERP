/** Warehouse selector dropdown — for global nav or scoped use. */

import type { Warehouse } from "../types";
import { useWarehouses } from "../hooks/useWarehouses";

interface Props {
  value: Warehouse | null;
  onChange: (warehouse: Warehouse | null) => void;
  /** If true, shows an "All Warehouses" option. */
  allowAll?: boolean;
  label?: string;
}

export function WarehouseSelector({
  value,
  onChange,
  allowAll = true,
  label = "Warehouse",
}: Props) {
  const { warehouses, loading, error } = useWarehouses();

  if (loading) return <span>Loading warehouses…</span>;
  if (error) return <span className="error">{error}</span>;

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = e.target.value;
    if (id === "") {
      onChange(null);
    } else {
      const wh = warehouses.find((w) => w.id === id) ?? null;
      onChange(wh);
    }
  };

  return (
    <label>
      {label}
      <select value={value?.id ?? ""} onChange={handleChange}>
        {allowAll && <option value="">All Warehouses</option>}
        {warehouses.map((wh) => (
          <option key={wh.id} value={wh.id}>
            {wh.name} ({wh.code})
          </option>
        ))}
      </select>
    </label>
  );
}
