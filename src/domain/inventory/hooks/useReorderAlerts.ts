/** Hook for fetching and managing reorder alerts. */

import { useCallback, useEffect, useState } from "react";

import type { ReorderAlertItem } from "../types";
import { acknowledgeAlert, fetchReorderAlerts } from "../../../lib/api/inventory";

export function useReorderAlerts(filters?: {
  status?: string;
  warehouseId?: string;
}) {
  const [alerts, setAlerts] = useState<ReorderAlertItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchReorderAlerts({
        status: filters?.status,
        warehouseId: filters?.warehouseId,
      });
      setAlerts(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load alerts");
    } finally {
      setLoading(false);
    }
  }, [filters?.status, filters?.warehouseId]);

  useEffect(() => {
    void load();
  }, [load]);

  return { alerts, total, loading, error, reload: load };
}

export function useAcknowledgeAlert() {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const acknowledge = useCallback(async (alertId: string) => {
    setSubmitting(true);
    setError(null);
    try {
      const result = await acknowledgeAlert(alertId);
      if (!result.ok) {
        setError(result.error);
        return false;
      }
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to acknowledge");
      return false;
    } finally {
      setSubmitting(false);
    }
  }, []);

  return { acknowledge, submitting, error };
}
