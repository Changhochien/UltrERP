import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../../../lib/apiFetch";

export interface ProductSupplierInfo {
  supplier_id: string;
  name: string;
  unit_cost: number | null;
  default_lead_time_days: number | null;
}

export function useProductSupplier(productId: string | null) {
  const [supplier, setSupplier] = useState<ProductSupplierInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!productId) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await apiFetch(
        `/api/v1/inventory/products/${encodeURIComponent(productId)}/supplier`,
      );
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        setError((body as { detail?: string }).detail ?? "Failed to load supplier");
        return;
      }
      const data = await resp.json().catch(() => null);
      setSupplier(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load supplier");
    } finally {
      setLoading(false);
    }
  }, [productId]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { supplier, loading, error, refetch };
}
