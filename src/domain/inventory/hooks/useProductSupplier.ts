import { useCallback, useEffect, useState } from "react";

import { fetchProductSupplier } from "../../../lib/api/inventory";
import type { ProductSupplierInfo } from "../types";

export function useProductSupplier(productId: string | null) {
  const [supplier, setSupplier] = useState<ProductSupplierInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!productId) return;
    setLoading(true);
    setError(null);
    const response = await fetchProductSupplier(productId);
    if (response.ok) {
      setSupplier(response.data);
    } else {
      setSupplier(null);
      setError(response.error);
    }
    setLoading(false);
  }, [productId]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { supplier, loading, error, refetch };
}
