/** Hook for fetching planning support for a product. */

import { useCallback, useEffect, useState } from "react";

import { fetchPlanningSupport } from "../../../lib/api/inventory";
import type { PlanningSupportResponse } from "../types";

export function useProductPlanningSupport(
  productId: string,
  options?: { months?: number; includeCurrentMonth?: boolean },
) {
  const [data, setData] = useState<PlanningSupportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!productId) {
      setData(null);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const result = await fetchPlanningSupport(productId, options);
      if (!result.ok) {
        setData(null);
        setError(result.error);
        return;
      }
      setData(result.data);
    } catch (e) {
      setData(null);
      setError(e instanceof Error ? e.message : "Failed to load planning support");
    } finally {
      setLoading(false);
    }
  }, [productId, options?.includeCurrentMonth, options?.months]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}