/** Morning Dashboard page. */

import { useNavigate } from "react-router-dom";

import { PageHeader, SectionCard } from "../../components/layout/PageLayout";
import { Button } from "../../components/ui/button";
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

  const quickActions = [
    canAccess("inventory") ? { label: "Inventory", description: "Stock, warehouses, and reorder alerts.", to: INVENTORY_ROUTE } : null,
    canAccess("customers") ? { label: "Customers", description: "Search accounts and review credit posture.", to: CUSTOMERS_ROUTE } : null,
    canWrite("customers") ? { label: "New customer", description: "Create a customer record and validate duplicates.", to: CUSTOMER_CREATE_ROUTE } : null,
    canAccess("invoices") ? { label: "Invoices", description: "Track payment status and issuance progress.", to: INVOICES_ROUTE } : null,
    canWrite("invoices") ? { label: "New invoice", description: "Issue a B2B or B2C invoice.", to: INVOICE_CREATE_ROUTE } : null,
    canAccess("orders") ? { label: "Orders", description: "Review order status and fulfillment flow.", to: ORDERS_ROUTE } : null,
    canWrite("orders") ? { label: "New order", description: "Create a sales order with stock validation.", to: ORDER_CREATE_ROUTE } : null,
    canAccess("payments") ? { label: "Payments", description: "Reconcile inbound transfers and manual matches.", to: PAYMENTS_ROUTE } : null,
    canAccess("admin") ? { label: "Admin", description: "Inspect user access and audit history.", to: ADMIN_ROUTE } : null,
  ].filter((item) => item !== null);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Workspace"
        title={APP_TITLE}
        description={`${APP_TAGLINE}. Operational overview with role-filtered shortcuts and live business signals.`}
        actions={(
          <div className="flex flex-wrap gap-3">
            {canWrite("orders") ? (
              <Button type="button" onClick={() => navigate(ORDER_CREATE_ROUTE)}>
                New order
              </Button>
            ) : null}
            {canWrite("invoices") ? (
              <Button type="button" variant="outline" onClick={() => navigate(INVOICE_CREATE_ROUTE)}>
                New invoice
              </Button>
            ) : null}
          </div>
        )}
      />

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,0.9fr)_minmax(0,1fr)]">
        <RevenueCard data={data} isLoading={isLoading} error={error} />
        <VisitorStatsCard />
        <LowStockAlertsCard />
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]">
        <TopProductsCard />
        <SectionCard
          title="Action Center"
          description="Daily shortcuts aligned to the capabilities available in your current role."
          contentClassName="space-y-3"
        >
          <div className="grid gap-3 sm:grid-cols-2">
            {quickActions.map((action) => (
              <button
                key={action.to}
                type="button"
                onClick={() => navigate(action.to)}
                className="rounded-2xl border border-border/80 bg-background px-4 py-4 text-left shadow-sm transition-colors hover:bg-accent"
              >
                <p className="text-sm font-semibold text-foreground">{action.label}</p>
                <p className="mt-1 text-sm text-muted-foreground">{action.description}</p>
              </button>
            ))}
          </div>
        </SectionCard>
      </section>
    </div>
  );
}
