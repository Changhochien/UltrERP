"""
Shared time-series utilities for dense, range-aware chart data.

This module provides helpers for:
- Zero-filling monthly and daily series
- Generating range metadata
- Bucket generation with timezone awareness

Architecture:
- Timezone-aware bucket generation (Asia/Taipei for UltrERP business logic)
- Backend owns densification for business-correct time buckets
- Range metadata follows explicit contract from Story 39-1 types
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Literal, TypedDict

# v1 support envelope limits
MAX_MONTHLY_POINTS = 120
MAX_DAILY_POINTS = 730

# Business timezone for UltrERP
BUSINESS_TIMEZONE = "Asia/Taipei"

BucketType = Literal["day", "week", "month"]


class DenseSeriesPoint(TypedDict):
    """Single point in a dense time-series response."""
    bucket_start: str
    bucket_label: str
    value: float
    is_zero_filled: bool
    period_status: Literal["closed", "partial"]
    source: Literal["aggregate", "live", "zero-filled"]


class DenseSeriesRange(TypedDict):
    """Range metadata for a dense time-series response."""
    requested_start: str
    requested_end: str
    available_start: str | None
    available_end: str | None
    default_visible_start: str
    default_visible_end: str
    bucket: BucketType
    timezone: str


def densify_monthly_series(
    source_data: dict[str, float],
    requested_start: date,
    requested_end: date,
    current_date: date | None = None,
) -> tuple[list[DenseSeriesPoint], DenseSeriesRange]:
    """
    Zero-fill a monthly time-series for the requested range.

    Args:
        source_data: Dict mapping "YYYY-MM" strings to values (e.g., {"2025-01": 150.0})
        requested_start: First month to include (inclusive)
        requested_end: Last month to include (inclusive)
        current_date: Current date for determining partial periods (defaults to today)

    Returns:
        Tuple of (points list, range metadata)
    """
    if current_date is None:
        current_date = date.today()

    current_month = date(current_date.year, current_date.month, 1)
    points: list[DenseSeriesPoint] = []
    
    # Generate all months in range
    current = requested_start
    available_start: str | None = None
    available_end: str | None = None

    while current <= requested_end:
        key = current.strftime("%Y-%m")
        value = source_data.get(key, 0.0)
        is_zero_filled = key not in source_data

        # Determine period status
        if current >= current_month:
            period_status: Literal["closed", "partial"] = "partial"
        else:
            period_status = "closed"

        # Determine source
        if is_zero_filled:
            source: Literal["aggregate", "live", "zero-filled"] = "zero-filled"
        elif period_status == "partial":
            source = "live"
        else:
            source = "aggregate"

        # Track available range
        if value != 0 or not is_zero_filled:
            if available_start is None:
                available_start = key
            available_end = key

        points.append(DenseSeriesPoint(
            bucket_start=key,
            bucket_label=key,
            value=float(value),
            is_zero_filled=is_zero_filled,
            period_status=period_status,
            source=source,
        ))

        # Advance to next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    # Build range metadata
    # Default visible end is the earlier of: end of requested range or current month
    default_visible_end = min(requested_end, current_month).strftime("%Y-%m")
    if default_visible_end < requested_start.strftime("%Y-%m"):
        # If requested range is entirely in the past, show last 12 months
        default_visible_end = requested_end.strftime("%Y-%m")
    
    # Calculate default visible start (12 months before end or start of range)
    end_as_date = date.fromisoformat(default_visible_end + "-01")
    default_visible_start = _shift_months(end_as_date, -11).strftime("%Y-%m")
    if default_visible_start < requested_start.strftime("%Y-%m"):
        default_visible_start = requested_start.strftime("%Y-%m")

    range_meta = DenseSeriesRange(
        requested_start=requested_start.strftime("%Y-%m"),
        requested_end=requested_end.strftime("%Y-%m"),
        available_start=available_start,
        available_end=available_end,
        default_visible_start=default_visible_start,
        default_visible_end=default_visible_end,
        bucket="month",
        timezone=BUSINESS_TIMEZONE,
    )

    return points, range_meta


def densify_daily_series(
    source_data: dict[str, float],
    requested_start: date,
    requested_end: date,
    current_date: date | None = None,
) -> tuple[list[DenseSeriesPoint], DenseSeriesRange]:
    """
    Zero-fill a daily time-series for the requested range.

    Args:
        source_data: Dict mapping "YYYY-MM-DD" strings to values
        requested_start: First day to include (inclusive)
        requested_end: Last day to include (inclusive)
        current_date: Current date for determining partial periods

    Returns:
        Tuple of (points list, range metadata)
    """
    if current_date is None:
        current_date = date.today()

    points: list[DenseSeriesPoint] = []
    available_start: str | None = None
    available_end: str | None = None

    current = requested_start
    while current <= requested_end:
        key = current.strftime("%Y-%m-%d")
        value = source_data.get(key, 0.0)
        is_zero_filled = key not in source_data

        # Today's data is partial, yesterday and before are closed
        if current == current_date:
            period_status: Literal["closed", "partial"] = "partial"
        else:
            period_status = "closed"

        if is_zero_filled:
            source: Literal["aggregate", "live", "zero-filled"] = "zero-filled"
        elif period_status == "partial":
            source = "live"
        else:
            source = "aggregate"

        # Track available range
        if value != 0 or not is_zero_filled:
            if available_start is None:
                available_start = key
            available_end = key

        points.append(DenseSeriesPoint(
            bucket_start=key,
            bucket_label=key,
            value=float(value),
            is_zero_filled=is_zero_filled,
            period_status=period_status,
            source=source,
        ))

        current = date(current.year, current.month, current.day + 1) if current.day < 28 else _next_day(current)

    # Build range metadata
    default_visible_end = min(requested_end, current_date).strftime("%Y-%m-%d")
    default_visible_start = (current_date - timedelta(days=29)).strftime("%Y-%m-%d")
    if default_visible_start < requested_start.strftime("%Y-%m-%d"):
        default_visible_start = requested_start.strftime("%Y-%m-%d")

    range_meta = DenseSeriesRange(
        requested_start=requested_start.strftime("%Y-%m-%d"),
        requested_end=requested_end.strftime("%Y-%m-%d"),
        available_start=available_start,
        available_end=available_end,
        default_visible_start=default_visible_start,
        default_visible_end=default_visible_end,
        bucket="day",
        timezone=BUSINESS_TIMEZONE,
    )

    return points, range_meta


def check_range_limits(
    requested_start: date,
    requested_end: date,
    bucket: BucketType,
) -> tuple[bool, str | None]:
    """
    Check if a requested range exceeds v1 support limits.

    Returns:
        Tuple of (within_limits, error_message)
        error_message is None if within_limits is True
    """
    if bucket == "month":
        months = _count_months(requested_start, requested_end)
        if months > MAX_MONTHLY_POINTS:
            return False, f"Requested range of {months} months exceeds v1 limit of {MAX_MONTHLY_POINTS}. Use a coarser bucket or narrower range."
    elif bucket == "day":
        days = (requested_end - requested_start).days + 1
        if days > MAX_DAILY_POINTS:
            return False, f"Requested range of {days} days exceeds v1 limit of {MAX_DAILY_POINTS}. Use a coarser bucket or narrower range."
    
    return True, None


def _next_day(d: date) -> date:
    """Get the next day after d."""
    return d + timedelta(days=1)


def shift_months(d: date, months: int) -> date:
    """Shift a date by N months (public API)."""
    target_month = d.month + months
    target_year = d.year + (target_month - 1) // 12
    target_month = ((target_month - 1) % 12) + 1
    max_day = calendar.monthrange(target_year, target_month)[1]
    target_day = min(d.day, max_day)
    return date(target_year, target_month, target_day)


# Backward compatibility alias
_shift_months = shift_months


def _count_months(start: date, end: date) -> int:
    """Count number of months from start to end (inclusive)."""
    return (end.year - start.year) * 12 + (end.month - start.month) + 1
