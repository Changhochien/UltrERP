/** Hook for fetching monthly demand for a product. */

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../../../lib/apiFetch";

export interface MonthlyDemandItem {
  month: string;
  total_qty: number;
}

export interface MonthlyDemandResponse {
  items: MonthlyDemandItem[];
  total: number;
}

export function useProductMonthlyDemand(productId: string) {
  const [items, setItems] = useState<MonthlyDemandItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!productId) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await apiFetch(
        `/api/v1/inventory/products/${encodeURIComponent(productId)}/monthly-demand`,
      );
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        setError((body as { detail?: string }).detail ?? "Failed to load monthly demand");
        return;
      }
      const data = (await resp.json()) as MonthlyDemandResponse;
      setItems(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load monthly demand");
    } finally {
      setLoading(false);
    }
  }, [productId]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { items, total, loading, error, refetch };
}
