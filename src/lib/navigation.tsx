import type { LucideIcon } from "lucide-react";
import {
  BriefcaseBusiness,
  Boxes,
  Calendar,
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
  FileText,
  Lightbulb,
  FileSpreadsheet,
  Calculator,
  Landmark,
  PiggyBank,
  AlertTriangle,
  HandCoins,
  FileTextIcon,
} from "lucide-react";

import type { AppFeature } from "../hooks/usePermissions";
import {
  ACCOUNTING_ROUTE,
  ADMIN_ROUTE,
  BALANCE_SHEET_ROUTE,
  BOM_CREATE_ROUTE,
  BANK_RECONCILIATION_ROUTE,
  BOM_LIST_ROUTE,
  BUDGETS_ROUTE,
  BUDGET_VARIANCE_ROUTE,
  CHART_OF_ACCOUNTS_ROUTE,
  CRM_LEAD_CREATE_ROUTE,
  CRM_LEADS_ROUTE,
  CRM_OPPORTUNITY_CREATE_ROUTE,
  CRM_OPPORTUNITIES_ROUTE,
  CRM_QUOTATION_CREATE_ROUTE,
  CRM_QUOTATIONS_ROUTE,
  CRM_REPORTING_ROUTE,
  CRM_SETUP_ROUTE,
  COLLECTIONS_ROUTE,
  CUSTOMER_CREATE_ROUTE,
  CUSTOMERS_ROUTE,
  FISCAL_YEARS_ROUTE,
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
  JOURNAL_ENTRIES_ROUTE,
  JOURNAL_ENTRY_DETAIL_ROUTE,
  LOGIN_ROUTE,
  MANUFACTURING_ROUTE,
  OEE_DASHBOARD_ROUTE,
  ORDERS_ROUTE,
  ORDER_CREATE_ROUTE,
  OWNER_DASHBOARD_ROUTE,
  PAYMENTS_ROUTE,
  PRODUCTION_PLANNING_ROUTE,
  PRODUCTION_PLAN_CREATE_ROUTE,
  PRODUCTION_PLANS_ROUTE,
  PROFIT_AND_LOSS_ROUTE,
  PURCHASES_ROUTE,
  PROCUREMENT_ROUTE,
  PROCUREMENT_PURCHASE_ORDERS_ROUTE,
  PROCUREMENT_PURCHASE_ORDER_CREATE_ROUTE,
  PROCUREMENT_RFQ_CREATE_ROUTE,
  PROCUREMENT_RFQ_DETAIL_ROUTE,
  ROUTING_CREATE_ROUTE,
  ROUTINGS_ROUTE,
  SETTINGS_ROUTE,
  TRIAL_BALANCE_ROUTE,
  WORK_ORDERS_ROUTE,
  WORKSTATION_CREATE_ROUTE,
  WORKSTATIONS_ROUTE,
} from "./routes";

// Navigation section types for organizing items
// 'standard' = primary workflow items (no section header)
// 'reports' = analytics and reporting tools (with "Reports" header, indented)
// 'setup' = configuration and settings (with "Setup" header, indented)
// 'quick-actions' = quick action shortcuts (shown at bottom when expanded)
export type NavigationSectionType = 'standard' | 'reports' | 'setup' | 'quick-actions';

