import type { LucideIcon } from "lucide-react";
import {
  Boxes,
  CircleDollarSign,
  LayoutDashboard,
  ReceiptText,
  Settings,
  ShieldCheck,
  ShoppingCart,
  Users,
  WalletCards,
} from "lucide-react";

import type { AppFeature } from "../hooks/usePermissions";
import {
  ADMIN_ROUTE,
  CUSTOMERS_ROUTE,
  CUSTOMER_CREATE_ROUTE,
  HOME_ROUTE,
  INVENTORY_ROUTE,
  INVOICES_ROUTE,
  INVOICE_CREATE_ROUTE,
  LOGIN_ROUTE,
  ORDERS_ROUTE,
  ORDER_CREATE_ROUTE,
  PAYMENTS_ROUTE,
  PURCHASES_ROUTE,
  SETTINGS_ROUTE,
} from "./routes";

export interface NavigationItem {
  feature: AppFeature;
  label: string; // i18n key, e.g. "nav.dashboard"
  to: string;
  description: string; // i18n key, e.g. "routes.dashboard.description"
  icon: LucideIcon;
}

export interface NavigationGroup {
  label: string; // i18n key, e.g. "nav.overview"
  items: NavigationItem[];
}

export const NAVIGATION_GROUPS: NavigationGroup[] = [
  {
    label: "nav.overview",
    items: [
      {
        feature: "dashboard",
        label: "nav.dashboard",
        to: HOME_ROUTE,
        description: "routes.dashboard.description",
        icon: LayoutDashboard,
      },
      {
        feature: "admin",
        label: "nav.admin",
        to: ADMIN_ROUTE,
        description: "routes.admin.description",
        icon: ShieldCheck,
      },
      {
        feature: "settings",
        label: "nav.settings",
        to: SETTINGS_ROUTE,
        description: "routes.settings.description",
        icon: Settings,
      },
    ],
  },
  {
    label: "nav.revenue",
    items: [
      {
        feature: "customers",
        label: "nav.customers",
        to: CUSTOMERS_ROUTE,
        description: "routes.customers.description",
        icon: Users,
      },
      {
        feature: "invoices",
        label: "nav.invoices",
        to: INVOICES_ROUTE,
        description: "routes.invoices.description",
        icon: ReceiptText,
      },
      {
        feature: "orders",
        label: "nav.orders",
        to: ORDERS_ROUTE,
        description: "routes.orders.description",
        icon: ShoppingCart,
      },
      {
        feature: "payments",
        label: "nav.payments",
        to: PAYMENTS_ROUTE,
        description: "routes.payments.description",
        icon: WalletCards,
      },
    ],
  },
  {
    label: "nav.operations",
    items: [
      {
        feature: "inventory",
        label: "nav.inventory",
        to: INVENTORY_ROUTE,
        description: "routes.inventory.description",
        icon: Boxes,
      },
      {
        feature: "purchases",
        label: "nav.purchases",
        to: PURCHASES_ROUTE,
        description: "routes.purchases.description",
        icon: CircleDollarSign,
      },
    ],
  },
];

// i18n keys for route contexts — resolved by callers via useTranslation
export const ROUTE_CONTEXT_KEYS = [
  { match: HOME_ROUTE, labelKey: "routes.dashboard.label", descriptionKey: "routes.dashboard.description" },
  { match: CUSTOMERS_ROUTE, labelKey: "routes.customers.label", descriptionKey: "routes.customers.description" },
  { match: CUSTOMER_CREATE_ROUTE, labelKey: "routes.createCustomer.label", descriptionKey: "routes.createCustomer.description" },
  { match: INVOICES_ROUTE, labelKey: "routes.invoices.label", descriptionKey: "routes.invoices.description" },
  { match: INVOICE_CREATE_ROUTE, labelKey: "routes.createInvoice.label", descriptionKey: "routes.createInvoice.description" },
  { match: ORDERS_ROUTE, labelKey: "routes.orders.label", descriptionKey: "routes.orders.description" },
  { match: ORDER_CREATE_ROUTE, labelKey: "routes.createOrder.label", descriptionKey: "routes.createOrder.description" },
  { match: PAYMENTS_ROUTE, labelKey: "routes.payments.label", descriptionKey: "routes.payments.description" },
  { match: INVENTORY_ROUTE, labelKey: "routes.inventory.label", descriptionKey: "routes.inventory.description" },
  { match: PURCHASES_ROUTE, labelKey: "routes.purchases.label", descriptionKey: "routes.purchases.description" },
  { match: ADMIN_ROUTE, labelKey: "routes.admin.label", descriptionKey: "routes.admin.description" },
  { match: SETTINGS_ROUTE, labelKey: "routes.settings.label", descriptionKey: "routes.settings.description" },
  { match: LOGIN_ROUTE, labelKey: "routes.login.label", descriptionKey: "routes.login.description" },
] as const;

export function getRouteContext(pathname: string) {
  if (pathname.startsWith(`${ORDERS_ROUTE}/`) && pathname !== ORDER_CREATE_ROUTE) {
    return {
      labelKey: "routes.orderDetail.label",
      descriptionKey: "routes.orderDetail.description",
      sectionKey: "routes.orderDetail.section",
    };
  }

  const route = ROUTE_CONTEXT_KEYS.find((entry) => entry.match === pathname);
  if (route) {
    const group = NAVIGATION_GROUPS.find((candidate) =>
      candidate.items.some((item) => item.to === pathname),
    );

    return {
      labelKey: route.labelKey,
      descriptionKey: route.descriptionKey,
      sectionKey: group ? `${group.label}` : "routes.workspace.label",
    };
  }

  return {
    labelKey: "routes.workspace.label",
    descriptionKey: "routes.workspace.description",
    sectionKey: "routes.workspace.section",
  };
}

export const DASHBOARD_QUICK_LINKS = [
  { label: "nav.createCustomer", to: CUSTOMER_CREATE_ROUTE, icon: Users },
  { label: "nav.createInvoice", to: INVOICE_CREATE_ROUTE, icon: ReceiptText },
  { label: "nav.newOrder", to: ORDER_CREATE_ROUTE, icon: CircleDollarSign },
];
