export const HOME_ROUTE = "/";
export const LOGIN_ROUTE = "/login";
export const OWNER_DASHBOARD_ROUTE = "/owner-dashboard";
export const INVENTORY_ROUTE = "/inventory";
export const PRODUCT_DETAIL_ROUTE = "/inventory/:productId";
export const PURCHASES_ROUTE = "/purchases";
export const CUSTOMERS_ROUTE = "/customers";
export const CUSTOMER_DETAIL_ROUTE = "/customers/:customerId";
export const CUSTOMER_CREATE_ROUTE = "/customers/new";
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
  | typeof PRODUCT_DETAIL_ROUTE
  | typeof PURCHASES_ROUTE
  | typeof CUSTOMERS_ROUTE
  | typeof CUSTOMER_DETAIL_ROUTE
  | typeof CUSTOMER_CREATE_ROUTE
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