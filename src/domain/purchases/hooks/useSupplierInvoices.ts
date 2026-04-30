import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  resolveStatusBadgeVariant,
  type StatusBadgeVariant,
} from "../../../components/ui/StatusBadge";
import {
  fetchSupplierInvoice,
  fetchSupplierInvoices,
} from "../../../lib/api/purchases";
import type {
  SupplierInvoice,
  SupplierInvoiceListItem,
  SupplierInvoiceStatus,
  SupplierInvoiceStatusTotals,
} from "../types";

const EMPTY_STATUS_TOTALS: SupplierInvoiceStatusTotals = {
  open: 0,
  paid: 0,
  voided: 0,
};

export function useSupplierInvoices(options?: {
  status?: SupplierInvoiceStatus;
  sort_by?: "created_at" | "invoice_date" | "total_amount";
  sort_order?: "asc" | "desc";
}) {
  const [items, setItems] = useState<SupplierInvoiceListItem[]>([]);
  const [statusTotals, setStatusTotals] = useState<SupplierInvoiceStatusTotals>(
    EMPTY_STATUS_TOTALS,
  );
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
        setStatusTotals(response.status_totals);
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

  return { items, statusTotals, total, page, pageSize, loading, error, reload: load };
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

type SupplierInvoiceStatusBadgeVariant = StatusBadgeVariant;

export function supplierInvoiceStatusBadgeVariant(
  status: SupplierInvoiceStatus,
): SupplierInvoiceStatusBadgeVariant {
  return resolveStatusBadgeVariant(status, { overrides: { open: "warning" } });
}

export function useSupplierInvoiceStatusLabel() {
  const { t } = useTranslation("purchase");

  return useCallback(
    (status: SupplierInvoiceStatus) => t(`status.${status}`),
    [t],
  );
}