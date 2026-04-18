/** Inventory domain types. */

import type { AlertSeverity } from "../../lib/alertSeverity";

export type ReorderAlertStatus =
  | "pending"
  | "acknowledged"
  | "snoozed"
  | "dismissed"
  | "resolved";

export type ReplenishmentPolicy = "continuous" | "periodic" | "manual";

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
  safety_factor: number;
  lead_time_days: number;
  policy_type: ReplenishmentPolicy;
  target_stock_qty: number;
  on_order_qty: number;
  in_transit_qty: number;
  reserved_qty: number;
  planning_horizon_days: number;
  review_cycle_days: number;
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

export interface Category {
  id: string;
  tenant_id: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CategoryListResponse {
  items: Category[];
  total: number;
}

export interface CategoryCreate {
  name: string;
}

export interface CategoryUpdate {
  name: string;
}

export interface CategoryStatusUpdate {
  status: "active" | "inactive";
}

export interface WarehouseStockInfo {
  stock_id: string;
  warehouse_id: string;
  warehouse_name: string;
  current_stock: number;
  reorder_point: number;
  safety_factor: number;
  lead_time_days: number;
  policy_type: ReplenishmentPolicy;
  target_stock_qty: number;
  on_order_qty: number;
  in_transit_qty: number;
  reserved_qty: number;
  planning_horizon_days: number;
  review_cycle_days: number;
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
  description: string | null;
  unit: string;
  status: string;
  legacy_master_snapshot?: Record<string, unknown> | null;
  total_stock: number;
  warehouses: WarehouseStockInfo[];
  adjustment_history: AdjustmentHistoryItem[];
}

export interface ProductStatusUpdate {
  status: "active" | "inactive";
}

export type PlanningSupportDataBasis =
  | "aggregated_only"
  | "aggregated_plus_live_current_month"
  | "live_current_month_only"
  | "no_history";

export interface PlanningSupportItem {
  month: string;
  quantity: string;
  source: "aggregated" | "live";
}

export interface PlanningSupportWindow {
  start_month: string;
  end_month: string;
  includes_current_month: boolean;
  is_partial: boolean;
}

export interface PlanningSupportResponse {
  product_id: string;
  items: PlanningSupportItem[];
  avg_monthly_quantity: string | null;
  peak_monthly_quantity: string | null;
  low_monthly_quantity: string | null;
  seasonality_index: string | null;
  above_average_months: string[];
  history_months_used: number;
  current_month_live_quantity: string | null;
  reorder_point: number;
  on_order_qty: number;
  in_transit_qty: number;
  reserved_qty: number;
  data_basis: PlanningSupportDataBasis;
  advisory_only: boolean;
  data_gap: boolean;
  window: PlanningSupportWindow;
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
  status: ReorderAlertStatus;
  severity: AlertSeverity;
  created_at: string;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  snoozed_until: string | null;
  snoozed_by: string | null;
  dismissed_at: string | null;
  dismissed_by: string | null;
}

export interface ReorderAlertListResponse {
  items: ReorderAlertItem[];
  total: number;
}

export interface AcknowledgeAlertResponse {
  id: string;
  status: ReorderAlertStatus;
  acknowledged_at: string;
  acknowledged_by: string;
}

export interface SnoozeAlertResponse {
  id: string;
  status: ReorderAlertStatus;
  snoozed_until: string;
  snoozed_by: string;
}

export interface DismissAlertResponse {
  id: string;
  status: ReorderAlertStatus;
  dismissed_at: string;
  dismissed_by: string;
}

// --- Stock history types ---

export interface StockHistoryPoint {
  date: string;
  quantity_change: number;
  reason_code: string;
  running_stock: number;
  notes: string | null;
}

export interface StockHistoryResponse {
  points: StockHistoryPoint[];
  current_stock: number;
  reorder_point: number;
  avg_daily_usage: number | null;
  lead_time_days: number | null;
  safety_stock: number | null;
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
  unit_price?: string | null;
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
    unit_price?: number;
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

// --- Stock history types ---

export interface StockSnapshotPoint {
  timestamp: string;
  quantity: number;
  change: number;
}

export type PlanningSupportDataBasis =
  | "aggregated_only"
  | "aggregated_plus_live_current_month"
  | "live_current_month_only"
  | "no_history";

export interface PlanningSupportItem {
  month: string;
  quantity: string;
  source: "aggregated" | "live";
}

export interface PlanningSupportWindow {
  start_month: string;
  end_month: string;
  includes_current_month: boolean;
  is_partial: boolean;
}

export interface SharedHistoryAdvisoryContext {
  advisory_only: boolean;
  data_basis: PlanningSupportDataBasis;
  history_months_used: number;
  avg_monthly_quantity: number | null;
  seasonality_index: number | null;
  current_month_live_quantity: number | null;
}

export interface PlanningSupportResponse {
  product_id: string;
  items: PlanningSupportItem[];
  avg_monthly_quantity: string | null;
  peak_monthly_quantity: string | null;
  low_monthly_quantity: string | null;
  seasonality_index: string | null;
  above_average_months: string[];
  history_months_used: number;
  current_month_live_quantity: string | null;
  reorder_point: number;
  on_order_qty: number;
  in_transit_qty: number;
  reserved_qty: number;
  data_basis: PlanningSupportDataBasis;
  advisory_only: boolean;
  data_gap: boolean;
  window: PlanningSupportWindow;
}

// --- Reorder point types ---

export interface ReorderPointPreviewRow {
  stock_id: string;
  product_id: string;
  product_name: string;
  warehouse_id: string;
  warehouse_name: string;
  current_quantity: number;
  inventory_position: number | null;
  on_order_qty: number | null;
  in_transit_qty: number | null;
  reserved_qty: number | null;
  current_reorder_point: number;
  policy_type: ReplenishmentPolicy | null;
  target_stock_qty: number | null;
  planning_horizon_days: number | null;
  effective_horizon_days: number | null;
  computed_reorder_point: number | null;
  avg_daily_usage: number | null;
  lead_time_days: number | null;
  lead_time_sample_count: number | null;
  lead_time_confidence: "high" | "medium" | "low" | null;
  review_cycle_days: number | null;
  safety_stock: number | null;
  target_stock_level: number | null;
  demand_basis: string | null;
  movement_count: number | null;
  lead_time_source: string | null;
  quality_note: string | null;
  skip_reason: string | null;
  shared_history_context?: SharedHistoryAdvisoryContext | null;
  is_selected: boolean;
  suggested_order_qty: number | null;
}

export interface ReorderPointComputeResponse {
  candidate_rows: ReorderPointPreviewRow[];
  skipped_rows: ReorderPointPreviewRow[];
  parameters: Record<string, unknown>;
}

export interface ReorderPointApplyResponse {
  updated_count: number;
  skipped_count: number;
  run_parameters: Record<string, unknown>;
}

// --- Product create types ---

export interface ProductCreate {
  code: string;
  name: string;
  category?: string;
  description?: string;
  unit?: string;
}

export interface ProductUpdate {
  code: string;
  name: string;
  category?: string;
  description?: string;
  unit: string;
}

export interface ProductResponse {
  id: string;
  code: string;
  name: string;
  category: string | null;
  description: string | null;
  unit: string;
  status: string;
  created_at: string;
}
