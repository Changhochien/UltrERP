/** useGoodsReceipt hook - Goods Receipt list and detail management. */

import { useCallback, useEffect, useState } from "react";
import {
  createGoodsReceipt,
  listGoodsReceipts,
  getGoodsReceipt,
  submitGoodsReceipt,
  cancelGoodsReceipt,
  listReceiptsForPO,
} from "@/lib/api/procurement";
import type {
  GoodsReceiptCreatePayload,
  GoodsReceiptListResponse,
  GoodsReceiptResponse,
} from "../types";

export interface UseGoodsReceiptListOptions {
  purchaseOrderId?: string;
  status?: string;
  q?: string;
  page?: number;
  pageSize?: number;
}

export interface UseGoodsReceiptListResult {
  data: GoodsReceiptListResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useGoodsReceiptList(
  options: UseGoodsReceiptListOptions = {},
): UseGoodsReceiptListResult {
  const [data, setData] = useState<GoodsReceiptListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refetch = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    listGoodsReceipts({
      purchase_order_id: options.purchaseOrderId,
      status: options.status,
      q: options.q,
      page: options.page ?? 1,
      page_size: options.pageSize ?? 20,
    })
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
  }, [
    refreshKey,
    options.purchaseOrderId,
    options.status,
    options.q,
    options.page,
    options.pageSize,
  ]);

  return { data, loading, error, refetch };
}

export interface UseGoodsReceiptResult {
  data: GoodsReceiptResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useGoodsReceipt(grId: string | null): UseGoodsReceiptResult {
  const [data, setData] = useState<GoodsReceiptResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refetch = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    if (!grId) {
      setData(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    getGoodsReceipt(grId)
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
  }, [grId, refreshKey]);

  return { data, loading, error, refetch };
}

export interface UseReceiptsForPOOptions {
  status?: string;
  page?: number;
  pageSize?: number;
}

export interface UseReceiptsForPOResult {
  data: GoodsReceiptListResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useReceiptsForPO(
  poId: string | null,
  options: UseReceiptsForPOOptions = {},
): UseReceiptsForPOResult {
  const [data, setData] = useState<GoodsReceiptListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refetch = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    if (!poId) {
      setData(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    listReceiptsForPO(poId, {
      status: options.status,
      page: options.page ?? 1,
      page_size: options.pageSize ?? 20,
    })
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
  }, [poId, refreshKey, options.status, options.page, options.pageSize]);

  return { data, loading, error, refetch };
}

export interface GoodsReceiptActions {
  create: (payload: GoodsReceiptCreatePayload) => Promise<GoodsReceiptResponse>;
  submit: (grId: string) => Promise<GoodsReceiptResponse>;
  cancel: (grId: string) => Promise<GoodsReceiptResponse>;
}

export function useGoodsReceiptActions(): GoodsReceiptActions {
  const create = useCallback((payload: GoodsReceiptCreatePayload) => createGoodsReceipt(payload), []);
  const submit = useCallback((grId: string) => submitGoodsReceipt(grId), []);
  const cancel = useCallback((grId: string) => cancelGoodsReceipt(grId), []);

  return { create, submit, cancel };
}
