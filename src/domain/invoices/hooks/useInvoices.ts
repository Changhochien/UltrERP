/** Hooks for invoices domain. */

import { useCallback, useEffect, useRef, useState } from "react";

import {
  resolveStatusBadgeVariant,
  type StatusBadgeVariant,
} from "../../../components/ui/StatusBadge";
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
  customer_id?: string;
  payment_status?: string | string[];
  date_from?: string;
  date_to?: string;
  search?: string;
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
          customer_id: options?.customer_id,
          payment_status: options?.payment_status,
          date_from: options?.date_from,
          date_to: options?.date_to,
          search: options?.search,
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
    [
      options?.customer_id,
      options?.payment_status,
      options?.date_from,
      options?.date_to,
      options?.search,
      options?.sort_by,
      options?.sort_order,
      pageSize,
    ],
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
  const mountedRef = useRef(true);
  const activeRequestIdRef = useRef(0);

  useEffect(() => {
    mountedRef.current = true;
    const requestId = ++activeRequestIdRef.current;
    const controller = new AbortController();

    setLoading(true);
    fetchCustomerOutstanding(customerId, controller.signal)
      .then((res) => {
        if (!mountedRef.current || activeRequestIdRef.current !== requestId) {
          return;
        }
        setSummary(res);
      })
      .catch((err) => {
        if (!mountedRef.current || activeRequestIdRef.current !== requestId) {
          return;
        }
        if (err instanceof Error && err.name === "AbortError") {
          return;
        }
        setError(err instanceof Error ? err.message : "Failed to load outstanding");
      })
      .finally(() => {
        if (mountedRef.current && activeRequestIdRef.current === requestId) {
          setLoading(false);
        }
      });

    return () => {
      mountedRef.current = false;
      controller.abort();
    };
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

type InvoiceStatusBadgeVariant = StatusBadgeVariant;

export function paymentStatusBadgeVariant(status: string): InvoiceStatusBadgeVariant {
  return resolveStatusBadgeVariant(status);
}

export function eguiStatusBadgeVariant(status: string): InvoiceStatusBadgeVariant {
  return resolveStatusBadgeVariant(status);
}
