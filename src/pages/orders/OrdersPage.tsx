/** Orders page — list, create, and detail views. */

import { useLocation, useNavigate, useParams } from "react-router-dom";

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
    <div>
      <div style={{ marginBottom: 16 }}>
        <button type="button" onClick={() => navigate(ORDER_CREATE_ROUTE)}>
          + New Order
        </button>
      </div>
      <OrderList onSelect={(id) => navigate(`/orders/${id}`)} />
    </div>
  );
}
