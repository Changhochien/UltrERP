"""Tests for MIG 4.1 XML generation, object-store archival, and metadata persistence."""

from __future__ import annotations

import hashlib
import uuid
import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from common.object_store import FailingObjectStore, InMemoryObjectStore
from domains.invoices.artifact_model import InvoiceArtifact
from domains.invoices.artifacts import (
    ARTIFACT_BUCKET,
    ARTIFACT_KIND_MIG41,
    archive_invoice_xml,
)
from domains.invoices.mig41 import MIG_NS, MIG41Error, generate_mig41_xml
from domains.invoices.models import Invoice, InvoiceLine

_TENANT = uuid.UUID("00000000-0000-0000-0000-000000000001")
_INVOICE_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _line(
    *,
    line_number: int = 1,
    description: str = "Widget",
    quantity: Decimal = Decimal("2"),
    unit_price: Decimal = Decimal("100"),
    subtotal_amount: Decimal = Decimal("200"),
    tax_type: int = 1,
    tax_rate: Decimal = Decimal("0.05"),
    tax_amount: Decimal = Decimal("10"),
    total_amount: Decimal = Decimal("210"),
    zero_tax_rate_reason: str | None = None,
) -> InvoiceLine:
    return InvoiceLine(
        id=uuid.uuid4(),
        invoice_id=_INVOICE_ID,
        tenant_id=_TENANT,
        line_number=line_number,
        description=description,
        quantity=quantity,
        unit_price=unit_price,
        subtotal_amount=subtotal_amount,
        tax_type=tax_type,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        total_amount=total_amount,
        zero_tax_rate_reason=zero_tax_rate_reason,
    )


def _invoice(
    *,
    lines: list[InvoiceLine] | None = None,
    invoice_number: str = "AB00000001",
    invoice_date: date = date(2025, 7, 1),
    subtotal_amount: Decimal = Decimal("200"),
    tax_amount: Decimal = Decimal("10"),
    total_amount: Decimal = Decimal("210"),
    buyer_identifier_snapshot: str = "04595257",
) -> Invoice:
    inv = Invoice(
        id=_INVOICE_ID,
        tenant_id=_TENANT,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        customer_id=uuid.uuid4(),
        buyer_type="B2B",
        buyer_identifier_snapshot=buyer_identifier_snapshot,
        currency_code="TWD",
        subtotal_amount=subtotal_amount,
        tax_amount=tax_amount,
        total_amount=total_amount,
        status="issued",
        version=1,
    )
    inv.lines = lines if lines is not None else [_line()]
    return inv


# ── FakeAsyncSession (minimal — only needs add / begin) ──


class FakeAsyncSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, instance: object) -> None:
        self.added.append(instance)

    def begin(self) -> FakeAsyncSession:
        return self

    async def __aenter__(self) -> FakeAsyncSession:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# XML Generation
# ═══════════════════════════════════════════════════════════════════════════


