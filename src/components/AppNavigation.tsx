import { NavLink } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import { usePermissions } from "../hooks/usePermissions";
import {
  ADMIN_ROUTE,
  CUSTOMERS_ROUTE,
  HOME_ROUTE,
  INVENTORY_ROUTE,
  INVOICES_ROUTE,
  ORDERS_ROUTE,
  PAYMENTS_ROUTE,
} from "../lib/routes";

const NAV_ITEMS = [
  { feature: "dashboard", label: "Dashboard", to: HOME_ROUTE },
  { feature: "inventory", label: "Inventory", to: INVENTORY_ROUTE },
  { feature: "customers", label: "Customers", to: CUSTOMERS_ROUTE },
  { feature: "invoices", label: "Invoices", to: INVOICES_ROUTE },
  { feature: "orders", label: "Orders", to: ORDERS_ROUTE },
  { feature: "payments", label: "Payments", to: PAYMENTS_ROUTE },
  { feature: "admin", label: "Admin", to: ADMIN_ROUTE },
] as const;

export function AppNavigation() {
  const { user, logout } = useAuth();
  const { canAccess } = usePermissions();

  return (
    <header className="app-nav">
      <nav className="app-nav-links" aria-label="Primary">
        {NAV_ITEMS.filter((item) => canAccess(item.feature)).map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `app-nav-link${isActive ? " active" : ""}`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="app-nav-user">
        <span>{user?.role ?? "guest"}</span>
        <button type="button" onClick={logout}>
          Log out
        </button>
      </div>
    </header>
  );
}