/** Hook for fetching top customer for a product. */

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../../../lib/apiFetch";

export interface TopCustomer {
  customer_id: string;
  customer_name: string;
  total_qty: number;
}

export function useProductTopCustomer(productId: string) {
  const [customer, setCustomer] = useState<TopCustomer | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!productId) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await apiFetch(
        `/api/v1/inventory/products/${encodeURIComponent(productId)}/top-customer`,
      );
      if (resp.status === 204) {
        setCustomer(null);
        return;
      }
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        setError((body as { detail?: string }).detail ?? "Failed to load top customer");
        return;
      }
      const data = (await resp.json()) as TopCustomer;
      setCustomer(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load top customer");
    } finally {
      setLoading(false);
    }
  }, [productId]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { customer, loading, error, refetch };
}
