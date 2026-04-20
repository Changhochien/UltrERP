/** Orders page — list, create, and detail views. */

import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { PageHeader, SectionCard } from "../../components/layout/PageLayout";
import { Button } from "../../components/ui/button";
import { usePermissions } from "../../hooks/usePermissions";
import { ORDERS_ROUTE, ORDER_CREATE_ROUTE } from "../../lib/routes";
import { OrderForm } from "../../domain/orders/components/OrderForm";
import { OrderList } from "../../domain/orders/components/OrderList";
import { OrderDetail } from "../../domain/orders/components/OrderDetail";

export function OrdersPage() {
  const { t } = useTranslation("common");
  const { canWrite } = usePermissions();
  const location = useLocation();
  const navigate = useNavigate();
  const { orderId } = useParams<{ orderId: string }>();
  const canWriteOrders = canWrite("orders");

  if (orderId) {
    return (
      <OrderDetail
        orderId={orderId}
        onBack={() => navigate(ORDERS_ROUTE)}
      />
    );
  }

  if (location.pathname === ORDER_CREATE_ROUTE) {
    if (!canWriteOrders) {
      return (
        <div className="space-y-6">
          <SectionCard
            title={t("orders.form.newOrderTitle")}
            description={t("orders.form.newOrderDescription")}
          >
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">{t("orders.form.readOnly")}</p>
              <Button type="button" variant="outline" onClick={() => navigate(ORDERS_ROUTE)}>
                {t("orders.detail.backToList")}
              </Button>
            </div>
          </SectionCard>
        </div>
      );
    }

    return (
      <OrderForm
        onCreated={(id) => navigate(`/orders/${id}`)}
        onCancel={() => navigate(ORDERS_ROUTE)}
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Orders"
        title="Orders"
        description="Track order flow, inspect current pipeline, and jump into fulfillment details."
        actions={(
          canWriteOrders ? (
            <Button type="button" onClick={() => navigate(ORDER_CREATE_ROUTE)}>
              New Order
            </Button>
          ) : null
        )}
      />
      <SectionCard title="Order Pipeline" description="Filter and sort the current order queue.">
        <OrderList onSelect={(id) => navigate(`/orders/${id}`)} />
      </SectionCard>
    </div>
  );
}
