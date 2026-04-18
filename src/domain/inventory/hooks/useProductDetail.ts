import { useCallback, useEffect, useRef, useState } from "react";
import type { ProductDetail, ProductResponse } from "../types";
import { fetchProductDetail } from "../../../lib/api/inventory";

const UNKNOWN_ERROR = "Unknown error";

export function useProductDetail(productId: string | null) {
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const load = useCallback(async (clearFirst = false) => {
    if (!productId) {
      abortRef.current?.abort();
      abortRef.current = null;
      setProduct(null);
      setError(null);
      setLoading(false);
      return;
    }
    if (abortRef.current) {
      abortRef.current.abort();
    }
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    if (clearFirst) {
      setProduct(null);
    }
    try {
      const res = await fetchProductDetail(productId, { signal: controller.signal });
      if (res.ok) {
        setProduct(res.data);
        setError(null);
      } else {
        setProduct(null);
        setError(res.error);
      }
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        return;
      }
      setProduct(null);
      setError(err instanceof Error ? err.message : UNKNOWN_ERROR);
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
        setLoading(false);
      }
    }
  }, [productId]);

  useEffect(() => {
    void load();
    return () => {
      abortRef.current?.abort();
    };
  }, [load]);

  const reload = useCallback(async () => {
    await load(true);
  }, [load]);

  const applyLocalUpdate = useCallback((updated: ProductResponse) => {
    setProduct((current) => {
      if (!current) return current;
      if (
        current.code === updated.code &&
        current.name === updated.name &&
        current.category === updated.category &&
        current.description === updated.description &&
        current.unit === updated.unit &&
        current.standard_cost === updated.standard_cost &&
        current.status === updated.status
      ) {
        return current;
      }
      return {
        ...current,
        code: updated.code,
        name: updated.name,
        category: updated.category,
        description: updated.description,
        unit: updated.unit,
        standard_cost: updated.standard_cost,
        status: updated.status,
      };
    });
  }, []);

  return { product, loading, error, reload, applyLocalUpdate };
}
