/** Hooks for dashboard domain. */

import { useCallback, useEffect, useState } from "react";

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

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchTopCustomers(period);
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load top customers");
    } finally {
      setIsLoading(false);
    }
  }, [period]);

  useEffect(() => {
    void load();
  }, [load]);

  const refetch = useCallback(async () => {
    await load();
  }, [load]);

  return { data, isLoading, error, refetch, period, setPeriod };
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

  return { data, isLoading, error };
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

export function useRevenueTrend(initialPeriod: "month" | "quarter" | "year" = "month") {
  const [data, setData] = useState<RevenueTrendResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState(initialPeriod);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchRevenueTrend(period === "month" ? "month" : "week");
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load revenue trend");
    } finally {
      setIsLoading(false);
    }
  }, [period]);

  useEffect(() => {
    void load();
  }, [load]);

  const refetch = useCallback(async () => {
    await load();
  }, [load]);

  return { data, isLoading, error, refetch, period, setPeriod };
}
