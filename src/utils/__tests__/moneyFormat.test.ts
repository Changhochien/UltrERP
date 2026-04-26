/**
 * Tests for money formatting utilities (Story 25-5)
 */

import { describe, test, expect } from "vitest";
import {
  formatMoney,
  formatDualMoney,
  formatConversionRate,
  formatExchangeRate,
  validateLineHeaderTotals,
  validateConversionDrift,
  getCurrencyDisplayConfig,
  getCurrencyPrecision,
  roundToCurrencyPrecision,
  parseMoney,
} from "../moneyFormat";

describe("formatMoney", () => {
  test("formats TWD with no decimals", () => {
    expect(formatMoney(1234.56, "TWD")).toBe("NT$1,235");
  });

  test("formats USD with two decimals", () => {
    expect(formatMoney(1234.56, "USD")).toBe("$1,234.56 USD");
  });

  test("formats EUR with symbol and code", () => {
    expect(formatMoney(1000, "EUR")).toBe("€1,000.00 EUR");
  });

  test("formats negative amounts with minus sign", () => {
    expect(formatMoney(-500.5, "USD")).toBe("-$500.50 USD");
  });

  test("handles string input", () => {
    expect(formatMoney("1234.56", "USD")).toBe("$1,234.56 USD");
  });

  test("handles invalid input", () => {
    expect(formatMoney("invalid", "USD")).toBe("USD --");
  });
});

describe("formatConversionRate", () => {
  test("formats rate with default precision", () => {
    expect(formatConversionRate(32.5)).toBe("32.500000");
  });

  test("formats rate with custom precision", () => {
    expect(formatConversionRate(32.5, 2)).toBe("32.50");
  });

  test("handles string input", () => {
    expect(formatConversionRate("32.5678")).toBe("32.567800");
  });

  test("handles invalid input", () => {
    expect(formatConversionRate("invalid")).toBe("--");
  });
});

describe("formatExchangeRate", () => {
  test("formats exchange rate with currency pair", () => {
    expect(formatExchangeRate("USD", "TWD", 32.5)).toBe("1 USD = 32.500000 TWD");
  });
});

describe("getCurrencyDisplayConfig", () => {
  test("returns TWD config", () => {
    const config = getCurrencyDisplayConfig("TWD");
    expect(config.symbol).toBe("NT$");
    expect(config.decimalPlaces).toBe(0);
  });

  test("returns USD config", () => {
    const config = getCurrencyDisplayConfig("USD");
    expect(config.symbol).toBe("$");
    expect(config.decimalPlaces).toBe(2);
  });

  test("returns JPY config with no decimals", () => {
    const config = getCurrencyDisplayConfig("JPY");
    expect(config.symbol).toBe("¥");
    expect(config.decimalPlaces).toBe(0);
  });

  test("handles unknown currency with defaults", () => {
    const config = getCurrencyDisplayConfig("XYZ");
    expect(config.symbol).toBe("XYZ");
    expect(config.decimalPlaces).toBe(2);
    expect(config.showCode).toBe(true);
  });

  test("is case insensitive", () => {
    const config1 = getCurrencyDisplayConfig("usd");
    const config2 = getCurrencyDisplayConfig("USD");
    expect(config1.decimalPlaces).toBe(config2.decimalPlaces);
  });
});

describe("getCurrencyPrecision", () => {
  test("returns TWD precision", () => {
    expect(getCurrencyPrecision("TWD")).toBe(0);
  });

  test("returns USD precision", () => {
    expect(getCurrencyPrecision("USD")).toBe(2);
  });
});

describe("roundToCurrencyPrecision", () => {
  test("rounds TWD to whole numbers", () => {
    expect(roundToCurrencyPrecision(123.7, "TWD")).toBe(124);
    expect(roundToCurrencyPrecision(123.4, "TWD")).toBe(123);
  });

  test("rounds USD to two decimals", () => {
    expect(roundToCurrencyPrecision(123.456, "USD")).toBe(123.46);
    expect(roundToCurrencyPrecision(123.454, "USD")).toBe(123.45);
  });
});

describe("validateLineHeaderTotals", () => {
  test("passes when totals match", () => {
    const result = validateLineHeaderTotals([100, 200, 300], 600);
    expect(result.isValid).toBe(true);
    expect(result.error).toBeUndefined();
  });

  test("fails when totals exceed tolerance", () => {
    const result = validateLineHeaderTotals([100, 200], 350, 0.01);
    expect(result.isValid).toBe(false);
    expect(result.error).toContain("Line-header base total mismatch");
  });

  test("passes within tolerance", () => {
    const result = validateLineHeaderTotals([100, 200, 300], 600.005, 0.01);
    expect(result.isValid).toBe(true);
  });

  test("handles string inputs", () => {
    const result = validateLineHeaderTotals(["100", "200"], "300");
    expect(result.isValid).toBe(true);
  });
});

describe("validateConversionDrift", () => {
  test("passes when computed matches stored", () => {
    const result = validateConversionDrift(1000, 32.5, 32500, 2);
    expect(result.isValid).toBe(true);
  });

  test("fails when drift exceeds tolerance", () => {
    const result = validateConversionDrift(1000, 32.5, 32501, 2, 0.01);
    expect(result.isValid).toBe(false);
    expect(result.error).toContain("Conversion drift detected");
  });

  test("passes within tolerance", () => {
    const result = validateConversionDrift(1000, 32.5, 32500.01, 2, 0.02);
    expect(result.isValid).toBe(true);
  });
});

describe("parseMoney", () => {
  test("parses simple number", () => {
    expect(parseMoney("1234.56")).toBe(1234.56);
  });

  test("parses with commas", () => {
    expect(parseMoney("1,234.56")).toBe(1234.56);
  });

  test("parses with currency symbol", () => {
    expect(parseMoney("NT$1,234")).toBe(1234);
  });

  test("parses negative", () => {
    expect(parseMoney("-500")).toBe(-500);
  });

  test("returns 0 for invalid input", () => {
    expect(parseMoney("invalid")).toBe(0);
  });
});

describe("formatDualMoney", () => {
  test("formats dual money amounts", () => {
    const result = formatDualMoney(
      1000,
      "USD",
      32500,
      "TWD",
      "32.5",
      "2026-04-26",
      "manual"
    );

    expect(result.transaction).toBe("$1,000.00 USD");
    expect(result.base).toBe("NT$32,500");
    expect(result.rate).toBe("1 USD = 32.5 TWD");
    expect(result.effectiveDate).toBe("2026-04-26");
    expect(result.rateSource).toBe("manual");
  });
});
