"""Shared constants for intelligence services."""

from decimal import Decimal

# Quantization constants for consistent decimal precision
MONEY_QUANT = Decimal("0.01")
QUANTITY_QUANT = Decimal("0.001")
RATIO_QUANT = Decimal("0.0001")
PCT_QUANT = Decimal("0.01")
ZERO = Decimal("0.00")

# Category exclusion list
EXCLUDED_CATEGORIES: frozenset[str] = frozenset({
    "discount",
    "discounts",
    "freight",
    "misc",
    "miscellaneous",
    "non-merchandise",
    "service",
    "services",
    "shipping",
})

# Risk status priority ordering
RISK_STATUS_PRIORITY: dict[str, int] = {
    "dormant": 0,
    "at_risk": 1,
    "growing": 2,
    "stable": 3,
    "new": 4,
}

# Opportunity severity priority ordering
OPPORTUNITY_SEVERITY_PRIORITY: dict[str, int] = {
    "alert": 0,
    "warning": 1,
    "info": 2,
}

# Period month counts
REVENUE_DIAGNOSIS_PERIOD_MONTHS: dict[str, int] = {
    "1m": 1,
    "3m": 3,
    "6m": 6,
    "12m": 12,
}

CUSTOMER_BUYING_BEHAVIOR_PERIOD_MONTHS: dict[str, int] = {
    "3m": 3,
    "6m": 6,
    "12m": 12,
}
