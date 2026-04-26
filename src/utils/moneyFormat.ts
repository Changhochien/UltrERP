/**
 * FX Rounding, Display, and Audit Safeguards (Story 25-5)
 *
 * Shared money formatting utilities for consistent currency display across
 * all commercial documents.
 */

/**
 * Currency display configuration
 */
interface CurrencyDisplayConfig {
  symbol: string;
  code: string;
  decimalPlaces: number;
  showCode: boolean;
  showSymbol: boolean;
}

/**
 * Default currency display configurations by code
 */
export const CURRENCY_DISPLAY_CONFIG: Record<string, CurrencyDisplayConfig> = {
  TWD: { symbol: "NT$", code: "TWD", decimalPlaces: 0, showCode: false, showSymbol: true },
  USD: { symbol: "$", code: "USD", decimalPlaces: 2, showCode: true, showSymbol: true },
  EUR: { symbol: "€", code: "EUR", decimalPlaces: 2, showCode: true, showSymbol: true },
  JPY: { symbol: "¥", code: "JPY", decimalPlaces: 0, showCode: false, showSymbol: true },
  GBP: { symbol: "£", code: "GBP", decimalPlaces: 2, showCode: true, showSymbol: true },
  CNY: { symbol: "¥", code: "CNY", decimalPlaces: 2, showCode: true, showSymbol: true },
  HKD: { symbol: "HK$", code: "HKD", decimalPlaces: 2, showCode: true, showSymbol: true },
  AUD: { symbol: "A$", code: "AUD", decimalPlaces: 2, showCode: true, showSymbol: true },
  CAD: { symbol: "C$", code: "CAD", decimalPlaces: 2, showCode: true, showSymbol: true },
  SGD: { symbol: "S$", code: "SGD", decimalPlaces: 2, showCode: true, showSymbol: true },
};

/**
 * Get currency display configuration
 */
export function getCurrencyDisplayConfig(currencyCode: string): CurrencyDisplayConfig {
  return CURRENCY_DISPLAY_CONFIG[currencyCode.toUpperCase()] ?? {
    symbol: currencyCode,
    code: currencyCode.toUpperCase(),
    decimalPlaces: 2,
    showCode: true,
    showSymbol: false,
  };
}

/**
 * Format a number with thousand separators
 */
function formatNumber(value: number, decimalPlaces: number): string {
  const fixed = value.toFixed(decimalPlaces);
  const parts = fixed.split(".");
  const integerPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  if (parts.length === 1 || decimalPlaces === 0) {
    return integerPart;
  }
  return `${integerPart}.${parts[1]}`;
}

function toFiniteNumber(value: number | string): number | null {
  const parsed = typeof value === "string" ? parseFloat(value) : value;
  return Number.isFinite(parsed) ? parsed : null;
}

/**
 * Format a money amount for display
 */
export function formatMoney(
  amount: number | string,
  currencyCode: string,
  options?: Partial<CurrencyDisplayConfig>
): string {
  const numAmount = toFiniteNumber(amount);
  if (numAmount === null) {
    return `${currencyCode} --`;
  }

  const config = { ...getCurrencyDisplayConfig(currencyCode), ...options };
  const formattedNumber = formatNumber(Math.abs(numAmount), config.decimalPlaces);
  const prefix = numAmount < 0 ? "-" : "";

  if (config.showSymbol && config.showCode) {
    return `${prefix}${config.symbol}${formattedNumber} ${config.code}`;
  } else if (config.showSymbol) {
    return `${prefix}${config.symbol}${formattedNumber}`;
  } else if (config.showCode) {
    return `${prefix}${formattedNumber} ${config.code}`;
  }
  return `${prefix}${formattedNumber}`;
}

/**
 * Format a dual currency amount (transaction + base)
 */
export interface DualAmountDisplay {
  transaction: string;
  base: string;
  rate: string;
  effectiveDate: string;
  rateSource: string;
}

/**
 * Format money with both transaction and base currency amounts
 */
export function formatDualMoney(
  transactionAmount: number | string,
  transactionCurrency: string,
  baseAmount: number | string,
  baseCurrency: string,
  conversionRate?: string,
  effectiveDate?: string,
  rateSource?: string
): DualAmountDisplay {
  return {
    transaction: formatMoney(transactionAmount, transactionCurrency),
    base: formatMoney(baseAmount, baseCurrency),
    rate: conversionRate ? `1 ${transactionCurrency} = ${conversionRate} ${baseCurrency}` : "",
    effectiveDate: effectiveDate ?? "",
    rateSource: rateSource ?? "",
  };
}

/**
 * Format conversion rate for display
 */
export function formatConversionRate(rate: string | number, precision: number = 6): string {
  const numRate = toFiniteNumber(rate);
  if (numRate === null) return "--";
  return numRate.toFixed(precision);
}

/**
 * Format exchange rate with currency pair
 */
