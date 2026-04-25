/**
 * Hook for fetching dense stock history series with range metadata.
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

interface StockHistoryDenseResponse {
  points: DenseSeriesPoint[];
  range: DenseSeriesRange;
}

export interface UseStockHistorySeriesOptions {
  /** Start date (YYYY-MM-DD format) */
  startDate: string;
  /** End date (YYYY-MM-DD format) */
  endDate: string;
}

export function useStockHistorySeries(
  stockId: string,
  options: UseStockHistorySeriesOptions,
) {
  const [points, setPoints] = useState<DenseSeriesPoint[]>([]);
  const [range, setRange] = useState<DenseSeriesRange | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!stockId || !options.startDate || !options.endDate) {
      setPoints([]);
      setRange(null);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const resp = await apiFetch(
        `/api/v1/inventory/stock-history/${encodeURIComponent(stockId)}/series?start_date=${options.startDate}&end_date=${options.endDate}`,
      );

      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        setError((body as { detail?: string }).detail ?? "Failed to load stock history series");
        return;
      }

      const data = (await resp.json()) as StockHistoryDenseResponse;
      setPoints(data.points ?? []);
      setRange(data.range ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load stock history series");
    } finally {
      setLoading(false);
    }
  }, [stockId, options.startDate, options.endDate]);

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
export { getDateRangeFromPreset } from "../../shared/utils/dateRangeUtils";
