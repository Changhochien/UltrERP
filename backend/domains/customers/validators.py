"""Taiwan business number (統一編號) validation.

Implements the weighted checksum algorithm per current Ministry of Finance
guidance, including the post-2023 divisibility-by-5 revision for expanded
allocations and the special-case handling when the seventh digit is 7.

NOTE: Older repo artifacts and the MIG PoC use "MOD11" or mod-10 shorthand.
Those describe the pre-expansion rule. The revised rule (sum % 5 == 0) is
backwards-compatible: any value divisible by 10 is also divisible by 5, so
legacy BANs still pass.

Reference:
  https://www.ntbna.gov.tw/singlehtml/bbabfd4af20541b7859b4c5a099081f6
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_WEIGHTS = (1, 2, 1, 2, 1, 2, 4, 1)
_DIGITS_ONLY = re.compile(r"\D")


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Structured outcome for business-number validation."""

    valid: bool
    error: str | None = None


def _digit_sum(n: int) -> int:
    """Sum the decimal digits of *n* (e.g. 28 → 2+8 = 10)."""
    if n < 10:
        return n
    return (n // 10) + (n % 10)


def validate_taiwan_business_number(raw: str) -> ValidationResult:
    """Validate a Taiwan business number (統一編號).

    1. Normalize to digits-only.
    2. Reject if not exactly 8 digits.
    3. Apply weights ``1,2,1,2,1,2,4,1``, split two-digit products into
       their decimal digit sum, then total.
    4. Accept when ``total % 5 == 0``.
    5. Special case: if the seventh digit is ``7``, also accept when
       ``(total + 1) % 5 == 0``.

    Returns a :class:`ValidationResult` with ``valid=True`` on success,
    or ``valid=False`` with a human-readable ``error`` message.
    """
    normalized = _DIGITS_ONLY.sub("", raw)

    if len(normalized) != 8:
        return ValidationResult(
            valid=False,
            error=f"Business number must be exactly 8 digits, got {len(normalized)}.",
        )

    digits = tuple(int(ch) for ch in normalized)
    total = sum(_digit_sum(d * w) for d, w in zip(digits, _WEIGHTS))

    if total % 5 == 0:
        return ValidationResult(valid=True)

    # Special case: seventh digit is 7 → accept (total + 1) % 5 == 0
    if digits[6] == 7 and (total + 1) % 5 == 0:
        return ValidationResult(valid=True)

    return ValidationResult(
        valid=False,
        error="Business number checksum is invalid.",
    )