export interface NavigationItem {
  feature: AppFeature;
  label: string; // i18n key, e.g. "nav.dashboard"
  to: string;
  description: string; // i18n key, e.g. "dashboard.description"
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
    label: "nav.home",
    sections: [
      {
        type: 'standard',
        label: null,
        items: [
          {
            feature: "dashboard",
            label: "nav.dashboard",
            to: HOME_ROUTE,
            description: "dashboard.description",
            icon: LayoutDashboard,
          },
          {
            feature: "settings",
            label: "nav.settings",
            to: SETTINGS_ROUTE,
            description: "settings.description",
            icon: Settings,
          },
          {
            feature: "admin",
            label: "nav.admin",
            to: ADMIN_ROUTE,
            description: "admin.description",
            icon: ShieldCheck,
          },
          {
            feature: "owner_dashboard",
            label: "nav.ownerDashboard",
            to: OWNER_DASHBOARD_ROUTE,
            description: "ownerDashboard.description",
            icon: LayoutDashboardIcon,
          },
        ],
      },
      {
        type: 'quick-actions',
        label: "nav.quickActions",
        items: [
          {
            feature: "crm",
            label: "nav.createLead",
            to: CRM_LEAD_CREATE_ROUTE,
            description: "createLead.description",
            icon: Users,
          },
          {
            feature: "crm",
            label: "nav.createOpportunity",
            to: CRM_OPPORTUNITY_CREATE_ROUTE,
            description: "createOpportunity.description",
            icon: BriefcaseBusiness,
          },
          {
            feature: "invoices",
            label: "nav.createInvoice",
            to: INVOICE_CREATE_ROUTE,
            description: "createInvoice.description",
            icon: ReceiptText,
          },
          {
            feature: "orders",
            label: "nav.newOrder",
            to: ORDER_CREATE_ROUTE,
            description: "createOrder.description",
            icon: ShoppingCart,
          },
          {
            feature: "procurement",
            label: "nav.createRFQ",
            to: PROCUREMENT_RFQ_CREATE_ROUTE,
            description: "createRFQ.description",
            icon: FileText,
          },
        ],
      },
    ],
  },
  {
    label: "nav.sales",
    sections: [
      {
        type: 'standard',
        label: null,
        items: [
          {
            feature: "crm",
            label: "nav.crmLeads",
            to: CRM_LEADS_ROUTE,
            description: "crmLeads.description",
            icon: Users,
          },
          {
            feature: "crm",
            label: "nav.crmOpportunities",
            to: CRM_OPPORTUNITIES_ROUTE,
            description: "crmOpportunities.description",
            icon: BriefcaseBusiness,
          },
          {
            feature: "crm",
            label: "nav.crmQuotations",
            to: CRM_QUOTATIONS_ROUTE,
            description: "crmQuotations.description",
            icon: ReceiptText,
          },
          {
            feature: "customers",
            label: "nav.customers",
            to: CUSTOMERS_ROUTE,
            description: "customers.description",
            icon: Users,
          },
          {
            feature: "orders",
            label: "nav.orders",
            to: ORDERS_ROUTE,
            description: "orders.description",
            icon: ShoppingCart,
          },
        ],
      },
    ],
  },
  {
    label: "nav.inventory",
    sections: [
      {
        type: 'standard',
        label: null,
        items: [
          {
            feature: "inventory",
            label: "nav.products",
            to: INVENTORY_ROUTE,
            description: "inventory.description",
            icon: Boxes,
          },
          {
            feature: "inventory",
            label: "nav.suppliers",
            to: INVENTORY_SUPPLIERS_ROUTE,
            description: "suppliers.description",
            icon: Users,
          },
          {
            feature: "purchases",
            label: "nav.purchases",
            to: PURCHASES_ROUTE,
            description: "purchases.description",
            icon: CircleDollarSign,
          },
          {
            feature: "procurement",
            label: "nav.procurement",
            to: PROCUREMENT_ROUTE,
            description: "procurement.description",
            icon: FileText,
          },
          {
            feature: "procurement",
            label: "nav.purchaseOrders",
            to: PROCUREMENT_PURCHASE_ORDERS_ROUTE,
            description: "procurementPurchaseOrders.description",
            icon: ShoppingCart,
          },
        ],
      },
      {
        type: 'reports',
        label: "nav.reports",
        items: [
          {
            feature: "inventory",
            label: "nav.belowReorderReport",
            to: INVENTORY_BELOW_REORDER_REPORT_ROUTE,
            description: "belowReorderReport.description",
            icon: TrendingUp,
          },
          {
            feature: "inventory",
            label: "nav.inventoryValuation",
            to: INVENTORY_VALUATION_ROUTE,
            description: "inventoryValuation.description",
            icon: FileBarChart,
          },
          {
            feature: "inventory",
            label: "nav.reorderSuggestions",
            to: INVENTORY_REORDER_SUGGESTIONS_ROUTE,
            description: "reorderSuggestions.description",
            icon: Package,
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
            description: "inventoryCategories.description",
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
            description: "invoices.description",
            icon: ReceiptText,
          },
          {
            feature: "payments",
            label: "nav.payments",
            to: PAYMENTS_ROUTE,
            description: "payments.description",
            icon: WalletCards,
          },
          {
            feature: "accounting",
            label: "nav.accounting",
            to: ACCOUNTING_ROUTE,
            description: "accounting.description",
            icon: Calculator,
          },
          {
            feature: "accounting",
            label: "nav.chartOfAccounts",
            to: CHART_OF_ACCOUNTS_ROUTE,
            description: "chartOfAccounts.description",
            icon: FileSpreadsheet,
          },
          {
            feature: "accounting",
            label: "nav.fiscalYears",
            to: FISCAL_YEARS_ROUTE,
            description: "fiscalYears.description",
            icon: Calendar,
          },
          {
            feature: "accounting",
            label: "nav.journalEntries",
            to: JOURNAL_ENTRIES_ROUTE,
            description: "journalEntries.description",
            icon: FileTextIcon,
          },
        ],
      },
      {
        type: 'reports',
        label: "nav.reports",
        items: [
          {
            feature: "accounting",
            label: "nav.profitAndLoss",
            to: PROFIT_AND_LOSS_ROUTE,
            description: "profitAndLoss.description",
            icon: TrendingUp,
          },
          {
            feature: "accounting",
            label: "nav.balanceSheet",
            to: BALANCE_SHEET_ROUTE,
            description: "balanceSheet.description",
            icon: Landmark,
          },
          {
            feature: "accounting",
            label: "nav.trialBalance",
            to: TRIAL_BALANCE_ROUTE,
            description: "trialBalance.description",
            icon: FileBarChart,
          },
        ],
      },
      {
        type: 'setup',
        label: "nav.banking",
        items: [
          {
            feature: "accounting",
            label: "nav.bankReconciliation",
            to: BANK_RECONCILIATION_ROUTE,
            description: "bankReconciliation.description",
            icon: WalletCards,
          },
          {
            feature: "accounting",
            label: "nav.collections",
            to: COLLECTIONS_ROUTE,
            description: "collections.description",
            icon: HandCoins,
          },
          {
            feature: "accounting",
            label: "nav.budgets",
            to: BUDGETS_ROUTE,
            description: "budgets.description",
            icon: PiggyBank,
          },
          {
            feature: "accounting",
            label: "nav.budgetVariance",
            to: BUDGET_VARIANCE_ROUTE,
            description: "budgetVariance.description",
            icon: AlertTriangle,
          },
        ],
      },
    ],
  },
  {
    label: "nav.intelligence",
    sections: [
      {
        type: 'standard',
        label: null,
        items: [
          {
            feature: "intelligence",
            label: "nav.intelligence",
            to: INTELLIGENCE_ROUTE,
            description: "intelligence.description",
            icon: Lightbulb,
          },
        ],
      },
    ],
  },
  {
    label: "nav.manufacturing",
    sections: [
      {
        type: 'standard',
        label: null,
        items: [
          {
            feature: "manufacturing",
            label: "nav.boms",
            to: BOM_LIST_ROUTE,
            description: "boms.description",
            icon: Package,
          },
          {
            feature: "manufacturing",
            label: "nav.workOrders",
            to: WORK_ORDERS_ROUTE,
            description: "workOrders.description",
            icon: FileText,
          },
          {
            feature: "manufacturing",
            label: "nav.productionPlanning",
            to: PRODUCTION_PLANNING_ROUTE,
            description: "productionPlanning.description",
            icon: Calendar,
          },
          {
            feature: "manufacturing",
            label: "nav.productionPlans",
            to: PRODUCTION_PLANS_ROUTE,
            description: "productionPlans.description",
            icon: FileSpreadsheet,
          },
          {
            feature: "manufacturing",
            label: "nav.workstations",
            to: WORKSTATIONS_ROUTE,
            description: "workstations.description",
            icon: Settings,
          },
          {
            feature: "manufacturing",
            label: "nav.routings",
            to: ROUTINGS_ROUTE,
            description: "routings.description",
            icon: Boxes,
          },
        ],
      },
      {
        type: 'reports',
        label: "nav.reports",
        items: [
          {
            feature: "manufacturing",
            label: "nav.oee",
            to: OEE_DASHBOARD_ROUTE,
            description: "oee.description",
            icon: FileBarChart,
          },
        ],
      },
    ],
  },
];

