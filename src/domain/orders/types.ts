/** Orders domain types for API payloads and responses. */

export type OrderStatus = "pending" | "confirmed" | "shipped" | "fulfilled" | "cancelled";

export type OrderCommercialStatus = "pre_commit" | "committed" | "cancelled";

export type OrderBillingStatus =
  | "not_invoiced"
  | "unpaid"
  | "partial"
  | "paid"
  | "overdue"
  | "voided";

export type OrderFulfillmentStatus =
  | "not_started"
  | "ready_to_ship"
  | "shipped"
  | "fulfilled"
  | "cancelled";

export type OrderReservationStatus =
  | "not_reserved"
  | "reserved"
  | "released";

export type OrderWorkflowView =
  | "pending_intake"
  | "ready_to_ship"
  | "shipped_not_completed"
  | "invoiced_not_paid";

export type PaymentTermsCode = "NET_30" | "NET_60" | "COD";

export interface OrderLineCreate {
  product_id: string;
  source_quotation_line_no?: number;
  description: string;
  quantity: number;
  list_unit_price?: number;
  unit_price: number;
  discount_amount?: number;
  tax_policy_code: string;
}

export interface OrderSalesTeamAssignmentCreate {
  sales_person: string;
  allocated_percentage: number;
  commission_rate: number;
}

export interface OrderSalesTeamAssignment {
  sales_person: string;
  allocated_percentage: string;
  commission_rate: string;
  allocated_amount: string;
}

export interface OrderCreatePayload {
  customer_id: string;
  source_quotation_id?: string;
  payment_terms_code?: PaymentTermsCode;
  discount_amount?: number;
  discount_percent?: number;
  crm_context_snapshot?: Record<string, unknown> | null;
  notes?: string;
  sales_team?: OrderSalesTeamAssignmentCreate[];
  lines: OrderLineCreate[];
}

export interface OrderLineResponse {
  id: string;
  product_id: string;
  source_quotation_line_no?: number | null;
  line_number: number;
  description: string;
  quantity: string;
  list_unit_price: string;
  unit_price: string;
  discount_amount: string;
  tax_policy_code: string;
  tax_type: number;
  tax_rate: string;
  tax_amount: string;
  subtotal_amount: string;
  total_amount: string;
  available_stock_snapshot: number | null;
  backorder_note: string | null;
}

export interface OrderExecutionSummary {
  commercial_status: OrderCommercialStatus;
  fulfillment_status: OrderFulfillmentStatus;
  billing_status: OrderBillingStatus;
  reservation_status: OrderReservationStatus;
  ready_to_ship: boolean;
  has_backorder: boolean;
  backorder_line_count: number;
}

export interface OrderResponse {
  id: string;
  order_number: string;
  status: OrderStatus;
  customer_id: string;
  customer_name: string | null;
  source_quotation_id?: string | null;
  payment_terms_code: string;
  payment_terms_days: number;
  subtotal_amount: string;
  discount_amount: string | null;
  discount_percent: string | null;
  tax_amount: string;
  total_amount: string;
  sales_team: OrderSalesTeamAssignment[];
  total_commission: string;
  invoice_id: string | null;
  invoice_number: string | null;
  invoice_payment_status: OrderBillingStatus | null;
  execution: OrderExecutionSummary;
  notes: string | null;
  crm_context_snapshot?: Record<string, unknown> | null;
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
  source_quotation_id?: string | null;
  total_amount: string;
  sales_team: OrderSalesTeamAssignment[];
  total_commission: string;
  invoice_number: string | null;
  invoice_payment_status: OrderBillingStatus | null;
  execution: OrderExecutionSummary;
  crm_context_snapshot?: Record<string, unknown> | null;
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
