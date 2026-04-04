import type { ReactNode } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";

import { AppNavigation } from "./components/AppNavigation";
import { DesktopTrayController } from "./components/desktop/DesktopTrayController";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { ShortcutLayer } from "./components/shortcuts/ShortcutLayer";
import { AuthProvider } from "./hooks/useAuth";
import { usePostHogPageView } from "./hooks/usePostHogPageView";

import {
  ADMIN_ROUTE,
  CUSTOMER_CREATE_ROUTE,
  CUSTOMERS_ROUTE,
  HOME_ROUTE,
  INVENTORY_ROUTE,
  INVOICES_ROUTE,
  INVOICE_CREATE_ROUTE,
  LOGIN_ROUTE,
  ORDERS_ROUTE,
  ORDER_CREATE_ROUTE,
  ORDER_DETAIL_ROUTE,
  PAYMENTS_ROUTE,
} from "./lib/routes";
import { AdminPage } from "./pages/AdminPage";
import CreateCustomerPage from "./pages/customers/CreateCustomerPage";
import { CustomerListPage } from "./pages/customers/CustomerListPage";
import { DashboardPage } from "./pages/dashboard/DashboardPage";
import { InventoryPage } from "./pages/InventoryPage";
import CreateInvoicePage from "./pages/invoices/CreateInvoicePage";
import { InvoicesPage } from "./pages/InvoicesPage";
import { OrdersPage } from "./pages/orders/OrdersPage";
import { PaymentsPage } from "./pages/PaymentsPage";
import LoginPage from "./pages/LoginPage";

export const APP_TITLE = "UltrERP";
export const APP_TAGLINE = "AI-native ERP for Taiwan SMBs";

function RoutedPage({ children }: { children: ReactNode }) {
  return (
    <main className="app-shell">
      <div className="app-frame">
        <AppNavigation />
        <DesktopTrayController />
        <ShortcutLayer />
        {children}
      </div>
    </main>
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

export default function App() {
  usePostHogPageView();

  return (
    <AuthProvider>
      <Routes>
        <Route path={LOGIN_ROUTE} element={<LoginPage />} />
        <Route path={HOME_ROUTE} element={<ProtectedRoute requiredFeature="dashboard"><RoutedPage><DashboardPage /></RoutedPage></ProtectedRoute>} />
        <Route path={INVENTORY_ROUTE} element={<ProtectedRoute requiredFeature="inventory"><RoutedPage><InventoryPage /></RoutedPage></ProtectedRoute>} />
        <Route path={CUSTOMERS_ROUTE} element={<ProtectedRoute requiredFeature="customers"><CustomerListRoute /></ProtectedRoute>} />
        <Route path={CUSTOMER_CREATE_ROUTE} element={<ProtectedRoute requiredFeature="customers" requiredWrite><CreateCustomerRoute /></ProtectedRoute>} />
        <Route path={INVOICES_ROUTE} element={<ProtectedRoute requiredFeature="invoices"><RoutedPage><InvoicesPage /></RoutedPage></ProtectedRoute>} />
        <Route path={INVOICE_CREATE_ROUTE} element={<ProtectedRoute requiredFeature="invoices" requiredWrite><CreateInvoiceRoute /></ProtectedRoute>} />
        <Route path={ORDERS_ROUTE} element={<ProtectedRoute requiredFeature="orders"><RoutedPage><OrdersPage /></RoutedPage></ProtectedRoute>} />
        <Route path={ORDER_CREATE_ROUTE} element={<ProtectedRoute requiredFeature="orders" requiredWrite><RoutedPage><OrdersPage /></RoutedPage></ProtectedRoute>} />
        <Route path={ORDER_DETAIL_ROUTE} element={<ProtectedRoute requiredFeature="orders"><RoutedPage><OrdersPage /></RoutedPage></ProtectedRoute>} />
        <Route path={PAYMENTS_ROUTE} element={<ProtectedRoute requiredFeature="payments"><RoutedPage><PaymentsPage /></RoutedPage></ProtectedRoute>} />
        <Route path={ADMIN_ROUTE} element={<ProtectedRoute requiredFeature="admin"><RoutedPage><AdminPage /></RoutedPage></ProtectedRoute>} />
        <Route path="*" element={<Navigate to={HOME_ROUTE} replace />} />
      </Routes>
    </AuthProvider>
  );
}
