/** Morning Dashboard page. */

import { useNavigate } from "react-router-dom";

import {
  ADMIN_ROUTE,
  CUSTOMERS_ROUTE,
  CUSTOMER_CREATE_ROUTE,
  INVENTORY_ROUTE,
  INVOICES_ROUTE,
  INVOICE_CREATE_ROUTE,
  ORDERS_ROUTE,
  ORDER_CREATE_ROUTE,
  PAYMENTS_ROUTE,
} from "../../lib/routes";
import { useRevenueSummary } from "../../domain/dashboard/hooks/useDashboard";
import { RevenueCard } from "../../domain/dashboard/components/RevenueCard";
import { TopProductsCard } from "../../domain/dashboard/components/TopProductsCard";
import { LowStockAlertsCard } from "../../domain/dashboard/components/LowStockAlertsCard";
import { VisitorStatsCard } from "../../domain/dashboard/components/VisitorStatsCard";
import { APP_TITLE, APP_TAGLINE } from "../../App";
import { usePermissions } from "../../hooks/usePermissions";

export function DashboardPage() {
  const navigate = useNavigate();
  const { data, isLoading, error } = useRevenueSummary();
  const { canAccess, canWrite } = usePermissions();

  return (
    <>
      <section className="hero-card dashboard-hero">
        <div>
          <h1>{APP_TITLE}</h1>
          <p>{APP_TAGLINE}</p>
          <p className="caption">Operational overview with role-filtered navigation and action controls.</p>
        </div>
      </section>

      <section className="dashboard-grid">
        <RevenueCard data={data} isLoading={isLoading} error={error} />
        <TopProductsCard />
        <LowStockAlertsCard />
        <VisitorStatsCard />
      </section>

      <nav className="dashboard-actions">
        {canAccess("inventory") && (
          <button type="button" onClick={() => navigate(INVENTORY_ROUTE)}>
            Open Inventory
          </button>
        )}
        {canAccess("customers") && (
          <button type="button" onClick={() => navigate(CUSTOMERS_ROUTE)}>
            Browse Customers
          </button>
        )}
        {canWrite("customers") && (
          <button type="button" onClick={() => navigate(CUSTOMER_CREATE_ROUTE)}>
            Create Customer
          </button>
        )}
        {canAccess("invoices") && (
          <button type="button" onClick={() => navigate(INVOICES_ROUTE)}>
            Browse Invoices
          </button>
        )}
        {canWrite("invoices") && (
          <button type="button" onClick={() => navigate(INVOICE_CREATE_ROUTE)}>
            Create Invoice
          </button>
        )}
        {canAccess("orders") && (
          <button type="button" onClick={() => navigate(ORDERS_ROUTE)}>
            Browse Orders
          </button>
        )}
        {canWrite("orders") && (
          <button type="button" onClick={() => navigate(ORDER_CREATE_ROUTE)}>
            Create Order
          </button>
        )}
        {canAccess("payments") && (
          <button type="button" onClick={() => navigate(PAYMENTS_ROUTE)}>
            Open Payments
          </button>
        )}
        {canAccess("admin") && (
          <button type="button" onClick={() => navigate(ADMIN_ROUTE)}>
            Open Admin
          </button>
        )}
      </nav>
    </>
  );
}
