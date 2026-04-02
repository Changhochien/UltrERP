"""Tests for invoice PDF export — HTML template and validation."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from domains.customers.models import Customer  # noqa: F401  — mapper resolution
from domains.invoices.models import Invoice, InvoiceLine
from domains.invoices.pdf import (
	DEFAULT_SELLER,
	SellerInfo,
	_format_amount,
	_format_date,
	generate_invoice_pdf,
	pdf_filename,
	render_invoice_html,
)


# ── Helpers ───────────────────────────────────────────────────────────

_TENANT = uuid.UUID("00000000-0000-0000-0000-000000000001")
_INVOICE_ID = uuid.uuid4()


def _make_line(**overrides) -> InvoiceLine:
	defaults = dict(
		id=uuid.uuid4(),
		invoice_id=_INVOICE_ID,
		tenant_id=_TENANT,
		line_number=1,
		product_id=None,
		product_code_snapshot="A001",
		description="測試品項",
		quantity=Decimal("10"),
		unit_price=Decimal("100"),
		subtotal_amount=Decimal("1000"),
		tax_type=1,
		tax_rate=Decimal("0.05"),
		tax_amount=Decimal("50"),
		total_amount=Decimal("1050"),
		zero_tax_rate_reason=None,
	)
	defaults.update(overrides)
	return InvoiceLine(**defaults)


def _make_invoice(*, lines: list[InvoiceLine] | None = None, **overrides) -> Invoice:
	defaults = dict(
		id=_INVOICE_ID,
		tenant_id=_TENANT,
		invoice_number="AA00000001",
		invoice_date=date(2025, 3, 15),
		customer_id=uuid.uuid4(),
		buyer_type="B2B",
		buyer_identifier_snapshot="12345678",
		currency_code="TWD",
		subtotal_amount=Decimal("1000"),
		tax_amount=Decimal("50"),
		total_amount=Decimal("1050"),
		status="issued",
		version=1,
	)
	defaults.update(overrides)
	inv = Invoice(**defaults)
	inv.lines = lines if lines is not None else [_make_line()]
	return inv


SELLER = SellerInfo(name="Test Co", address="台中市", phone="04-1234", fax="04-5678")


# ── Format helpers ────────────────────────────────────────────────────

class TestFormatDate:
	def test_standard(self):
		assert _format_date(date(2025, 3, 5)) == "2025 年 03 月 05 日"

	def test_december(self):
		assert _format_date(date(2025, 12, 31)) == "2025 年 12 月 31 日"


class TestFormatAmount:
	def test_integer(self):
		assert _format_amount(Decimal("1000")) == "1,000"

	def test_fractional(self):
		assert _format_amount(Decimal("1000.50")) == "1,000.50"

	def test_zero(self):
		assert _format_amount(Decimal("0")) == "0"


# ── HTML rendering ────────────────────────────────────────────────────

class TestRenderInvoiceHtml:
	def test_contains_seller_name(self):
		html = render_invoice_html(_make_invoice(), SELLER)
		assert "Test Co" in html

	def test_contains_invoice_number(self):
		html = render_invoice_html(_make_invoice(), SELLER)
		assert "AA00000001" in html

	def test_contains_formatted_date(self):
		html = render_invoice_html(_make_invoice(), SELLER)
		assert "2025 年 03 月 15 日" in html

	def test_contains_buyer_identifier(self):
		html = render_invoice_html(_make_invoice(), SELLER)
		assert "12345678" in html

	def test_contains_line_description(self):
		html = render_invoice_html(_make_invoice(), SELLER)
		assert "測試品項" in html

	def test_contains_line_amounts(self):
		html = render_invoice_html(_make_invoice(), SELLER)
		assert "1,000" in html
		assert "1,050" in html

	def test_contains_totals(self):
		html = render_invoice_html(_make_invoice(), SELLER)
		assert "合　　計" in html
		assert "營業稅" in html
		assert "總　　計" in html

	def test_contains_css_classes(self):
		html = render_invoice_html(_make_invoice(), SELLER)
		assert "ips-grid" in html
		assert "ips-footer-right" in html
		assert "ips-header" in html

	def test_contains_page_size(self):
		html = render_invoice_html(_make_invoice(), SELLER)
		assert "A5 landscape" in html

	def test_escapes_html_in_description(self):
		line = _make_line(description='<script>alert("xss")</script>')
		html = render_invoice_html(_make_invoice(lines=[line]), SELLER)
		assert "<script>" not in html
		assert "&lt;script&gt;" in html

	def test_default_seller(self):
		html = render_invoice_html(_make_invoice())
		assert DEFAULT_SELLER.name in html

	def test_multiple_lines(self):
		lines = [
			_make_line(description="第一項", product_code_snapshot="B001"),
			_make_line(description="第二項", product_code_snapshot="B002"),
		]
		html = render_invoice_html(_make_invoice(lines=lines), SELLER)
		assert "第一項" in html
		assert "第二項" in html
		assert "B001" in html
		assert "B002" in html


# ── PDF filename ──────────────────────────────────────────────────────

class TestPdfFilename:
	def test_format(self):
		inv = _make_invoice(invoice_number="BB00000042")
		assert pdf_filename(inv) == "invoice-BB00000042.pdf"


# ── Validation gates ─────────────────────────────────────────────────

class TestGeneratePdfValidation:
	def test_rejects_voided_invoice(self):
		inv = _make_invoice(status="voided")
		with pytest.raises(ValueError, match="voided"):
			generate_invoice_pdf(inv, SELLER)

	def test_rejects_empty_lines(self):
		inv = _make_invoice(lines=[])
		with pytest.raises(ValueError, match="no line items"):
			generate_invoice_pdf(inv, SELLER)
