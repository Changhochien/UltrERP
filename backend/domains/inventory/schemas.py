"""Pydantic schemas for the inventory domain."""

from __future__ import annotations

import uuid
from datetime import date, datetime
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
    notes: str | None = Field(None, max_length=1000)


class SupplierOrderLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity_ordered: int
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
    lead_time_source: str | None = None  # "actual" | "supplier_default" | "fallback_7d" | "manual_override"
    quality_note: str | None = None  # Human-readable explanation
    skip_reason: str | None = None  # "insufficient_history" | "source_unresolved" | None
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
