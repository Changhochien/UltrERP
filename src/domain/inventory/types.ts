/** Inventory domain types. */

export interface Warehouse {
  id: string;
  tenant_id: string;
  name: string;
  code: string;
  location: string | null;
  address: string | null;
  contact_email: string | null;
  is_active: boolean;
  created_at: string;
}

export interface WarehouseListResponse {
  items: Warehouse[];
  total: number;
}

export interface TransferRequest {
  from_warehouse_id: string;
  to_warehouse_id: string;
  product_id: string;
  quantity: number;
  notes?: string;
}

export interface TransferResponse {
  id: string;
  tenant_id: string;
  product_id: string;
  from_warehouse_id: string;
  to_warehouse_id: string;
  quantity: number;
  actor_id: string;
  notes: string | null;
  created_at: string;
}

export interface InventoryStock {
  id: string;
  tenant_id: string;
  product_id: string;
  warehouse_id: string;
  quantity: number;
  reorder_point: number;
  updated_at: string;
}

export interface ProductSearchResult {
  id: string;
  code: string;
  name: string;
  category: string | null;
  status: string;
  current_stock: number;
  relevance: number;
}

export interface ProductSearchResponse {
  items: ProductSearchResult[];
  total: number;
}

export interface WarehouseStockInfo {
  warehouse_id: string;
  warehouse_name: string;
  current_stock: number;
  reorder_point: number;
  is_below_reorder: boolean;
  last_adjusted: string | null;
}

export interface AdjustmentHistoryItem {
  id: string;
  created_at: string;
  quantity_change: number;
  reason_code: string;
  actor_id: string;
  notes: string | null;
}

export interface ProductDetail {
  id: string;
  code: string;
  name: string;
  category: string | null;
  status: string;
  total_stock: number;
  warehouses: WarehouseStockInfo[];
  adjustment_history: AdjustmentHistoryItem[];
}

export interface StockAdjustmentRequest {
  product_id: string;
  warehouse_id: string;
  quantity_change: number;
  reason_code: string;
  notes?: string;
}

export interface StockAdjustmentResponse {
  id: string;
  product_id: string;
  warehouse_id: string;
  quantity_change: number;
  reason_code: string;
  actor_id: string;
  notes: string | null;
  updated_stock: number;
  created_at: string;
}

export interface ReasonCodeItem {
  value: string;
  label: string;
  user_selectable: boolean;
}

export interface ReasonCodeListResponse {
  items: ReasonCodeItem[];
}

export interface ReorderAlertItem {
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

export interface ReorderAlertListResponse {
  items: ReorderAlertItem[];
  total: number;
}

export interface AcknowledgeAlertResponse {
  id: string;
  status: string;
  acknowledged_at: string;
  acknowledged_by: string;
}

// --- Supplier types ---

export interface Supplier {
  id: string;
  tenant_id: string;
  name: string;
  contact_email: string | null;
  phone: string | null;
  address: string | null;
  default_lead_time_days: number | null;
  is_active: boolean;
  created_at: string;
}

export interface SupplierListResponse {
  items: Supplier[];
  total: number;
}

// --- Supplier order types ---

export type SupplierOrderStatus =
  | "pending"
  | "confirmed"
  | "shipped"
  | "partially_received"
  | "received"
  | "cancelled";

export interface SupplierOrderLine {
  id: string;
  product_id: string;
  warehouse_id: string;
  quantity_ordered: number;
  quantity_received: number;
  notes: string | null;
}

export interface SupplierOrder {
  id: string;
  tenant_id: string;
  supplier_id: string;
  supplier_name: string;
  order_number: string;
  status: SupplierOrderStatus;
  order_date: string;
  expected_arrival_date: string | null;
  received_date: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  lines: SupplierOrderLine[];
}

export interface SupplierOrderListItem {
  id: string;
  supplier_id: string;
  supplier_name: string;
  order_number: string;
  status: SupplierOrderStatus;
  order_date: string;
  expected_arrival_date: string | null;
  received_date: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  line_count: number;
}

export interface SupplierOrderListResponse {
  items: SupplierOrderListItem[];
  total: number;
}

export interface CreateSupplierOrderRequest {
  supplier_id: string;
  order_date?: string;
  expected_arrival_date?: string | null;
  lines: Array<{
    product_id: string;
    warehouse_id: string;
    quantity_ordered: number;
    notes?: string;
  }>;
}

export interface ReceiveOrderRequest {
  received_quantities?: Record<string, number>;
  received_date?: string;
}

export interface UpdateOrderStatusRequest {
  status: SupplierOrderStatus;
  notes?: string;
}
