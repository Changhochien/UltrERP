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
            description: "routes.dashboard.description",
            icon: LayoutDashboard,
          },
          {
            feature: "settings",
            label: "nav.settings",
            to: SETTINGS_ROUTE,
            description: "routes.settings.description",
            icon: Settings,
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
            description: "routes.createLead.description",
            icon: Users,
          },
          {
            feature: "crm",
            label: "nav.createOpportunity",
            to: CRM_OPPORTUNITY_CREATE_ROUTE,
            description: "routes.createOpportunity.description",
            icon: BriefcaseBusiness,
          },
          {
            feature: "invoices",
            label: "nav.createInvoice",
            to: INVOICE_CREATE_ROUTE,
            description: "routes.createInvoice.description",
            icon: ReceiptText,
          },
          {
            feature: "orders",
            label: "nav.newOrder",
            to: ORDER_CREATE_ROUTE,
            description: "routes.createOrder.description",
            icon: ShoppingCart,
          },
          {
            feature: "procurement",
            label: "nav.createRFQ",
            to: PROCUREMENT_RFQ_CREATE_ROUTE,
            description: "routes.createRFQ.description",
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
            feature: "orders",
            label: "nav.orders",
            to: ORDERS_ROUTE,
            description: "routes.orders.description",
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
            description: "routes.inventory.description",
            icon: Boxes,
          },
          {
            feature: "inventory",
            label: "nav.suppliers",
            to: INVENTORY_SUPPLIERS_ROUTE,
            description: "routes.suppliers.description",
            icon: Users,
          },
          {
            feature: "purchases",
            label: "nav.purchases",
            to: PURCHASES_ROUTE,
            description: "routes.purchases.description",
            icon: CircleDollarSign,
          },
          {
            feature: "procurement",
            label: "nav.procurement",
            to: PROCUREMENT_ROUTE,
            description: "routes.procurement.description",
            icon: FileText,
          },
          {
            feature: "procurement",
            label: "nav.purchaseOrders",
            to: PROCUREMENT_PURCHASE_ORDERS_ROUTE,
            description: "routes.procurementPurchaseOrders.description",
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
          {
            feature: "inventory",
            label: "nav.reorderSuggestions",
            to: INVENTORY_REORDER_SUGGESTIONS_ROUTE,
            description: "routes.reorderSuggestions.description",
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
            description: "routes.inventoryCategories.description",
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
            feature: "payments",
            label: "nav.payments",
            to: PAYMENTS_ROUTE,
            description: "routes.payments.description",
            icon: WalletCards,
          },
          {
            feature: "accounting",
            label: "nav.accounting",
            to: ACCOUNTING_ROUTE,
            description: "routes.accounting.description",
            icon: Calculator,
          },
          {
            feature: "accounting",
            label: "nav.chartOfAccounts",
            to: CHART_OF_ACCOUNTS_ROUTE,
            description: "routes.chartOfAccounts.description",
            icon: FileSpreadsheet,
          },
          {
            feature: "accounting",
            label: "nav.fiscalYears",
            to: FISCAL_YEARS_ROUTE,
            description: "routes.fiscalYears.description",
            icon: Calendar,
          },
          {
            feature: "accounting",
            label: "nav.journalEntries",
            to: JOURNAL_ENTRIES_ROUTE,
            description: "routes.journalEntries.description",
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
            description: "routes.profitAndLoss.description",
            icon: TrendingUp,
          },
          {
            feature: "accounting",
            label: "nav.balanceSheet",
            to: BALANCE_SHEET_ROUTE,
            description: "routes.balanceSheet.description",
            icon: Landmark,
          },
          {
            feature: "accounting",
            label: "nav.trialBalance",
            to: TRIAL_BALANCE_ROUTE,
            description: "routes.trialBalance.description",
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
            description: "routes.bankReconciliation.description",
            icon: WalletCards,
          },
          {
            feature: "accounting",
            label: "nav.collections",
            to: COLLECTIONS_ROUTE,
            description: "routes.collections.description",
            icon: HandCoins,
          },
          {
            feature: "accounting",
            label: "nav.budgets",
            to: BUDGETS_ROUTE,
            description: "routes.budgets.description",
            icon: PiggyBank,
          },
          {
            feature: "accounting",
            label: "nav.budgetVariance",
            to: BUDGET_VARIANCE_ROUTE,
            description: "routes.budgetVariance.description",
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
            description: "routes.intelligence.description",
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
            description: "routes.boms.description",
            icon: Package,
          },
          {
            feature: "manufacturing",
            label: "nav.workOrders",
            to: WORK_ORDERS_ROUTE,
            description: "routes.workOrders.description",
            icon: FileText,
          },
          {
            feature: "manufacturing",
            label: "nav.productionPlanning",
            to: PRODUCTION_PLANNING_ROUTE,
            description: "routes.productionPlanning.description",
            icon: Calendar,
          },
          {
            feature: "manufacturing",
            label: "nav.productionPlans",
            to: PRODUCTION_PLANS_ROUTE,
            description: "routes.productionPlans.description",
            icon: FileSpreadsheet,
          },
          {
            feature: "manufacturing",
            label: "nav.workstations",
            to: WORKSTATIONS_ROUTE,
            description: "routes.workstations.description",
            icon: Settings,
          },
          {
            feature: "manufacturing",
            label: "nav.routings",
            to: ROUTINGS_ROUTE,
            description: "routes.routings.description",
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
            description: "routes.oee.description",
            icon: FileBarChart,
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
  { match: PROCUREMENT_ROUTE, labelKey: "routes.procurement.label", descriptionKey: "routes.procurement.description" },
  { match: PROCUREMENT_PURCHASE_ORDERS_ROUTE, labelKey: "routes.procurementPurchaseOrders.label", descriptionKey: "routes.procurementPurchaseOrders.description" },
  { match: PROCUREMENT_PURCHASE_ORDER_CREATE_ROUTE, labelKey: "routes.procurementPurchaseOrderCreate.label", descriptionKey: "routes.procurementPurchaseOrderCreate.description" },
  { match: PROCUREMENT_RFQ_CREATE_ROUTE, labelKey: "routes.procurementRFQCreate.label", descriptionKey: "routes.procurementRFQCreate.description" },
  { match: PROCUREMENT_RFQ_DETAIL_ROUTE, labelKey: "routes.procurementRFQDetail.label", descriptionKey: "routes.procurementRFQDetail.description" },
  { match: ADMIN_ROUTE, labelKey: "routes.admin.label", descriptionKey: "routes.admin.description" },
  { match: OWNER_DASHBOARD_ROUTE, labelKey: "routes.ownerDashboard.label", descriptionKey: "routes.ownerDashboard.description" },
  { match: SETTINGS_ROUTE, labelKey: "routes.settings.label", descriptionKey: "routes.settings.description" },
  { match: LOGIN_ROUTE, labelKey: "routes.login.label", descriptionKey: "routes.login.description" },
  // Accounting routes (Epic 26)
  { match: ACCOUNTING_ROUTE, labelKey: "routes.accounting.label", descriptionKey: "routes.accounting.description" },
  { match: CHART_OF_ACCOUNTS_ROUTE, labelKey: "routes.chartOfAccounts.label", descriptionKey: "routes.chartOfAccounts.description" },
  { match: FISCAL_YEARS_ROUTE, labelKey: "routes.fiscalYears.label", descriptionKey: "routes.fiscalYears.description" },
  { match: JOURNAL_ENTRIES_ROUTE, labelKey: "routes.journalEntries.label", descriptionKey: "routes.journalEntries.description" },
  { match: JOURNAL_ENTRY_DETAIL_ROUTE, labelKey: "routes.journalEntryDetail.label", descriptionKey: "routes.journalEntryDetail.description" },
  { match: PROFIT_AND_LOSS_ROUTE, labelKey: "routes.profitAndLoss.label", descriptionKey: "routes.profitAndLoss.description" },
  { match: BALANCE_SHEET_ROUTE, labelKey: "routes.balanceSheet.label", descriptionKey: "routes.balanceSheet.description" },
  { match: TRIAL_BALANCE_ROUTE, labelKey: "routes.trialBalance.label", descriptionKey: "routes.trialBalance.description" },
  { match: BANK_RECONCILIATION_ROUTE, labelKey: "routes.bankReconciliation.label", descriptionKey: "routes.bankReconciliation.description" },
  { match: COLLECTIONS_ROUTE, labelKey: "routes.collections.label", descriptionKey: "routes.collections.description" },
  { match: BUDGETS_ROUTE, labelKey: "routes.budgets.label", descriptionKey: "routes.budgets.description" },
  { match: BUDGET_VARIANCE_ROUTE, labelKey: "routes.budgetVariance.label", descriptionKey: "routes.budgetVariance.description" },
  { match: MANUFACTURING_ROUTE, labelKey: "routes.manufacturing.label", descriptionKey: "routes.manufacturing.description" },
  { match: BOM_LIST_ROUTE, labelKey: "routes.boms.label", descriptionKey: "routes.boms.description" },
  { match: BOM_CREATE_ROUTE, labelKey: "routes.createBom.label", descriptionKey: "routes.createBom.description" },
  { match: WORK_ORDERS_ROUTE, labelKey: "routes.workOrders.label", descriptionKey: "routes.workOrders.description" },
  { match: WORKSTATIONS_ROUTE, labelKey: "routes.workstations.label", descriptionKey: "routes.workstations.description" },
  { match: WORKSTATION_CREATE_ROUTE, labelKey: "routes.createWorkstation.label", descriptionKey: "routes.createWorkstation.description" },
  { match: ROUTINGS_ROUTE, labelKey: "routes.routings.label", descriptionKey: "routes.routings.description" },
  { match: ROUTING_CREATE_ROUTE, labelKey: "routes.createRouting.label", descriptionKey: "routes.createRouting.description" },
  { match: PRODUCTION_PLANNING_ROUTE, labelKey: "routes.productionPlanning.label", descriptionKey: "routes.productionPlanning.description" },
  { match: PRODUCTION_PLANS_ROUTE, labelKey: "routes.productionPlans.label", descriptionKey: "routes.productionPlans.description" },
  { match: PRODUCTION_PLAN_CREATE_ROUTE, labelKey: "routes.createProductionPlan.label", descriptionKey: "routes.createProductionPlan.description" },
  { match: OEE_DASHBOARD_ROUTE, labelKey: "routes.oee.label", descriptionKey: "routes.oee.description" },
] as const;

// Lookup table for exact route matches - single route detail pages
const EXACT_ROUTE_CONTEXT: Record<string, { labelKey: string; descriptionKey: string; sectionKey: string }> = {
  [INVENTORY_CATEGORIES_ROUTE]: { labelKey: "routes.inventoryCategories.label", descriptionKey: "routes.inventoryCategories.description", sectionKey: "nav.operations" },
  [INVENTORY_UNITS_ROUTE]: { labelKey: "routes.inventoryUnits.label", descriptionKey: "routes.inventoryUnits.description", sectionKey: "nav.operations" },
  [INVENTORY_TRANSFERS_ROUTE]: { labelKey: "routes.inventoryTransfers.label", descriptionKey: "routes.inventoryTransfers.description", sectionKey: "nav.operations" },
  [INVENTORY_BELOW_REORDER_REPORT_ROUTE]: { labelKey: "routes.belowReorderReport.label", descriptionKey: "routes.belowReorderReport.description", sectionKey: "nav.operations" },
  [INVENTORY_VALUATION_ROUTE]: { labelKey: "routes.inventoryValuation.label", descriptionKey: "routes.inventoryValuation.description", sectionKey: "nav.operations" },
  [INVENTORY_REORDER_SUGGESTIONS_ROUTE]: { labelKey: "routes.reorderSuggestions.label", descriptionKey: "routes.reorderSuggestions.description", sectionKey: "nav.operations" },
  [INVENTORY_SUPPLIERS_ROUTE]: { labelKey: "routes.inventorySuppliers.label", descriptionKey: "routes.suppliers.description", sectionKey: "nav.operations" },
  [INVENTORY_COUNT_SESSIONS_ROUTE]: { labelKey: "routes.inventoryCountSessions.label", descriptionKey: "routes.inventoryCountSessions.description", sectionKey: "nav.operations" },
  [PROCUREMENT_PURCHASE_ORDERS_ROUTE]: { labelKey: "routes.procurementPurchaseOrders.label", descriptionKey: "routes.procurementPurchaseOrders.description", sectionKey: "nav.operations" },
  [PROCUREMENT_PURCHASE_ORDER_CREATE_ROUTE]: { labelKey: "routes.procurementPurchaseOrderCreate.label", descriptionKey: "routes.procurementPurchaseOrderCreate.description", sectionKey: "nav.operations" },
  [PROCUREMENT_RFQ_CREATE_ROUTE]: { labelKey: "routes.procurementRFQCreate.label", descriptionKey: "routes.procurementRFQCreate.description", sectionKey: "nav.operations" },
  [MANUFACTURING_ROUTE]: { labelKey: "routes.manufacturing.label", descriptionKey: "routes.manufacturing.description", sectionKey: "nav.manufacturing" },
  [BOM_LIST_ROUTE]: { labelKey: "routes.boms.label", descriptionKey: "routes.boms.description", sectionKey: "nav.manufacturing" },
  [BOM_CREATE_ROUTE]: { labelKey: "routes.createBom.label", descriptionKey: "routes.createBom.description", sectionKey: "nav.manufacturing" },
  [WORK_ORDERS_ROUTE]: { labelKey: "routes.workOrders.label", descriptionKey: "routes.workOrders.description", sectionKey: "nav.manufacturing" },
  [WORKSTATIONS_ROUTE]: { labelKey: "routes.workstations.label", descriptionKey: "routes.workstations.description", sectionKey: "nav.manufacturing" },
  [WORKSTATION_CREATE_ROUTE]: { labelKey: "routes.createWorkstation.label", descriptionKey: "routes.createWorkstation.description", sectionKey: "nav.manufacturing" },
  [ROUTINGS_ROUTE]: { labelKey: "routes.routings.label", descriptionKey: "routes.routings.description", sectionKey: "nav.manufacturing" },
  [ROUTING_CREATE_ROUTE]: { labelKey: "routes.createRouting.label", descriptionKey: "routes.createRouting.description", sectionKey: "nav.manufacturing" },
  [PRODUCTION_PLANNING_ROUTE]: { labelKey: "routes.productionPlanning.label", descriptionKey: "routes.productionPlanning.description", sectionKey: "nav.manufacturing" },
  [PRODUCTION_PLANS_ROUTE]: { labelKey: "routes.productionPlans.label", descriptionKey: "routes.productionPlans.description", sectionKey: "nav.manufacturing" },
  [PRODUCTION_PLAN_CREATE_ROUTE]: { labelKey: "routes.createProductionPlan.label", descriptionKey: "routes.createProductionPlan.description", sectionKey: "nav.manufacturing" },
  [OEE_DASHBOARD_ROUTE]: { labelKey: "routes.oee.label", descriptionKey: "routes.oee.description", sectionKey: "nav.manufacturing" },
} as const;

// Lookup table for prefix route matches (nested routes like /suppliers/:id)
const PREFIX_ROUTE_CONTEXT: ReadonlyArray<{ prefix: string; labelKey: string; descriptionKey: string; sectionKey: string }> = [
  { prefix: `${INVENTORY_COUNT_SESSIONS_ROUTE}/`, labelKey: "routes.inventoryCountSessionDetail.label", descriptionKey: "routes.inventoryCountSessionDetail.description", sectionKey: "nav.operations" },
  { prefix: `${INVENTORY_SUPPLIERS_ROUTE}/`, labelKey: "routes.supplierDetail.label", descriptionKey: "routes.supplierDetail.description", sectionKey: "nav.operations" },
  { prefix: "/procurement/rfq/", labelKey: "routes.procurementRFQDetail.label", descriptionKey: "routes.procurementRFQDetail.description", sectionKey: "nav.operations" },
  { prefix: `${PROCUREMENT_PURCHASE_ORDERS_ROUTE}/`, labelKey: "routes.procurementPurchaseOrderDetail.label", descriptionKey: "routes.procurementPurchaseOrderDetail.description", sectionKey: "nav.operations" },
  { prefix: "/procurement/goods-receipts/", labelKey: "routes.procurementGoodsReceiptDetail.label", descriptionKey: "routes.procurementGoodsReceiptDetail.description", sectionKey: "nav.operations" },
  { prefix: "/manufacturing/boms/", labelKey: "routes.bomDetail.label", descriptionKey: "routes.bomDetail.description", sectionKey: "nav.manufacturing" },
  { prefix: "/manufacturing/work-orders/", labelKey: "routes.workOrderDetail.label", descriptionKey: "routes.workOrderDetail.description", sectionKey: "nav.manufacturing" },
  { prefix: "/manufacturing/workstations/", labelKey: "routes.workstationDetail.label", descriptionKey: "routes.workstationDetail.description", sectionKey: "nav.manufacturing" },
  { prefix: "/manufacturing/routings/", labelKey: "routes.routingDetail.label", descriptionKey: "routes.routingDetail.description", sectionKey: "nav.manufacturing" },
  { prefix: "/manufacturing/production-plans/", labelKey: "routes.productionPlanDetail.label", descriptionKey: "routes.productionPlanDetail.description", sectionKey: "nav.manufacturing" },
];

// Conditional detail routes requiring additional path logic
function getConditionalRouteContext(pathname: string) {
  // Order detail: /orders/* but not /orders/new
  if (pathname.startsWith(`${ORDERS_ROUTE}/`) && pathname !== ORDER_CREATE_ROUTE) {
    return { labelKey: "routes.orderDetail.label", descriptionKey: "routes.orderDetail.description", sectionKey: "routes.orderDetail.section" };
  }
  // Lead detail: /crm/leads/* but not /crm/leads/new
  if (pathname.startsWith(`${CRM_LEADS_ROUTE}/`) && pathname !== CRM_LEAD_CREATE_ROUTE) {
    return { labelKey: "routes.leadDetail.label", descriptionKey: "routes.leadDetail.description", sectionKey: "nav.revenue" };
  }
  // Opportunity detail: /crm/opportunities/* but not /crm/opportunities/new
  if (pathname.startsWith(`${CRM_OPPORTUNITIES_ROUTE}/`) && pathname !== CRM_OPPORTUNITY_CREATE_ROUTE) {
    return { labelKey: "routes.opportunityDetail.label", descriptionKey: "routes.opportunityDetail.description", sectionKey: "nav.revenue" };
  }
  // Quotation detail: /crm/quotations/* but not /crm/quotations/new
  if (pathname.startsWith(`${CRM_QUOTATIONS_ROUTE}/`) && pathname !== CRM_QUOTATION_CREATE_ROUTE) {
    return { labelKey: "routes.quotationDetail.label", descriptionKey: "routes.quotationDetail.description", sectionKey: "nav.revenue" };
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
    return { labelKey: "routes.productDetail.label", descriptionKey: "routes.productDetail.description", sectionKey: "nav.operations" };
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
      sectionKey: group ? `${group.label}` : "routes.workspace.label",
    };
  }

  // 5. Default fallback
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
