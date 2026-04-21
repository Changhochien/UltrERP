import './i18n';

import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import { AppNavigation } from "./components/AppNavigation";
import { DesktopTrayController } from "./components/desktop/DesktopTrayController";
import { ThemeProvider } from "./components/theme/ThemeProvider";
import { ThemeToggle } from "./components/theme/ThemeToggle";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { ShortcutLayer } from "./components/shortcuts/ShortcutLayer";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "./components/ui/sidebar";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import { usePostHogPageView } from "./hooks/usePostHogPageView";
import { getRouteContext } from "./lib/navigation";
import { formatWorkspaceDate } from "./lib/utils";
import { ToastProvider } from "./providers/ToastProvider";

import {
  ADMIN_ROUTE,
  CRM_LEAD_CREATE_ROUTE,
  CRM_LEAD_DETAIL_ROUTE,
  CRM_LEADS_ROUTE,
  CUSTOMER_CREATE_ROUTE,
  CUSTOMER_DETAIL_ROUTE,
  CUSTOMERS_ROUTE,
  COUNT_SESSION_DETAIL_ROUTE,
  HOME_ROUTE,
  INVENTORY_BELOW_REORDER_REPORT_ROUTE,
  INVENTORY_CATEGORIES_ROUTE,
  INVENTORY_COUNT_SESSIONS_ROUTE,
  INVENTORY_TRANSFERS_ROUTE,
  INVENTORY_UNITS_ROUTE,
  INVENTORY_VALUATION_ROUTE,
  INVENTORY_REORDER_SUGGESTIONS_ROUTE,
  INVENTORY_SUPPLIERS_ROUTE,
  INVENTORY_ROUTE,
  INTELLIGENCE_ROUTE,
  PRODUCT_DETAIL_ROUTE,
  INVOICES_ROUTE,
  INVOICE_CREATE_ROUTE,
  INVOICE_DETAIL_ROUTE,
  LOGIN_ROUTE,
  ORDERS_ROUTE,
  ORDER_CREATE_ROUTE,
  ORDER_DETAIL_ROUTE,
  OWNER_DASHBOARD_ROUTE,
  PAYMENTS_ROUTE,
  PURCHASES_ROUTE,
  SETTINGS_ROUTE,
  SUPPLIER_DETAIL_ROUTE,
} from "./lib/routes";
import { AdminPage } from "./pages/AdminPage";
import CreateLeadPage from "./pages/crm/CreateLeadPage";
import { LeadListPage } from "./pages/crm/LeadListPage";
import CreateCustomerPage from "./pages/customers/CreateCustomerPage";
import { CustomerListPage } from "./pages/customers/CustomerListPage";
import { DashboardPage } from "./pages/dashboard/DashboardPage";
import { OwnerDashboardPage } from "./domain/owner-dashboard/OwnerDashboardPage";
import { InventoryPage } from "./pages/InventoryPage";
import { IntelligencePage } from "./pages/IntelligencePage";
import { BelowReorderReportPage } from "./pages/inventory/BelowReorderReportPage";
import { CategoriesPage } from "./pages/inventory/CategoriesPage";
import { CountSessionDetailPage } from "./pages/inventory/CountSessionDetailPage";
import { CountSessionsPage } from "./pages/inventory/CountSessionsPage";
import { InventoryValuationPage } from "./pages/inventory/InventoryValuationPage";
import { ProductDetailPage } from "./pages/inventory/ProductDetailPage";
import { ReorderSuggestionsPage } from "./pages/inventory/ReorderSuggestionsPage";
import { SupplierDetailPage } from "./pages/inventory/SupplierDetailPage";
import { SuppliersPage } from "./pages/inventory/SuppliersPage";
import { TransfersPage } from "./pages/inventory/TransfersPage";
import { UnitsPage } from "./pages/inventory/UnitsPage";
import CreateInvoicePage from "./pages/invoices/CreateInvoicePage";
import { InvoicesPage } from "./pages/InvoicesPage";
import { OrdersPage } from "./pages/orders/OrdersPage";
import { PaymentsPage } from "./pages/PaymentsPage";
import { PurchasesPage } from "./pages/PurchasesPage";
import LoginPage from "./pages/LoginPage";
import SettingsPage from "./pages/settings/SettingsPage";

