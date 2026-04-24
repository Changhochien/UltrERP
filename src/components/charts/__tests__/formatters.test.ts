/**
 * Tests for chart formatters.
 */

import { describe, expect, it } from "vitest";
import {
  formatChartCurrency,
  formatChartQuantity,
  formatChartQuantityCompact,
  formatChartMonth,
  formatChartPercent,
  formatCurrencyAxis,
} from "../formatters";

describe("formatChartCurrency", () => {
  it("formats TWD currency correctly", () => {
    const result = formatChartCurrency(1234.56, "zh-TW", "TWD");
    expect(result).toContain("1,234.56");
  });

  it("formats small values correctly", () => {
    const result = formatChartCurrency(99.99, "en-US", "TWD");
    expect(result).toContain("99.99");
  });
});

describe("formatChartQuantity", () => {
  it("formats integer quantities correctly", () => {
    const result = formatChartQuantity(1500, "en-US");
    expect(result).toBe("1,500");
  });

  it("respects maximumFractionDigits option", () => {
    const result = formatChartQuantity(123.456, "en-US", { maximumFractionDigits: 1 });
    expect(result).toBe("123.5");
  });
});

describe("formatChartQuantityCompact", () => {
  it("formats thousands as K", () => {
    const result = formatChartQuantityCompact(1500, "en-US");
    expect(result).toBe("1.5K");
  });

  it("formats millions as M", () => {
    const result = formatChartQuantityCompact(2500000, "en-US");
    expect(result).toBe("2.5M");
  });

  it("formats small values as-is", () => {
    const result = formatChartQuantityCompact(500, "en-US");
    expect(result).toBe("500");
  });
});

describe("formatChartMonth", () => {
  it("formats YYYY-MM to localized month", () => {
    const result = formatChartMonth("2025-03", "en-US");
    expect(result).toContain("2025");
    expect(result).toContain("Mar");
  });
});

describe("formatChartPercent", () => {
  it("formats percentage correctly", () => {
    const result = formatChartPercent(25.5, "en-US");
    expect(result).toContain("25.5");
  });
});

describe("formatCurrencyAxis", () => {
  it("formats millions as M", () => {
    const result = formatCurrencyAxis(2500000, "en-US", "NT$");
    expect(result).toContain("3M"); // 2.5 rounds to 3
  });

  it("formats thousands as K", () => {
    const result = formatCurrencyAxis(15000, "en-US", "NT$");
    expect(result).toContain("15K");
  });
});
