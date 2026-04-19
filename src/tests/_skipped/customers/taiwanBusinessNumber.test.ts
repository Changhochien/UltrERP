/**
 * Tests for Taiwan business number (統一編號) checksum validation.
 *
 * Fixtures mirror the backend test suite in
 * `backend/tests/domains/customers/test_business_number_validation.py`
 * so both runtimes stay aligned on the same official acceptance rule.
 *
 * The test set explicitly covers the rule drift between older repo shorthand
 * (divisible-by-10 / "MOD11") and the current official guidance (divisible-by-5)
 * so regressions to the stale rule are caught.
 */

import { describe, expect, it } from "vitest";

import { validateTaiwanBusinessNumber } from "../../lib/validation/taiwanBusinessNumber";

// ── Shared fixtures — mirrored in backend tests ──────────────────────────

/** Standard direct-pass official example (sum divisible by both 5 and 10) */
const VALID_STANDARD = "04595257";

/** Seventh-digit special-case pass (sum % 5 != 0, but (sum+1) % 5 == 0, d7==7) */
const VALID_SEVENTH_DIGIT_SPECIAL = "19312376";

/**
 * Expanded-allocation fixture: sum=25, divisible by 5 but NOT by 10.
 * Passes the current official rule but would FAIL a stale mod-10 check.
 */
const VALID_EXPANDED_ALLOCATION = "55555555";

/** Invalid checksum mutation of VALID_STANDARD (last digit changed 7→8) */
const INVALID_CHECKSUM_MUTATION = "04595258";

/** Non-8-digit format failure */
const INVALID_FORMAT_SHORT = "0459525";
const INVALID_FORMAT_LONG = "045952570";

// ── Valid cases ──────────────────────────────────────────────────────────

describe("valid business numbers", () => {
  it("accepts a standard official example", () => {
    const result = validateTaiwanBusinessNumber(VALID_STANDARD);
    expect(result).toEqual({ valid: true });
  });

  it("accepts the seventh-digit special case", () => {
    const result = validateTaiwanBusinessNumber(VALID_SEVENTH_DIGIT_SPECIAL);
    expect(result).toEqual({ valid: true });
  });

  it("accepts expanded-allocation number (divisible by 5 but not 10)", () => {
    // Regression guard: if the validator regresses to the stale mod-10
    // rule, this test fails.
    const result = validateTaiwanBusinessNumber(VALID_EXPANDED_ALLOCATION);
    expect(result).toEqual({ valid: true });
  });
});

// ── Invalid cases ────────────────────────────────────────────────────────

describe("invalid business numbers", () => {
  it("rejects an invalid checksum mutation", () => {
    const result = validateTaiwanBusinessNumber(INVALID_CHECKSUM_MUTATION);
    expect(result.valid).toBe(false);
    expect(result.error).toBeDefined();
    expect(result.error!.toLowerCase()).toContain("checksum");
  });

  it("rejects a short input", () => {
    const result = validateTaiwanBusinessNumber(INVALID_FORMAT_SHORT);
    expect(result.valid).toBe(false);
    expect(result.error).toContain("8 digits");
  });

  it("rejects a long input", () => {
    const result = validateTaiwanBusinessNumber(INVALID_FORMAT_LONG);
    expect(result.valid).toBe(false);
    expect(result.error).toContain("8 digits");
  });

  it("rejects an empty string", () => {
    const result = validateTaiwanBusinessNumber("");
    expect(result.valid).toBe(false);
  });

  it("passes 00000000 (valid by checksum; higher-level rules may reject)", () => {
    const result = validateTaiwanBusinessNumber("00000000");
    expect(result.valid).toBe(true);
  });
});

// ── Normalization ────────────────────────────────────────────────────────

describe("input normalization", () => {
  it("strips hyphens", () => {
    expect(validateTaiwanBusinessNumber("0459-5257")).toEqual({ valid: true });
  });

  it("strips spaces", () => {
    expect(validateTaiwanBusinessNumber("04595 257")).toEqual({ valid: true });
  });

  it("strips mixed non-digit characters", () => {
    expect(validateTaiwanBusinessNumber("04-59 52.57")).toEqual({ valid: true });
  });

  it("rejects non-digit-only input", () => {
    const result = validateTaiwanBusinessNumber("abcdefgh");
    expect(result.valid).toBe(false);
    expect(result.error).toContain("8 digits");
  });
});

// ── Structured result contract ───────────────────────────────────────────

describe("result contract", () => {
  it("returns no error field on valid input", () => {
    const result = validateTaiwanBusinessNumber(VALID_STANDARD);
    expect(result.valid).toBe(true);
    expect(result.error).toBeUndefined();
  });

  it("returns a non-empty error string on invalid input", () => {
    const result = validateTaiwanBusinessNumber(INVALID_CHECKSUM_MUTATION);
    expect(result.valid).toBe(false);
    expect(typeof result.error).toBe("string");
    expect(result.error!.length).toBeGreaterThan(0);
  });
});
