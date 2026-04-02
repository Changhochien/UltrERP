"""Invoice domain enums shared across models, schemas, and services."""

from __future__ import annotations

from enum import StrEnum


class BuyerType(StrEnum):
    B2B = "b2b"
    B2C = "b2c"


class InvoiceStatus(StrEnum):
    ISSUED = "issued"
    VOIDED = "voided"


# Only these transitions are permitted.
ALLOWED_TRANSITIONS: dict[InvoiceStatus, frozenset[InvoiceStatus]] = {
    InvoiceStatus.ISSUED: frozenset({InvoiceStatus.VOIDED}),
    InvoiceStatus.VOIDED: frozenset(),
}