/** Hooks for dashboard domain. */

import { useCallback, useEffect, useState } from "react";

import { fetchRevenueSummary, fetchTopProducts, fetchLowStockAlerts, fetchVisitorStats } from "../../../lib/api/dashboard";
import type { RevenueSummary, TopProductsResponse, LowStockAlertListResponse, VisitorStatsResponse } from "../types";

export function useRevenueSummary() {
  const [data, setData] = useState<RevenueSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setIsLoading(true);
    fetchRevenueSummary()
      .then(setData)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load revenue"),
      )
      .finally(() => setIsLoading(false));
  }, []);

  return { data, isLoading, error };
}

export function useTopProducts(period: "day" | "week") {
  const [data, setData] = useState<TopProductsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchTopProducts(period);
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load top products");
    } finally {
      setIsLoading(false);
    }
  }, [period]);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, isLoading, error };
}

export function useLowStockAlerts() {
  const [data, setData] = useState<LowStockAlertListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setIsLoading(true);
    fetchLowStockAlerts()
      .then(setData)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load alerts"),
      )
      .finally(() => setIsLoading(false));
  }, []);

  return { data, isLoading, error };
}

const REFRESH_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

export function useVisitorStats() {
  const [data, setData] = useState<VisitorStatsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchVisitorStats();
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load visitor stats");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [load]);

  return { data, isLoading, error };
}