export const APP_TITLE = "UltrERP";

function AuthGate({ children }: { children: ReactNode }) {
  const { t } = useTranslation("common");
  const { isAuthLoading } = useAuth();

  if (isAuthLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center px-6 py-16">
        <div className="w-full max-w-md rounded-[2rem] border border-border/80 bg-card/95 p-8 text-center shadow-[0_24px_80px_-40px_rgba(15,23,42,0.5)]">
          <p className="text-xs font-semibold uppercase tracking-[0.32em] text-primary/80">{t("navMenu.workspace")}</p>
          <div className="mt-4 text-3xl font-semibold tracking-tight">{APP_TITLE}</div>
          <div className="mt-2 text-sm text-muted-foreground">{t("auth.signingIn")}</div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

function ShellHeader() {
  const location = useLocation();
  const context = getRouteContext(location.pathname);
  const { t } = useTranslation("common");

  return (
    <header className="sticky top-0 z-20 border-b border-border/55 bg-background/78 backdrop-blur-xl">
      <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex min-w-0 items-center gap-3">
          <div className="rounded-full border border-border/70 bg-card/78 p-1 shadow-sm backdrop-blur-sm">
            <SidebarTrigger />
          </div>
          <div className="min-w-0 space-y-1">
            <div className="flex min-w-0 items-center gap-2">
              <span className="inline-flex items-center rounded-full border border-border/70 bg-card/74 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.24em] text-muted-foreground">
                {t(context.sectionKey)}
              </span>
              <p className="truncate text-sm font-medium text-foreground/88 sm:text-[0.95rem]">
                {t(context.labelKey)}
              </p>
            </div>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2.5">
          <div className="hidden rounded-full border border-border/70 bg-card/74 px-3 py-1.5 text-xs text-muted-foreground sm:block">
            {formatWorkspaceDate()}
          </div>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}

function RoutedPage({ children }: { children: ReactNode }) {
  return (
    <SidebarProvider defaultOpen>
        <AppNavigation />
        <SidebarInset>
          <DesktopTrayController />
          <ShortcutLayer />
          <ShellHeader />
          <main className="px-4 py-8 sm:px-6 lg:px-8">
            <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-6">{children}</div>
          </main>
        </SidebarInset>
    </SidebarProvider>
  );
}

function CreateCustomerRoute() {
  const navigate = useNavigate();
  return (
    <RoutedPage>
      <CreateCustomerPage onNavigate={(path) => navigate(path)} />
    </RoutedPage>
  );
}

function CreateLeadRoute() {
  const navigate = useNavigate();
  return (
    <RoutedPage>
      <CreateLeadPage onNavigate={(path) => navigate(path)} />
    </RoutedPage>
  );
}

function LeadListRoute() {
  return (
    <RoutedPage>
      <LeadListPage />
    </RoutedPage>
  );
}

function CustomerListRoute() {
  return (
    <RoutedPage>
      <CustomerListPage />
    </RoutedPage>
  );
}

function CreateInvoiceRoute() {
  return (
    <RoutedPage>
      <CreateInvoicePage />
    </RoutedPage>
  );
}

function ProtectedAppRoute({
  requiredFeature,
  requiredWrite,
  children,
}: {
  requiredFeature: Parameters<typeof ProtectedRoute>[0]["requiredFeature"];
  requiredWrite?: boolean;
  children: ReactNode;
}) {
  return (
    <AuthGate>
      <ProtectedRoute requiredFeature={requiredFeature} requiredWrite={requiredWrite}>
        {children}
      </ProtectedRoute>
    </AuthGate>
  );
}

export default function App() {
  usePostHogPageView();

  return (
    <ThemeProvider>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            <Route path={LOGIN_ROUTE} element={<LoginPage />} />
            <Route
              path={HOME_ROUTE}
              element={
                <ProtectedAppRoute requiredFeature="dashboard">
                  <RoutedPage>
                    <DashboardPage />
                  </RoutedPage>
                </ProtectedAppRoute>
              }
            />
            <Route
              path={INVENTORY_ROUTE}
              element={
                <ProtectedAppRoute requiredFeature="inventory">
                  <RoutedPage>
                    <InventoryPage />
                  </RoutedPage>
                </ProtectedAppRoute>
              }
            />
            <Route
              path={INVENTORY_CATEGORIES_ROUTE}
              element={
                <ProtectedAppRoute requiredFeature="inventory">
                  <RoutedPage>
                    <CategoriesPage />
                  </RoutedPage>
                </ProtectedAppRoute>
              }
            />
            <Route
              path={INVENTORY_UNITS_ROUTE}
              element={
                <ProtectedAppRoute requiredFeature="inventory">
                  <RoutedPage>
                    <UnitsPage />
                  </RoutedPage>
                </ProtectedAppRoute>
              }
            />
            <Route
              path={INVENTORY_TRANSFERS_ROUTE}
              element={
                <ProtectedAppRoute requiredFeature="inventory">
                  <RoutedPage>
                    <TransfersPage />
                  </RoutedPage>
                </ProtectedAppRoute>
              }
            />
            <Route
              path={INVENTORY_COUNT_SESSIONS_ROUTE}
              element={
              <ProtectedAppRoute requiredFeature="inventory">
                <RoutedPage>
                  <CountSessionsPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={COUNT_SESSION_DETAIL_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="inventory">
                <RoutedPage>
                  <CountSessionDetailPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={INVENTORY_BELOW_REORDER_REPORT_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="inventory">
                <RoutedPage>
                  <BelowReorderReportPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={INVENTORY_VALUATION_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="inventory">
                <RoutedPage>
                  <InventoryValuationPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={INVENTORY_REORDER_SUGGESTIONS_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="inventory">
                <RoutedPage>
                  <ReorderSuggestionsPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={INVENTORY_SUPPLIERS_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="inventory">
                <RoutedPage>
                  <SuppliersPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={SUPPLIER_DETAIL_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="inventory">
                <RoutedPage>
                  <SupplierDetailPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={PRODUCT_DETAIL_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="inventory">
                <RoutedPage>
                  <ProductDetailPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={CRM_LEADS_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="crm">
                <LeadListRoute />
              </ProtectedAppRoute>
            }
          />
          <Route
            path={CRM_LEAD_DETAIL_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="crm">
                <LeadListRoute />
              </ProtectedAppRoute>
            }
          />
          <Route
            path={CRM_LEAD_CREATE_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="crm" requiredWrite>
                <CreateLeadRoute />
              </ProtectedAppRoute>
            }
          />
          <Route
            path={CUSTOMERS_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="customers">
                <CustomerListRoute />
              </ProtectedAppRoute>
            }
          />
          <Route
            path={CUSTOMER_DETAIL_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="customers">
                <CustomerListRoute />
              </ProtectedAppRoute>
            }
          />
          <Route
            path={CUSTOMER_CREATE_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="customers" requiredWrite>
                <CreateCustomerRoute />
              </ProtectedAppRoute>
            }
          />
          <Route
            path={INVOICES_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="invoices">
                <RoutedPage>
                  <InvoicesPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={INVOICE_DETAIL_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="invoices">
                <RoutedPage>
                  <InvoicesPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={INVOICE_CREATE_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="invoices" requiredWrite>
                <CreateInvoiceRoute />
              </ProtectedAppRoute>
            }
          />
          <Route
            path={ORDERS_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="orders">
                <RoutedPage>
                  <OrdersPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={ORDER_CREATE_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="orders" requiredWrite>
                <RoutedPage>
                  <OrdersPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={ORDER_DETAIL_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="orders">
                <RoutedPage>
                  <OrdersPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={PAYMENTS_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="payments">
                <RoutedPage>
                  <PaymentsPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={PURCHASES_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="purchases">
                <RoutedPage>
                  <PurchasesPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={ADMIN_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="admin">
                <RoutedPage>
                  <AdminPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={OWNER_DASHBOARD_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="owner_dashboard">
                <RoutedPage>
                  <OwnerDashboardPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={INTELLIGENCE_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="intelligence">
                <RoutedPage>
                  <IntelligencePage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={SETTINGS_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="settings">
                <RoutedPage>
                  <SettingsPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route path="*" element={<Navigate to={HOME_ROUTE} replace />} />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
