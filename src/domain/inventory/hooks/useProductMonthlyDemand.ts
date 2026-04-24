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

export interface UseProductMonthlyDemandOptions {
  months?: number;
  includeCurrentMonth?: boolean;
}

export function useProductMonthlyDemand(
  productId: string,
  options?: UseProductMonthlyDemandOptions,
) {
  const [items, setItems] = useState<MonthlyDemandItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!productId) {
      setItems([]);
      setTotal(0);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (options?.months != null) {
        params.set("months", String(options.months));
      }
      if (options?.includeCurrentMonth != null) {
        params.set("include_current_month", String(options.includeCurrentMonth));
      }
      const query = params.size ? `?${params.toString()}` : "";
      const resp = await apiFetch(
        `/api/v1/inventory/products/${encodeURIComponent(productId)}/monthly-demand${query}`,
      );
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        setItems([]);
        setTotal(0);
        setError((body as { detail?: string }).detail ?? "Failed to load monthly demand");
        return;
      }
      const data = (await resp.json()) as MonthlyDemandResponse;
      setItems(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (e) {
      setItems([]);
      setTotal(0);
      setError(e instanceof Error ? e.message : "Failed to load monthly demand");
    } finally {
      setLoading(false);
    }
  }, [productId, options?.includeCurrentMonth, options?.months]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { items, total, loading, error, refetch };
}
