/** Hook for paginated product search with server-side sorting. */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ProductSearchResult } from "../types";
import { searchProducts } from "../../../lib/api/inventory";
import type { DataTableSortState } from "../../../components/layout/DataTable";

const PAGE_SIZE = 20;

export function useProductSearch(debounceMs = 300) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ProductSearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [sortState, setSortState] = useState<DataTableSortState | null>(null);
  const [currentWarehouseId, setCurrentWarehouseId] = useState<string | undefined>(undefined);
  const [currentCategory, setCurrentCategory] = useState<string>("");
  const [includeInactive, setIncludeInactive] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const search = useCallback(
    (
      q: string,
      warehouseId?: string,
      pageNum = 1,
      sort?: DataTableSortState | null,
      nextIncludeInactive = includeInactive,
      category = currentCategory,
    ) => {
      setQuery(q);
      setError(null);
      setPage(pageNum);
      setCurrentWarehouseId(warehouseId);
      setCurrentCategory(category);
      setIncludeInactive(nextIncludeInactive);
      if (sort) setSortState(sort);

      if (timerRef.current) clearTimeout(timerRef.current);
      if (abortRef.current) abortRef.current.abort();

      const trimmed = q.trim();

      setLoading(true);
      timerRef.current = setTimeout(async () => {
        const controller = new AbortController();
        abortRef.current = controller;
        try {
          const resp = await searchProducts(trimmed, {
            limit: PAGE_SIZE,
            offset: (pageNum - 1) * PAGE_SIZE,
            category: category || undefined,
            warehouseId,
            includeInactive: nextIncludeInactive,
            sortBy: sort?.columnId ?? "code",
            sortDir: sort?.direction ?? "asc",
            signal: controller.signal,
          });
          if (!controller.signal.aborted) {
            setResults(resp.items);
            setTotal(resp.total);
            setPage(pageNum);
          }
        } catch {
          if (!controller.signal.aborted) {
            setError("Search failed — please try again.");
            setResults([]);
            setTotal(0);
          }
        } finally {
          if (!controller.signal.aborted) {
            setLoading(false);
          }
        }
      }, debounceMs);
    },
    [currentCategory, debounceMs, includeInactive],
  );

  const nextPage = useCallback(() => {
    if (page * PAGE_SIZE < total) {
      search(query, currentWarehouseId, page + 1, sortState ?? undefined, includeInactive, currentCategory);
    }
  }, [currentCategory, currentWarehouseId, includeInactive, page, total, query, search, sortState]);

  const prevPage = useCallback(() => {
    if (page > 1) {
      search(query, currentWarehouseId, page - 1, sortState ?? undefined, includeInactive, currentCategory);
    }
  }, [currentCategory, currentWarehouseId, includeInactive, page, query, search, sortState]);

  const setSort = useCallback(
    (sort: DataTableSortState | null) => {
      setSortState(sort);
      search(query, currentWarehouseId, 1, sort, includeInactive, currentCategory);
    },
    [currentCategory, currentWarehouseId, includeInactive, query, search],
  );

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (abortRef.current) abortRef.current.abort();
    };
  }, []);

  return {
    query,
    results,
    total,
    page,
    pageSize: PAGE_SIZE,
    loading,
    error,
    includeInactive,
    category: currentCategory,
    search,
    nextPage,
    prevPage,
    sortState,
    setSort,
  };
}
