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


class VisitorStatsResponse(BaseModel):
    visitor_count: int
    inquiry_count: int
    conversion_rate: Decimal | None  # None if visitor_count == 0
    date: date
    is_configured: bool
    error: str | None = None
