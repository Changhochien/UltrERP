/** Hook for fetching audit log for a product. */

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../../../lib/apiFetch";

export interface AuditLogItem {
  id: string;
  created_at: string;
  actor_id: string;
  field: string;
  old_value: string | null;
  new_value: string | null;
}

export interface AuditLogResponse {
  items: AuditLogItem[];
  total: number;
}

export function useProductAuditLog(
  productId: string,
  options?: { limit?: number; offset?: number },
) {
  const [items, setItems] = useState<AuditLogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!productId) return;
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (options?.limit != null) params.set("limit", String(options.limit));
      if (options?.offset != null) params.set("offset", String(options.offset));
      const qs = params.toString();
      const url = `/api/v1/inventory/products/${encodeURIComponent(productId)}/audit-log${qs ? `?${qs}` : ""}`;
      const resp = await apiFetch(url);
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        setError((body as { detail?: string }).detail ?? "Failed to load audit log");
        return;
      }
      const data = (await resp.json()) as AuditLogResponse;
      setItems(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load audit log");
    } finally {
      setLoading(false);
    }
  }, [productId, options?.limit, options?.offset]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { items, total, loading, error, refetch };
}
