import { useCallback, useEffect, useState } from "react";

import {
  createSupplierOrder,
  fetchSupplierOrder,
  fetchSupplierOrders,
  fetchSuppliers,
  receiveSupplierOrder,
  updateSupplierOrderStatus,
} from "../../../lib/api/inventory";
import type {
  CreateSupplierOrderRequest,
  ReceiveOrderRequest,
  Supplier,
  SupplierOrder,
  SupplierOrderListItem,
  SupplierOrderStatus,
  UpdateOrderStatusRequest,
} from "../types";

/* ── Suppliers hook ────────────────────────────────────────── */

export function useSuppliers() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetchSuppliers();
        if (!cancelled) {
          if (res.ok) setSuppliers(res.data.items);
          else setError(res.error);
        }
      } catch (err) {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return { suppliers, loading, error };
}

/* ── Supplier order list hook ──────────────────────────────── */

export function useSupplierOrders(options?: {
  status?: string;
  supplierId?: string;
}) {
  const [items, setItems] = useState<SupplierOrderListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchSupplierOrders({
        status: options?.status,
        supplierId: options?.supplierId,
      });
      if (res.ok) {
        setItems(res.data.items);
        setTotal(res.data.total);
      } else {
        setError(res.error);
        setItems([]);
        setTotal(0);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [options?.status, options?.supplierId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { items, total, loading, error, reload };
}

/* ── Supplier order detail hook ────────────────────────────── */

export function useSupplierOrderDetail(orderId: string | null) {
  const [order, setOrder] = useState<SupplierOrder | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!orderId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchSupplierOrder(orderId);
      if (res.ok) {
        setOrder(res.data);
      } else {
        setError(res.error);
      }
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

export function useCreateSupplierOrder() {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = useCallback(
    async (
      payload: CreateSupplierOrderRequest,
    ): Promise<SupplierOrder | null> => {
      setSubmitting(true);
      setError(null);
      try {
        const res = await createSupplierOrder(payload);
        if (res.ok) return res.data;
        setError(res.error);
        return null;
      } catch {
        setError("Network error");
        return null;
      } finally {
        setSubmitting(false);
      }
    },
    [],
  );

  return { create, submitting, error };
}

/* ── Status update action ──────────────────────────────────── */

export function useUpdateOrderStatus() {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateStatus = useCallback(
    async (
      orderId: string,
      payload: UpdateOrderStatusRequest,
    ): Promise<SupplierOrder | null> => {
      setSubmitting(true);
      setError(null);
      try {
        const res = await updateSupplierOrderStatus(orderId, payload);
        if (res.ok) return res.data;
        setError(res.error);
        return null;
      } catch {
        setError("Network error");
        return null;
      } finally {
        setSubmitting(false);
      }
    },
    [],
  );

  return { updateStatus, submitting, error };
}

/* ── Receive order action ──────────────────────────────────── */

export function useReceiveOrder() {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const receive = useCallback(
    async (
      orderId: string,
      payload?: ReceiveOrderRequest,
    ): Promise<SupplierOrder | null> => {
      setSubmitting(true);
      setError(null);
      try {
        const res = await receiveSupplierOrder(orderId, payload);
        if (res.ok) return res.data;
        setError(res.error);
        return null;
      } catch {
        setError("Network error");
        return null;
      } finally {
        setSubmitting(false);
      }
    },
    [],
  );

  return { receive, submitting, error };
}

/* ── Status helpers ────────────────────────────────────────── */

const STATUS_LABELS: Record<SupplierOrderStatus, string> = {
  pending: "Pending",
  confirmed: "Confirmed",
  shipped: "Shipped",
  partially_received: "Partially Received",
  received: "Received",
  cancelled: "Cancelled",
};

export function statusLabel(s: SupplierOrderStatus): string {
  return STATUS_LABELS[s] ?? s;
}

type SupplierOrderStatusBadgeVariant = "neutral" | "info" | "success" | "warning" | "destructive";

const STATUS_BADGE_VARIANTS: Record<SupplierOrderStatus, SupplierOrderStatusBadgeVariant> = {
  pending: "neutral",
  confirmed: "info",
  shipped: "info",
  partially_received: "warning",
  received: "success",
  cancelled: "destructive",
};

export function statusBadgeVariant(s: SupplierOrderStatus): SupplierOrderStatusBadgeVariant {
  return STATUS_BADGE_VARIANTS[s] ?? "neutral";
}
