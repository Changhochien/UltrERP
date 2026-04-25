"""Shared category helpers for intelligence services."""

from .constants import EXCLUDED_CATEGORIES


def is_excluded_category(category: str | None) -> bool:
    """Check if a category should be excluded from analytics."""
    if category is None:
        return True
    return category.strip().casefold() in EXCLUDED_CATEGORIES
