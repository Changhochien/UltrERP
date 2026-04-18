import { useCallback, useEffect, useState } from "react";

import { fetchBelowReorderReport } from "../../../lib/api/inventory";
import type { BelowReorderReportItem } from "../types";

export function useBelowReorderReport(filters?: {
  warehouseId?: string;
}) {
  const [items, setItems] = useState<BelowReorderReportItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchBelowReorderReport({ warehouseId: filters?.warehouseId });
      if (response.ok) {
        setItems(response.data.items);
        setTotal(response.data.total);
      } else {
        setItems([]);
        setTotal(0);
        setError(response.error);
      }
    } catch (err) {
      setItems([]);
      setTotal(0);
      setError(err instanceof Error ? err.message : "Failed to load below-reorder report");
    } finally {
      setLoading(false);
    }
  }, [filters?.warehouseId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { items, total, loading, error, reload };
}