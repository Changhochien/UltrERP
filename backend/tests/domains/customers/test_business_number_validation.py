"""Tests for Taiwan business number (統一編號) checksum validation.

Fixtures mirror the frontend test suite in
``src/tests/customers/taiwanBusinessNumber.test.ts`` so both runtimes stay
aligned on the same official acceptance rule.

The test set explicitly covers the rule drift between older repo shorthand
(divisible-by-10 / "MOD11") and the current official guidance (divisible-by-5)
so regressions to the stale rule are caught.
"""

from domains.customers.validators import ValidationResult, validate_taiwan_business_number

# ---------------------------------------------------------------------------
# Shared fixtures — mirrored in frontend tests
# ---------------------------------------------------------------------------

# Standard direct-pass official example (sum divisible by both 5 and 10)
VALID_STANDARD = "04595257"

# Seventh-digit special-case pass (sum % 5 != 0, but (sum+1) % 5 == 0, d7==7)
VALID_SEVENTH_DIGIT_SPECIAL = "19312376"

# Expanded-allocation fixture: sum=25, divisible by 5 but NOT by 10.
# Passes the current official rule but would FAIL a stale mod-10 check.
VALID_EXPANDED_ALLOCATION = "55555555"

# Invalid checksum mutation of VALID_STANDARD (last digit changed 7→8)
INVALID_CHECKSUM_MUTATION = "04595258"

# Non-8-digit format failure
INVALID_FORMAT_SHORT = "0459525"
INVALID_FORMAT_LONG = "045952570"


# ---------------------------------------------------------------------------
# Valid cases
# ---------------------------------------------------------------------------


class TestValidBusinessNumbers:
    def test_standard_official_example(self) -> None:
        result = validate_taiwan_business_number(VALID_STANDARD)
        assert result == ValidationResult(valid=True)

    def test_seventh_digit_special_case(self) -> None:
        result = validate_taiwan_business_number(VALID_SEVENTH_DIGIT_SPECIAL)
        assert result == ValidationResult(valid=True)

    def test_expanded_allocation_passes_divisible_by_5(self) -> None:
        """Regression guard: this number is divisible by 5 but NOT by 10.

        If the validator regresses to the stale mod-10 rule, this test fails.
        """
        result = validate_taiwan_business_number(VALID_EXPANDED_ALLOCATION)
        assert result == ValidationResult(valid=True)


# ---------------------------------------------------------------------------
# Invalid cases
# ---------------------------------------------------------------------------


class TestInvalidBusinessNumbers:
    def test_invalid_checksum_mutation(self) -> None:
        result = validate_taiwan_business_number(INVALID_CHECKSUM_MUTATION)
        assert result.valid is False
        assert result.error is not None
        assert "checksum" in result.error.lower()

    def test_too_short(self) -> None:
        result = validate_taiwan_business_number(INVALID_FORMAT_SHORT)
        assert result.valid is False
        assert result.error is not None
        assert "8 digits" in result.error

    def test_too_long(self) -> None:
        result = validate_taiwan_business_number(INVALID_FORMAT_LONG)
        assert result.valid is False
        assert result.error is not None
        assert "8 digits" in result.error

    def test_empty_string(self) -> None:
        result = validate_taiwan_business_number("")
        assert result.valid is False

    def test_all_zeros(self) -> None:
        """00000000 has sum=0 which is divisible by 5 — technically valid
        by checksum alone. A higher-level business rule may reject it, but
        the checksum validator should pass it."""
        result = validate_taiwan_business_number("00000000")
        assert result.valid is True


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


class TestNormalization:
    def test_strips_hyphens(self) -> None:
        result = validate_taiwan_business_number("0459-5257")
        assert result == ValidationResult(valid=True)

    def test_strips_spaces(self) -> None:
        result = validate_taiwan_business_number("04595 257")
        assert result == ValidationResult(valid=True)

    def test_strips_mixed_non_digit_chars(self) -> None:
        result = validate_taiwan_business_number("04-59 52.57")
        assert result == ValidationResult(valid=True)

    def test_non_digit_only_input(self) -> None:
        result = validate_taiwan_business_number("abcdefgh")
        assert result.valid is False
        assert "8 digits" in (result.error or "")


# ---------------------------------------------------------------------------
# Structured result contract
# ---------------------------------------------------------------------------


class TestResultContract:
    def test_valid_result_has_no_error(self) -> None:
        result = validate_taiwan_business_number(VALID_STANDARD)
        assert result.valid is True
        assert result.error is None

    def test_invalid_result_has_error_message(self) -> None:
        result = validate_taiwan_business_number(INVALID_CHECKSUM_MUTATION)
        assert result.valid is False
        assert isinstance(result.error, str)
        assert len(result.error) > 0
