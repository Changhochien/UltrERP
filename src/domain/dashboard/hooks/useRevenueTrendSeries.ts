/**
 * Hook for fetching dense revenue trend series with range metadata.
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

interface RevenueTrendDenseResponse {
  points: DenseSeriesPoint[];
  range: DenseSeriesRange;
}

export interface UseRevenueTrendSeriesOptions {
  /** Granularity: "day" or "month" */
  granularity?: "day" | "month";
  /** Start date (YYYY-MM-DD for day, YYYY-MM for month) */
  startDate: string;
  /** End date (YYYY-MM-DD for day, YYYY-MM for month) */
  endDate: string;
}

export function useRevenueTrendSeries(options: UseRevenueTrendSeriesOptions) {
  const [points, setPoints] = useState<DenseSeriesPoint[]>([]);
  const [range, setRange] = useState<DenseSeriesRange | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!options.startDate || !options.endDate) {
      setPoints([]);
      setRange(null);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const granularity = options.granularity ?? "month";
      const resp = await apiFetch(
        `/api/v1/dashboard/revenue-trend-series?granularity=${granularity}&start_date=${encodeURIComponent(options.startDate)}&end_date=${encodeURIComponent(options.endDate)}`,
      );

      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        setError((body as { detail?: string }).detail ?? "Failed to load revenue trend series");
        return;
      }

      const data = (await resp.json()) as RevenueTrendDenseResponse;
      setPoints(data.points ?? []);
      setRange(data.range ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load revenue trend series");
    } finally {
      setLoading(false);
    }
  }, [options.granularity, options.startDate, options.endDate]);

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