// i18n keys for route contexts — resolved by callers via useTranslation
export const ROUTE_CONTEXT_KEYS = [
  { match: HOME_ROUTE, labelKey: "dashboard.label", descriptionKey: "dashboard.description" },
  { match: CRM_LEADS_ROUTE, labelKey: "crmLeads.label", descriptionKey: "crmLeads.description" },
  { match: CRM_LEAD_CREATE_ROUTE, labelKey: "createLead.label", descriptionKey: "createLead.description" },
  { match: CRM_OPPORTUNITIES_ROUTE, labelKey: "crmOpportunities.label", descriptionKey: "crmOpportunities.description" },
  { match: CRM_OPPORTUNITY_CREATE_ROUTE, labelKey: "createOpportunity.label", descriptionKey: "createOpportunity.description" },
  { match: CRM_QUOTATIONS_ROUTE, labelKey: "crmQuotations.label", descriptionKey: "crmQuotations.description" },
  { match: CRM_QUOTATION_CREATE_ROUTE, labelKey: "createQuotation.label", descriptionKey: "createQuotation.description" },
  { match: CRM_REPORTING_ROUTE, labelKey: "crmReporting.label", descriptionKey: "crmReporting.description" },
  { match: CRM_SETUP_ROUTE, labelKey: "crmSetup.label", descriptionKey: "crmSetup.description" },
  { match: CUSTOMERS_ROUTE, labelKey: "customers.label", descriptionKey: "customers.description" },
  { match: CUSTOMER_CREATE_ROUTE, labelKey: "createCustomer.label", descriptionKey: "createCustomer.description" },
  { match: INTELLIGENCE_ROUTE, labelKey: "intelligence.label", descriptionKey: "intelligence.description" },
  { match: INVOICES_ROUTE, labelKey: "invoices.label", descriptionKey: "invoices.description" },
  { match: INVOICE_CREATE_ROUTE, labelKey: "createInvoice.label", descriptionKey: "createInvoice.description" },
  { match: ORDERS_ROUTE, labelKey: "orders.label", descriptionKey: "orders.description" },
  { match: ORDER_CREATE_ROUTE, labelKey: "createOrder.label", descriptionKey: "createOrder.description" },
  { match: PAYMENTS_ROUTE, labelKey: "payments.label", descriptionKey: "payments.description" },
  { match: INVENTORY_ROUTE, labelKey: "inventory.label", descriptionKey: "inventory.description" },
  { match: INVENTORY_CATEGORIES_ROUTE, labelKey: "inventoryCategories.label", descriptionKey: "inventoryCategories.description" },
  { match: INVENTORY_UNITS_ROUTE, labelKey: "inventoryUnits.label", descriptionKey: "inventoryUnits.description" },
  { match: INVENTORY_TRANSFERS_ROUTE, labelKey: "inventoryTransfers.label", descriptionKey: "inventoryTransfers.description" },
  { match: INVENTORY_COUNT_SESSIONS_ROUTE, labelKey: "inventoryCountSessions.label", descriptionKey: "inventoryCountSessions.description" },
  { match: INVENTORY_BELOW_REORDER_REPORT_ROUTE, labelKey: "belowReorderReport.label", descriptionKey: "belowReorderReport.description" },
  { match: INVENTORY_VALUATION_ROUTE, labelKey: "inventoryValuation.label", descriptionKey: "inventoryValuation.description" },
  { match: INVENTORY_REORDER_SUGGESTIONS_ROUTE, labelKey: "reorderSuggestions.label", descriptionKey: "reorderSuggestions.description" },
  { match: INVENTORY_SUPPLIERS_ROUTE, labelKey: "inventorySuppliers.label", descriptionKey: "inventorySuppliers.description" },
  { match: PURCHASES_ROUTE, labelKey: "purchases.label", descriptionKey: "purchases.description" },
  { match: PROCUREMENT_ROUTE, labelKey: "procurement.label", descriptionKey: "procurement.description" },
  { match: PROCUREMENT_PURCHASE_ORDERS_ROUTE, labelKey: "procurementPurchaseOrders.label", descriptionKey: "procurementPurchaseOrders.description" },
  { match: PROCUREMENT_PURCHASE_ORDER_CREATE_ROUTE, labelKey: "procurementPurchaseOrderCreate.label", descriptionKey: "procurementPurchaseOrderCreate.description" },
  { match: PROCUREMENT_RFQ_CREATE_ROUTE, labelKey: "procurementRFQCreate.label", descriptionKey: "procurementRFQCreate.description" },
  { match: PROCUREMENT_RFQ_DETAIL_ROUTE, labelKey: "procurementRFQDetail.label", descriptionKey: "procurementRFQDetail.description" },
  { match: ADMIN_ROUTE, labelKey: "admin.label", descriptionKey: "admin.description" },
  { match: OWNER_DASHBOARD_ROUTE, labelKey: "ownerDashboard.label", descriptionKey: "ownerDashboard.description" },
  { match: SETTINGS_ROUTE, labelKey: "settings.label", descriptionKey: "settings.description" },
  { match: LOGIN_ROUTE, labelKey: "login.label", descriptionKey: "login.description" },
  // Accounting routes (Epic 26)
  { match: ACCOUNTING_ROUTE, labelKey: "accounting.label", descriptionKey: "accounting.description" },
  { match: CHART_OF_ACCOUNTS_ROUTE, labelKey: "chartOfAccounts.label", descriptionKey: "chartOfAccounts.description" },
  { match: FISCAL_YEARS_ROUTE, labelKey: "fiscalYears.label", descriptionKey: "fiscalYears.description" },
  { match: JOURNAL_ENTRIES_ROUTE, labelKey: "journalEntries.label", descriptionKey: "journalEntries.description" },
  { match: JOURNAL_ENTRY_DETAIL_ROUTE, labelKey: "journalEntryDetail.label", descriptionKey: "journalEntryDetail.description" },
  { match: PROFIT_AND_LOSS_ROUTE, labelKey: "profitAndLoss.label", descriptionKey: "profitAndLoss.description" },
  { match: BALANCE_SHEET_ROUTE, labelKey: "balanceSheet.label", descriptionKey: "balanceSheet.description" },
  { match: TRIAL_BALANCE_ROUTE, labelKey: "trialBalance.label", descriptionKey: "trialBalance.description" },
  { match: BANK_RECONCILIATION_ROUTE, labelKey: "bankReconciliation.label", descriptionKey: "bankReconciliation.description" },
  { match: COLLECTIONS_ROUTE, labelKey: "collections.label", descriptionKey: "collections.description" },
  { match: BUDGETS_ROUTE, labelKey: "budgets.label", descriptionKey: "budgets.description" },
  { match: BUDGET_VARIANCE_ROUTE, labelKey: "budgetVariance.label", descriptionKey: "budgetVariance.description" },
  { match: MANUFACTURING_ROUTE, labelKey: "manufacturing.label", descriptionKey: "manufacturing.description" },
  { match: BOM_LIST_ROUTE, labelKey: "boms.label", descriptionKey: "boms.description" },
  { match: BOM_CREATE_ROUTE, labelKey: "createBom.label", descriptionKey: "createBom.description" },
  { match: WORK_ORDERS_ROUTE, labelKey: "workOrders.label", descriptionKey: "workOrders.description" },
  { match: WORKSTATIONS_ROUTE, labelKey: "workstations.label", descriptionKey: "workstations.description" },
  { match: WORKSTATION_CREATE_ROUTE, labelKey: "createWorkstation.label", descriptionKey: "createWorkstation.description" },
  { match: ROUTINGS_ROUTE, labelKey: "routings.label", descriptionKey: "routings.description" },
  { match: ROUTING_CREATE_ROUTE, labelKey: "createRouting.label", descriptionKey: "createRouting.description" },
  { match: PRODUCTION_PLANNING_ROUTE, labelKey: "productionPlanning.label", descriptionKey: "productionPlanning.description" },
  { match: PRODUCTION_PLANS_ROUTE, labelKey: "productionPlans.label", descriptionKey: "productionPlans.description" },
  { match: PRODUCTION_PLAN_CREATE_ROUTE, labelKey: "createProductionPlan.label", descriptionKey: "createProductionPlan.description" },
  { match: OEE_DASHBOARD_ROUTE, labelKey: "oee.label", descriptionKey: "oee.description" },
] as const;

