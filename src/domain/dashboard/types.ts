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
