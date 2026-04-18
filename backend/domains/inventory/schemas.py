"""Pydantic schemas for the inventory domain."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from common.time import today

# --- Warehouse schemas ---


class WarehouseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    code: str = Field(..., min_length=1, max_length=50)
    location: str | None = Field(None, max_length=500)
    address: str | None = Field(None, max_length=500)
    contact_email: str | None = Field(None, max_length=255)


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseResponse(WarehouseBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    is_active: bool
    created_at: datetime


class WarehouseList(BaseModel):
    items: list[WarehouseResponse]
    total: int


# --- Transfer schemas ---


class TransferRequest(BaseModel):
    from_warehouse_id: uuid.UUID
    to_warehouse_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int = Field(..., gt=0)
    notes: str | None = Field(None, max_length=1000)


class TransferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    product_id: uuid.UUID
    from_warehouse_id: uuid.UUID
    to_warehouse_id: uuid.UUID
    quantity: int
    actor_id: str
    notes: str | None
    created_at: datetime

class TransferHistoryItem(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    product_id: uuid.UUID
    product_code: str
    product_name: str
    from_warehouse_id: uuid.UUID
    from_warehouse_name: str
    from_warehouse_code: str
    to_warehouse_id: uuid.UUID
    to_warehouse_name: str
    to_warehouse_code: str
    quantity: int
    actor_id: str
    notes: str | None
    created_at: datetime

class TransferHistoryListResponse(BaseModel):
    items: list[TransferHistoryItem]
    total: int


# --- Inventory stock schemas ---


class InventoryStockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: int
    reorder_point: int
    safety_factor: float
    lead_time_days: int
    policy_type: Literal["continuous", "periodic", "manual"]
    target_stock_qty: int
    on_order_qty: int
    in_transit_qty: int
    reserved_qty: int
    planning_horizon_days: int
    review_cycle_days: int
    updated_at: datetime


class StockSettingsUpdateRequest(BaseModel):
    reorder_point: int | None = Field(None, ge=0)
    safety_factor: float | None = Field(None, ge=0.0)
    lead_time_days: int | None = Field(None, ge=0)
    policy_type: Literal["continuous", "periodic", "manual"] | None = None
    target_stock_qty: int | None = Field(None, ge=0)
    on_order_qty: int | None = Field(None, ge=0)
    in_transit_qty: int | None = Field(None, ge=0)
    reserved_qty: int | None = Field(None, ge=0)
    planning_horizon_days: int | None = Field(None, ge=0)
    review_cycle_days: int | None = Field(None, ge=0)


# --- Monthly demand schemas ---


class MonthlyDemandItem(BaseModel):
    month: str  # YYYY-MM
    total_qty: int


class MonthlyDemandResponse(BaseModel):
    items: list[MonthlyDemandItem]
    total: int


PlanningSupportDataBasis = Literal[
    "aggregated_only",
    "aggregated_plus_live_current_month",
    "live_current_month_only",
    "no_history",
]


class PlanningSupportItem(BaseModel):
    month: str
    quantity: Decimal
    source: Literal["aggregated", "live"]


class PlanningSupportWindow(BaseModel):
    start_month: str
    end_month: str
    includes_current_month: bool
    is_partial: bool


class SharedHistoryAdvisoryContext(BaseModel):
    advisory_only: bool
    data_basis: PlanningSupportDataBasis
    history_months_used: int
    avg_monthly_quantity: float | None
    seasonality_index: float | None
    current_month_live_quantity: float | None


class PlanningSupportResponse(BaseModel):
    product_id: uuid.UUID
    items: list[PlanningSupportItem]
    avg_monthly_quantity: Decimal | None
    peak_monthly_quantity: Decimal | None
    low_monthly_quantity: Decimal | None
    seasonality_index: Decimal | None
    above_average_months: list[str]
    history_months_used: int
    current_month_live_quantity: Decimal | None
    reorder_point: int
    on_order_qty: int
    in_transit_qty: int
    reserved_qty: int
    data_basis: PlanningSupportDataBasis
    advisory_only: bool
    data_gap: bool
    window: PlanningSupportWindow


# --- Sales history schemas ---


class SalesHistoryItem(BaseModel):
    date: datetime
    quantity_change: int
    reason_code: str
    actor_id: str


class SalesHistoryResponse(BaseModel):
    items: list[SalesHistoryItem]
    total: int


# --- Top customer schemas ---


class TopCustomerResponse(BaseModel):
    customer_id: uuid.UUID
    customer_name: str
    total_qty: int


# --- Product supplier schemas ---


class ProductSupplierResponse(BaseModel):
    supplier_id: uuid.UUID
    name: str
    unit_cost: float | None = None
    default_lead_time_days: int | None = None


class ProductSupplierAssociationCreate(BaseModel):
    supplier_id: uuid.UUID
    unit_cost: float | None = Field(None, ge=0)
    lead_time_days: int | None = Field(None, ge=0)
    is_default: bool = False


class ProductSupplierAssociationUpdate(BaseModel):
    unit_cost: float | None = Field(None, ge=0)
    lead_time_days: int | None = Field(None, ge=0)
    is_default: bool | None = None


class ProductSupplierAssociationResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_name: str
    unit_cost: float | None = None
    lead_time_days: int | None = None
    is_default: bool
    created_at: datetime
    updated_at: datetime


class ProductSupplierAssociationListResponse(BaseModel):
    items: list[ProductSupplierAssociationResponse]
    total: int


# --- Category schemas ---


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(CategoryBase):
    pass


class CategoryStatusUpdate(BaseModel):
    is_active: bool


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CategoryListResponse(BaseModel):
    items: list[CategoryResponse]
    total: int


# --- Unit of measure schemas ---


class UnitOfMeasureBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    decimal_places: int = Field(default=0, ge=0, le=6)


class UnitOfMeasureCreate(UnitOfMeasureBase):
    pass


class UnitOfMeasureUpdate(UnitOfMeasureBase):
    pass


class UnitOfMeasureStatusUpdate(BaseModel):
    is_active: bool


class UnitOfMeasureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    code: str
    name: str
    decimal_places: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UnitOfMeasureListResponse(BaseModel):
    items: list[UnitOfMeasureResponse]
    total: int


# --- Product search schemas ---


class ProductSearchResult(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    category: str | None
    status: str
    current_stock: int
    relevance: float


class ProductSearchResponse(BaseModel):
    items: list[ProductSearchResult]
    total: int


# --- Product schemas ---


class ProductCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=500)
    category: str | None = Field(None, max_length=200)
    description: str | None = None
    unit: str = Field(default="pcs", max_length=50)
    standard_cost: Decimal | None = Field(default=None, ge=0, max_digits=19, decimal_places=4)


class ProductUpdate(BaseModel):
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=500)
    category: str | None = Field(None, max_length=200)
    description: str | None = None
    unit: str = Field(..., min_length=1, max_length=50)
    standard_cost: Decimal | None = Field(default=None, ge=0, max_digits=19, decimal_places=4)


class ProductStatusUpdate(BaseModel):
    status: Literal["active", "inactive"]


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    category: str | None
    description: str | None
    unit: str
    standard_cost: Decimal | None = None
    status: str
    created_at: datetime


# --- Product detail schemas ---


class WarehouseStockInfo(BaseModel):
    stock_id: uuid.UUID
    warehouse_id: uuid.UUID
    warehouse_name: str
    current_stock: int
    reorder_point: int
    safety_factor: float
    lead_time_days: int
    policy_type: Literal["continuous", "periodic", "manual"]
    target_stock_qty: int
    on_order_qty: int
    in_transit_qty: int
    reserved_qty: int
    planning_horizon_days: int
    review_cycle_days: int
    is_below_reorder: bool
    last_adjusted: datetime | None


class AdjustmentHistoryItem(BaseModel):
    id: uuid.UUID
    created_at: datetime
    quantity_change: int
    reason_code: str
    actor_id: str
    notes: str | None


class ProductDetailResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    category: str | None
    description: str | None
    unit: str
    standard_cost: Decimal | None = None
    status: str
    legacy_master_snapshot: dict[str, Any] | None = None
    total_stock: int
    warehouses: list[WarehouseStockInfo]
    adjustment_history: list[AdjustmentHistoryItem]


# --- Stock adjustment schemas ---

USER_SELECTABLE_REASON_CODES = [
    "received",
    "damaged",
    "returned",
    "correction",
    "other",
]


class StockAdjustmentRequest(BaseModel):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity_change: int = Field(..., description="Positive to add, negative to remove")
    reason_code: str = Field(..., min_length=1, max_length=50)
    notes: str | None = Field(None, max_length=1000)


class StockAdjustmentResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity_change: int
    reason_code: str
    actor_id: str
    notes: str | None
    updated_stock: int
    created_at: datetime


class ReasonCodeItem(BaseModel):
    value: str
    label: str
    user_selectable: bool


class ReasonCodeListResponse(BaseModel):
    items: list[ReasonCodeItem]


# --- Physical count schemas ---


class PhysicalCountSessionCreate(BaseModel):
    warehouse_id: uuid.UUID


class PhysicalCountLineUpdateRequest(BaseModel):
    counted_qty: int = Field(..., ge=0)
    notes: str | None = Field(None, max_length=1000)


class PhysicalCountLineResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_code: str | None = None
    product_name: str | None = None
    system_qty_snapshot: int
    counted_qty: int | None
    variance_qty: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PhysicalCountSessionSummary(BaseModel):
    id: uuid.UUID
    warehouse_id: uuid.UUID
    warehouse_name: str | None = None
    status: Literal["in_progress", "submitted", "approved"]
    created_by: str
    submitted_by: str | None
    submitted_at: datetime | None
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime
    total_lines: int
    counted_lines: int
    variance_total: int


class PhysicalCountSessionResponse(PhysicalCountSessionSummary):
    lines: list[PhysicalCountLineResponse]


class PhysicalCountSessionListResponse(BaseModel):
    items: list[PhysicalCountSessionSummary]
    total: int


# --- Reorder alert schemas ---


class StockHistoryPoint(BaseModel):
    date: datetime
    quantity_change: int
    reason_code: str
    running_stock: int
    notes: str | None


class StockHistoryResponse(BaseModel):
    points: list[StockHistoryPoint]
    current_stock: int
    reorder_point: int
    avg_daily_usage: float | None
    lead_time_days: int | None
    safety_stock: float | None


class ReorderAlertItem(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    warehouse_id: uuid.UUID
    warehouse_name: str
    current_stock: int
    reorder_point: int
    status: str
    severity: Literal["CRITICAL", "WARNING", "INFO"]
    created_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by: str | None
    snoozed_until: datetime | None
    snoozed_by: str | None
    dismissed_at: datetime | None
    dismissed_by: str | None


class ReorderAlertListResponse(BaseModel):
    items: list[ReorderAlertItem]
    total: int


class ReorderSuggestionSupplierHint(BaseModel):
    supplier_id: uuid.UUID
    name: str
    unit_cost: float | None = None
    default_lead_time_days: int | None = None


class ReorderSuggestionItem(BaseModel):
    product_id: uuid.UUID
    product_code: str
    product_name: str
    warehouse_id: uuid.UUID
    warehouse_name: str
    current_stock: int
    reorder_point: int
    inventory_position: int
    target_stock_qty: int | None
    suggested_qty: int
    supplier_hint: ReorderSuggestionSupplierHint | None = None


class ReorderSuggestionListResponse(BaseModel):
    items: list[ReorderSuggestionItem]
    total: int


class ReorderSuggestionOrderRequestItem(BaseModel):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    suggested_qty: int = Field(..., gt=0)


class CreateReorderSuggestionOrdersRequest(BaseModel):
    items: list[ReorderSuggestionOrderRequestItem] = Field(..., min_length=1)


class ReorderSuggestionCreatedOrder(BaseModel):
    order_id: uuid.UUID
    order_number: str
    supplier_id: uuid.UUID
    supplier_name: str
    line_count: int


class CreateReorderSuggestionOrdersResponse(BaseModel):
    created_orders: list[ReorderSuggestionCreatedOrder]
    unresolved_rows: list[ReorderSuggestionItem]


class BelowReorderReportItem(BaseModel):
    product_id: uuid.UUID
    product_code: str
    product_name: str
    category: str | None = None
    warehouse_id: uuid.UUID
    warehouse_name: str
    current_stock: int
    reorder_point: int
    shortage_qty: int
    on_order_qty: int
    in_transit_qty: int
    default_supplier: str | None = None


class BelowReorderReportResponse(BaseModel):
    items: list[BelowReorderReportItem]
    total: int


class InventoryValuationItem(BaseModel):
    product_id: uuid.UUID
    product_code: str
    product_name: str
    category: str | None = None
    warehouse_id: uuid.UUID
    warehouse_name: str
    quantity: int
    unit_cost: Decimal | None = None
    extended_value: Decimal
    cost_source: Literal["standard_cost", "latest_purchase", "missing"]


class InventoryValuationWarehouseTotal(BaseModel):
    warehouse_id: uuid.UUID
    warehouse_name: str
    total_quantity: int
    total_value: Decimal
    row_count: int


class InventoryValuationResponse(BaseModel):
    items: list[InventoryValuationItem]
    warehouse_totals: list[InventoryValuationWarehouseTotal]
    grand_total_value: Decimal
    grand_total_quantity: int
    total_rows: int


class AcknowledgeAlertResponse(BaseModel):
    id: uuid.UUID
    status: str
    acknowledged_at: datetime
    acknowledged_by: str


class SnoozeAlertRequest(BaseModel):
    duration_minutes: int = Field(ge=1, le=7 * 24 * 60)


class SnoozeAlertResponse(BaseModel):
    id: uuid.UUID
    status: str
    snoozed_until: datetime
    snoozed_by: str


class DismissAlertResponse(BaseModel):
    id: uuid.UUID
    status: str
    dismissed_at: datetime
    dismissed_by: str


# --- Supplier schemas ---


class SupplierBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    contact_email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    default_lead_time_days: int | None = Field(default=None, ge=0)


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(SupplierBase):
    pass


class SupplierStatusUpdate(BaseModel):
    is_active: bool


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    contact_email: str | None
    phone: str | None
    address: str | None
    default_lead_time_days: int | None
    is_active: bool
    legacy_master_snapshot: dict[str, Any] | None = None
    created_at: datetime


class SupplierListResponse(BaseModel):
    items: list[SupplierResponse]
    total: int


# --- Supplier order schemas ---


class SupplierOrderLineRequest(BaseModel):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity_ordered: int = Field(..., gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    notes: str | None = Field(None, max_length=1000)


class SupplierOrderLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity_ordered: int
    unit_price: Decimal | None = None
    quantity_received: int
    notes: str | None


class SupplierOrderCreate(BaseModel):
    supplier_id: uuid.UUID
    order_date: date = Field(default_factory=today)
    expected_arrival_date: date | None = None
    lines: list[SupplierOrderLineRequest] = Field(..., min_length=1)


class SupplierOrderResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_name: str
    order_number: str
    status: str
    order_date: date
    expected_arrival_date: date | None
    received_date: date | None
    created_by: str
    lines: list[SupplierOrderLineResponse]
    created_at: datetime
    updated_at: datetime


class SupplierOrderListItem(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_name: str
    order_number: str
    status: str
    order_date: date
    expected_arrival_date: date | None
    received_date: date | None
    created_by: str
    created_at: datetime
    updated_at: datetime
    line_count: int


class SupplierOrderListResponse(BaseModel):
    items: list[SupplierOrderListItem]
    total: int


class UpdateOrderStatusRequest(BaseModel):
    status: str = Field(
        ...,
        pattern=r"^(pending|confirmed|shipped|partially_received|received|cancelled)$",
    )
    notes: str | None = None


class ReceiveOrderRequest(BaseModel):
    received_quantities: dict[str, int] = Field(default_factory=dict)
    received_date: date | None = None


# ── Reorder point schemas ───────────────────────────────────────


class ReorderPointPreviewRow(BaseModel):
    stock_id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    warehouse_id: uuid.UUID
    warehouse_name: str
    current_quantity: float
    inventory_position: int | None = None
    on_order_qty: int | None = None
    in_transit_qty: int | None = None
    reserved_qty: int | None = None
    current_reorder_point: float
    policy_type: Literal["continuous", "periodic", "manual"] | None = None
    target_stock_qty: int | None = None
    planning_horizon_days: int | None = None
    effective_horizon_days: int | None = None
    computed_reorder_point: float | None = None  # None if skipped
    avg_daily_usage: float | None = None
    lead_time_days: float | None = None
    lead_time_sample_count: int | None = None
    lead_time_confidence: Literal["high", "medium", "low"] | None = None
    review_cycle_days: float | None = None
    safety_stock: float | None = None
    target_stock_level: float | None = None
    demand_basis: str | None = None  # e.g. "SALES_RESERVATION"
    movement_count: int | None = None
    # "actual" | "supplier_default" | "fallback_7d" | "manual_override"
    lead_time_source: str | None = None
    quality_note: str | None = None  # Human-readable explanation
    skip_reason: str | None = None  # "insufficient_history" | "source_unresolved" | None
    shared_history_context: SharedHistoryAdvisoryContext | None = None
    is_selected: bool = False
    suggested_order_qty: int | None = None  # computed at preview time, not persisted


class ReorderPointComputeRequest(BaseModel):
    safety_factor: float = 0.5  # 0.0 to 1.0
    lookback_days: int = Field(default=90, ge=1, le=365)  # demand history lookback (1–365 days)
    lookback_days_lead_time: int = 180
    warehouse_id: uuid.UUID | None = None
    # category_id intentionally omitted — Product.category is a str; wire up separately when needed


class ReorderPointComputeResponse(BaseModel):
    candidate_rows: list[ReorderPointPreviewRow]
    skipped_rows: list[ReorderPointPreviewRow]
    parameters: dict  # The input params used


class ReorderPointApplyRequest(BaseModel):
    selected_stock_ids: list[uuid.UUID]
    safety_factor: float
    lookback_days: int
    lookback_days_lead_time: int = 180
    warehouse_id: uuid.UUID | None = None


class ReorderPointApplyResponse(BaseModel):
    updated_count: int
    skipped_count: int
    run_parameters: dict


# ── Audit log schemas ─────────────────────────────────────────


class AuditLogItem(BaseModel):
    id: uuid.UUID
    created_at: datetime
    actor_id: str
    field: str
    old_value: str | None
    new_value: str | None


class AuditLogListResponse(BaseModel):
    items: list[AuditLogItem]
    total: int
