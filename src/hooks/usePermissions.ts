/** Role-based permission checker. */

import { useOptionalAuth } from "./useAuth";

export type AppFeature =
  | "dashboard"
  | "inventory"
  | "purchases"
  | "customers"
  | "intelligence"
  | "invoices"
  | "orders"
  | "payments"
  | "admin"
  | "owner_dashboard"
  | "settings";

export type PermissionLevel = "read" | "write";

export const ROLE_PERMISSIONS: Record<string, Partial<Record<AppFeature, PermissionLevel>>> = {
  admin: {
    dashboard: "write",
    inventory: "write",
    purchases: "write",
    customers: "write",
    intelligence: "read",
    invoices: "write",
    orders: "write",
    payments: "write",
    admin: "write",
    owner_dashboard: "write",
    settings: "write",
  },
  owner: {
    dashboard: "write",
    inventory: "write",
    purchases: "write",
    customers: "write",
    intelligence: "read",
    invoices: "write",
    orders: "write",
    payments: "write",
    admin: "write",
    owner_dashboard: "write",
    settings: "write",
  },
  finance: {
    dashboard: "read",
    purchases: "read",
    customers: "read",
    invoices: "write",
    payments: "write",
    settings: "write",
  },
  warehouse: {
    dashboard: "read",
    inventory: "write",
    purchases: "read",
    orders: "read",
  },
  sales: {
    dashboard: "read",
    inventory: "read",
    customers: "write",
    intelligence: "read",
    invoices: "read",
    orders: "write",
  },
};

export function usePermissions() {
  const auth = useOptionalAuth();
  const user = auth?.user ?? null;

  function canAccess(feature: AppFeature): boolean {
    if (!user) return false;
    return Boolean(ROLE_PERMISSIONS[user.role]?.[feature]);
  }

  function canWrite(feature: AppFeature): boolean {
    if (!user) return false;
    return ROLE_PERMISSIONS[user.role]?.[feature] === "write";
  }

  return { canAccess, canWrite };
}
