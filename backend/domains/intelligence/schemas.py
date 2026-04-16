"""Schemas for intelligence domain responses."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CategoryRevenue(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    revenue: Decimal
    order_count: int
    revenue_pct_of_total: Decimal


class ProductPurchase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: uuid.UUID
    product_name: str
    category: str | None
    order_count: int
    total_quantity: Decimal
    total_revenue: Decimal


class TopProductByRevenue(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: uuid.UUID
    product_name: str
    revenue: Decimal


class CategoryTrend(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    current_period_revenue: Decimal
    prior_period_revenue: Decimal
    revenue_delta_pct: float | None
    current_period_orders: int
    prior_period_orders: int
    order_delta_pct: float | None
    customer_count: int
    prior_customer_count: int
    new_customer_count: int
    churned_customer_count: int
    top_products: list[TopProductByRevenue]
    trend: Literal["growing", "declining", "stable"]
    trend_context: Literal["newly_active", "insufficient_history"] | None = None
    activity_basis: Literal["confirmed_or_later_orders"]


class CategoryTrends(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period: Literal["last_30d", "last_90d", "last_12m"]
    trends: list[CategoryTrend]
    generated_at: datetime


class CustomerRiskSignal(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: uuid.UUID
    company_name: str
    status: Literal["growing", "at_risk", "dormant", "new", "stable"]
    revenue_current: Decimal
    revenue_prior: Decimal
    revenue_delta_pct: float | None
    order_count_current: int
    order_count_prior: int
    avg_order_value_current: Decimal
    avg_order_value_prior: Decimal
    days_since_last_order: int | None
    reason_codes: list[str]
    confidence: Literal["high", "medium", "low"]
    signals: list[str]
    products_expanded_into: list[str]
    products_contracted_from: list[str]
    last_order_date: date | None
    first_order_date: date | None


class CustomerRiskSignals(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customers: list[CustomerRiskSignal]
    total: int
    status_filter: Literal["all", "growing", "at_risk", "dormant", "new", "stable"]
    limit: int
    generated_at: datetime


class ProspectScoreComponents(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    frequency_similarity: float
    breadth_similarity: float
    adjacent_category_support: float
    recency_factor: float


class ProspectFit(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: uuid.UUID
    company_name: str
    total_revenue: Decimal
    category_count: int
    avg_order_value: Decimal
    last_order_date: date | None
    affinity_score: float
    score_components: ProspectScoreComponents
    reason_codes: list[str]
    confidence: Literal["high", "medium", "low"]
    reason: str
    tags: list[str]


class ProspectGaps(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    target_category: str
    target_category_revenue: Decimal
    existing_buyers_count: int
    prospects_count: int
    prospects: list[ProspectFit]
    available_categories: list[str]
    generated_at: datetime


class OpportunitySignal(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    signal_type: Literal["category_growth", "concentration_risk"]
    severity: Literal["info", "warning", "alert"]
    headline: str
    detail: str
    affected_customer_count: int
    revenue_impact: Decimal
    recommended_action: str
    support_counts: dict[str, int] | None = None
    source_period: Literal["last_30d", "last_90d", "last_12m"]


class MarketOpportunities(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period: Literal["last_30d", "last_90d", "last_12m"]
    generated_at: datetime
    signals: list[OpportunitySignal]
    deferred_signal_types: list[str]


class AffinityPair(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_a_id: uuid.UUID
    product_b_id: uuid.UUID
    product_a_name: str
    product_b_name: str
    shared_customer_count: int
    customer_count_a: int
    customer_count_b: int
    shared_order_count: int | None = None
    overlap_pct: float
    affinity_score: float
    pitch_hint: str


class ProductAffinityMap(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pairs: list[AffinityPair]
    total: int
    min_shared: int
    limit: int
    computed_at: datetime


class CustomerProductProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: uuid.UUID
    company_name: str
    total_revenue_12m: Decimal
    order_count_12m: int
    order_count_3m: int
    order_count_6m: int
    order_count_prior_12m: int
    order_count_prior_3m: int
    frequency_trend: Literal["increasing", "declining", "stable"]
    avg_order_value: Decimal
    avg_order_value_prior: Decimal
    aov_trend: Literal["increasing", "declining", "stable"]
    top_categories: list[CategoryRevenue]
    top_products: list[ProductPurchase]
    last_order_date: date | None
    days_since_last_order: int | None
    is_dormant: bool
    new_categories: list[str]
    confidence: Literal["high", "medium", "low"]
    activity_basis: Literal["confirmed_or_later_orders"]


class RevenueDiagnosisWindow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start_month: date
    end_month: date


class RevenueDiagnosisSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    current_revenue: Decimal
    prior_revenue: Decimal
    revenue_delta: Decimal
    revenue_delta_pct: float | None


class RevenueDiagnosisComponents(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    price_effect_total: Decimal
    volume_effect_total: Decimal
    mix_effect_total: Decimal


class RevenueDiagnosisDriver(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: uuid.UUID
    product_name: str
    product_category_snapshot: str
    current_quantity: Decimal
    prior_quantity: Decimal
    current_revenue: Decimal
    prior_revenue: Decimal
    current_order_count: int
    prior_order_count: int
    current_avg_unit_price: Decimal
    prior_avg_unit_price: Decimal
    price_effect: Decimal
    volume_effect: Decimal
    mix_effect: Decimal
    revenue_delta: Decimal
    revenue_delta_pct: float | None
    data_basis: Literal["aggregate_only", "aggregate_plus_live_current_month"]
    window_is_partial: bool


class RevenueDiagnosis(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period: Literal["1m", "3m", "6m", "12m"]
    anchor_month: date
    current_window: RevenueDiagnosisWindow
    prior_window: RevenueDiagnosisWindow
    computed_at: datetime
    summary: RevenueDiagnosisSummary
    components: RevenueDiagnosisComponents
    drivers: list[RevenueDiagnosisDriver]
    data_basis: Literal["aggregate_only", "aggregate_plus_live_current_month"]
    window_is_partial: bool


ProductPerformanceDataBasis = Literal["aggregate_only", "aggregate_plus_live_current_month"]
ProductLifecycleStage = Literal["new", "end_of_life", "declining", "growing", "mature", "stable"]
CustomerBuyingBehaviorPeriod = Literal["3m", "6m", "12m"]
CustomerBuyingBehaviorDataBasis = Literal["transactional_fallback"]
CustomerBuyingBehaviorCustomerType = Literal["dealer", "end_user", "unknown", "all"]


class ProductPerformanceWindow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start_month: date
    end_month: date


class ProductPerformancePeriodMetrics(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    revenue: Decimal
    quantity: Decimal
    order_count: int
    avg_unit_price: Decimal


class ProductPerformanceRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: uuid.UUID
    product_name: str
    product_category_snapshot: str
    lifecycle_stage: ProductLifecycleStage
    stage_reasons: list[str]
    first_sale_month: date
    last_sale_month: date
    months_on_sale: int
    current_period: ProductPerformancePeriodMetrics
    prior_period: ProductPerformancePeriodMetrics
    peak_month_revenue: Decimal
    revenue_delta_pct: float | None
    data_basis: ProductPerformanceDataBasis
    window_is_partial: bool


class ProductPerformance(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    current_window: ProductPerformanceWindow
    prior_window: ProductPerformanceWindow
    computed_at: datetime
    products: list[ProductPerformanceRow]
    total: int
    data_basis: ProductPerformanceDataBasis
    window_is_partial: bool


class CustomerBuyingBehaviorWindow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start_month: date
    end_month: date


class CustomerBuyingBehaviorCategory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    revenue: Decimal
    order_count: int
    customer_count: int
    revenue_share: Decimal


class CustomerBuyingBehaviorCrossSell(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    anchor_category: str
    recommended_category: str
    anchor_customer_count: int
    shared_customer_count: int
    outside_segment_anchor_customer_count: int
    outside_segment_shared_customer_count: int
    segment_penetration: Decimal
    outside_segment_penetration: Decimal
    lift_score: Decimal | None


class CustomerBuyingBehaviorPattern(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    month_start: date
    revenue: Decimal
    order_count: int
    customer_count: int


class CustomerBuyingBehavior(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_type: CustomerBuyingBehaviorCustomerType
    period: CustomerBuyingBehaviorPeriod
    window: CustomerBuyingBehaviorWindow
    computed_at: datetime
    customer_count: int
    avg_revenue_per_customer: Decimal
    avg_order_count_per_customer: Decimal
    avg_categories_per_customer: Decimal
    top_categories: list[CustomerBuyingBehaviorCategory]
    cross_sell_opportunities: list[CustomerBuyingBehaviorCrossSell]
    buying_patterns: list[CustomerBuyingBehaviorPattern]
    data_basis: CustomerBuyingBehaviorDataBasis
    window_is_partial: bool
