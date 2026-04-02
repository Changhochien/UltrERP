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
