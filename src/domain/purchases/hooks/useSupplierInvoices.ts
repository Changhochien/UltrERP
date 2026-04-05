import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  fetchSupplierInvoice,
  fetchSupplierInvoices,
} from "../../../lib/api/purchases";
import type {
  SupplierInvoice,
  SupplierInvoiceListItem,
  SupplierInvoiceStatus,
} from "../types";

export function useSupplierInvoices(options?: {
  status?: SupplierInvoiceStatus;
  sort_by?: "created_at" | "invoice_date" | "total_amount";
  sort_order?: "asc" | "desc";
}) {
  const [items, setItems] = useState<SupplierInvoiceListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (nextPage: number) => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetchSupplierInvoices({
          status: options?.status,
          sort_by: options?.sort_by,
          sort_order: options?.sort_order,
          page: nextPage,
          page_size: pageSize,
        });
        setItems(response.items);
        setTotal(response.total);
        setPage(nextPage);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load supplier invoices",
        );
      } finally {
        setLoading(false);
      }
    },
    [options?.sort_by, options?.sort_order, options?.status, pageSize],
  );

  useEffect(() => {
    void load(1);
  }, [load]);

  return { items, total, page, pageSize, loading, error, reload: load };
}

export function useSupplierInvoice(invoiceId: string) {
  const [invoice, setInvoice] = useState<SupplierInvoice | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const nextInvoice = await fetchSupplierInvoice(invoiceId);
      setInvoice(nextInvoice);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load supplier invoice",
      );
    } finally {
      setLoading(false);
    }
  }, [invoiceId]);

  useEffect(() => {
    void load();
  }, [load]);

  return { invoice, loading, error, reload: load };
}

type SupplierInvoiceStatusBadgeVariant =
  | "neutral"
  | "success"
  | "warning"
  | "destructive";

export function supplierInvoiceStatusBadgeVariant(
  status: SupplierInvoiceStatus,
): SupplierInvoiceStatusBadgeVariant {
  switch (status) {
    case "paid":
      return "success";
    case "voided":
      return "destructive";
    default:
      return "warning";
  }
}

export function useSupplierInvoiceStatusLabel() {
  const { t } = useTranslation("common");

  return useCallback(
    (status: SupplierInvoiceStatus) => t(`purchase.status.${status}`),
    [t],
  );
}