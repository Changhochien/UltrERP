import { useEffect, useState } from "react";

import { getSupplierControls } from "@/lib/api/procurement";
import type { SupplierControlsStatus } from "../types";

interface UseSupplierControlsResult {
  data: SupplierControlsStatus | null;
  loading: boolean;
  error: string | null;
}

export function useSupplierControls(supplierId: string | null): UseSupplierControlsResult {
  const [data, setData] = useState<SupplierControlsStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!supplierId) {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    getSupplierControls(supplierId)
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setLoading(false);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [supplierId]);

  return { data, loading, error };
}