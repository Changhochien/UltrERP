/** Hook for debounced product search. */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ProductSearchResult } from "../types";
import { searchProducts } from "../../../lib/api/inventory";

export function useProductSearch(debounceMs = 300) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ProductSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const search = useCallback(
    (q: string, warehouseId?: string) => {
      setQuery(q);
      setError(null);

      if (timerRef.current) clearTimeout(timerRef.current);
      if (abortRef.current) abortRef.current.abort();

      const trimmed = q.trim();
      if (trimmed.length < 3) {
        setResults([]);
        setLoading(false);
        return;
      }

      setLoading(true);
      timerRef.current = setTimeout(async () => {
        const controller = new AbortController();
        abortRef.current = controller;
        try {
          const resp = await searchProducts(trimmed, {
            limit: 100,
            warehouseId,
            signal: controller.signal,
          });
          if (!controller.signal.aborted) {
            setResults(resp.items);
          }
        } catch {
          if (!controller.signal.aborted) {
            setError("Search failed — please try again.");
            setResults([]);
          }
        } finally {
          if (!controller.signal.aborted) {
            setLoading(false);
          }
        }
      }, debounceMs);
    },
    [debounceMs],
  );

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (abortRef.current) abortRef.current.abort();
    };
  }, []);

  return { query, results, loading, error, search };
}
