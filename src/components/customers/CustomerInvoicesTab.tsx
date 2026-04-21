/** Customer invoices tab — paginated list of invoices for a specific customer. */

import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { DataTable, DataTableToolbar, type DataTableColumn } from "../../components/layout/DataTable";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { fetchInvoices } from "../../lib/api/invoices";
import { paymentStatusLabel } from "../../domain/invoices/hooks/useInvoices";
import type { InvoiceListItem } from "../../domain/invoices/types";

interface CustomerInvoicesTabProps {
  customerId: string;
}

export function CustomerInvoicesTab({ customerId }: CustomerInvoicesTabProps) {
  const { t } = useTranslation("common");
  const navigate = useNavigate();

  return (
    <CustomerInvoicesTable customerId={customerId} onSelect={(id) => navigate(`/invoices/${id}`)} t={t} />
  );
}

function CustomerInvoicesTable({
  customerId,
  onSelect,
  t,
}: {
  customerId: string;
  onSelect: (id: string) => void;
  t: ReturnType<typeof useTranslation<"common">>["t"];
}) {
  const [items, setItems] = useState<InvoiceListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (p: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchInvoices({
        customer_id: customerId,
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
  }, [customerId, pageSize]);

  useEffect(() => {
    void load(1);
  }, [load]);

  const columns: DataTableColumn<InvoiceListItem>[] = [
    {
      id: "invoice_number",
      header: t("invoice.listPage.invoiceNumber") ?? "Invoice #",
      sortable: true,
      getSortValue: (item) => item.invoice_number,
      cell: (item) => <span className="font-medium">{item.invoice_number}</span>,
    },
    {
      id: "invoice_date",
      header: t("invoice.listPage.invoiceDate") ?? "Date",
      sortable: true,
      getSortValue: (item) => item.invoice_date,
      cell: (item) => item.invoice_date,
    },
    {
      id: "total_amount",
      header: t("invoice.totals.total") ?? "Amount",
      cell: (item) => `${item.currency_code} ${item.total_amount}`,
    },
    {
      id: "payment_status",
      header: t("invoice.listPage.status") ?? "Status",
      cell: (item) => (
        <StatusBadge status={item.payment_status} label={paymentStatusLabel(item.payment_status)} />
      ),
    },
  ];

  return (
    <DataTable
      columns={columns}
      data={items}
      loading={loading}
      error={error}
      emptyTitle={t("customer.detail.invoices.emptyTitle") ?? "No invoices found for this customer."}
      emptyDescription={t("customer.detail.invoices.emptyDescription") ?? "This customer has no issued invoices."}
      toolbar={
        <DataTableToolbar>
          <div className="space-y-1">
            <h2 className="text-lg font-semibold tracking-tight">
              {t("customer.detail.invoices.title") ?? "Invoices"}
            </h2>
            <p className="text-sm text-muted-foreground">
              {t("customer.detail.invoices.description") ?? "Invoices issued to this customer."}
            </p>
          </div>
        </DataTableToolbar>
      }
      page={page}
      pageSize={pageSize}
      totalItems={total}
      onPageChange={(p) => {
        void load(p);
      }}
      getRowId={(item) => item.id}
      rowLabel={(item) => `Invoice ${item.invoice_number}`}
      onRowClick={(item) => onSelect(item.id)}
    />
  );
}
