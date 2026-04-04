"""Invoice domain enums shared across models, schemas, and services."""

from __future__ import annotations

from enum import StrEnum


class BuyerType(StrEnum):
    B2B = "b2b"
    B2C = "b2c"


class InvoiceStatus(StrEnum):
    ISSUED = "issued"
    VOIDED = "voided"


class EguiSubmissionStatus(StrEnum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    SENT = "SENT"
    ACKED = "ACKED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    DEAD_LETTER = "DEAD_LETTER"


# Only these transitions are permitted.
ALLOWED_TRANSITIONS: dict[InvoiceStatus, frozenset[InvoiceStatus]] = {
    InvoiceStatus.ISSUED: frozenset({InvoiceStatus.VOIDED}),
    InvoiceStatus.VOIDED: frozenset(),
}


ALLOWED_EGUI_SUBMISSION_TRANSITIONS: dict[EguiSubmissionStatus, frozenset[EguiSubmissionStatus]] = {
    EguiSubmissionStatus.PENDING: frozenset({EguiSubmissionStatus.QUEUED, EguiSubmissionStatus.FAILED}),
    EguiSubmissionStatus.QUEUED: frozenset({EguiSubmissionStatus.SENT, EguiSubmissionStatus.FAILED}),
    EguiSubmissionStatus.SENT: frozenset({EguiSubmissionStatus.ACKED, EguiSubmissionStatus.FAILED}),
    EguiSubmissionStatus.ACKED: frozenset(),
    EguiSubmissionStatus.FAILED: frozenset({EguiSubmissionStatus.RETRYING, EguiSubmissionStatus.DEAD_LETTER}),
    EguiSubmissionStatus.RETRYING: frozenset({EguiSubmissionStatus.SENT, EguiSubmissionStatus.DEAD_LETTER}),
    EguiSubmissionStatus.DEAD_LETTER: frozenset(),
}