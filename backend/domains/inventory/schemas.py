"""Pydantic schemas for the inventory domain."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

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
    updated_at: datetime


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
    warehouse_id: uuid.UUID
    warehouse_name: str
    current_stock: int
    reorder_point: int
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


class ReorderAlertItem(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    warehouse_id: uuid.UUID
    warehouse_name: str
    current_stock: int
    reorder_point: int
    status: str
    created_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by: str | None


class ReorderAlertListResponse(BaseModel):
    items: list[ReorderAlertItem]
    total: int


class AcknowledgeAlertResponse(BaseModel):
    id: uuid.UUID
    status: str
    acknowledged_at: datetime
    acknowledged_by: str


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
    order_date: date = Field(default_factory=date.today)
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
