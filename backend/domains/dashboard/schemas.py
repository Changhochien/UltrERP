"""Dashboard domain schemas."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


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
