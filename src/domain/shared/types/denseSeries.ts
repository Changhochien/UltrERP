/**
 * Shared types for dense time-series data.
 * 
 * These types are used across inventory and dashboard domains
 * for explorer-tier chart data.
 */

/** Single point in a dense time-series response. */
export interface DenseSeriesPoint {
  bucket_start: string;
  bucket_label: string;
  value: number;
  is_zero_filled: boolean;
  period_status: "closed" | "partial";
  source: "aggregate" | "live" | "zero-filled";
}

/** Range metadata for dense time-series responses. */
export interface DenseSeriesRange {
  requested_start: string;
  requested_end: string;
  available_start: string | null;
  available_end: string | null;
  default_visible_start: string;
  default_visible_end: string;
  bucket: "day" | "week" | "month";
  timezone: string;
}
