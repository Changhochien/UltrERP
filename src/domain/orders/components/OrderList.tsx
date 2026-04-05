/** Paginated order list with status filter. */

import { useState } from "react";
import { useTranslation } from "react-i18next";

import { DataTable, DataTableToolbar } from "../../../components/layout/DataTable";
import { Badge } from "../../../components/ui/badge";
import { useOrders, statusBadgeVariant, statusLabel } from "../hooks/useOrders";

interface OrderListProps {
  onSelect: (orderId: string) => void;
}

const STATUS_OPTIONS: Array<{ value: string; labelKey: string }> = [
  { value: "", labelKey: "orders.list.allStatuses" },
  { value: "pending", labelKey: "orders.list.pending" },
  { value: "confirmed", labelKey: "orders.list.confirmed" },
  { value: "shipped", labelKey: "orders.list.shipped" },
  { value: "fulfilled", labelKey: "orders.list.fulfilled" },
  { value: "cancelled", labelKey: "orders.list.cancelled" },
];

export function OrderList({ onSelect }: OrderListProps) {
  const { t } = useTranslation("common");
  const [statusFilter, setStatusFilter] = useState("");
  const { items, total, page, pageSize, loading, error, reload } = useOrders({
    status: statusFilter || undefined,
  });

  return (
    <section aria-label="Order list">
      <DataTable
        columns={[
          {
            id: "order_number",
            header: t("orders.list.orderNumber"),
            sortable: true,
            getSortValue: (item) => item.order_number,
            cell: (item) => <span className="font-medium">{item.order_number}</span>,
          },
          {
            id: "status",
            header: t("orders.list.status"),
            sortable: true,
            getSortValue: (item) => item.status,
            cell: (item) => (
              <Badge variant={statusBadgeVariant(item.status)} className="normal-case tracking-normal">
                {statusLabel(item.status)}
              </Badge>
            ),
          },
          {
            id: "total_amount",
            header: t("orders.list.total"),
            sortable: true,
            getSortValue: (item) => Number(item.total_amount),
            cell: (item) => `$${item.total_amount}`,
          },
          {
            id: "created_at",
            header: t("orders.list.created"),
            sortable: true,
            getSortValue: (item) => new Date(item.created_at).getTime(),
            cell: (item) => new Date(item.created_at).toLocaleDateString(),
          },
        ]}
        data={items}
        loading={loading}
        error={error}
        emptyTitle={t("orders.list.noOrders")}
        emptyDescription={t("orders.list.adjustFilter")}
        toolbar={(
          <DataTableToolbar>
            <div className="space-y-1">
              <h2 className="text-lg font-semibold tracking-tight">{t("orders.list.title")}</h2>
              <p className="text-sm text-muted-foreground">{t("orders.list.description")}</p>
            </div>
            <label className="flex flex-col items-start gap-2 text-sm font-medium text-foreground sm:flex-row sm:items-center sm:gap-3">
              <span>{t("orders.list.statusLabel")}</span>
              <select
                id="ol-status"
                aria-label="Status:"
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
                className="w-full sm:w-44"
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {t(opt.labelKey)}
                  </option>
                ))}
              </select>
            </label>
          </DataTableToolbar>
        )}
        page={page}
        pageSize={pageSize}
        totalItems={total}
        onPageChange={(nextPage) => {
          void reload(nextPage);
        }}
        getRowId={(item) => item.id}
        rowLabel={(item) => `Order ${item.order_number}`}
        onRowClick={(item) => onSelect(item.id)}
      />
    </section>
  );
}
