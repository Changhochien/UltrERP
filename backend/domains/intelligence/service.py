"""Compatibility facade for intelligence domain analytics."""

from __future__ import annotations

from .services.affinity import get_product_affinity_map
from .services.buying_behavior import get_customer_buying_behavior
from .services.category_trends import get_category_trends
from .services.customer_profile import build_empty_customer_product_profile, get_customer_product_profile
from .services.market_opportunities import get_market_opportunities
from .services.product_performance import get_product_performance
from .services.prospect_gaps import get_prospect_gaps
from .services.revenue_diagnosis import get_revenue_diagnosis
from .services.risk_signals import get_customer_risk_signals

__all__ = [
    "build_empty_customer_product_profile",
    "get_category_trends",
    "get_customer_buying_behavior",
    "get_customer_product_profile",
    "get_customer_risk_signals",
    "get_market_opportunities",
    "get_product_affinity_map",
    "get_product_performance",
    "get_prospect_gaps",
    "get_revenue_diagnosis",
]
