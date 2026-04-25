"""Shared support layer for intelligence services.

This package contains pure helpers, constants, and shared types that are
used across multiple intelligence feature modules. It must not depend on
any feature modules to maintain clean architectural boundaries.
"""

# Re-export all shared components for convenient imports
from .category_trend_loader import load_category_trends
from .category_helpers import is_excluded_category
from .constants import (
    CUSTOMER_BUYING_BEHAVIOR_PERIOD_MONTHS,
    EXCLUDED_CATEGORIES,
    MONEY_QUANT,
    OPPORTUNITY_SEVERITY_PRIORITY,
    PCT_QUANT,
    QUANTITY_QUANT,
    RATIO_QUANT,
    REVENUE_DIAGNOSIS_PERIOD_MONTHS,
    RISK_STATUS_PRIORITY,
    ZERO,
)
from .date_helpers import (
    iter_month_starts,
    months_between_inclusive,
    month_start_from_timestamp,
    normalize_month_start,
    period_windows,
    shift_month_start,
    subtract_months,
)
from .decimal_helpers import (
    aov_trend,
    average_count,
    bounded_similarity,
    confidence,
    frequency_trend,
    percent_change,
    ratio,
    safe_average,
    to_decimal,
    to_ratio,
)

__all__ = [
    # Date helpers
    "normalize_month_start",
    # Decimal helpers
    "confidence",
    # Constants
    "MONEY_QUANT",
    "QUANTITY_QUANT",
    "RATIO_QUANT",
    "PCT_QUANT",
    "ZERO",
    "EXCLUDED_CATEGORIES",
    "RISK_STATUS_PRIORITY",
    "OPPORTUNITY_SEVERITY_PRIORITY",
    "REVENUE_DIAGNOSIS_PERIOD_MONTHS",
    "CUSTOMER_BUYING_BEHAVIOR_PERIOD_MONTHS",
    # Date helpers
    "subtract_months",
    "shift_month_start",
    "months_between_inclusive",
    "month_start_from_timestamp",
    "iter_month_starts",
    "period_windows",
    # Decimal helpers
    "to_decimal",
    "safe_average",
    "average_count",
    "ratio",
    "to_ratio",
    "percent_change",
    "frequency_trend",
    "aov_trend",
    "bounded_similarity",
    "load_category_trends",
    # Category helpers
    "is_excluded_category",
]
