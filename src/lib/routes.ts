export const HOME_ROUTE = "/";
export const LOGIN_ROUTE = "/login";
export const OWNER_DASHBOARD_ROUTE = "/owner-dashboard";
export const INVENTORY_ROUTE = "/inventory";
export const INVENTORY_CATEGORIES_ROUTE = "/inventory/categories";
export const INVENTORY_UNITS_ROUTE = "/inventory/units";
export const INVENTORY_TRANSFERS_ROUTE = "/inventory/transfers";
export const INVENTORY_COUNT_SESSIONS_ROUTE = "/inventory/count-sessions";
export const COUNT_SESSION_DETAIL_ROUTE = "/inventory/count-sessions/:sessionId";
export const INVENTORY_BELOW_REORDER_REPORT_ROUTE = "/inventory/reports/below-reorder";
export const INVENTORY_VALUATION_ROUTE = "/inventory/reports/valuation";
export const INVENTORY_REORDER_SUGGESTIONS_ROUTE = "/inventory/reorder-suggestions";
export const INVENTORY_SUPPLIERS_ROUTE = "/inventory/suppliers";
export const SUPPLIER_DETAIL_ROUTE = "/inventory/suppliers/:supplierId";
export const PRODUCT_DETAIL_ROUTE = "/inventory/:productId";
export const PURCHASES_ROUTE = "/purchases";
export const CRM_LEADS_ROUTE = "/crm/leads";
export const CRM_LEAD_DETAIL_ROUTE = "/crm/leads/:leadId";
export const CRM_LEAD_CREATE_ROUTE = "/crm/leads/new";
export const CRM_OPPORTUNITIES_ROUTE = "/crm/opportunities";
export const CRM_OPPORTUNITY_DETAIL_ROUTE = "/crm/opportunities/:opportunityId";
export const CRM_OPPORTUNITY_CREATE_ROUTE = "/crm/opportunities/new";
export const CUSTOMERS_ROUTE = "/customers";
export const CUSTOMER_DETAIL_ROUTE = "/customers/:customerId";
export const CUSTOMER_CREATE_ROUTE = "/customers/new";
export const INTELLIGENCE_ROUTE = "/intelligence";
export const INVOICES_ROUTE = "/invoices";
export const INVOICE_CREATE_ROUTE = "/invoices/new";
export const INVOICE_DETAIL_ROUTE = "/invoices/:invoiceId";
export const ORDERS_ROUTE = "/orders";
export const ORDER_CREATE_ROUTE = "/orders/new";
export const ORDER_DETAIL_ROUTE = "/orders/:orderId";
export const PAYMENTS_ROUTE = "/payments";
export const ADMIN_ROUTE = "/admin";
export const SETTINGS_ROUTE = "/settings";

export type AppRoute =
  | typeof HOME_ROUTE
  | typeof LOGIN_ROUTE
  | typeof INVENTORY_ROUTE
  | typeof INVENTORY_CATEGORIES_ROUTE
  | typeof INVENTORY_UNITS_ROUTE
  | typeof INVENTORY_TRANSFERS_ROUTE
  | typeof INVENTORY_COUNT_SESSIONS_ROUTE
  | typeof COUNT_SESSION_DETAIL_ROUTE
  | typeof INVENTORY_BELOW_REORDER_REPORT_ROUTE
  | typeof INVENTORY_VALUATION_ROUTE
  | typeof INVENTORY_REORDER_SUGGESTIONS_ROUTE
  | typeof INVENTORY_SUPPLIERS_ROUTE
  | typeof SUPPLIER_DETAIL_ROUTE
  | typeof PRODUCT_DETAIL_ROUTE
  | typeof PURCHASES_ROUTE
  | typeof CRM_LEADS_ROUTE
  | typeof CRM_LEAD_DETAIL_ROUTE
  | typeof CRM_LEAD_CREATE_ROUTE
  | typeof CRM_OPPORTUNITIES_ROUTE
  | typeof CRM_OPPORTUNITY_DETAIL_ROUTE
  | typeof CRM_OPPORTUNITY_CREATE_ROUTE
  | typeof CUSTOMERS_ROUTE
  | typeof CUSTOMER_DETAIL_ROUTE
  | typeof CUSTOMER_CREATE_ROUTE
  | typeof INTELLIGENCE_ROUTE
  | typeof INVOICES_ROUTE
  | typeof INVOICE_CREATE_ROUTE
  | typeof INVOICE_DETAIL_ROUTE
  | typeof ORDERS_ROUTE
  | typeof ORDER_CREATE_ROUTE
  | typeof ORDER_DETAIL_ROUTE
  | typeof PAYMENTS_ROUTE
  | typeof ADMIN_ROUTE
  | typeof SETTINGS_ROUTE
  | typeof OWNER_DASHBOARD_ROUTE;

export function buildSupplierDetailPath(supplierId: string): string {
  return SUPPLIER_DETAIL_ROUTE.replace(":supplierId", encodeURIComponent(supplierId));
}

export function buildLeadDetailPath(leadId: string): string {
  return CRM_LEAD_DETAIL_ROUTE.replace(":leadId", encodeURIComponent(leadId));
}

export function buildOpportunityDetailPath(opportunityId: string): string {
  return CRM_OPPORTUNITY_DETAIL_ROUTE.replace(":opportunityId", encodeURIComponent(opportunityId));
}

export function buildCustomerDetailPath(customerId: string): string {
  return CUSTOMER_DETAIL_ROUTE.replace(":customerId", encodeURIComponent(customerId));
}

export function buildCountSessionDetailPath(sessionId: string): string {
  return COUNT_SESSION_DETAIL_ROUTE.replace(":sessionId", encodeURIComponent(sessionId));
}

export function buildProductDetailPath(productId: string, tab?: string): string {
  const basePath = PRODUCT_DETAIL_ROUTE.replace(":productId", encodeURIComponent(productId));
  if (!tab) {
    return basePath;
  }
  return `${basePath}?tab=${encodeURIComponent(tab)}`;
}

export function buildInventoryTransfersPath(productId?: string, warehouseId?: string): string {
  const params = new URLSearchParams();
  if (productId) {
    params.set("productId", productId);
  }
  if (warehouseId) {
    params.set("warehouseId", warehouseId);
  }
  const query = params.toString();
  return `${INVENTORY_TRANSFERS_ROUTE}${query ? `?${query}` : ""}`;
}
