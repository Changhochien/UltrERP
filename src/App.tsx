import type { ReactNode } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";

import {
  CUSTOMER_CREATE_ROUTE,
  CUSTOMERS_ROUTE,
  HOME_ROUTE,
} from "./lib/routes";
import CreateCustomerPage from "./pages/customers/CreateCustomerPage";
import { CustomerListPage } from "./pages/customers/CustomerListPage";

export const APP_TITLE = "UltrERP";
export const APP_TAGLINE = "AI-native ERP for Taiwan SMBs";

function RoutedPage({ children }: { children: ReactNode }) {
  const navigate = useNavigate();

  return (
    <main className="app-shell">
      <nav className="top-nav">
        <button type="button" onClick={() => navigate(HOME_ROUTE)}>
          ← Home
        </button>
      </nav>
      {children}
    </main>
  );
}

function HomePage() {
  const navigate = useNavigate();

  return (
    <main className="app-shell">
      <section className="hero-card">
        <p className="eyebrow">Epic 3 Customer Management</p>
        <h1>{APP_TITLE}</h1>
        <p>{APP_TAGLINE}</p>
        <p className="caption">Frontend scaffold is live and ready for domain slices.</p>
        <nav style={{ marginTop: "1.5rem", display: "flex", gap: "1rem" }}>
          <button type="button" onClick={() => navigate(CUSTOMERS_ROUTE)}>
            Browse Customers
          </button>
          <button type="button" onClick={() => navigate(CUSTOMER_CREATE_ROUTE)}>
            Create Customer
          </button>
        </nav>
      </section>
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

export default function App() {
  return (
    <Routes>
      <Route path={HOME_ROUTE} element={<HomePage />} />
      <Route path={CUSTOMERS_ROUTE} element={<CustomerListRoute />} />
      <Route path={CUSTOMER_CREATE_ROUTE} element={<CreateCustomerRoute />} />
      <Route path="*" element={<Navigate to={HOME_ROUTE} replace />} />
    </Routes>
  );
}
