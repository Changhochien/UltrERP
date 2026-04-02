/** Orders domain types for API payloads and responses. */

export type OrderStatus = "pending" | "confirmed" | "shipped" | "fulfilled" | "cancelled";

export type PaymentTermsCode = "NET_30" | "NET_60" | "COD";

export interface OrderLineCreate {
  product_id: string;
  description: string;
  quantity: number;
  unit_price: number;
  tax_policy_code: string;
}

export interface OrderCreatePayload {
  customer_id: string;
  payment_terms_code?: PaymentTermsCode;
  notes?: string;
  lines: OrderLineCreate[];
}

export interface OrderLineResponse {
  id: string;
  product_id: string;
  line_number: number;
  description: string;
  quantity: string;
  unit_price: string;
  tax_policy_code: string;
  tax_type: number;
  tax_rate: string;
  tax_amount: string;
  subtotal_amount: string;
  total_amount: string;
  available_stock_snapshot: number | null;
  backorder_note: string | null;
}

export interface OrderResponse {
  id: string;
  order_number: string;
  status: OrderStatus;
  customer_id: string;
  payment_terms_code: string;
  payment_terms_days: number;
  subtotal_amount: string;
  tax_amount: string;
  total_amount: string;
  invoice_id: string | null;
  notes: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  confirmed_at: string | null;
  lines: OrderLineResponse[];
}

export interface OrderListItem {
  id: string;
  order_number: string;
  status: OrderStatus;
  customer_id: string;
  total_amount: string;
  created_at: string;
}

export interface OrderListResponse {
  items: OrderListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface PaymentTermsItem {
  code: string;
  label: string;
  days: number;
}

export interface PaymentTermsListResponse {
  items: PaymentTermsItem[];
  total: number;
}

export interface WarehouseStockInfo {
  warehouse_id: string;
  warehouse_name: string;
  available: number;
}

export interface StockCheckResponse {
  product_id: string;
  warehouses: WarehouseStockInfo[];
  total_available: number;
}
