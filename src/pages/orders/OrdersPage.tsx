/** Orders page — list, create, and detail views. */

import { useLocation, useNavigate, useParams } from "react-router-dom";

import { PageHeader, SectionCard } from "../../components/layout/PageLayout";
import { Button } from "../../components/ui/button";
import { ORDERS_ROUTE, ORDER_CREATE_ROUTE } from "../../lib/routes";
import { OrderForm } from "../../domain/orders/components/OrderForm";
import { OrderList } from "../../domain/orders/components/OrderList";
import { OrderDetail } from "../../domain/orders/components/OrderDetail";

export function OrdersPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { orderId } = useParams<{ orderId: string }>();

  if (orderId) {
    return (
      <OrderDetail
        orderId={orderId}
        onBack={() => navigate(ORDERS_ROUTE)}
      />
    );
  }

  if (location.pathname === ORDER_CREATE_ROUTE) {
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
          <Button type="button" onClick={() => navigate(ORDER_CREATE_ROUTE)}>
            New Order
          </Button>
        )}
      />
      <SectionCard title="Order Pipeline" description="Filter and sort the current order queue.">
        <OrderList onSelect={(id) => navigate(`/orders/${id}`)} />
      </SectionCard>
    </div>
  );
}
