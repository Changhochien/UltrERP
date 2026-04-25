"""Intelligence services package.

This package contains feature-scoped service modules extracted from the
main intelligence service monolith. The service.py facade maintains backward
compatibility while allowing independent evolution of feature modules.
"""

# The services package will contain:
# - shared/          # Shared pure helpers and constants (no feature dependencies)
# - affinity.py      # Product affinity analysis
# - customer_profile.py  # Customer product profile
# - risk_signals.py     # Customer risk signals
# - prospect_gaps.py    # Prospect gap analysis
# - buying_behavior.py  # Customer buying behavior
# - category_trends.py  # Category trend analysis
# - market_opportunities.py  # Market opportunity signals
# - revenue_diagnosis.py     # Revenue diagnosis
# - product_performance.py   # Product performance
