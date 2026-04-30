import { useState } from "react";
import { useTranslation } from "react-i18next";

import {
  DataTable,
  DataTableToolbar,
  type DataTableSortState,
} from "../../../components/layout/DataTable";
import { Badge } from "../../../components/ui/badge";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import {
  useSupplierInvoiceStatusLabel,
  useSupplierInvoices,
} from "../hooks/useSupplierInvoices";
import type { SupplierInvoiceStatus } from "../types";

interface SupplierInvoiceListProps {
  onSelect: (invoiceId: string) => void;
}

const STATUS_OPTIONS: SupplierInvoiceStatus[] = ["open", "paid", "voided"];

export function SupplierInvoiceList({ onSelect }: SupplierInvoiceListProps) {
  const { t } = useTranslation("purchase");
  const statusLabel = useSupplierInvoiceStatusLabel();
  const [statusFilter, setStatusFilter] = useState<"" | SupplierInvoiceStatus>("");
  const [sortState, setSortState] = useState<DataTableSortState | null>({
    columnId: "invoice_date",
    direction: "desc",
  });

  const { items, statusTotals, total, page, pageSize, loading, error, reload } = useSupplierInvoices({
    status: statusFilter || undefined,
    sort_by: sortState?.columnId as "created_at" | "invoice_date" | "total_amount" | undefined,
    sort_order: sortState?.direction,
  });
  const allStatusCount = statusTotals.open + statusTotals.paid + statusTotals.voided;

  return (
    <section aria-label={t("list.ariaLabel")}>
      <DataTable
        columns={[
          {
            id: "invoice_number",
            header: t("list.columns.invoiceNumber"),
            sortable: true,
            cell: (item) => <span className="font-medium">{item.invoice_number}</span>,
          },
          {
            id: "invoice_date",
            header: t("list.columns.invoiceDate"),
            sortable: true,
            cell: (item) => item.invoice_date,
          },
          {
            id: "supplier_name",
            header: t("list.columns.supplier"),
            cell: (item) => item.supplier_name,
          },
          {
            id: "total_amount",
            header: t("list.columns.total"),
            sortable: true,
            cell: (item) => `${item.currency_code} ${item.total_amount}`,
          },
          {
            id: "line_count",
            header: t("list.columns.lines"),
            cell: (item) => item.line_count,
          },
          {
            id: "status",
            header: t("list.columns.status"),
            cell: (item) => (
              <StatusBadge status={item.status} label={statusLabel(item.status)} />
            ),
          },
        ]}
        data={items}
        loading={loading}
        error={error}
        emptyTitle={t("list.emptyTitle")}
        emptyDescription={t("list.emptyDescription")}
        toolbar={(
          <DataTableToolbar>
            <div className="space-y-1">
              <h2 className="text-lg font-semibold tracking-tight">
                {t("list.title")}
              </h2>
              <p className="text-sm text-muted-foreground">
                {t("list.description")}
              </p>
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <span className="text-xs text-muted-foreground">
                  {t("list.statusOverview")}
                </span>
                <Badge variant="outline" className="normal-case tracking-normal">
                  {t("list.allStatuses")} {allStatusCount}
                </Badge>
                {STATUS_OPTIONS.map((status) => (
                  <StatusBadge
                    key={status}
                    status={status}
                    label={`${statusLabel(status)} ${statusTotals[status]}`}
                  />
                ))}
              </div>
            </div>
            <label className="flex flex-col items-start gap-2 text-sm font-medium text-foreground sm:flex-row sm:items-center sm:gap-3">
              <span>{t("list.statusFilter")}</span>
              <select
                value={statusFilter}
                onChange={(event) =>
                  setStatusFilter(event.target.value as "" | SupplierInvoiceStatus)
                }
                aria-label={t("list.statusFilter")}
                className="w-full sm:w-48"
              >
                <option value="">{t("list.allStatuses")}</option>
                {STATUS_OPTIONS.map((status) => (
                  <option key={status} value={status}>
                    {statusLabel(status)}
                  </option>
                ))}
              </select>
            </label>
          </DataTableToolbar>
        )}
        summary={
          items.length > 0
            ? t("list.summary", { count: items.length, total })
            : undefined
        }
        page={page}
        pageSize={pageSize}
        totalItems={total}
        onPageChange={(nextPage) => {
          void reload(nextPage);
        }}
        sortState={sortState}
        onSortChange={setSortState}
        getRowId={(item) => item.id}
        rowLabel={(item) =>
          t("list.rowLabel", { invoiceNumber: item.invoice_number })
        }
        onRowClick={(item) => onSelect(item.id)}
      />
    </section>
  );
}