/** Morning Dashboard page. */

import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

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
import { APP_TITLE } from "../../App";
import { usePermissions } from "../../hooks/usePermissions";

interface QAAction {
  key: string;
  route: string;
  perm: "inventory" | "customers" | "invoices" | "orders" | "payments" | "admin";
  write?: true;
}

const QA_KEYS: QAAction[] = [
  { key: "inventory", route: INVENTORY_ROUTE, perm: "inventory" },
  { key: "customers", route: CUSTOMERS_ROUTE, perm: "customers" },
  { key: "newCustomer", route: CUSTOMER_CREATE_ROUTE, perm: "customers", write: true },
  { key: "invoices", route: INVOICES_ROUTE, perm: "invoices" },
  { key: "newInvoice", route: INVOICE_CREATE_ROUTE, perm: "invoices", write: true },
  { key: "orders", route: ORDERS_ROUTE, perm: "orders" },
  { key: "newOrder", route: ORDER_CREATE_ROUTE, perm: "orders", write: true },
  { key: "payments", route: PAYMENTS_ROUTE, perm: "payments" },
  { key: "admin", route: ADMIN_ROUTE, perm: "admin" },
];

export function DashboardPage() {
  const { t } = useTranslation("dashboard");
const { t: tRoutes } = useTranslation("routes");
  const navigate = useNavigate();
  const { data, isLoading, error } = useRevenueSummary();
  const { canAccess, canWrite } = usePermissions();

  const quickActions = QA_KEYS
    .filter((qa) => (qa.write ? canWrite(qa.perm) : canAccess(qa.perm)))
    .map((qa) => ({
      label: t(`dashboard.quickActions.${qa.key}`),
      description: t(`dashboard.quickActions.${qa.key}Description`),
      to: qa.route,
    }));

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={[{ label: tRoutes("dashboard.label") }]}
        eyebrow={tRoutes("workspace.label")}
        title={APP_TITLE}
        description={`${t("app.tagline")}. ${t("pageDescription")}`}
        actions={(
          <div className="flex flex-wrap gap-3">
            {canWrite("orders") ? (
              <Button type="button" onClick={() => navigate(ORDER_CREATE_ROUTE)}>
                {t("quickActions.newOrder")}
              </Button>
            ) : null}
            {canWrite("invoices") ? (
              <Button type="button" variant="outline" onClick={() => navigate(INVOICE_CREATE_ROUTE)}>
                {t("quickActions.newInvoice")}
              </Button>
            ) : null}
          </div>
        )}
      />

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,0.9fr)_minmax(0,1fr)]">
        <RevenueCard data={data} isLoading={isLoading} error={error} />
        <VisitorStatsCard />
        {canAccess("inventory") ? <LowStockAlertsCard /> : null}
      </section>

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]">
        <TopProductsCard />
        <SectionCard
          title={t("actionCenter.title")}
          description={t("actionCenter.description")}
          contentClassName="space-y-3"
        >
          <div className="grid gap-3">
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
