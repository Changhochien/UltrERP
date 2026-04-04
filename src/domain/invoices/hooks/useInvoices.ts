/** Hooks for invoices domain. */

import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchCustomerOutstanding,
  fetchInvoice,
  fetchInvoices,
  refreshInvoiceEguiStatus,
} from "../../../lib/api/invoices";
import type {
  CustomerOutstandingSummary,
  InvoiceListItem,
  InvoiceResponse,
} from "../types";

/* ── Invoice list hook ─────────────────────────────────────── */

export function useInvoices(options?: {
  payment_status?: string;
  sort_by?: string;
  sort_order?: string;
}) {
  const [items, setItems] = useState<InvoiceListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (p: number) => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetchInvoices({
          payment_status: options?.payment_status,
          sort_by: options?.sort_by,
          sort_order: options?.sort_order,
          page: p,
          page_size: pageSize,
        });
        setItems(res.items);
        setTotal(res.total);
        setPage(p);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load invoices");
      } finally {
        setLoading(false);
      }
    },
    [options?.payment_status, options?.sort_by, options?.sort_order, pageSize],
  );

  useEffect(() => {
    void load(1);
  }, [load]);

  return { items, total, page, pageSize, loading, error, reload: load };
}

/* ── Single invoice hook ───────────────────────────────────── */

export function useInvoice(invoiceId: string) {
  const [invoice, setInvoice] = useState<InvoiceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [eguiError, setEguiError] = useState<string | null>(null);
  const [refreshingEgui, setRefreshingEgui] = useState(false);
  const activeRequestIdRef = useRef(0);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      activeRequestIdRef.current += 1;
    };
  }, []);

  const load = useCallback(async () => {
    const requestId = ++activeRequestIdRef.current;
    setLoading(true);
    setLoadError(null);
    setEguiError(null);
    try {
      const nextInvoice = await fetchInvoice(invoiceId);
      if (!mountedRef.current || activeRequestIdRef.current !== requestId) {
        return;
      }
      setInvoice(nextInvoice);
    } catch (err) {
      if (!mountedRef.current || activeRequestIdRef.current !== requestId) {
        return;
      }
      setLoadError(err instanceof Error ? err.message : "Failed to load invoice");
    } finally {
      if (mountedRef.current && activeRequestIdRef.current === requestId) {
        setLoading(false);
      }
    }
  }, [invoiceId]);

  useEffect(() => {
    void load();
  }, [load]);

  const refreshEgui = useCallback(async () => {
    const requestId = ++activeRequestIdRef.current;
    setRefreshingEgui(true);
    setEguiError(null);
    try {
      const eguiSubmission = await refreshInvoiceEguiStatus(invoiceId);
      if (!mountedRef.current || activeRequestIdRef.current !== requestId) {
        return;
      }
      setInvoice((currentInvoice) => {
        if (!currentInvoice) {
          return currentInvoice;
        }
        return {
          ...currentInvoice,
          egui_submission: eguiSubmission,
        };
      });
    } catch (err) {
      if (!mountedRef.current || activeRequestIdRef.current !== requestId) {
        return;
      }
      setEguiError(
        err instanceof Error ? err.message : "Failed to refresh eGUI status",
      );
    } finally {
      if (mountedRef.current && activeRequestIdRef.current === requestId) {
        setRefreshingEgui(false);
      }
    }
  }, [invoiceId]);

  return {
    invoice,
    loading,
    error: loadError,
    eguiError,
    refreshEgui,
    refreshingEgui,
    reload: load,
  };
}

/* ── Customer outstanding hook ─────────────────────────────── */

export function useCustomerOutstanding(customerId: string) {
  const [summary, setSummary] = useState<CustomerOutstandingSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchCustomerOutstanding(customerId)
      .then(setSummary)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load outstanding"))
      .finally(() => setLoading(false));
  }, [customerId]);

  return { summary, loading, error };
}

/* ── Helpers ───────────────────────────────────────────────── */

export function paymentStatusLabel(status: string): string {
  switch (status) {
    case "paid": return "Paid";
    case "partial": return "Partial";
    case "unpaid": return "Unpaid";
    case "overdue": return "Overdue";
    case "voided": return "Voided";
    default: return status;
  }
}

export function paymentStatusColor(status: string): string {
  switch (status) {
    case "paid": return "#16a34a";
    case "partial": return "#ca8a04";
    case "unpaid": return "#6b7280";
    case "overdue": return "#dc2626";
    case "voided": return "#9ca3af";
    default: return "#374151";
  }
}

export function eguiStatusColor(status: string): string {
  switch (status) {
    case "ACKED": return "#15803d";
    case "FAILED":
    case "DEAD_LETTER": return "#b91c1c";
    case "RETRYING": return "#b45309";
    case "QUEUED":
    case "SENT": return "#1d4ed8";
    default: return "#475569";
  }
}
