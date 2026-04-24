"""Dashboard domain schemas."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class RevenueSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    today_revenue: Decimal
    yesterday_revenue: Decimal
    change_percent: Decimal | None  # None when both days are zero
    today_date: date
    yesterday_date: date


class TopProductItem(BaseModel):
    product_id: uuid.UUID
    product_name: str
    quantity_sold: Decimal
    revenue: Decimal


class TopProductsResponse(BaseModel):
    period: str
    start_date: date
    end_date: date
    items: list[TopProductItem]


class TopCustomerItem(BaseModel):
    customer_id: uuid.UUID
    company_name: str
    total_revenue: Decimal
    invoice_count: int
    last_invoice_date: date


class TopCustomersResponse(BaseModel):
    period: str
    start_date: date
    end_date: date
    customers: list[TopCustomerItem]


class VisitorStatsResponse(BaseModel):
    visitor_count: int
    inquiry_count: int
    conversion_rate: Decimal | None  # None if visitor_count == 0
    date: date
    is_configured: bool
    error: str | None = None


class KpiSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    today_revenue: Decimal
    yesterday_revenue: Decimal
    revenue_change_pct: Decimal | None  # None when yesterday_revenue is 0
    open_invoice_count: int
    open_invoice_amount: Decimal
    pending_order_count: int
    pending_order_revenue: Decimal
    low_stock_product_count: int
    overdue_receivables_amount: Decimal


class CashFlowItem(BaseModel):
    date: date
    amount: Decimal


class RunningBalanceItem(BaseModel):
    date: date
    cumulative_balance: Decimal


class CashFlowResponse(BaseModel):
    start_date: date
    end_date: date
    cash_inflows: list[CashFlowItem]
    cash_outflows: list[CashFlowItem]
    net_cash_flow: Decimal
    running_balance_by_date: list[RunningBalanceItem]


class GrossMarginPeriodResponse(BaseModel):
    available: bool
    gross_margin_percent: Decimal | None


class GrossMarginResponse(BaseModel):
    available: bool
    gross_margin: Decimal
    gross_margin_percent: Decimal | None
    revenue: Decimal
    cogs: Decimal
    margin_percent: Decimal | None  # None when revenue is 0
    previous_period: GrossMarginPeriodResponse


class RevenueTrendItem(BaseModel):
    date: date  # Day, week (Monday), or month (1st) depending on granularity
    revenue: Decimal
    order_count: int


class RevenueTrendResponse(BaseModel):
    items: list[RevenueTrendItem]
    start_date: date
    end_date: date
    has_more: bool = False
    total: int | None = None  # total months with data (monthly granularity only)


# =============================================================================
# Dense Time-Series Response Schemas (Story 39-2)
# =============================================================================


class RevenueTrendDensePoint(BaseModel):
    """Single point in dense revenue trend series."""
    bucket_start: str  # YYYY-MM-DD or YYYY-MM
    bucket_label: str  # Human-readable label
    value: float  # Revenue amount in TWD
    is_zero_filled: bool
    period_status: Literal["closed", "partial"]
    source: Literal["aggregate", "live", "zero-filled"]


class RevenueTrendDenseRange(BaseModel):
    """Range metadata for dense revenue trend."""
    requested_start: str
    requested_end: str
    available_start: str | None = None
    available_end: str | None = None
    default_visible_start: str
    default_visible_end: str
    bucket: Literal["day", "week", "month"]
    timezone: str = "Asia/Taipei"


class RevenueTrendDenseResponse(BaseModel):
    """Dense revenue trend series with range metadata for explorer charts."""
    points: list[RevenueTrendDensePoint]
    range: RevenueTrendDenseRange
