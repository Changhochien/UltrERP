import type { LucideIcon } from "lucide-react";
import {
  Boxes,
  CircleDollarSign,
  LayoutDashboard,
  ReceiptText,
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
} from "./routes";

export interface NavigationItem {
  feature: AppFeature;
  label: string;
  to: string;
  description: string;
  icon: LucideIcon;
}

export interface NavigationGroup {
  label: string;
  items: NavigationItem[];
}

export const NAVIGATION_GROUPS: NavigationGroup[] = [
  {
    label: "Overview",
    items: [
      {
        feature: "dashboard",
        label: "Dashboard",
        to: HOME_ROUTE,
        description: "Snapshot of revenue, traffic, and stock health.",
        icon: LayoutDashboard,
      },
      {
        feature: "admin",
        label: "Admin",
        to: ADMIN_ROUTE,
        description: "Owner-only visibility into users and audit activity.",
        icon: ShieldCheck,
      },
    ],
  },
  {
    label: "Revenue",
    items: [
      {
        feature: "customers",
        label: "Customers",
        to: CUSTOMERS_ROUTE,
        description: "Search, inspect, and update customer records.",
        icon: Users,
      },
      {
        feature: "invoices",
        label: "Invoices",
        to: INVOICES_ROUTE,
        description: "Track invoice status, balances, and eGUI updates.",
        icon: ReceiptText,
      },
      {
        feature: "orders",
        label: "Orders",
        to: ORDERS_ROUTE,
        description: "Create orders and advance operational statuses.",
        icon: ShoppingCart,
      },
      {
        feature: "payments",
        label: "Payments",
        to: PAYMENTS_ROUTE,
        description: "Reconcile inbound payments against invoices.",
        icon: WalletCards,
      },
    ],
  },
  {
    label: "Operations",
    items: [
      {
        feature: "inventory",
        label: "Inventory",
        to: INVENTORY_ROUTE,
        description: "Search stock, switch warehouses, and act on alerts.",
        icon: Boxes,
      },
    ],
  },
];

const ROUTE_CONTEXTS = [
  { match: HOME_ROUTE, label: "Dashboard", description: "Morning operating metrics and action shortcuts." },
  { match: CUSTOMERS_ROUTE, label: "Customers", description: "Customer search, status filters, and record health." },
  { match: CUSTOMER_CREATE_ROUTE, label: "Create Customer", description: "Capture a new customer record with validation." },
  { match: INVOICES_ROUTE, label: "Invoices", description: "Invoice search, payment status, and detail review." },
  { match: INVOICE_CREATE_ROUTE, label: "Create Invoice", description: "Draft invoice lines and preview totals in real time." },
  { match: ORDERS_ROUTE, label: "Orders", description: "Sales order intake, routing, and lifecycle updates." },
  { match: ORDER_CREATE_ROUTE, label: "Create Order", description: "Compose a new sales order with live stock visibility." },
  { match: PAYMENTS_ROUTE, label: "Payments", description: "Auto-match, review, and manually reconcile payments." },
  { match: INVENTORY_ROUTE, label: "Inventory", description: "Read-heavy stock workspace with warehouse switching." },
  { match: ADMIN_ROUTE, label: "Admin", description: "User access and the latest audit events." },
  { match: LOGIN_ROUTE, label: "Login", description: "Secure access to the ERP workspace." },
];

export function getRouteContext(pathname: string) {
  if (pathname.startsWith(`${ORDERS_ROUTE}/`) && pathname !== ORDER_CREATE_ROUTE) {
    return {
      label: "Order Detail",
      description: "Review line items and transition order status.",
      section: "Revenue",
    };
  }

  const route = ROUTE_CONTEXTS.find((entry) => entry.match === pathname);
  if (route) {
    const group = NAVIGATION_GROUPS.find((candidate) =>
      candidate.items.some((item) => item.to === pathname),
    );

    return {
      ...route,
      section: group?.label ?? "Workspace",
    };
  }

  return {
    label: "Workspace",
    description: "Operational tools for UltrERP.",
    section: "Workspace",
  };
}

export const DASHBOARD_QUICK_LINKS = [
  { label: "Create Customer", to: CUSTOMER_CREATE_ROUTE, icon: Users },
  { label: "Create Invoice", to: INVOICE_CREATE_ROUTE, icon: ReceiptText },
  { label: "New Order", to: ORDER_CREATE_ROUTE, icon: CircleDollarSign },
];