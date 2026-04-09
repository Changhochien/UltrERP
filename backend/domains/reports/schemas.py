"""Reports domain schemas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ARAgingBucketItem(BaseModel):
    bucket_label: str
    amount: Decimal
    invoice_count: int


class ARAgingReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    as_of_date: date
    buckets: list[ARAgingBucketItem]
    total_outstanding: Decimal
    total_overdue: Decimal


APAgingReportResponse = ARAgingReportResponse
