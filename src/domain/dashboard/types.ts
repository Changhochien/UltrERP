/** Dashboard domain types. */

export interface RevenueSummary {
  today_revenue: string;
  yesterday_revenue: string;
  change_percent: string | null;
  today_date: string;
  yesterday_date: string;
}

export interface TopProductItem {
  product_id: string;
  product_name: string;
  quantity_sold: string;
  revenue: string;
}

export interface TopProductsResponse {
  period: string;
  start_date: string;
  end_date: string;
  items: TopProductItem[];
}

export interface LowStockAlert {
  id: string;
  product_id: string;
  product_name: string;
  warehouse_id: string;
  warehouse_name: string;
  current_stock: number;
  reorder_point: number;
  status: string;
  created_at: string;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
}

export interface LowStockAlertListResponse {
  items: LowStockAlert[];
  total: number;
}

export interface VisitorStatsResponse {
  visitor_count: number;
  inquiry_count: number;
  conversion_rate: string | null;
  date: string;
  is_configured: boolean;
  error: string | null;
}

// KPI Summary
export interface KPISummary {
  today_revenue: string;
  yesterday_revenue: string;
  revenue_change_pct: string | null;
  open_invoice_count: number;
  open_invoice_amount: string;
  pending_order_count: number;
  pending_order_revenue: string;
  low_stock_product_count: number;
  overdue_receivables_amount: string;
}

// Top Customers
export interface TopCustomerItem {
  customer_id: string;
  company_name: string;
  total_revenue: string;
  invoice_count: number;
  last_invoice_date: string;
}

export interface TopCustomersResponse {
  period: string;
  start_date: string;
  end_date: string;
  customers: TopCustomerItem[];
}

// AR Aging
export interface ARAgingBucket {
  bucket_label: string;
  amount: string;
  invoice_count: number;
}

export interface ARAgingResponse {
  as_of_date: string;
  buckets: ARAgingBucket[];
  total_outstanding: string;
  total_overdue: string;
}

// AP Aging
export interface APAgingBucket {
  bucket_label: string;
  amount: string;
  invoice_count: number;
}

export interface APAgingResponse {
  as_of_date: string;
  buckets: APAgingBucket[];
  total_outstanding: string;
  total_overdue: string;
}

// Gross Margin
export interface GrossMarginPreviousPeriod {
  gross_margin_percent: string;
}

export interface GrossMarginResponse {
  available: boolean;
  gross_margin_percent: string;
  revenue: string;
  cogs: string;
  previous_period: GrossMarginPreviousPeriod;
}

// Cash Flow
export interface CashFlowItem {
  date: string;
  amount: string;
}

export interface CashFlowResponse {
  period: string;
  start_date: string;
  end_date: string;
  cash_inflows: CashFlowItem[];
  cash_outflows: CashFlowItem[];
}

// Revenue Trend
export interface RevenueTrendItem {
  date: string;
  revenue: string;
}

export interface RevenueTrendResponse {
  period: string;
  start_date: string;
  end_date: string;
  items: RevenueTrendItem[];
}
