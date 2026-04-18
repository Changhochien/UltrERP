import { useCallback, useEffect, useState } from "react";
import type { ProductDetail, ProductResponse } from "../types";
import { fetchProductDetail } from "../../../lib/api/inventory";

export function useProductDetail(productId: string | null) {
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (preserveCurrent = false) => {
    if (!productId) return;
    setLoading(true);
    setError(null);
    if (!preserveCurrent) {
      setProduct(null);
    }
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

  const reload = useCallback(async () => {
    await load(true);
  }, [load]);

  const applyLocalUpdate = useCallback((updated: ProductResponse) => {
    setProduct((current) => {
      if (!current) {
        return current;
      }
      return {
        ...current,
        code: updated.code,
        name: updated.name,
        category: updated.category,
        description: updated.description,
        unit: updated.unit,
        status: updated.status,
      };
    });
  }, []);

  return { product, loading, error, reload, applyLocalUpdate };
}