class TestMIG41XmlGeneration:
    """generate_mig41_xml — produces valid MIG 4.1 A0101 XML."""

    def test_generates_valid_xml_for_standard_invoice(self) -> None:
        inv = _invoice()
        xml_bytes = generate_mig41_xml(inv)

        root = ET.fromstring(xml_bytes)
        assert root.tag == f"{{{MIG_NS}}}Invoice"

    def test_invoice_number_in_xml(self) -> None:
        inv = _invoice(invoice_number="CD12345678")
        root = ET.fromstring(generate_mig41_xml(inv))

        num = root.find(f".//{{{MIG_NS}}}InvoiceNumber")
        assert num is not None
        assert num.text == "CD12345678"

    def test_invoice_date_format_yyyymmdd(self) -> None:
        inv = _invoice(invoice_date=date(2025, 1, 15))
        root = ET.fromstring(generate_mig41_xml(inv))

        dt = root.find(f".//{{{MIG_NS}}}InvoiceDate")
        assert dt is not None
        assert dt.text == "20250115"

    def test_amounts_are_integer_strings(self) -> None:
        inv = _invoice(
            subtotal_amount=Decimal("1000.50"),
            tax_amount=Decimal("50.25"),
            total_amount=Decimal("1050.75"),
        )
        root = ET.fromstring(generate_mig41_xml(inv))

        sales = root.find(f".//{{{MIG_NS}}}SalesAmount")
        tax = root.find(f".//{{{MIG_NS}}}TaxAmount")
        total = root.find(f".//{{{MIG_NS}}}TotalAmount")
        assert sales is not None and sales.text == "1000"
        assert tax is not None and tax.text == "50"
        assert total is not None and total.text == "1050"

    def test_line_items_appear_in_details(self) -> None:
        lines = [
            _line(line_number=1, description="Widget A"),
            _line(line_number=2, description="Widget B"),
        ]
        inv = _invoice(lines=lines)
        root = ET.fromstring(generate_mig41_xml(inv))

        items = root.findall(f".//{{{MIG_NS}}}ProductItem")
        assert len(items) == 2

    def test_seller_info_in_xml(self) -> None:
        inv = _invoice()
        root = ET.fromstring(generate_mig41_xml(inv, seller_ban="12345678"))

        seller_id = root.find(f".//{{{MIG_NS}}}Seller/{{{MIG_NS}}}Identifier")
        assert seller_id is not None
        assert seller_id.text == "12345678"

    def test_buyer_identifier_snapshot_in_xml(self) -> None:
        inv = _invoice(buyer_identifier_snapshot="04595257")
        root = ET.fromstring(generate_mig41_xml(inv))

        buyer_id = root.find(f".//{{{MIG_NS}}}Buyer/{{{MIG_NS}}}Identifier")
        assert buyer_id is not None
        assert buyer_id.text == "04595257"

    def test_mixed_tax_types_produce_type_9(self) -> None:
        lines = [
            _line(line_number=1, tax_type=1),
            _line(line_number=2, tax_type=2, zero_tax_rate_reason="export"),
        ]
        inv = _invoice(lines=lines)
        root = ET.fromstring(generate_mig41_xml(inv))

        amt_tax_type = root.find(f".//{{{MIG_NS}}}Amount/{{{MIG_NS}}}TaxType")
        assert amt_tax_type is not None
        assert amt_tax_type.text == "9"

    def test_zero_tax_rate_reason_present_when_type_2(self) -> None:
        lines = [_line(tax_type=2, tax_rate=Decimal("0"), zero_tax_rate_reason="export")]
        inv = _invoice(lines=lines)
        root = ET.fromstring(generate_mig41_xml(inv))

        reason = root.find(f".//{{{MIG_NS}}}ZeroTaxRateReason")
        assert reason is not None
        assert reason.text == "export"

    def test_special_tax_uses_invoice_type_08(self) -> None:
        lines = [_line(tax_type=4)]
        inv = _invoice(lines=lines)
        root = ET.fromstring(generate_mig41_xml(inv))

        inv_type = root.find(f".//{{{MIG_NS}}}InvoiceType")
        assert inv_type is not None
        assert inv_type.text == "08"

    def test_standard_tax_uses_invoice_type_07(self) -> None:
        inv = _invoice()
        root = ET.fromstring(generate_mig41_xml(inv))

        inv_type = root.find(f".//{{{MIG_NS}}}InvoiceType")
        assert inv_type is not None
        assert inv_type.text == "07"

    def test_raises_on_empty_lines(self) -> None:
        inv = _invoice(lines=[])

        with pytest.raises(MIG41Error, match="no line items"):
            generate_mig41_xml(inv)

    def test_sequence_number_zero_padded(self) -> None:
        inv = _invoice(lines=[_line(line_number=3)])
        root = ET.fromstring(generate_mig41_xml(inv))

        seq = root.find(f".//{{{MIG_NS}}}SequenceNumber")
        assert seq is not None
        assert seq.text == "0003"

    def test_xml_is_utf8_encoded(self) -> None:
        inv = _invoice()
        xml_bytes = generate_mig41_xml(inv)

        assert xml_bytes.startswith(b"<?xml version='1.0' encoding='utf-8'?>")


# ═══════════════════════════════════════════════════════════════════════════
# Object Key Formatting
# ═══════════════════════════════════════════════════════════════════════════


class TestObjectKeyFormatting:
    def test_key_follows_tenant_mig41_invoice_pattern(self) -> None:
        from domains.invoices.artifacts import _object_key

        inv = _invoice()
        key = _object_key(inv)

        assert key == f"{_TENANT}/mig41/{_INVOICE_ID}.xml"


# ═══════════════════════════════════════════════════════════════════════════
# Artifact Archival (upload + metadata)
# ═══════════════════════════════════════════════════════════════════════════


