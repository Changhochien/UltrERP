"""Shared pure date and window helpers for intelligence services."""

from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Literal

from domains.product_analytics.service import normalize_month_start

from .constants import MONEY_QUANT, ZERO

# Re-export normalize_month_start from product_analytics
from domains.product_analytics.service import normalize_month_start


def subtract_months(anchor: datetime, months: int) -> datetime:
    """Subtract months from a datetime, adjusting day to valid range."""
    year = anchor.year
    month = anchor.month - months
    while month <= 0:
        year -= 1
        month += 12
    day = min(anchor.day, monthrange(year, month)[1])
    return anchor.replace(year=year, month=month, day=day)


def shift_month_start(value: date, months: int) -> date:
    """Shift a month-start date by given months (negative or positive).
    
    This is the single authoritative implementation - duplicates should be removed.
    """
    month_index = (value.year * 12 + value.month - 1) + months
    year = month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def months_between_inclusive(start_month: date, end_month: date) -> int:
    """Count inclusive months between two month-start dates."""
    return ((end_month.year - start_month.year) * 12) + (end_month.month - start_month.month) + 1


def month_start_from_timestamp(value: datetime | date) -> date:
    """Normalize a timestamp to its month start."""
    if isinstance(value, datetime):
        return normalize_month_start(value.date())
    return normalize_month_start(value)


def iter_month_starts(start_month: date, end_month: date) -> tuple[date, ...]:
    """Generate all month-start dates from start to end inclusive."""
    months: list[date] = []
    cursor = start_month
    while cursor <= end_month:
        months.append(cursor)
        cursor = shift_month_start(cursor, 1)
    return tuple(months)


def period_windows(
    period: Literal["last_30d", "last_90d", "last_12m"],
    *,
    anchor: datetime | None = None,
) -> tuple[date, date, date]:
    """Calculate current, prior, and end dates for a period.
    
    Returns (current_start, prior_start, end) tuple.
    """
    end = (anchor or datetime.now()).date()
    days = 90
    if period == "last_30d":
        days = 30
    elif period == "last_12m":
        days = 365

    current_start = end - timedelta(days=days)
    prior_start = current_start - timedelta(days=days)
    return current_start, prior_start, end