// Lookup table for exact route matches - single route detail pages
const EXACT_ROUTE_CONTEXT: Record<string, { labelKey: string; descriptionKey: string; sectionKey: string }> = {
  [INVENTORY_CATEGORIES_ROUTE]: { labelKey: "inventoryCategories.label", descriptionKey: "inventoryCategories.description", sectionKey: "nav.operations" },
  [INVENTORY_UNITS_ROUTE]: { labelKey: "inventoryUnits.label", descriptionKey: "inventoryUnits.description", sectionKey: "nav.operations" },
  [INVENTORY_TRANSFERS_ROUTE]: { labelKey: "inventoryTransfers.label", descriptionKey: "inventoryTransfers.description", sectionKey: "nav.operations" },
  [INVENTORY_BELOW_REORDER_REPORT_ROUTE]: { labelKey: "belowReorderReport.label", descriptionKey: "belowReorderReport.description", sectionKey: "nav.operations" },
  [INVENTORY_VALUATION_ROUTE]: { labelKey: "inventoryValuation.label", descriptionKey: "inventoryValuation.description", sectionKey: "nav.operations" },
  [INVENTORY_REORDER_SUGGESTIONS_ROUTE]: { labelKey: "reorderSuggestions.label", descriptionKey: "reorderSuggestions.description", sectionKey: "nav.operations" },
  [INVENTORY_SUPPLIERS_ROUTE]: { labelKey: "inventorySuppliers.label", descriptionKey: "suppliers.description", sectionKey: "nav.operations" },
  [INVENTORY_COUNT_SESSIONS_ROUTE]: { labelKey: "inventoryCountSessions.label", descriptionKey: "inventoryCountSessions.description", sectionKey: "nav.operations" },
  [PROCUREMENT_PURCHASE_ORDERS_ROUTE]: { labelKey: "procurementPurchaseOrders.label", descriptionKey: "procurementPurchaseOrders.description", sectionKey: "nav.operations" },
  [PROCUREMENT_PURCHASE_ORDER_CREATE_ROUTE]: { labelKey: "procurementPurchaseOrderCreate.label", descriptionKey: "procurementPurchaseOrderCreate.description", sectionKey: "nav.operations" },
  [PROCUREMENT_RFQ_CREATE_ROUTE]: { labelKey: "procurementRFQCreate.label", descriptionKey: "procurementRFQCreate.description", sectionKey: "nav.operations" },
  [MANUFACTURING_ROUTE]: { labelKey: "manufacturing.label", descriptionKey: "manufacturing.description", sectionKey: "nav.manufacturing" },
  [BOM_LIST_ROUTE]: { labelKey: "boms.label", descriptionKey: "boms.description", sectionKey: "nav.manufacturing" },
  [BOM_CREATE_ROUTE]: { labelKey: "createBom.label", descriptionKey: "createBom.description", sectionKey: "nav.manufacturing" },
  [WORK_ORDERS_ROUTE]: { labelKey: "workOrders.label", descriptionKey: "workOrders.description", sectionKey: "nav.manufacturing" },
  [WORKSTATIONS_ROUTE]: { labelKey: "workstations.label", descriptionKey: "workstations.description", sectionKey: "nav.manufacturing" },
  [WORKSTATION_CREATE_ROUTE]: { labelKey: "createWorkstation.label", descriptionKey: "createWorkstation.description", sectionKey: "nav.manufacturing" },
  [ROUTINGS_ROUTE]: { labelKey: "routings.label", descriptionKey: "routings.description", sectionKey: "nav.manufacturing" },
  [ROUTING_CREATE_ROUTE]: { labelKey: "createRouting.label", descriptionKey: "createRouting.description", sectionKey: "nav.manufacturing" },
  [PRODUCTION_PLANNING_ROUTE]: { labelKey: "productionPlanning.label", descriptionKey: "productionPlanning.description", sectionKey: "nav.manufacturing" },
  [PRODUCTION_PLANS_ROUTE]: { labelKey: "productionPlans.label", descriptionKey: "productionPlans.description", sectionKey: "nav.manufacturing" },
  [PRODUCTION_PLAN_CREATE_ROUTE]: { labelKey: "createProductionPlan.label", descriptionKey: "createProductionPlan.description", sectionKey: "nav.manufacturing" },
  [OEE_DASHBOARD_ROUTE]: { labelKey: "oee.label", descriptionKey: "oee.description", sectionKey: "nav.manufacturing" },
} as const;