export function formatExchangeRate(
  sourceCurrency: string,
  targetCurrency: string,
  rate: string | number
): string {
  const formattedRate = formatConversionRate(rate);
  return `1 ${sourceCurrency} = ${formattedRate} ${targetCurrency}`;
}

/**
 * Validation result for FX calculations
 */
export interface FXValidationResult {
  isValid: boolean;
  error?: string;
  details?: {
    expectedBaseTotal: string;
    actualBaseTotal: string;
    tolerance: string;
    difference: string;
  };
}

/**
 * Validate that line totals match header totals after conversion
 */
export function validateLineHeaderTotals(
  lineBaseTotals: (number | string)[],
  headerBaseTotal: number | string,
  tolerance: number = 0.01
): FXValidationResult {
  const headerNum = toFiniteNumber(headerBaseTotal);
  if (headerNum === null) {
    return {
      isValid: false,
      error: "Invalid header total provided for line/header validation",
    };
  }
  const sumOfLines = lineBaseTotals.reduce<number>((sum, val) => {
    const num = toFiniteNumber(val);
    return sum + (num ?? 0);
  }, 0);

  const difference = Math.abs(headerNum - sumOfLines);

  if (difference > tolerance) {
    return {
      isValid: false,
      error: `Line-header base total mismatch: lines sum to ${sumOfLines.toFixed(2)}, header shows ${headerNum.toFixed(2)}, diff=${difference.toFixed(2)} exceeds tolerance ${tolerance}`,
      details: {
        expectedBaseTotal: headerNum.toFixed(2),
        actualBaseTotal: sumOfLines.toFixed(2),
        tolerance: tolerance.toFixed(2),
        difference: difference.toFixed(2),
      },
    };
  }

  return { isValid: true };
}

/**
 * Validate conversion drift between stored and computed base amounts
 */
export function validateConversionDrift(
  originalTotal: number | string,
  conversionRate: number | string,
  storedBaseTotal: number | string,
  targetPrecision: number = 2,
  tolerance: number = 0.02
): FXValidationResult {
  const origNum = toFiniteNumber(originalTotal);
  const rateNum = toFiniteNumber(conversionRate);
  const storedNum = toFiniteNumber(storedBaseTotal);

  if (origNum === null || rateNum === null || storedNum === null) {
    return {
      isValid: false,
      error: "Invalid numeric values provided for conversion validation",
    };
  }

  const computedBaseTotal = origNum * rateNum;
  const roundedComputed = parseFloat(computedBaseTotal.toFixed(targetPrecision));
  const difference = Math.abs(roundedComputed - storedNum);

  if (difference > tolerance) {
    return {
      isValid: false,
      error: `Conversion drift detected: computed=${roundedComputed.toFixed(targetPrecision)}, stored=${storedNum.toFixed(targetPrecision)}, diff=${difference.toFixed(targetPrecision)} exceeds tolerance ${tolerance}`,
      details: {
        expectedBaseTotal: roundedComputed.toFixed(targetPrecision),
        actualBaseTotal: storedNum.toFixed(targetPrecision),
        tolerance: tolerance.toFixed(2),
        difference: difference.toFixed(targetPrecision),
      },
    };
  }

  return { isValid: true };
}

/**
 * Format audit details for FX display
 */
export interface FXAuditDetails {
  currencyCode: string;
  baseCurrency: string;
  conversionRate: string;
  effectiveDate: string;
  rateSource: string;
  transactionAmount: string;
  baseAmount: string;
}

/**
 * Create audit details object from document data
 */
export function createFXAuditDetails(
  currencyCode: string,
  baseCurrency: string,
  conversionRate: string | number,
  effectiveDate: string,
  rateSource: string,
  transactionAmount: number | string,
  baseAmount: number | string
): FXAuditDetails {
  return {
    currencyCode,
    baseCurrency,
    conversionRate: formatConversionRate(conversionRate),
    effectiveDate,
    rateSource,
    transactionAmount: formatMoney(transactionAmount, currencyCode),
    baseAmount: formatMoney(baseAmount, baseCurrency),
  };
}

/**
 * Parse money string back to number
 */
export function parseMoney(value: string): number {
  // Remove currency symbols, spaces, and commas
  const cleaned = value.replace(/[^0-9.-]/g, "");
  const parsed = parseFloat(cleaned);
  return isNaN(parsed) ? 0 : parsed;
}

/**
 * Get precision for a currency code
 */
export function getCurrencyPrecision(currencyCode: string): number {
  const config = getCurrencyDisplayConfig(currencyCode);
  return config.decimalPlaces;
}

/**
 * Round amount to currency precision
 */
export function roundToCurrencyPrecision(amount: number, currencyCode: string): number {
  const precision = getCurrencyPrecision(currencyCode);
  const factor = Math.pow(10, precision);
  return Math.round(amount * factor) / factor;
}
