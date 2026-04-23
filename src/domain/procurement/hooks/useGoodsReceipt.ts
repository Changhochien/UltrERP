/** useGoodsReceipt hook - Goods Receipt list and detail management. */

import { useCallback, useEffect, useState } from "react";
import {
  createGoodsReceipt,
  listGoodsReceipts,
  getGoodsReceipt,
  submitGoodsReceipt,
  cancelGoodsReceipt,
} from "@/lib/api/procurement";
import type {
  GoodsReceiptCreatePayload,
  GoodsReceiptListResponse,
  GoodsReceiptResponse,
} from "../types";

// --------------------------------------------------------------------------
// Shared fetch pattern hook
// --------------------------------------------------------------------------

interface UseFetchState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

function useFetch<T>(
  fetchFn: () => Promise<T>,
  deps: unknown[],
): UseFetchState<T> {
  const [refreshKey, setRefreshKey] = useState(0);
  const [state, setState] = useState<UseFetchState<T>>({
    data: null,
    loading: true,
    error: null,
    refresh: () => setRefreshKey((k) => k + 1),
  });

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));

    fetchFn()
      .then((result) => {
        if (!cancelled) setState({ data: result, loading: false, error: null, refresh: state.refresh });
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ data: null, loading: false, error: err.message, refresh: state.refresh });
      });

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey, ...deps]);

  return state;
}

// --------------------------------------------------------------------------
// Hooks
// --------------------------------------------------------------------------

export function useGoodsReceiptList(options: {
  purchaseOrderId?: string;
  status?: string;
  q?: string;
  page?: number;
  pageSize?: number;
} = {}) {
  const { data, loading, error, refresh } = useFetch(
    () => listGoodsReceipts({
      purchase_order_id: options.purchaseOrderId,
      status: options.status,
      q: options.q,
      page: options.page ?? 1,
      page_size: options.pageSize ?? 20,
    }),
    [options.purchaseOrderId, options.status, options.q, options.page, options.pageSize],
  );
  return { data: data as GoodsReceiptListResponse | null, loading, error, refetch: refresh };
}

export function useGoodsReceipt(grId: string | null) {
  const { data, loading, error, refresh } = useFetch(
    () => grId ? getGoodsReceipt(grId) : Promise.resolve(null),
    [grId],
  );
  return { data: data as GoodsReceiptResponse | null, loading, error, refetch: refresh };
}

export function useReceiptsForPO(poId: string | null, options: { status?: string; page?: number; pageSize?: number } = {}) {
  const { data, loading, error, refresh } = useFetch(
    () => poId ? listGoodsReceipts({
      purchase_order_id: poId,
      status: options.status,
      page: options.page ?? 1,
      page_size: options.pageSize ?? 100,
    }) : Promise.resolve(null),
    [poId, options.status, options.page, options.pageSize],
  );
  return { data: data as GoodsReceiptListResponse | null, loading, error, refetch: refresh };
}

// --------------------------------------------------------------------------
// Actions
// --------------------------------------------------------------------------

export function useGoodsReceiptActions() {
  const create = useCallback((payload: GoodsReceiptCreatePayload) => createGoodsReceipt(payload), []);
  const submit = useCallback((grId: string) => submitGoodsReceipt(grId), []);
  const cancel = useCallback((grId: string) => cancelGoodsReceipt(grId), []);
  return { create, submit, cancel };
}
