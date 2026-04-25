"""Pure domain helpers extracted from services.py - quantization, normalization, serialization."""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from common.errors import ValidationError

if TYPE_CHECKING:
    from common.models.category import Category


# ── Quantization constants ──────────────────────────────────────

_PLANNING_QUANTITY_QUANT = Decimal("0.001")
_PLANNING_INDEX_QUANT = Decimal("0.001")
_STANDARD_COST_QUANT = Decimal("0.0001")
_VALUATION_AMOUNT_QUANT = Decimal("0.0001")
_ZERO_QUANTITY = Decimal("0.000")

DEFAULT_UNIT_OF_MEASURE_SEEDS: tuple[tuple[str, str, int], ...] = (
    ("pcs", "Pieces", 0),
    ("kg", "Kilogram", 3),
    ("g", "Gram", 0),
    ("box", "Box", 0),
    ("carton", "Carton", 0),
    ("pallet", "Pallet", 0),
    ("liter", "Liter", 3),
    ("ml", "Milliliter", 0),
    ("meter", "Meter", 3),
    ("cm", "Centimeter", 0),
)

SUPPORTED_CATEGORY_LOCALES: tuple[str, ...] = ("en", "zh-Hant")
DEFAULT_CATEGORY_LOCALE = "en"
ZH_HANT_LOCALE = "zh-Hant"


# ── Quantization helpers ────────────────────────────────────────


def quantize_quantity(value: Decimal | int | float | None) -> Decimal:
    """Quantize a quantity value for planning precision."""
    return Decimal(str(value or "0")).quantize(
        _PLANNING_QUANTITY_QUANT, rounding=ROUND_HALF_UP
    )


def quantize_index(value: Decimal) -> Decimal:
    """Quantize an index value."""
    return value.quantize(_PLANNING_INDEX_QUANT, rounding=ROUND_HALF_UP)


def quantize_valuation_amount(value: Decimal | int | float | None) -> Decimal:
    """Quantize a monetary/valuation amount."""
    return Decimal(str(value or "0")).quantize(
        _VALUATION_AMOUNT_QUANT, rounding=ROUND_HALF_UP
    )


def normalize_standard_cost(value: object | None) -> Decimal | None:
    """Normalize and validate a standard cost value."""
    if value is None or value == "":
        return None

    standard_cost = value if isinstance(value, Decimal) else Decimal(str(value))
    if standard_cost < 0:
        raise ValidationError(
            [
                {
                    "loc": ("standard_cost",),
                    "msg": "standard_cost must be greater than or equal to 0",
                    "type": "value_error",
                }
            ]
        )
    return standard_cost.quantize(_STANDARD_COST_QUANT, rounding=ROUND_HALF_UP)


def normalize_unit_code(value: str) -> str:
    """Normalize a unit of measure code."""
    normalized = value.strip().lower()
    if not normalized:
        raise ValidationError(
            [{"loc": ("code",), "msg": "code cannot be blank", "type": "value_error"}]
        )
    return normalized


def normalize_unit_name(value: str) -> str:
    """Normalize a unit of measure name."""
    normalized = value.strip()
    if not normalized:
        raise ValidationError(
            [{"loc": ("name",), "msg": "name cannot be blank", "type": "value_error"}]
        )
    return normalized


def normalize_optional_product_text(value: str | None) -> str | None:
    """Normalize an optional text field, returning None for empty strings."""
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def normalize_category_name(name: str) -> str:
    """Normalize a category name."""
    normalized = name.strip()
    if not normalized:
        raise ValidationError(
            [{"loc": ("name",), "msg": "name cannot be blank", "type": "value_error"}]
        )
    return normalized


def normalize_category_locale(locale: str | None) -> str | None:
    """Normalize a locale string to a supported locale."""
    if locale is None:
        return None

    normalized = locale.strip().replace("_", "-")
    if not normalized:
        return None

    lower = normalized.lower()
    if lower.startswith("zh-hant"):
        return ZH_HANT_LOCALE
    if lower.startswith("en"):
        return DEFAULT_CATEGORY_LOCALE
    if normalized in SUPPORTED_CATEGORY_LOCALES:
        return normalized
    return None


def resolve_category_locale(
    locale: str | None,
    accept_language: str | None = None,
) -> str:
    """Resolve a locale string to a supported locale."""
    normalized = normalize_category_locale(locale)
    if normalized is not None:
        return normalized

    if accept_language:
        for candidate in accept_language.split(","):
            language_tag = candidate.split(";", 1)[0].strip()
            normalized = normalize_category_locale(language_tag)
            if normalized is not None:
                return normalized

    return DEFAULT_CATEGORY_LOCALE


def normalize_category_translations(
    translations: dict[str, str] | None,
) -> dict[str, str]:
    """Normalize category translations dictionary."""
    normalized: dict[str, str] = {}
    if not translations:
        return normalized

    errors: list[dict[str, str | tuple[str, ...]]] = []
    for locale, value in translations.items():
        normalized_locale = normalize_category_locale(locale)
        if normalized_locale is None:
            errors.append(
                {
                    "loc": ("translations", locale),
                    "msg": "unsupported locale",
                    "type": "value_error",
                }
            )
            continue
        try:
            normalized[normalized_locale] = normalize_category_name(value)
        except ValidationError:
            errors.append(
                {
                    "loc": ("translations", normalized_locale),
                    "msg": "name cannot be blank",
                    "type": "value_error",
                }
            )

    if errors:
        raise ValidationError(errors)

    return normalized


def category_translation_map(category: Category) -> dict[str, str]:
    """Build a translation map from a category entity."""
    translations = {t.locale: t.name for t in category.translations}
    if DEFAULT_CATEGORY_LOCALE not in translations and category.name:
        translations[DEFAULT_CATEGORY_LOCALE] = category.name
    return translations


def localized_category_name(
    category: Category | None,
    locale: str,
    *,
    fallback_name: str | None = None,
) -> str | None:
    """Get the localized name for a category."""
    if category is None:
        return fallback_name

    translations = category_translation_map(category)
    return (
        translations.get(locale)
        or translations.get(DEFAULT_CATEGORY_LOCALE)
        or category.name
        or fallback_name
    )


def serialize_category(category: Category, locale: str) -> dict[str, object]:
    """Serialize a category to a dictionary."""
    translations = category_translation_map(category)
    return {
        "id": category.id,
        "tenant_id": category.tenant_id,
        "name": translations.get(locale) or translations.get(DEFAULT_CATEGORY_LOCALE) or category.name,
        "name_en": translations.get(DEFAULT_CATEGORY_LOCALE) or category.name,
        "name_zh_hant": translations.get(ZH_HANT_LOCALE),
        "translations": translations,
        "is_active": category.is_active,
        "created_at": category.created_at,
        "updated_at": category.updated_at,
    }


# ── Month series helpers ─────────────────────────────────────────


def iter_month_starts(start_month: date, end_month: date) -> list[date]:
    """Iterate month start dates between two dates."""
    from common.time_series import shift_months as _shift_months

    month_starts: list[date] = []
    cursor = start_month
    while cursor <= end_month:
        month_starts.append(cursor)
        cursor = _shift_months(cursor, 1)
    return month_starts


def format_month(month_start: date) -> str:
    """Format a month start date as YYYY-MM."""
    return month_start.strftime("%Y-%m")
