/**
 * Hook for fetching dense monthly demand series with range metadata.
 * 
 * This hook uses the new dense time-series endpoint that provides:
 * - Zero-filled data points for the full requested range
 * - Range metadata (available range, default visible range)
 * - Period status (closed vs partial)
 * - Source provenance (aggregate, live, zero-filled)
 */

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../../../lib/apiFetch";
import type { DenseSeriesPoint, DenseSeriesRange } from "../../shared/types/denseSeries";

// Re-export shared types for consumers
export type { DenseSeriesPoint, DenseSeriesRange } from "../../shared/types/denseSeries";

interface MonthlyDemandDenseResponse {
  points: DenseSeriesPoint[];
  range: DenseSeriesRange;
}

export interface UseProductMonthlyDemandSeriesOptions {
  /** Start month (YYYY-MM format) */
  startMonth: string;
  /** End month (YYYY-MM format) */
  endMonth: string;
}

export function useProductMonthlyDemandSeries(
  productId: string,
  options: UseProductMonthlyDemandSeriesOptions,
) {
  const [points, setPoints] = useState<DenseSeriesPoint[]>([]);
  const [range, setRange] = useState<DenseSeriesRange | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!productId || !options.startMonth || !options.endMonth) {
      setPoints([]);
      setRange(null);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const resp = await apiFetch(
        `/api/v1/inventory/products/${encodeURIComponent(productId)}/monthly-demand-series?start_month=${options.startMonth}&end_month=${options.endMonth}`,
      );

      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        setError((body as { detail?: string }).detail ?? "Failed to load monthly demand series");
        return;
      }

      const data = (await resp.json()) as MonthlyDemandDenseResponse;
      setPoints(data.points ?? []);
      setRange(data.range ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load monthly demand series");
    } finally {
      setLoading(false);
    }
  }, [productId, options.startMonth, options.endMonth]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return {
    points,
    range,
    loading,
    error,
    refetch,
  };
}

// Re-export preset utilities
export { getMonthlyRangeFromPreset } from "../../shared/utils/dateRangeUtils";
