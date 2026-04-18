import { useCallback, useEffect, useRef, useState } from "react";

import { fetchInventoryValuation } from "../../../lib/api/inventory";
import type {
  InventoryValuationItem,
  InventoryValuationWarehouseTotal,
} from "../types";

const DEFAULT_GRAND_TOTAL_VALUE = "0.0000";

interface InventoryValuationState {
  items: InventoryValuationItem[];
  warehouseTotals: InventoryValuationWarehouseTotal[];
  grandTotalValue: string;
  grandTotalQuantity: number;
  totalRows: number;
}

const DEFAULT_STATE: InventoryValuationState = {
  items: [],
  warehouseTotals: [],
  grandTotalValue: DEFAULT_GRAND_TOTAL_VALUE,
  grandTotalQuantity: 0,
  totalRows: 0,
};

export function useInventoryValuation(filters?: {
  warehouseId?: string;
}) {
  const [state, setState] = useState<InventoryValuationState>(DEFAULT_STATE);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const warehouseId = filters?.warehouseId;

  const reload = useCallback(async () => {
    if (abortRef.current) {
      abortRef.current.abort("useInventoryValuation: new request starting");
    }
    const abortController = new AbortController();
    abortRef.current = abortController;

    setLoading(true);
    setError(null);
    try {
      const response = await fetchInventoryValuation(
        { warehouseId },
        { signal: abortController.signal },
      );
      if (abortRef.current !== abortController || abortController.signal.aborted) {
        return;
      }
      if (response.ok) {
        setState({
          items: response.data.items,
          warehouseTotals: response.data.warehouse_totals,
          grandTotalValue: response.data.grand_total_value,
          grandTotalQuantity: response.data.grand_total_quantity,
          totalRows: response.data.total_rows,
        });
      } else {
        setState(DEFAULT_STATE);
        setError(response.error);
      }
    } catch (err) {
      if (abortController.signal.aborted) {
        return;
      }
      setState(DEFAULT_STATE);
      setError(err instanceof Error ? err.message : "Failed to load inventory valuation");
    } finally {
      if (abortRef.current === abortController) {
        abortRef.current = null;
        setLoading(false);
      }
    }
  }, [warehouseId]);

  useEffect(() => {
    void reload();
    return () => {
      abortRef.current?.abort("useInventoryValuation: unmounting");
    };
  }, [reload]);

  return {
    items: state.items,
    warehouseTotals: state.warehouseTotals,
    grandTotalValue: state.grandTotalValue,
    grandTotalQuantity: state.grandTotalQuantity,
    totalRows: state.totalRows,
    loading,
    error,
    reload,
  };
}
