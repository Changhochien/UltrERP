"""Shared pure decimal and numeric helpers for intelligence services."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from .constants import MONEY_QUANT, RATIO_QUANT, ZERO


def to_decimal(value: object | None, *, quant: Decimal = MONEY_QUANT) -> Decimal:
    """Convert a value to a quantized Decimal."""
    return Decimal(str(value or "0")).quantize(quant)


def safe_average(total: Decimal, count: int) -> Decimal:
    """Calculate average, returning ZERO for non-positive count."""
    if count <= 0:
        return ZERO
    return (total / Decimal(count)).quantize(MONEY_QUANT)


def average_count(total: int, count: int) -> Decimal:
    """Calculate integer average as Decimal."""
    if count <= 0:
        return ZERO
    return (Decimal(total) / Decimal(count)).quantize(MONEY_QUANT)


def ratio(numerator: int, denominator: int) -> Decimal:
    """Calculate ratio, returning 0.0000 for non-positive denominator."""
    if denominator <= 0:
        return Decimal("0.0000")
    return (Decimal(numerator) / Decimal(denominator)).quantize(RATIO_QUANT)


def to_ratio(value: Decimal, *, quant: Decimal = RATIO_QUANT) -> float:
    """Convert Decimal to float with quantization."""
    return float(value.quantize(quant))


def percent_change(current_value: Decimal, prior_value: Decimal) -> float | None:
    """Calculate percentage change, returning None if prior is zero."""
    if prior_value == 0:
        return None
    return float(((current_value - prior_value) / prior_value * Decimal("100")).quantize(Decimal("0.1")))


def frequency_trend(current_count: int, prior_count: int) -> Literal["increasing", "declining", "stable"]:
    """Determine frequency trend based on threshold heuristics."""
    if prior_count <= 0:
        return "increasing" if current_count > 0 else "stable"
    if current_count > prior_count * 1.20:
        return "increasing"
    if current_count < prior_count * 0.80:
        return "declining"
    return "stable"


def aov_trend(current_value: Decimal, prior_value: Decimal) -> Literal["increasing", "declining", "stable"]:
    """Determine AOV trend based on threshold heuristics."""
    if prior_value <= 0:
        return "increasing" if current_value > 0 else "stable"
    if current_value > prior_value * Decimal("1.10"):
        return "increasing"
    if current_value < prior_value * Decimal("0.90"):
        return "declining"
    return "stable"


def bounded_similarity(value: float, baseline: float) -> float:
    """Calculate bounded similarity: 0.0 to 1.0 based on distance from baseline."""
    if baseline <= 0:
        return 0.0
    return max(0.0, 1.0 - min(abs(value - baseline) / baseline, 1.0))


def confidence(order_count_12m: int) -> Literal["high", "medium", "low"]:
    """Determine confidence level based on 12-month order count."""
    if order_count_12m >= 6:
        return "high"
    if order_count_12m >= 2:
        return "medium"
    return "low"