class TestArchiveInvoiceXml:
    """archive_invoice_xml — stores XML and records metadata."""

    @pytest.mark.asyncio
    async def test_stores_xml_in_object_store(self) -> None:
        store = InMemoryObjectStore()
        session = FakeAsyncSession()
        inv = _invoice()

        await archive_invoice_xml(session, inv, store)

        expected_key = f"{_TENANT}/mig41/{_INVOICE_ID}.xml"
        assert (ARTIFACT_BUCKET, expected_key) in store.stored

    @pytest.mark.asyncio
    async def test_stored_xml_is_parseable(self) -> None:
        store = InMemoryObjectStore()
        session = FakeAsyncSession()
        inv = _invoice()

        await archive_invoice_xml(session, inv, store)

        key = f"{_TENANT}/mig41/{_INVOICE_ID}.xml"
        xml_bytes = store.get_object(ARTIFACT_BUCKET, key)
        root = ET.fromstring(xml_bytes)
        assert root.tag == f"{{{MIG_NS}}}Invoice"

    @pytest.mark.asyncio
    async def test_persists_artifact_record(self) -> None:
        store = InMemoryObjectStore()
        session = FakeAsyncSession()
        inv = _invoice()

        artifact = await archive_invoice_xml(session, inv, store)

        assert isinstance(artifact, InvoiceArtifact)
        assert artifact.artifact_kind == ARTIFACT_KIND_MIG41
        assert artifact.content_type == "application/xml"
        assert artifact.invoice_id == _INVOICE_ID
        assert artifact.tenant_id == _TENANT
        assert artifact in session.added

    @pytest.mark.asyncio
    async def test_checksum_matches_stored_content(self) -> None:
        store = InMemoryObjectStore()
        session = FakeAsyncSession()
        inv = _invoice()

        artifact = await archive_invoice_xml(session, inv, store)

        key = f"{_TENANT}/mig41/{_INVOICE_ID}.xml"
        xml_bytes = store.get_object(ARTIFACT_BUCKET, key)
        expected_sha = hashlib.sha256(xml_bytes).hexdigest()
        assert artifact.checksum_sha256 == expected_sha

    @pytest.mark.asyncio
    async def test_byte_size_matches(self) -> None:
        store = InMemoryObjectStore()
        session = FakeAsyncSession()
        inv = _invoice()

        artifact = await archive_invoice_xml(session, inv, store)

        key = f"{_TENANT}/mig41/{_INVOICE_ID}.xml"
        xml_bytes = store.get_object(ARTIFACT_BUCKET, key)
        assert artifact.byte_size == len(xml_bytes)

    @pytest.mark.asyncio
    async def test_retention_10_year_baseline(self) -> None:
        inv = _invoice(invoice_date=date(2025, 7, 1))
        store = InMemoryObjectStore()
        session = FakeAsyncSession()

        artifact = await archive_invoice_xml(session, inv, store)

        assert artifact.retention_class == "legal-10y"
        assert artifact.retention_until == "2035-07-01"

    @pytest.mark.asyncio
    async def test_persists_custom_storage_policy(self) -> None:
        store = InMemoryObjectStore()
        session = FakeAsyncSession()
        inv = _invoice()

        artifact = await archive_invoice_xml(
            session,
            inv,
            store,
            storage_policy="object-lock-governance",
        )

        assert artifact.storage_policy == "object-lock-governance"

    @pytest.mark.asyncio
    async def test_persists_custom_retention_class(self) -> None:
        store = InMemoryObjectStore()
        session = FakeAsyncSession()
        inv = _invoice()

        artifact = await archive_invoice_xml(
            session,
            inv,
            store,
            retention_class="finance-archive-10y",
        )

        assert artifact.retention_class == "finance-archive-10y"

    @pytest.mark.asyncio
    async def test_raises_when_store_unavailable(self) -> None:
        store = FailingObjectStore()
        session = FakeAsyncSession()
        inv = _invoice()

        with pytest.raises(ConnectionError, match="unavailable"):
            await archive_invoice_xml(session, inv, store)

    @pytest.mark.asyncio
    async def test_raises_on_empty_invoice(self) -> None:
        store = InMemoryObjectStore()
        session = FakeAsyncSession()
        inv = _invoice(lines=[])

        with pytest.raises(MIG41Error, match="no line items"):
            await archive_invoice_xml(session, inv, store)