// Lookup table for prefix route matches (nested routes like /suppliers/:id)
const PREFIX_ROUTE_CONTEXT: ReadonlyArray<{ prefix: string; labelKey: string; descriptionKey: string; sectionKey: string }> = [
  { prefix: `${INVENTORY_COUNT_SESSIONS_ROUTE}/`, labelKey: "inventoryCountSessionDetail.label", descriptionKey: "inventoryCountSessionDetail.description", sectionKey: "nav.operations" },
  { prefix: `${INVENTORY_SUPPLIERS_ROUTE}/`, labelKey: "supplierDetail.label", descriptionKey: "supplierDetail.description", sectionKey: "nav.operations" },
  { prefix: "/procurement/rfq/", labelKey: "procurementRFQDetail.label", descriptionKey: "procurementRFQDetail.description", sectionKey: "nav.operations" },
  { prefix: `${PROCUREMENT_PURCHASE_ORDERS_ROUTE}/`, labelKey: "procurementPurchaseOrderDetail.label", descriptionKey: "procurementPurchaseOrderDetail.description", sectionKey: "nav.operations" },
  { prefix: "/procurement/goods-receipts/", labelKey: "procurementGoodsReceiptDetail.label", descriptionKey: "procurementGoodsReceiptDetail.description", sectionKey: "nav.operations" },
  { prefix: "/manufacturing/boms/", labelKey: "bomDetail.label", descriptionKey: "bomDetail.description", sectionKey: "nav.manufacturing" },
  { prefix: "/manufacturing/work-orders/", labelKey: "workOrderDetail.label", descriptionKey: "workOrderDetail.description", sectionKey: "nav.manufacturing" },
  { prefix: "/manufacturing/workstations/", labelKey: "workstationDetail.label", descriptionKey: "workstationDetail.description", sectionKey: "nav.manufacturing" },
  { prefix: "/manufacturing/routings/", labelKey: "routingDetail.label", descriptionKey: "routingDetail.description", sectionKey: "nav.manufacturing" },
  { prefix: "/manufacturing/production-plans/", labelKey: "productionPlanDetail.label", descriptionKey: "productionPlanDetail.description", sectionKey: "nav.manufacturing" },
];

