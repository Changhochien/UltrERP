import type { LucideIcon } from "lucide-react";
import {
  Boxes,
  BrainCircuit,
  CircleDollarSign,
  LayoutDashboard,
  ReceiptText,
  Settings,
  ShieldCheck,
  ShoppingCart,
  Users,
  WalletCards,
  LayoutDashboardIcon,
} from "lucide-react";

import type { AppFeature } from "../hooks/usePermissions";
import {
  ADMIN_ROUTE,
  CUSTOMER_CREATE_ROUTE,
  CUSTOMERS_ROUTE,
  HOME_ROUTE,
  INVENTORY_BELOW_REORDER_REPORT_ROUTE,
  INVENTORY_CATEGORIES_ROUTE,
  INVENTORY_REORDER_SUGGESTIONS_ROUTE,
  INVENTORY_VALUATION_ROUTE,
  INVENTORY_ROUTE,
  INTELLIGENCE_ROUTE,
  INVOICES_ROUTE,
  INVOICE_CREATE_ROUTE,
  LOGIN_ROUTE,
  ORDERS_ROUTE,
  ORDER_CREATE_ROUTE,
  OWNER_DASHBOARD_ROUTE,
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
        feature: "owner_dashboard",
        label: "nav.ownerDashboard",
        to: OWNER_DASHBOARD_ROUTE,
        description: "routes.ownerDashboard.description",
        icon: LayoutDashboardIcon,
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
        feature: "intelligence",
        label: "nav.intelligence",
        to: INTELLIGENCE_ROUTE,
        description: "routes.intelligence.description",
        icon: BrainCircuit,
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
  { match: INTELLIGENCE_ROUTE, labelKey: "routes.intelligence.label", descriptionKey: "routes.intelligence.description" },
  { match: INVOICES_ROUTE, labelKey: "routes.invoices.label", descriptionKey: "routes.invoices.description" },
  { match: INVOICE_CREATE_ROUTE, labelKey: "routes.createInvoice.label", descriptionKey: "routes.createInvoice.description" },
  { match: ORDERS_ROUTE, labelKey: "routes.orders.label", descriptionKey: "routes.orders.description" },
  { match: ORDER_CREATE_ROUTE, labelKey: "routes.createOrder.label", descriptionKey: "routes.createOrder.description" },
  { match: PAYMENTS_ROUTE, labelKey: "routes.payments.label", descriptionKey: "routes.payments.description" },
  { match: INVENTORY_ROUTE, labelKey: "routes.inventory.label", descriptionKey: "routes.inventory.description" },
  { match: INVENTORY_CATEGORIES_ROUTE, labelKey: "routes.inventoryCategories.label", descriptionKey: "routes.inventoryCategories.description" },
  { match: INVENTORY_BELOW_REORDER_REPORT_ROUTE, labelKey: "routes.belowReorderReport.label", descriptionKey: "routes.belowReorderReport.description" },
  { match: INVENTORY_VALUATION_ROUTE, labelKey: "routes.inventoryValuation.label", descriptionKey: "routes.inventoryValuation.description" },
  { match: INVENTORY_REORDER_SUGGESTIONS_ROUTE, labelKey: "routes.reorderSuggestions.label", descriptionKey: "routes.reorderSuggestions.description" },
  { match: PURCHASES_ROUTE, labelKey: "routes.purchases.label", descriptionKey: "routes.purchases.description" },
  { match: ADMIN_ROUTE, labelKey: "routes.admin.label", descriptionKey: "routes.admin.description" },
  { match: OWNER_DASHBOARD_ROUTE, labelKey: "routes.ownerDashboard.label", descriptionKey: "routes.ownerDashboard.description" },
  { match: SETTINGS_ROUTE, labelKey: "routes.settings.label", descriptionKey: "routes.settings.description" },
  { match: LOGIN_ROUTE, labelKey: "routes.login.label", descriptionKey: "routes.login.description" },
] as const;

export function getRouteContext(pathname: string) {
  if (pathname === INVENTORY_CATEGORIES_ROUTE) {
    return {
      labelKey: "routes.inventoryCategories.label",
      descriptionKey: "routes.inventoryCategories.description",
      sectionKey: "nav.operations",
    };
  }

  if (pathname === INVENTORY_BELOW_REORDER_REPORT_ROUTE) {
    return {
      labelKey: "routes.belowReorderReport.label",
      descriptionKey: "routes.belowReorderReport.description",
      sectionKey: "nav.operations",
    };
  }

  if (pathname === INVENTORY_VALUATION_ROUTE) {
    return {
      labelKey: "routes.inventoryValuation.label",
      descriptionKey: "routes.inventoryValuation.description",
      sectionKey: "nav.operations",
    };
  }

  if (pathname === INVENTORY_REORDER_SUGGESTIONS_ROUTE) {
    return {
      labelKey: "routes.reorderSuggestions.label",
      descriptionKey: "routes.reorderSuggestions.description",
      sectionKey: "nav.operations",
    };
  }

  if (pathname.startsWith(`${ORDERS_ROUTE}/`) && pathname !== ORDER_CREATE_ROUTE) {
    return {
      labelKey: "routes.orderDetail.label",
      descriptionKey: "routes.orderDetail.description",
      sectionKey: "routes.orderDetail.section",
    };
  }

  if (
    pathname.startsWith(`${INVENTORY_ROUTE}/`) &&
    pathname !== INVENTORY_ROUTE &&
    !pathname.startsWith(INVENTORY_CATEGORIES_ROUTE)
  ) {
    return {
      labelKey: "routes.productDetail.label",
      descriptionKey: "routes.productDetail.description",
      sectionKey: "nav.operations",
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
