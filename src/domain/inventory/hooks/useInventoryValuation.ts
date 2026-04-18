import { useCallback, useEffect, useState } from "react";

import { fetchInventoryValuation } from "../../../lib/api/inventory";
import type {
  InventoryValuationItem,
  InventoryValuationWarehouseTotal,
} from "../types";

export function useInventoryValuation(filters?: {
  warehouseId?: string;
}) {
  const [items, setItems] = useState<InventoryValuationItem[]>([]);
  const [warehouseTotals, setWarehouseTotals] = useState<InventoryValuationWarehouseTotal[]>([]);
  const [grandTotalValue, setGrandTotalValue] = useState("0.0000");
  const [grandTotalQuantity, setGrandTotalQuantity] = useState(0);
  const [totalRows, setTotalRows] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchInventoryValuation({ warehouseId: filters?.warehouseId });
      if (response.ok) {
        setItems(response.data.items);
        setWarehouseTotals(response.data.warehouse_totals);
        setGrandTotalValue(response.data.grand_total_value);
        setGrandTotalQuantity(response.data.grand_total_quantity);
        setTotalRows(response.data.total_rows);
      } else {
        setItems([]);
        setWarehouseTotals([]);
        setGrandTotalValue("0.0000");
        setGrandTotalQuantity(0);
        setTotalRows(0);
        setError(response.error);
      }
    } catch (err) {
      setItems([]);
      setWarehouseTotals([]);
      setGrandTotalValue("0.0000");
      setGrandTotalQuantity(0);
      setTotalRows(0);
      setError(err instanceof Error ? err.message : "Failed to load inventory valuation");
    } finally {
      setLoading(false);
    }
  }, [filters?.warehouseId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return {
    items,
    warehouseTotals,
    grandTotalValue,
    grandTotalQuantity,
    totalRows,
    loading,
    error,
    reload,
  };
}