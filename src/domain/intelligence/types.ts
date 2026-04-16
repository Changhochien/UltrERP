export interface CategoryRevenue {
  category: string;
  revenue: string;
  order_count: number;
  revenue_pct_of_total: string;
}

export interface ProductPurchase {
  product_id: string;
  product_name: string;
  category: string | null;
  order_count: number;
  total_quantity: string;
  total_revenue: string;
}

export interface AffinityPair {
  product_a_id: string;
  product_b_id: string;
  product_a_name: string;
  product_b_name: string;
  shared_customer_count: number;
  customer_count_a: number;
  customer_count_b: number;
  shared_order_count: number | null;
  overlap_pct: number;
  affinity_score: number;
  pitch_hint: string;
}

export interface ProductAffinityMap {
  pairs: AffinityPair[];
  total: number;
  min_shared: number;
  limit: number;
  computed_at: string;
}

export interface TopProductByRevenue {
  product_id: string;
  product_name: string;
  revenue: string;
}

export interface CategoryTrend {
  category: string;
  current_period_revenue: string;
  prior_period_revenue: string;
  revenue_delta_pct: number | null;
  current_period_orders: number;
  prior_period_orders: number;
  order_delta_pct: number | null;
  customer_count: number;
  prior_customer_count: number;
  new_customer_count: number;
  churned_customer_count: number;
  top_products: TopProductByRevenue[];
  trend: "growing" | "declining" | "stable";
  trend_context?: "newly_active" | "insufficient_history" | null;
  activity_basis: "confirmed_or_later_orders";
}

export interface CategoryTrends {
  period: "last_30d" | "last_90d" | "last_12m";
  trends: CategoryTrend[];
  generated_at: string;
}

export interface CustomerRiskSignal {
  customer_id: string;
  company_name: string;
  status: "growing" | "at_risk" | "dormant" | "new" | "stable";
  revenue_current: string;
  revenue_prior: string;
  revenue_delta_pct: number | null;
  order_count_current: number;
  order_count_prior: number;
  avg_order_value_current: string;
  avg_order_value_prior: string;
  days_since_last_order: number | null;
  reason_codes: string[];
  confidence: "high" | "medium" | "low";
  signals: string[];
  products_expanded_into: string[];
  products_contracted_from: string[];
  last_order_date: string | null;
  first_order_date: string | null;
}

export interface CustomerRiskSignals {
  customers: CustomerRiskSignal[];
  total: number;
  status_filter: "all" | "growing" | "at_risk" | "dormant" | "new" | "stable";
  limit: number;
  generated_at: string;
}

export interface ProspectScoreComponents {
  frequency_similarity: number;
  breadth_similarity: number;
  adjacent_category_support: number;
  recency_factor: number;
}

export type ProspectGapCustomerFilter = "dealer" | "end_user" | "unknown" | "all";

export interface ProspectFit {
  customer_id: string;
  company_name: string;
  total_revenue: string;
  category_count: number;
  avg_order_value: string;
  last_order_date: string | null;
  affinity_score: number;
  score_components: ProspectScoreComponents;
  reason_codes: string[];
  confidence: "high" | "medium" | "low";
  reason: string;
  tags: string[];
}

export interface ProspectGaps {
  target_category: string;
  target_category_revenue: string;
  existing_buyers_count: number;
  prospects_count: number;
  prospects: ProspectFit[];
  available_categories: string[];
  generated_at: string;
}

export interface OpportunitySignal {
  signal_type: "category_growth" | "concentration_risk";
  severity: "info" | "warning" | "alert";
  headline: string;
  detail: string;
  affected_customer_count: number;
  revenue_impact: string;
  recommended_action: string;
  support_counts?: Record<string, number> | null;
  source_period: "last_30d" | "last_90d" | "last_12m";
}

export interface MarketOpportunities {
  period: "last_30d" | "last_90d" | "last_12m";
  generated_at: string;
  signals: OpportunitySignal[];
  deferred_signal_types: string[];
}

export type RevenueDiagnosisPeriod = "1m" | "3m" | "6m" | "12m";
export type RevenueDiagnosisDataBasis = "aggregate_only" | "aggregate_plus_live_current_month";

export interface RevenueDiagnosisWindow {
  start_month: string;
  end_month: string;
}

export interface RevenueDiagnosisSummary {
  current_revenue: string;
  prior_revenue: string;
  revenue_delta: string;
  revenue_delta_pct: number | null;
}

export interface RevenueDiagnosisComponents {
  price_effect_total: string;
  volume_effect_total: string;
  mix_effect_total: string;
}

export interface RevenueDiagnosisDriver {
  product_id: string;
  product_name: string;
  product_category_snapshot: string;
  current_quantity: string;
  prior_quantity: string;
  current_revenue: string;
  prior_revenue: string;
  current_order_count: number;
  prior_order_count: number;
  current_avg_unit_price: string;
  prior_avg_unit_price: string;
  price_effect: string;
  volume_effect: string;
  mix_effect: string;
  revenue_delta: string;
  revenue_delta_pct: number | null;
  data_basis: RevenueDiagnosisDataBasis;
  window_is_partial: boolean;
}

export interface RevenueDiagnosis {
  period: RevenueDiagnosisPeriod;
  anchor_month: string;
  current_window: RevenueDiagnosisWindow;
  prior_window: RevenueDiagnosisWindow;
  computed_at: string;
  summary: RevenueDiagnosisSummary;
  components: RevenueDiagnosisComponents;
  drivers: RevenueDiagnosisDriver[];
  data_basis: RevenueDiagnosisDataBasis;
  window_is_partial: boolean;
}

export type ProductPerformanceDataBasis = "aggregate_only" | "aggregate_plus_live_current_month";
export type ProductLifecycleStage = "new" | "end_of_life" | "declining" | "growing" | "mature" | "stable";

export interface ProductPerformanceWindow {
  start_month: string;
  end_month: string;
}

export interface ProductPerformancePeriodMetrics {
  revenue: string;
  quantity: string;
  order_count: number;
  avg_unit_price: string;
}

export interface ProductPerformanceRow {
  product_id: string;
  product_name: string;
  product_category_snapshot: string;
  lifecycle_stage: ProductLifecycleStage;
  stage_reasons: string[];
  first_sale_month: string;
  last_sale_month: string;
  months_on_sale: number;
  current_period: ProductPerformancePeriodMetrics;
  prior_period: ProductPerformancePeriodMetrics;
  peak_month_revenue: string;
  revenue_delta_pct: number | null;
  data_basis: ProductPerformanceDataBasis;
  window_is_partial: boolean;
}

export interface ProductPerformance {
  current_window: ProductPerformanceWindow;
  prior_window: ProductPerformanceWindow;
  computed_at: string;
  products: ProductPerformanceRow[];
  total: number;
  data_basis: ProductPerformanceDataBasis;
  window_is_partial: boolean;
}

export interface CustomerProductProfile {
  customer_id: string;
  company_name: string;
  total_revenue_12m: string;
  order_count_12m: number;
  order_count_3m: number;
  order_count_6m: number;
  order_count_prior_12m: number;
  order_count_prior_3m: number;
  frequency_trend: "increasing" | "declining" | "stable";
  avg_order_value: string;
  avg_order_value_prior: string;
  aov_trend: "increasing" | "declining" | "stable";
  top_categories: CategoryRevenue[];
  top_products: ProductPurchase[];
  last_order_date: string | null;
  days_since_last_order: number | null;
  is_dormant: boolean;
  new_categories: string[];
  confidence: "high" | "medium" | "low";
  activity_basis: "confirmed_or_later_orders";
}