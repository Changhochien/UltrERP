/** Hook for checking stock availability — debounced per product. */

import { useCallback, useEffect, useRef, useState } from "react";

import { checkStock } from "../../../lib/api/orders";
import type { StockCheckResponse } from "../types";

export function useStockCheck(debounceMs = 300) {
  const [cache, setCache] = useState<Record<string, StockCheckResponse>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const cacheRef = useRef(cache);
  const timerRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  // Keep ref in sync with state
  useEffect(() => {
    cacheRef.current = cache;
  }, [cache]);

  const check = useCallback(
    (productId: string) => {
      if (!productId) return;

      // Already cached — use ref to avoid dep on cache state
      if (cacheRef.current[productId]) return;

      // Clear pending timer for this product
      if (timerRef.current[productId]) {
        clearTimeout(timerRef.current[productId]);
      }

      setLoading((prev) => ({ ...prev, [productId]: true }));

      timerRef.current[productId] = setTimeout(async () => {
        try {
          const data = await checkStock(productId);
          setCache((prev) => ({ ...prev, [productId]: data }));
        } catch {
          // Silently fail — stock display is informational
        } finally {
          setLoading((prev) => ({ ...prev, [productId]: false }));
        }
      }, debounceMs);
    },
    [debounceMs],
  );

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      for (const t of Object.values(timerRef.current)) {
        clearTimeout(t);
      }
    };
  }, []);

  return { stockData: cache, stockLoading: loading, checkProductStock: check };
}
