/** Hooks for orders domain. */

import { useCallback, useEffect, useState } from "react";

import {
  createOrder,
  fetchOrder,
  fetchOrders,
  fetchPaymentTerms,
} from "../../../lib/api/orders";
import type {
  OrderCreatePayload,
  OrderListItem,
  OrderResponse,
  OrderStatus,
  PaymentTermsItem,
} from "../types";

/* ── Payment terms hook ────────────────────────────────────── */

export function usePaymentTerms() {
  const [items, setItems] = useState<PaymentTermsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPaymentTerms()
      .then((res) => setItems(res.items))
      .catch((err) => {
        setItems([]);
        setError(err instanceof Error ? err.message : "Failed to load payment terms");
      })
      .finally(() => setLoading(false));
  }, []);

  return { items, loading, error };
}

/* ── Order list hook ───────────────────────────────────────── */

export function useOrders(options?: {
  status?: string | string[];
  customerId?: string;
  dateFrom?: string;
  dateTo?: string;
  search?: string;
  sortBy?: string;
  sortOrder?: string;
}) {
  const [items, setItems] = useState<OrderListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async (pageNum = 1) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchOrders({
        status: options?.status,
        customer_id: options?.customerId,
        date_from: options?.dateFrom,
        date_to: options?.dateTo,
        search: options?.search,
        sort_by: options?.sortBy,
        sort_order: options?.sortOrder,
        page: pageNum,
      });
      setItems(res.items);
      setTotal(res.total);
      setPage(res.page);
      setPageSize(res.page_size);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [options?.status, options?.customerId, options?.dateFrom, options?.dateTo, options?.search, options?.sortBy, options?.sortOrder]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { items, total, page, pageSize, loading, error, reload };
}

/* ── Order detail hook ─────────────────────────────────────── */

export function useOrderDetail(orderId: string | null) {
  const [order, setOrder] = useState<OrderResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!orderId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchOrder(orderId);
      setOrder(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Not found");
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { order, loading, error, reload };
}

/* ── Create order action ───────────────────────────────────── */

export function useCreateOrder() {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Array<{ field: string; message: string }>>([]);

  const create = useCallback(
    async (payload: OrderCreatePayload): Promise<OrderResponse | null> => {
      setSubmitting(true);
      setError(null);
      setFieldErrors([]);
      try {
        const res = await createOrder(payload);
        if (!res.ok) {
          setFieldErrors(res.errors);
          const msg = res.errors.find((e) => !e.field)?.message ?? res.errors[0]?.message ?? "Failed to create order";
          setError(msg);
          return null;
        }
        return res.data;
      } finally {
        setSubmitting(false);
      }
    },
    [],
  );

  return { create, submitting, error, fieldErrors };
}

/* ── Status helpers ────────────────────────────────────────── */

const STATUS_LABELS: Record<OrderStatus, string> = {
  pending: "Pending",
  confirmed: "Confirmed",
  shipped: "Shipped",
  fulfilled: "Fulfilled",
  cancelled: "Cancelled",
};

export function statusLabel(s: OrderStatus): string {
  return STATUS_LABELS[s] ?? s;
}

type OrderStatusBadgeVariant = "neutral" | "info" | "success" | "destructive";

const STATUS_BADGE_VARIANTS: Record<OrderStatus, OrderStatusBadgeVariant> = {
  pending: "neutral",
  confirmed: "info",
  shipped: "info",
  fulfilled: "success",
  cancelled: "destructive",
};

export function statusBadgeVariant(s: OrderStatus): OrderStatusBadgeVariant {
  return STATUS_BADGE_VARIANTS[s] ?? "neutral";
}
