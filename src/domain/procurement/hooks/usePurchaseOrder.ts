/**
 * usePurchaseOrder hook - Purchase Order list and detail management.
 */

import { useCallback, useEffect, useState } from "react";
import {
  createPOFromAward,
  listPurchaseOrders,
  getPurchaseOrder,
  submitPurchaseOrder,
  holdPurchaseOrder,
  releasePurchaseOrder,
  completePurchaseOrder,
  cancelPurchaseOrder,
  closePurchaseOrder,
} from "@/lib/api/procurement";
import type {
  PurchaseOrderListResponse,
  PurchaseOrderResponse,
} from "../types";

export interface UsePurchaseOrderListOptions {
  status?: string;
  supplierId?: string;
  q?: string;
  page?: number;
  pageSize?: number;
}

export interface UsePurchaseOrderListResult {
  data: PurchaseOrderListResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function usePurchaseOrderList(
  options: UsePurchaseOrderListOptions = {},
): UsePurchaseOrderListResult {
  const [data, setData] = useState<PurchaseOrderListResponse | null>(null);
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

    listPurchaseOrders({
      status: options.status,
      supplier_id: options.supplierId,
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
    options.status,
    options.supplierId,
    options.q,
    options.page,
    options.pageSize,
  ]);

  return { data, loading, error, refetch };
}

export interface UsePurchaseOrderResult {
  data: PurchaseOrderResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function usePurchaseOrder(poId: string | null): UsePurchaseOrderResult {
  const [data, setData] = useState<PurchaseOrderResponse | null>(null);
  const [loading, setLoading] = useState(false);
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

    getPurchaseOrder(poId)
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
  }, [poId, refreshKey]);

  return { data, loading, error, refetch };
}

export interface PurchaseOrderActions {
  createFromAward: (awardId: string) => Promise<PurchaseOrderResponse>;
  submit: (poId: string) => Promise<PurchaseOrderResponse>;
  hold: (poId: string) => Promise<PurchaseOrderResponse>;
  release: (poId: string) => Promise<PurchaseOrderResponse>;
  complete: (poId: string) => Promise<PurchaseOrderResponse>;
  cancel: (poId: string) => Promise<PurchaseOrderResponse>;
  close: (poId: string) => Promise<PurchaseOrderResponse>;
}

export function usePurchaseOrderActions(): PurchaseOrderActions {
  const createFromAward = useCallback((awardId: string) => createPOFromAward(awardId), []);
  const submit = useCallback((poId: string) => submitPurchaseOrder(poId), []);
  const hold = useCallback((poId: string) => holdPurchaseOrder(poId), []);
  const release = useCallback((poId: string) => releasePurchaseOrder(poId), []);
  const complete = useCallback((poId: string) => completePurchaseOrder(poId), []);
  const cancel = useCallback((poId: string) => cancelPurchaseOrder(poId), []);
  const close = useCallback((poId: string) => closePurchaseOrder(poId), []);

  return { createFromAward, submit, hold, release, complete, cancel, close };
}
