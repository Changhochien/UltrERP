"""Shared inventory domain exceptions.

These types define the stable error contract for both the legacy
``services.py`` surface and the newer modular command/query packages.
"""

from __future__ import annotations


class InsufficientStockError(Exception):
    """Raised when a transfer or adjustment exceeds available stock."""

    def __init__(self, available: int = 0, requested: int = 0) -> None:
        self.available = available
        self.requested = requested
        super().__init__(
            f"Insufficient stock: available={available}, requested={requested}",
        )


class TransferValidationError(Exception):
    """Raised for invalid stock transfer or adjustment parameters."""


class PhysicalCountNotFoundError(Exception):
    """Raised when a physical count session or line does not exist."""


class PhysicalCountConflictError(Exception):
    """Raised when a physical count operation conflicts with live stock."""


class PhysicalCountStateError(Exception):
    """Raised when a physical count action is invalid for the current state."""