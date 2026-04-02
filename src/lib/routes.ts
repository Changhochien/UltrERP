export const HOME_ROUTE = "/";
export const CUSTOMERS_ROUTE = "/customers";
export const CUSTOMER_CREATE_ROUTE = "/customers/new";

export type AppRoute =
  | typeof HOME_ROUTE
  | typeof CUSTOMERS_ROUTE
  | typeof CUSTOMER_CREATE_ROUTE;