/**
 * Taiwan business number (統一編號) validation.
 *
 * Implements the weighted checksum algorithm per current Ministry of Finance
 * guidance, including the post-2023 divisibility-by-5 revision for expanded
 * allocations and the special-case handling when the seventh digit is 7.
 *
 * NOTE: Older repo artifacts use "MOD11" or mod-10 shorthand — those describe
 * the pre-expansion rule. The revised rule (sum % 5 === 0) is backwards-
 * compatible: any value divisible by 10 is also divisible by 5.
 *
 * @see https://www.ntbna.gov.tw/singlehtml/bbabfd4af20541b7859b4c5a099081f6
 */

const WEIGHTS = [1, 2, 1, 2, 1, 2, 4, 1] as const;

export interface ValidationResult {
  valid: boolean;
  error?: string;
}

function digitSum(n: number): number {
  if (n < 10) return n;
  return Math.floor(n / 10) + (n % 10);
}

/**
 * Validate a Taiwan business number (統一編號).
 *
 * 1. Normalize to digits-only.
 * 2. Reject if not exactly 8 digits.
 * 3. Apply weights `1,2,1,2,1,2,4,1`, split two-digit products into
 *    their decimal digit sum, then total.
 * 4. Accept when `total % 5 === 0`.
 * 5. Special case: if the seventh digit is `7`, also accept when
 *    `(total + 1) % 5 === 0`.
 *
 * Returns a {@link ValidationResult} suitable for inline form feedback.
 */
export function validateTaiwanBusinessNumber(raw: string): ValidationResult {
  const normalized = raw.replace(/\D/g, "");

  if (normalized.length !== 8) {
    return {
      valid: false,
      error: "Business number must be exactly 8 digits.",
    };
  }

  const digits = Array.from(normalized, Number);
  const total = digits.reduce(
    (sum, d, i) => sum + digitSum(d * WEIGHTS[i]),
    0,
  );

  if (total % 5 === 0) {
    return { valid: true };
  }

  // Special case: seventh digit is 7 → accept (total + 1) % 5 === 0
  if (digits[6] === 7 && (total + 1) % 5 === 0) {
    return { valid: true };
  }

  return { valid: false, error: "Business number checksum is invalid." };
}
