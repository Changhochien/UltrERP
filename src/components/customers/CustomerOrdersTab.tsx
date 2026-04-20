/** Customer orders tab — paginated list of orders for a specific customer. */

import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { DataTable, DataTableToolbar, type DataTableColumn } from "../../components/layout/DataTable";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { usePermissions } from "../../hooks/usePermissions";
import { fetchOrders } from "../../lib/api/orders";
import { ORDER_CREATE_ROUTE } from "../../lib/routes";
import { statusBadgeVariant, statusLabel } from "../../domain/orders/hooks/useOrders";
import type { OrderListItem } from "../../domain/orders/types";

interface CustomerOrdersTabProps {
  customerId: string;
}

export function CustomerOrdersTab({ customerId }: CustomerOrdersTabProps) {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const { canWrite } = usePermissions();
  const canCreateOrders = canWrite("orders");

  return (
    <CustomerOrdersTable
      customerId={customerId}
      canCreateOrders={canCreateOrders}
      onCreateOrder={() => navigate(`${ORDER_CREATE_ROUTE}?customer_id=${encodeURIComponent(customerId)}`)}
      onSelect={(id) => navigate(`/orders/${id}`)}
      t={t}
    />
  );
}

function CustomerOrdersTable({
  canCreateOrders,
  customerId,
  onCreateOrder,
  onSelect,
  t,
}: {
  canCreateOrders: boolean;
  customerId: string;
  onCreateOrder: () => void;
  onSelect: (id: string) => void;
  t: ReturnType<typeof useTranslation<"common">>["t"];
}) {
  const [items, setItems] = useState<OrderListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (p: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchOrders({
        customer_id: customerId,
        page: p,
        page_size: pageSize,
      });
      setItems(res.items);
      setTotal(res.total);
      setPage(p);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load orders");
    } finally {
      setLoading(false);
    }
  }, [customerId, pageSize]);

  useEffect(() => {
    void load(1);
  }, [load]);

  const columns: DataTableColumn<OrderListItem>[] = [
    {
      id: "order_number",
      header: t("orders.list.orderNumber") ?? "Order #",
      sortable: true,
      getSortValue: (item) => item.order_number,
      cell: (item) => <span className="font-medium">{item.order_number}</span>,
    },
    {
      id: "created_at",
      header: t("orders.list.created") ?? "Date",
      sortable: true,
      getSortValue: (item) => new Date(item.created_at).getTime(),
      cell: (item) => new Date(item.created_at).toLocaleDateString(),
    },
    {
      id: "total_amount",
      header: t("orders.list.total") ?? "Amount",
      sortable: true,
      getSortValue: (item) => Number(item.total_amount),
      cell: (item) => `$${item.total_amount}`,
    },
    {
      id: "status",
      header: t("orders.list.status") ?? "Status",
      sortable: true,
      getSortValue: (item) => statusLabel(item.status),
      cell: (item) => (
        <Badge
          variant={statusBadgeVariant(item.status)}
          className="normal-case tracking-normal"
        >
          {statusLabel(item.status)}
        </Badge>
      ),
    },
  ];

  return (
    <DataTable
      columns={columns}
      data={items}
      loading={loading}
      error={error}
      emptyTitle={t("customer.detail.orders.emptyTitle") ?? "No orders found for this customer."}
      emptyDescription={t("customer.detail.orders.emptyDescription") ?? "This customer has no orders."}
      toolbar={
        <DataTableToolbar>
          <div className="space-y-1">
            <h2 className="text-lg font-semibold tracking-tight">
              {t("customer.detail.orders.title") ?? "Orders"}
            </h2>
            <p className="text-sm text-muted-foreground">
              {t("customer.detail.orders.description") ?? "Orders placed by this customer."}
            </p>
          </div>
          {canCreateOrders ? (
            <Button type="button" onClick={onCreateOrder}>
              {t("customer.detail.orders.createOrder") ?? "Create Order"}
            </Button>
          ) : null}
        </DataTableToolbar>
      }
      page={page}
      pageSize={pageSize}
      totalItems={total}
      onPageChange={(p) => {
        void load(p);
      }}
      getRowId={(item) => item.id}
      rowLabel={(item) => `Order ${item.order_number}`}
      onRowClick={(item) => onSelect(item.id)}
    />
  );
}
