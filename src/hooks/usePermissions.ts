/** Role-based permission checker. */

import { useAuth } from "./useAuth";

export type AppFeature =
  | "dashboard"
  | "inventory"
  | "customers"
  | "invoices"
  | "orders"
  | "payments"
  | "admin";

type PermissionLevel = "read" | "write";

const ROLE_PERMISSIONS: Record<string, Partial<Record<AppFeature, PermissionLevel>>> = {
  owner: {
    dashboard: "write",
    inventory: "write",
    customers: "write",
    invoices: "write",
    orders: "write",
    payments: "write",
    admin: "write",
  },
  finance: {
    dashboard: "read",
    customers: "read",
    invoices: "write",
    payments: "write",
  },
  warehouse: {
    dashboard: "read",
    inventory: "write",
    orders: "read",
  },
  sales: {
    dashboard: "read",
    inventory: "read",
    customers: "write",
    invoices: "read",
    orders: "write",
  },
};

export function usePermissions() {
  const { user } = useAuth();

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
