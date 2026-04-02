export const HOME_ROUTE = "/";
export const CUSTOMERS_ROUTE = "/customers";
export const CUSTOMER_CREATE_ROUTE = "/customers/new";
export const ORDERS_ROUTE = "/orders";
export const ORDER_CREATE_ROUTE = "/orders/new";
export const ORDER_DETAIL_ROUTE = "/orders/:orderId";

export type AppRoute =
  | typeof HOME_ROUTE
  | typeof CUSTOMERS_ROUTE
  | typeof CUSTOMER_CREATE_ROUTE
  | typeof ORDERS_ROUTE
  | typeof ORDER_CREATE_ROUTE
  | typeof ORDER_DETAIL_ROUTE;