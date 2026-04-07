import { useCallback, useEffect, useState } from "react";
import type { ProductDetail } from "../types";
import { fetchProductDetail } from "../../../lib/api/inventory";

export function useProductDetail(productId: string | null) {
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!productId) return;
    setLoading(true);
    setError(null);
    setProduct(null);
    try {
      const res = await fetchProductDetail(productId);
      if (res.ok) {
        setProduct(res.data);
      } else {
        setError(res.error);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [productId]);

  useEffect(() => {
    void load();
  }, [load]);

  return { product, loading, error, reload: load };
}
