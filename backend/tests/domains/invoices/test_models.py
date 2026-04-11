"""Regression tests for invoice model enum bindings."""

from __future__ import annotations

from sqlalchemy.dialects import postgresql

import app.main  # noqa: F401
from domains.invoices.enums import InvoiceStatus
from domains.invoices.models import Invoice


def test_invoice_status_enum_binds_lowercase_database_values() -> None:
    status_type = Invoice.__table__.c.status.type
    bind = status_type.bind_processor(postgresql.dialect())

    assert status_type.enums == ["issued", "paid", "voided"]
    assert bind is not None
    assert bind(InvoiceStatus.VOIDED) == "voided"
    assert bind("issued") == "issued"