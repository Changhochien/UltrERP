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
  ACCOUNTING_ROUTE,
  ADMIN_ROUTE,
  BALANCE_SHEET_ROUTE,
  BANK_RECONCILIATION_ROUTE,
  BUDGET_VARIANCE_ROUTE,
  BUDGETS_ROUTE,
  CHART_OF_ACCOUNTS_ROUTE,
  CRM_LEAD_CREATE_ROUTE,
  CRM_LEAD_DETAIL_ROUTE,
  CRM_LEADS_ROUTE,
  CRM_OPPORTUNITY_CREATE_ROUTE,
  CRM_OPPORTUNITY_DETAIL_ROUTE,
  CRM_OPPORTUNITIES_ROUTE,
  CRM_QUOTATION_CREATE_ROUTE,
  CRM_QUOTATION_DETAIL_ROUTE,
  CRM_QUOTATIONS_ROUTE,
  CRM_REPORTING_ROUTE,
  CRM_SETUP_ROUTE,
  COLLECTIONS_ROUTE,
  CUSTOMER_CREATE_ROUTE,
  CUSTOMER_DETAIL_ROUTE,
  CUSTOMERS_ROUTE,
  COUNT_SESSION_DETAIL_ROUTE,
  FISCAL_YEARS_ROUTE,
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
  JOURNAL_ENTRIES_ROUTE,
  JOURNAL_ENTRY_DETAIL_ROUTE,
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
  PROCUREMENT_ROUTE,
  PROCUREMENT_PURCHASE_ORDERS_ROUTE,
  PROCUREMENT_PURCHASE_ORDER_CREATE_ROUTE,
  PROCUREMENT_PURCHASE_ORDER_DETAIL_ROUTE,
  PROCUREMENT_RFQ_CREATE_ROUTE,
  PROCUREMENT_RFQ_DETAIL_ROUTE,
  PROCUREMENT_GOODS_RECEIPT_LIST_ROUTE,
  PROCUREMENT_GOODS_RECEIPT_DETAIL_ROUTE,
  PROCUREMENT_CREATE_GOODS_RECEIPT_ROUTE,
  PROFIT_AND_LOSS_ROUTE,
  PURCHASES_ROUTE,
  SETTINGS_ROUTE,
  SUPPLIER_DETAIL_ROUTE,
  TRIAL_BALANCE_ROUTE,
} from "./lib/routes";
import { AdminPage } from "./pages/AdminPage";
import CreateLeadPage from "./pages/crm/CreateLeadPage";
import { LeadListPage } from "./pages/crm/LeadListPage";
import CreateOpportunityPage from "./pages/crm/CreateOpportunityPage";
import { OpportunityListPage } from "./pages/crm/OpportunityListPage";
import CRMPipelineReportPage from "./pages/crm/CRMPipelineReportPage";
import CRMSetupPage from "./pages/crm/CRMSetupPage";
import CreateQuotationPage from "./pages/crm/CreateQuotationPage";
import { QuotationListPage } from "./pages/crm/QuotationListPage";
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
import { RFQListPage } from "./pages/procurement/RFQListPage";
import CreateRFQPage from "./pages/procurement/CreateRFQPage";
import { RFQDetailPage } from "./pages/procurement/RFQDetailPage";
import { PurchaseOrderListPage } from "./pages/procurement/PurchaseOrderListPage";
import { PurchaseOrderDetailPage } from "./pages/procurement/PurchaseOrderDetailPage";
import { CreatePurchaseOrderPage } from "./pages/procurement/CreatePurchaseOrderPage";
import { GoodsReceiptListPage } from "./pages/procurement/GoodsReceiptListPage";
import { GoodsReceiptDetailPage } from "./pages/procurement/GoodsReceiptDetailPage";
import { CreateGoodsReceiptPage } from "./pages/procurement/CreateGoodsReceiptPage";
import LoginPage from "./pages/LoginPage";
import SettingsPage from "./pages/settings/SettingsPage";
import { ChartOfAccountsPage } from "./pages/accounting/ChartOfAccountsPage";
import { FiscalYearsPage } from "./pages/accounting/FiscalYearsPage";
import { JournalEntriesPage } from "./pages/accounting/JournalEntriesPage";
import { JournalEntryDetailPage } from "./pages/accounting/JournalEntryDetailPage";
import { ProfitAndLossPage } from "./pages/accounting/ProfitAndLossPage";
import { BalanceSheetPage } from "./pages/accounting/BalanceSheetPage";
import { TrialBalancePage } from "./pages/accounting/TrialBalancePage";
import { BankReconciliationPage } from "./pages/accounting/BankReconciliationPage";
import { CollectionsPage } from "./pages/accounting/CollectionsPage";
import { BudgetsPage } from "./pages/accounting/BudgetsPage";
import { BudgetVariancePage } from "./pages/accounting/BudgetVariancePage";

export const APP_TITLE = "UltrERP";