// Conditional detail routes requiring additional path logic
function getConditionalRouteContext(pathname: string) {
  // Order detail: /orders/* but not /orders/new
  if (pathname.startsWith(`${ORDERS_ROUTE}/`) && pathname !== ORDER_CREATE_ROUTE) {
    return { labelKey: "orderDetail.label", descriptionKey: "orderDetail.description", sectionKey: "routes.orderDetail.section" };
  }
  // Lead detail: /crm/leads/* but not /crm/leads/new
  if (pathname.startsWith(`${CRM_LEADS_ROUTE}/`) && pathname !== CRM_LEAD_CREATE_ROUTE) {
    return { labelKey: "leadDetail.label", descriptionKey: "leadDetail.description", sectionKey: "nav.revenue" };
  }
  // Opportunity detail: /crm/opportunities/* but not /crm/opportunities/new
  if (pathname.startsWith(`${CRM_OPPORTUNITIES_ROUTE}/`) && pathname !== CRM_OPPORTUNITY_CREATE_ROUTE) {
    return { labelKey: "opportunityDetail.label", descriptionKey: "opportunityDetail.description", sectionKey: "nav.revenue" };
  }
  // Quotation detail: /crm/quotations/* but not /crm/quotations/new
  if (pathname.startsWith(`${CRM_QUOTATIONS_ROUTE}/`) && pathname !== CRM_QUOTATION_CREATE_ROUTE) {
    return { labelKey: "quotationDetail.label", descriptionKey: "quotationDetail.description", sectionKey: "nav.revenue" };
  }
  // Product detail: /inventory/* excluding sub-routes
  if (
    pathname.startsWith(`${INVENTORY_ROUTE}/`) &&
    pathname !== INVENTORY_ROUTE &&
    !pathname.startsWith(INVENTORY_CATEGORIES_ROUTE) &&
    !pathname.startsWith(INVENTORY_TRANSFERS_ROUTE) &&
    !pathname.startsWith(INVENTORY_COUNT_SESSIONS_ROUTE) &&
    !pathname.startsWith(INVENTORY_SUPPLIERS_ROUTE)
  ) {
    return { labelKey: "productDetail.label", descriptionKey: "productDetail.description", sectionKey: "nav.operations" };
  }
  return null;
}

