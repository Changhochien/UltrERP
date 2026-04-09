/** Hook for fetching stock movement history for trend charts. */

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../../../lib/apiFetch";
import type { StockHistoryPoint } from "../types";

export interface StockHistoryResponse {
  points: StockHistoryPoint[];
  current_stock: number;
  reorder_point: number;
  avg_daily_usage: number | null;
  lead_time_days: number | null;
  safety_stock: number | null;
}

export function useStockHistory(
  stockId: string,
  options?: {
    fromDate?: string;
    toDate?: string;
    granularity?: "daily" | "raw";
  },
) {
  const [history, setHistory] = useState<StockHistoryPoint[]>([]);
  const [currentStock, setCurrentStock] = useState(0);
  const [reorderPoint, setReorderPoint] = useState(0);
  const [avgDailyUsage, setAvgDailyUsage] = useState<number | null>(null);
  const [leadTimeDays, setLeadTimeDays] = useState<number | null>(null);
  const [safetyStock, setSafetyStock] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!stockId) return;
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (options?.fromDate) params.set("from_date", options.fromDate);
      if (options?.toDate) params.set("to_date", options.toDate);
      if (options?.granularity) params.set("granularity", options.granularity);
      const qs = params.toString();
      const url = `/api/v1/inventory/stock-history/${encodeURIComponent(stockId)}${qs ? `?${qs}` : ""}`;
      const resp = await apiFetch(url);
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        setError((body as { detail?: string }).detail ?? "Failed to load stock history");
        return;
      }
      const data = (await resp.json()) as StockHistoryResponse;
      setHistory(data.points ?? []);
      setCurrentStock(data.current_stock ?? 0);
      setReorderPoint(data.reorder_point ?? 0);
      setAvgDailyUsage(data.avg_daily_usage ?? null);
      setLeadTimeDays(data.lead_time_days ?? null);
      setSafetyStock(data.safety_stock ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load stock history");
    } finally {
      setLoading(false);
    }
  }, [stockId, options?.fromDate, options?.toDate, options?.granularity]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return {
    history,
    currentStock,
    reorderPoint,
    avgDailyUsage,
    leadTimeDays,
    safetyStock,
    loading,
    error,
    refetch,
  };
}