function AuthGate({ children }: { children: ReactNode }) {
  const { t: tShell } = useTranslation("shell");
  const { t: tCommon } = useTranslation("common");
  const { isAuthLoading } = useAuth();

  if (isAuthLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center px-6 py-16">
        <div className="w-full max-w-md rounded-[2rem] border border-border/80 bg-card/95 p-8 text-center shadow-[0_24px_80px_-40px_rgba(15,23,42,0.5)]">
          <p className="text-xs font-semibold uppercase tracking-[0.32em] text-primary/80">{tShell("navMenu.workspace")}</p>
          <div className="mt-4 text-3xl font-semibold tracking-tight">{APP_TITLE}</div>
          <div className="mt-2 text-sm text-muted-foreground">{tCommon("auth.signingIn")}</div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

function ShellHeader() {
  const location = useLocation();
  const context = getRouteContext(location.pathname);
  const { t } = useTranslation("routes");
  const { t: tShell } = useTranslation("shell");

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
                {tShell(context.sectionKey)}
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

function CreateOpportunityRoute() {
  const navigate = useNavigate();
  return (
    <RoutedPage>
      <CreateOpportunityPage onNavigate={(path) => navigate(path)} />
    </RoutedPage>
  );
}

function OpportunityListRoute() {
  return (
    <RoutedPage>
      <OpportunityListPage />
    </RoutedPage>
  );
}

function CreateQuotationRoute() {
  const navigate = useNavigate();
  return (
    <RoutedPage>
      <CreateQuotationPage onNavigate={(path) => navigate(path)} />
    </RoutedPage>
  );
}

function QuotationListRoute() {
  return (
    <RoutedPage>
      <QuotationListPage />
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
            path={CRM_OPPORTUNITIES_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="crm">
                <OpportunityListRoute />
              </ProtectedAppRoute>
            }
          />
          <Route
            path={CRM_OPPORTUNITY_DETAIL_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="crm">
                <OpportunityListRoute />
              </ProtectedAppRoute>
            }
          />
          <Route
            path={CRM_OPPORTUNITY_CREATE_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="crm" requiredWrite>
                <CreateOpportunityRoute />
              </ProtectedAppRoute>
            }
          />
          <Route
            path={CRM_QUOTATIONS_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="crm">
                <QuotationListRoute />
              </ProtectedAppRoute>
            }
          />
          <Route
            path={CRM_QUOTATION_DETAIL_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="crm">
                <QuotationListRoute />
              </ProtectedAppRoute>
            }
          />
          <Route
            path={CRM_QUOTATION_CREATE_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="crm" requiredWrite>
                <CreateQuotationRoute />
              </ProtectedAppRoute>
            }
          />
          <Route
            path={CRM_REPORTING_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="crm">
                <RoutedPage>
                  <CRMPipelineReportPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={CRM_SETUP_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="settings">
                <RoutedPage>
                  <CRMSetupPage />
                </RoutedPage>
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
          {/* Procurement - RFQ and Supplier Quotation workspace (Epic 24) */}
          <Route
            path={PROCUREMENT_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="procurement">
                <RoutedPage>
                  <RFQListPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={PROCUREMENT_RFQ_CREATE_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="procurement" requiredWrite>
                <RoutedPage>
                  <CreateRFQPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={PROCUREMENT_RFQ_DETAIL_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="procurement">
                <RoutedPage>
                  <RFQDetailPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={PROCUREMENT_PURCHASE_ORDERS_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="procurement">
                <RoutedPage>
                  <PurchaseOrderListPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={PROCUREMENT_PURCHASE_ORDER_CREATE_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="procurement" requiredWrite>
                <RoutedPage>
                  <CreatePurchaseOrderPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={PROCUREMENT_PURCHASE_ORDER_DETAIL_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="procurement">
                <RoutedPage>
                  <PurchaseOrderDetailPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          {/* Goods Receipt Routes (Story 24-3) */}
          <Route
            path={PROCUREMENT_GOODS_RECEIPT_LIST_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="procurement">
                <RoutedPage>
                  <GoodsReceiptListPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={PROCUREMENT_GOODS_RECEIPT_DETAIL_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="procurement">
                <RoutedPage>
                  <GoodsReceiptDetailPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={PROCUREMENT_CREATE_GOODS_RECEIPT_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="procurement" requiredWrite>
                <RoutedPage>
                  <CreateGoodsReceiptPage />
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
          {/* Accounting Routes (Epic 26) */}
          <Route
            path={ACCOUNTING_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="accounting">
                <RoutedPage>
                  <ChartOfAccountsPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={CHART_OF_ACCOUNTS_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="accounting">
                <RoutedPage>
                  <ChartOfAccountsPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={FISCAL_YEARS_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="accounting">
                <RoutedPage>
                  <FiscalYearsPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={JOURNAL_ENTRIES_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="accounting">
                <RoutedPage>
                  <JournalEntriesPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={JOURNAL_ENTRY_DETAIL_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="accounting">
                <RoutedPage>
                  <JournalEntryDetailPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={PROFIT_AND_LOSS_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="accounting">
                <RoutedPage>
                  <ProfitAndLossPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={BALANCE_SHEET_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="accounting">
                <RoutedPage>
                  <BalanceSheetPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={TRIAL_BALANCE_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="accounting">
                <RoutedPage>
                  <TrialBalancePage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={BANK_RECONCILIATION_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="accounting">
                <RoutedPage>
                  <BankReconciliationPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={COLLECTIONS_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="accounting">
                <RoutedPage>
                  <CollectionsPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={BUDGETS_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="accounting">
                <RoutedPage>
                  <BudgetsPage />
                </RoutedPage>
              </ProtectedAppRoute>
            }
          />
          <Route
            path={BUDGET_VARIANCE_ROUTE}
            element={
              <ProtectedAppRoute requiredFeature="accounting">
                <RoutedPage>
                  <BudgetVariancePage />
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
