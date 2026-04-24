/**
 * rechartsRangeBridge - Bridge layer for recharts to use explorer range state.
 * 
 * Allows existing recharts charts to adopt the shared visible-range model
 * without being ported to @visx in the same PR.
 */

import type { ExplorerRange } from "./useExplorerRange";

/**
 * Filter recharts data based on visible range.
 * 
 * Use this helper when migrating recharts charts to explorer kit:
 * ```tsx
 * const filteredData = filterDataByRange(rawData, visibleRange);
 * ```
 */
export function filterDataByRange<T extends { date: string }>(
  data: T[],
  visibleRange: ExplorerRange
): T[] {
  if (!data.length) return [];

  const start = new Date(visibleRange.start).getTime();
  const end = new Date(visibleRange.end).getTime();

  return data.filter((item) => {
    const itemDate = new Date(item.date).getTime();
    return itemDate >= start && itemDate <= end;
  });
}

/**
 * Calculate brush boundaries for recharts Brush component.
 * 
 * Returns start/end indices into the data array.
 */
export function calculateBrushIndices(
  dataLength: number,
  visibleRange: ExplorerRange,
  dataAccessor?: (index: number) => Date
): { startIndex?: number; endIndex?: number } {
  if (!dataLength) return {};

  const start = new Date(visibleRange.start).getTime();
  const end = new Date(visibleRange.end).getTime();

  // Simple binary search for indices
  let startIndex: number | undefined;
  let endIndex: number | undefined;

  for (let i = 0; i < dataLength; i++) {
    const date = dataAccessor ? dataAccessor(i) : new Date(`2025-01-01`); // Fallback
    const t = date.getTime();

    if (t >= start && startIndex === undefined) {
      startIndex = Math.max(0, i - 1);
    }
    if (t <= end) {
      endIndex = i;
    }
  }

  return { startIndex, endIndex };
}

/**
 * Parse date string for recharts compatibility.
 * 
 * Handles both YYYY-MM-DD and YYYY-MM formats.
 */
export function parseChartDate(value: string): Date {
  // Handle monthly data (YYYY-MM format)
  if (value.length === 7) {
    return new Date(value + "-01");
  }
  return new Date(value);
}

/**
 * Format date for recharts axis/tick.
 */
export function formatChartDateForAxis(
  value: string | Date,
  format: "short" | "medium" | "full" = "short"
): string {
  const date = typeof value === "string" ? parseChartDate(value) : value;

  switch (format) {
    case "short":
      return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    case "medium":
      return date.toLocaleDateString(undefined, { month: "short", year: "2-digit" });
    case "full":
      return date.toLocaleDateString(undefined, { month: "short", year: "numeric" });
  }
}
