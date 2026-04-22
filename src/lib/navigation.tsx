import type { LucideIcon } from "lucide-react";
import {
  BriefcaseBusiness,
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
  TrendingUp,
  FileBarChart,
  Package,
} from "lucide-react";

import type { AppFeature } from "../hooks/usePermissions";
import {
  ADMIN_ROUTE,
  CRM_LEAD_CREATE_ROUTE,
  CRM_LEADS_ROUTE,
  CRM_OPPORTUNITY_CREATE_ROUTE,
  CRM_OPPORTUNITIES_ROUTE,
  CRM_QUOTATION_CREATE_ROUTE,
  CRM_QUOTATIONS_ROUTE,
  CRM_REPORTING_ROUTE,
  CRM_SETUP_ROUTE,
  CUSTOMER_CREATE_ROUTE,
  CUSTOMERS_ROUTE,
  HOME_ROUTE,
  INVENTORY_BELOW_REORDER_REPORT_ROUTE,
  INVENTORY_CATEGORIES_ROUTE,
  INVENTORY_COUNT_SESSIONS_ROUTE,
  INVENTORY_TRANSFERS_ROUTE,
  INVENTORY_UNITS_ROUTE,
  INVENTORY_REORDER_SUGGESTIONS_ROUTE,
  INVENTORY_SUPPLIERS_ROUTE,
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

// Navigation section types for organizing items
// 'standard' = primary workflow items (no section header)
// 'reports' = analytics and reporting tools (with "Reports" header, indented)
// 'setup' = configuration and settings (with "Setup" header, indented)
export type NavigationSectionType = 'standard' | 'reports' | 'setup';

export interface NavigationItem {
  feature: AppFeature;
  label: string; // i18n key, e.g. "nav.dashboard"
  to: string;
  description: string; // i18n key, e.g. "routes.dashboard.description"
  icon: LucideIcon;
}

export interface NavigationSection {
  type: NavigationSectionType;
  label: string | null; // null = no header shown for standard section
  items: NavigationItem[];
}

export interface NavigationGroup {
  label: string; // i18n key, e.g. "nav.overview"
  sections: NavigationSection[];
}

export const NAVIGATION_GROUPS: NavigationGroup[] = [
  {
    label: "nav.overview",
    sections: [
      {
        type: 'standard',
        label: null,
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
    ],
  },
  {
    label: "nav.crm",
    sections: [
      {
        type: 'standard',
        label: null,
        items: [
          {
            feature: "crm",
            label: "nav.crmLeads",
            to: CRM_LEADS_ROUTE,
            description: "routes.crmLeads.description",
            icon: Users,
          },
          {
            feature: "crm",
            label: "nav.crmOpportunities",
            to: CRM_OPPORTUNITIES_ROUTE,
            description: "routes.crmOpportunities.description",
            icon: BriefcaseBusiness,
          },
          {
            feature: "crm",
            label: "nav.crmQuotations",
            to: CRM_QUOTATIONS_ROUTE,
            description: "routes.crmQuotations.description",
            icon: ReceiptText,
          },
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
        ],
      },
      {
        type: 'reports',
        label: "nav.reports",
        items: [
          {
            feature: "crm",
            label: "nav.crmReporting",
            to: CRM_REPORTING_ROUTE,
            description: "routes.crmReporting.description",
            icon: TrendingUp,
          },
          {
            feature: "intelligence",
            label: "nav.intelligence",
            to: INTELLIGENCE_ROUTE,
            description: "routes.intelligence.description",
            icon: BrainCircuit,
          },
        ],
      },
      {
        type: 'setup',
        label: "nav.setup",
        items: [
          {
            feature: "settings",
            label: "nav.crmSetup",
            to: CRM_SETUP_ROUTE,
            description: "routes.crmSetup.description",
            icon: Settings,
          },
        ],
      },
    ],
  },
  {
    label: "nav.finance",
    sections: [
      {
        type: 'standard',
        label: null,
        items: [
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
        type: 'reports',
        label: "nav.reports",
        items: [
          {
            feature: "invoices",
            label: "nav.invoiceReports",
            to: INVOICES_ROUTE,
            description: "routes.invoiceReports.description",
            icon: FileBarChart,
          },
        ],
      },
    ],
  },
  {
    label: "nav.operations",
    sections: [
      {
        type: 'standard',
        label: null,
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
      {
        type: 'reports',
        label: "nav.reports",
        items: [
          {
            feature: "inventory",
            label: "nav.inventoryReports",
            to: INVENTORY_ROUTE,
            description: "routes.inventoryReports.description",
            icon: Package,
          },
          {
            feature: "inventory",
            label: "nav.belowReorderReport",
            to: INVENTORY_BELOW_REORDER_REPORT_ROUTE,
            description: "routes.belowReorderReport.description",
            icon: TrendingUp,
          },
          {
            feature: "inventory",
            label: "nav.inventoryValuation",
            to: INVENTORY_VALUATION_ROUTE,
            description: "routes.inventoryValuation.description",
            icon: FileBarChart,
          },
        ],
      },
      {
        type: 'setup',
        label: "nav.setup",
        items: [
          {
            feature: "inventory",
            label: "nav.inventoryCategories",
            to: INVENTORY_CATEGORIES_ROUTE,
            description: "routes.inventoryCategories.description",
            icon: Settings,
          },
          {
            feature: "purchases",
            label: "nav.suppliers",
            to: INVENTORY_SUPPLIERS_ROUTE,
            description: "routes.suppliers.description",
            icon: Settings,
          },
        ],
      },
    ],
  },
];

// i18n keys for route contexts — resolved by callers via useTranslation
export const ROUTE_CONTEXT_KEYS = [
  { match: HOME_ROUTE, labelKey: "routes.dashboard.label", descriptionKey: "routes.dashboard.description" },
  { match: CRM_LEADS_ROUTE, labelKey: "routes.crmLeads.label", descriptionKey: "routes.crmLeads.description" },
  { match: CRM_LEAD_CREATE_ROUTE, labelKey: "routes.createLead.label", descriptionKey: "routes.createLead.description" },
  { match: CRM_OPPORTUNITIES_ROUTE, labelKey: "routes.crmOpportunities.label", descriptionKey: "routes.crmOpportunities.description" },
  { match: CRM_OPPORTUNITY_CREATE_ROUTE, labelKey: "routes.createOpportunity.label", descriptionKey: "routes.createOpportunity.description" },
  { match: CRM_QUOTATIONS_ROUTE, labelKey: "routes.crmQuotations.label", descriptionKey: "routes.crmQuotations.description" },
  { match: CRM_QUOTATION_CREATE_ROUTE, labelKey: "routes.createQuotation.label", descriptionKey: "routes.createQuotation.description" },
  { match: CRM_REPORTING_ROUTE, labelKey: "routes.crmReporting.label", descriptionKey: "routes.crmReporting.description" },
  { match: CRM_SETUP_ROUTE, labelKey: "routes.crmSetup.label", descriptionKey: "routes.crmSetup.description" },
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
  { match: INVENTORY_UNITS_ROUTE, labelKey: "routes.inventoryUnits.label", descriptionKey: "routes.inventoryUnits.description" },
  { match: INVENTORY_TRANSFERS_ROUTE, labelKey: "routes.inventoryTransfers.label", descriptionKey: "routes.inventoryTransfers.description" },
  { match: INVENTORY_COUNT_SESSIONS_ROUTE, labelKey: "routes.inventoryCountSessions.label", descriptionKey: "routes.inventoryCountSessions.description" },
  { match: INVENTORY_BELOW_REORDER_REPORT_ROUTE, labelKey: "routes.belowReorderReport.label", descriptionKey: "routes.belowReorderReport.description" },
  { match: INVENTORY_VALUATION_ROUTE, labelKey: "routes.inventoryValuation.label", descriptionKey: "routes.inventoryValuation.description" },
  { match: INVENTORY_REORDER_SUGGESTIONS_ROUTE, labelKey: "routes.reorderSuggestions.label", descriptionKey: "routes.reorderSuggestions.description" },
  { match: INVENTORY_SUPPLIERS_ROUTE, labelKey: "routes.inventorySuppliers.label", descriptionKey: "routes.inventorySuppliers.description" },
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

  if (pathname === INVENTORY_UNITS_ROUTE) {
    return {
      labelKey: "routes.inventoryUnits.label",
      descriptionKey: "routes.inventoryUnits.description",
      sectionKey: "nav.operations",
    };
  }

  if (pathname === INVENTORY_TRANSFERS_ROUTE) {
    return {
      labelKey: "routes.inventoryTransfers.label",
      descriptionKey: "routes.inventoryTransfers.description",
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

  if (pathname === INVENTORY_SUPPLIERS_ROUTE) {
    return {
      labelKey: "routes.inventorySuppliers.label",
      descriptionKey: "routes.inventorySuppliers.description",
      sectionKey: "nav.operations",
    };
  }

  if (pathname === INVENTORY_COUNT_SESSIONS_ROUTE) {
    return {
      labelKey: "routes.inventoryCountSessions.label",
      descriptionKey: "routes.inventoryCountSessions.description",
      sectionKey: "nav.operations",
    };
  }

  if (pathname.startsWith(`${INVENTORY_COUNT_SESSIONS_ROUTE}/`)) {
    return {
      labelKey: "routes.inventoryCountSessionDetail.label",
      descriptionKey: "routes.inventoryCountSessionDetail.description",
      sectionKey: "nav.operations",
    };
  }

  if (pathname.startsWith(INVENTORY_SUPPLIERS_ROUTE + "/")) {
    return {
      labelKey: "routes.supplierDetail.label",
      descriptionKey: "routes.supplierDetail.description",
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

  if (pathname.startsWith(`${CRM_LEADS_ROUTE}/`) && pathname !== CRM_LEAD_CREATE_ROUTE) {
    return {
      labelKey: "routes.leadDetail.label",
      descriptionKey: "routes.leadDetail.description",
      sectionKey: "nav.revenue",
    };
  }

  if (pathname.startsWith(`${CRM_OPPORTUNITIES_ROUTE}/`) && pathname !== CRM_OPPORTUNITY_CREATE_ROUTE) {
    return {
      labelKey: "routes.opportunityDetail.label",
      descriptionKey: "routes.opportunityDetail.description",
      sectionKey: "nav.revenue",
    };
  }

  if (pathname.startsWith(`${CRM_QUOTATIONS_ROUTE}/`) && pathname !== CRM_QUOTATION_CREATE_ROUTE) {
    return {
      labelKey: "routes.quotationDetail.label",
      descriptionKey: "routes.quotationDetail.description",
      sectionKey: "nav.revenue",
    };
  }

  if (
    pathname.startsWith(`${INVENTORY_ROUTE}/`) &&
    pathname !== INVENTORY_ROUTE &&
    !pathname.startsWith(INVENTORY_CATEGORIES_ROUTE) &&
    !pathname.startsWith(INVENTORY_TRANSFERS_ROUTE) &&
    !pathname.startsWith(INVENTORY_COUNT_SESSIONS_ROUTE) &&
    !pathname.startsWith(INVENTORY_SUPPLIERS_ROUTE)
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
      candidate.sections.flatMap((s) => s.items).some((item) => item.to === pathname),
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
  { label: "nav.createOpportunity", to: CRM_OPPORTUNITY_CREATE_ROUTE, icon: BriefcaseBusiness },
  { label: "nav.crmLeads", to: CRM_LEAD_CREATE_ROUTE, icon: Users },
  { label: "nav.createCustomer", to: CUSTOMER_CREATE_ROUTE, icon: Users },
  { label: "nav.createInvoice", to: INVOICE_CREATE_ROUTE, icon: ReceiptText },
  { label: "nav.newOrder", to: ORDER_CREATE_ROUTE, icon: CircleDollarSign },
];
