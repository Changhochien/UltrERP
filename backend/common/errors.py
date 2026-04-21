from __future__ import annotations

import uuid
from typing import Any


class ApplicationError(Exception):
    """Base application error for service-level failures."""


class ValidationError(ApplicationError):
    """One or more fields failed validation."""

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        self.errors = errors
        super().__init__(f"Validation failed: {errors}")


class DuplicateBusinessNumberError(ApplicationError):
    """A customer with this business number already exists."""

    def __init__(
        self,
        existing_id: uuid.UUID,
        existing_name: str,
        normalized_business_number: str,
    ) -> None:
        self.existing_id = existing_id
        self.existing_name = existing_name
        self.normalized_business_number = normalized_business_number
        super().__init__(
            f"Duplicate business number {normalized_business_number}: "
            f"existing customer {existing_id} ({existing_name})"
        )


class DuplicateLeadConflictError(ApplicationError):
    """A lead collides with existing lead or customer records."""

    def __init__(self, candidates: list[dict[str, Any]]) -> None:
        self.candidates = candidates
        super().__init__(f"Duplicate lead conflict: {candidates}")


class DuplicateProductCodeError(ApplicationError):
    """A product with this code already exists for the tenant."""

    def __init__(self, existing_id: uuid.UUID, existing_code: str) -> None:
        self.existing_id = existing_id
        self.existing_code = existing_code
        super().__init__(f"Duplicate product code {existing_code}: existing product {existing_id}")


class DuplicateCategoryNameError(ApplicationError):
    """A category with this name already exists for the tenant."""

    def __init__(self, existing_id: uuid.UUID, existing_name: str) -> None:
        self.existing_id = existing_id
        self.existing_name = existing_name
        super().__init__(f"Duplicate category name {existing_name}: existing category {existing_id}")


class DuplicateUnitCodeError(ApplicationError):
    """A unit code already exists for the tenant."""

    def __init__(self, existing_id: uuid.UUID, existing_code: str) -> None:
        self.existing_id = existing_id
        self.existing_code = existing_code
        super().__init__(f"Duplicate unit code {existing_code}: existing unit {existing_id}")


class VersionConflictError(ApplicationError):
    """Optimistic locking conflict — the record was modified since last read."""

    def __init__(self, expected: int, actual: int) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Version conflict: expected {expected}, got {actual}"
        )


def error_response(errors: list[dict[str, Any]]) -> dict[str, Any]:
    """Standard structured error envelope."""
    return {"detail": errors}


def duplicate_response(err: DuplicateBusinessNumberError) -> dict[str, Any]:
    """Stable 409 duplicate error envelope."""
    return {
        "error": "duplicate_business_number",
        "existing_customer_id": str(err.existing_id),
        "existing_customer_name": err.existing_name,
        "normalized_business_number": err.normalized_business_number,
    }


def duplicate_lead_response(err: DuplicateLeadConflictError) -> dict[str, Any]:
    """Stable 409 duplicate lead guidance envelope."""
    return {
        "error": "duplicate_lead",
        "candidates": err.candidates,
    }


def duplicate_product_code_response(err: DuplicateProductCodeError) -> dict[str, Any]:
    """Stable 409 duplicate product code error envelope."""
    return {
        "error": "duplicate_product_code",
        "existing_product_id": str(err.existing_id),
        "existing_product_code": err.existing_code,
    }


def duplicate_category_name_response(err: DuplicateCategoryNameError) -> dict[str, Any]:
    """Stable 409 duplicate category name error envelope."""
    return {
        "error": "duplicate_category_name",
        "existing_category_id": str(err.existing_id),
        "existing_category_name": err.existing_name,
    }


def duplicate_unit_code_response(err: DuplicateUnitCodeError) -> dict[str, Any]:
    """Stable 409 duplicate unit code error envelope."""
    return {
        "error": "duplicate_unit_code",
        "existing_unit_id": str(err.existing_id),
        "existing_unit_code": err.existing_code,
    }
