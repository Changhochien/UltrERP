/**
 * Locale-aware formatting helpers for charts.
 * 
 * These are pure functions that accept locale as a parameter.
 * They do NOT call useTranslation() directly.
 */

/**
 * Format a currency value for chart display.
 */
export function formatChartCurrency(
  value: number,
  locale: string,
  currency: string = "TWD",
  options: Partial<Intl.NumberFormatOptions> = {},
): string {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    minimumFractionDigits: options.minimumFractionDigits ?? 2,
    maximumFractionDigits: options.maximumFractionDigits ?? 2,
    ...options,
  }).format(value);
}

/**
 * Format a quantity value for chart display.
 */
export function formatChartQuantity(
  value: number,
  locale: string,
  options: Partial<Intl.NumberFormatOptions> = {}
): string {
  return new Intl.NumberFormat(locale, {
    notation: "standard",
    maximumFractionDigits: options.maximumFractionDigits ?? 0,
    ...options,
  }).format(value);
}

/**
 * Format a large quantity with K/M/B suffixes.
 */
export function formatChartQuantityCompact(
  value: number,
  locale: string
): string {
  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }
  return formatChartQuantity(value, locale);
}

/**
 * Format a date value for chart axis/tooltip display.
 */
export function formatChartDate(
  value: string | Date,
  locale: string,
  options: Intl.DateTimeFormatOptions = {}
): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return date.toLocaleDateString(locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
    ...options,
  });
}

/**
 * Format a date for axis labels (compact format).
 */
export function formatChartDateCompact(
  value: string | Date,
  locale: string
): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return date.toLocaleDateString(locale, {
    month: "short",
    day: "numeric",
  });
}

/**
 * Format a month label (YYYY-MM format).
 */
export function formatChartMonth(
  value: string,
  locale: string
): string {
  const [year, month] = value.split("-");
  const date = new Date(parseInt(year), parseInt(month) - 1, 1);
  return date.toLocaleDateString(locale, {
    year: "numeric",
    month: "short",
  });
}

/**
 * Format a percentage value for chart display.
 */
export function formatChartPercent(
  value: number,
  locale: string,
  decimals: number = 1
): string {
  return new Intl.NumberFormat(locale, {
    style: "percent",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value / 100);
}

/**
 * Format a chart axis tick for currency (e.g., "NT$ 10k").
 */
export function formatCurrencyAxis(
  value: number,
  _locale: string,
  currency: string = "NT$"
): string {
  if (value >= 1_000_000) {
    return `${currency} ${(value / 1_000_000).toFixed(0)}M`;
  }
  if (value >= 1_000) {
    return `${currency} ${(value / 1_000).toFixed(0)}K`;
  }
  return `${currency} ${value.toFixed(0)}`;
}
