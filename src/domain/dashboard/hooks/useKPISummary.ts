/** Hook for KPI summary data. */

import { useCallback, useEffect, useState } from "react";

import { fetchKPISummary } from "../../../lib/api/dashboard";
import type { KPISummary } from "../types";

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
  }, []);

  return { data, isLoading, error, refetch };
}
