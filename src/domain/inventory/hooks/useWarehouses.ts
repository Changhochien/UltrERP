/** Hook for fetching warehouse list. */

import { useCallback, useEffect, useState } from "react";
import type { Warehouse } from "../types";
import { fetchWarehouses } from "../../../lib/api/inventory";

export function useWarehouses(activeOnly = true) {
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchWarehouses(activeOnly);
      setWarehouses(data.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load warehouses");
    } finally {
      setLoading(false);
    }
  }, [activeOnly]);

  useEffect(() => {
    load();
  }, [load]);

  return { warehouses, loading, error, reload: load };
}