export function getRouteContext(pathname: string) {
  // 1. Check exact route matches (O(1) lookup)
  const exactMatch = EXACT_ROUTE_CONTEXT[pathname];
  if (exactMatch) {
    return exactMatch;
  }

  // 2. Check prefix route matches (nested routes)
  for (const { prefix, labelKey, descriptionKey, sectionKey } of PREFIX_ROUTE_CONTEXT) {
    if (pathname.startsWith(prefix)) {
      return { labelKey, descriptionKey, sectionKey };
    }
  }

  // 3. Check conditional routes (requires additional logic)
  const conditional = getConditionalRouteContext(pathname);
  if (conditional) {
    return conditional;
  }

  // 4. Fall back to ROUTE_CONTEXT_KEYS lookup
  const route = ROUTE_CONTEXT_KEYS.find((entry) => entry.match === pathname);
  if (route) {
    const group = NAVIGATION_GROUPS.find((candidate) =>
      candidate.sections.flatMap((s) => s.items).some((item) => item.to === pathname),
    );
    return {
      labelKey: route.labelKey,
      descriptionKey: route.descriptionKey,
      sectionKey: group ? `${group.label}` : "workspace.label",
    };
  }

  // 5. Default fallback
  return {
    labelKey: "workspace.label",
    descriptionKey: "workspace.description",
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
