/** Hooks for dashboard domain. */

import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchRevenueSummary,
  fetchTopProducts,
  fetchLowStockAlerts,
  fetchVisitorStats,
  fetchKPISummary,
  fetchTopCustomers,
  fetchARAging,
  fetchAPAging,
  fetchGrossMargin,
  fetchCashFlow,
  fetchRevenueTrend,
} from "../../../lib/api/dashboard";
import { appTodayISO } from "../../../lib/time";
import type {
  RevenueSummary,
  TopProductsResponse,
  LowStockAlertListResponse,
  VisitorStatsResponse,
  KPISummary,
  TopCustomersResponse,
  ARAgingResponse,
  APAgingResponse,
  GrossMarginResponse,
  CashFlowResponse,
  RevenueTrendResponse,
  RevenueTrendItem,
} from "../types";

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

export function useKPISummary() {
  const [data, setData] = useState<KPISummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchKPISummary();
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load KPI summary");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { data, isLoading, error, refetch };
}

export function useTopCustomers(initialPeriod: "month" | "quarter" | "year" = "month") {
  const [data, setData] = useState<TopCustomersResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState(initialPeriod);
  const [anchorDate, setAnchorDate] = useState(() => appTodayISO());

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchTopCustomers(period, anchorDate);
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load top customers");
    } finally {
      setIsLoading(false);
    }
  }, [anchorDate, period]);

  useEffect(() => {
    void load();
  }, [load]);

  const refetch = useCallback(async () => {
    await load();
  }, [load]);

  return { data, isLoading, error, refetch, period, setPeriod, anchorDate, setAnchorDate };
}

export function useARAging() {
  const [data, setData] = useState<ARAgingResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchARAging();
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load AR aging");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const refetch = useCallback(async () => {
    await load();
  }, [load]);

  return { data, isLoading, error, refetch };
}

export function useAPAging() {
  const [data, setData] = useState<APAgingResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchAPAging();
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load AP aging");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const refetch = useCallback(async () => {
    await load();
  }, [load]);

  return { data, isLoading, error, refetch };
}

export function useGrossMargin() {
  const [data, setData] = useState<GrossMarginResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setIsLoading(true);
    fetchGrossMargin()
      .then(setData)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load gross margin"),
      )
      .finally(() => setIsLoading(false));
  }, []);

  const refetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchGrossMargin();
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load gross margin");
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { data, isLoading, error, refetch };
}

export function useCashFlow() {
  const [data, setData] = useState<CashFlowResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchCashFlow();
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load cash flow");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const refetch = useCallback(async () => {
    await load();
  }, [load]);

  return { data, isLoading, error, refetch };
}

export function useRevenueTrend(period: "month" | "quarter" | "year" = "month") {
  const [allItems, setAllItems] = useState<RevenueTrendItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  const latestItemsRef = useRef<RevenueTrendItem[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const load = useCallback(async (before: string | null = null) => {
    // Cancel any in-flight request
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    if (!before) setIsLoading(true);
    else setIsLoadingMore(true);
    setError(null);
    try {
      const res = await fetchRevenueTrend(period, before);
      // Guard: if request was aborted, ignore response
      if (abortRef.current?.signal.aborted) return;
      if (!before) {
        latestItemsRef.current = res.items;
        setAllItems(res.items);
      } else {
        const newItems = [...res.items, ...latestItemsRef.current];
        latestItemsRef.current = newItems;
        setAllItems(newItems);
      }
      setHasMore(res.has_more ?? false);
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      setError(err instanceof Error ? err.message : "Failed to load revenue trend");
    } finally {
      if (!before) setIsLoading(false);
      else setIsLoadingMore(false);
    }
  }, [period]);

  useEffect(() => {
    latestItemsRef.current = [];
    setAllItems([]);
    abortRef.current?.abort();
    void load(null);
  }, [load]);

  const refetch = useCallback(async () => {
    latestItemsRef.current = [];
    setAllItems([]);
    await load(null);
  }, [load]);

  const loadMore = useCallback(async () => {
    if (isLoadingMore || !hasMore || !latestItemsRef.current.length) return;
    const oldest = latestItemsRef.current[0]?.date;
    if (!oldest) return;
    await load(oldest);
  }, [hasMore, isLoadingMore, load]);

  const data: RevenueTrendResponse | null = allItems.length > 0
    ? { items: allItems, start_date: allItems[0].date, end_date: allItems[allItems.length - 1].date, has_more: hasMore }
    : null;

  return { data, isLoading, isLoadingMore, error, refetch, hasMore, loadMore };
}
