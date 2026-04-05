"""MIG 4.1 XML generator — produces A0101 Invoice Message from persisted data.

Generates schema-valid MIG 4.1 XML from an Invoice ORM object and its loaded
InvoiceLine relations.  All values come from the persisted snapshot — never
from transient UI payloads.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import time
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domains.invoices.models import Invoice

MIG_NS = "urn:GEINV:Message:4.1"

# MIG 4.1 tax-type codes
_TAX_TYPE_LABELS = {1: "taxable", 2: "zero-rate", 3: "tax-free", 4: "special", 9: "mixed"}

# Default seller info — will come from tenant config later
_DEFAULT_SELLER_BAN = "000000000"
_DEFAULT_SELLER_NAME = "UltrERP"


class MIG41Error(Exception):
    """Raised when an invoice cannot be serialised to valid MIG 4.1 XML."""


def _text(parent: ET.Element, tag: str, value: str) -> ET.Element:
    el = ET.SubElement(parent, f"{{{MIG_NS}}}{tag}")
    el.text = value
    return el


def _int_str(d: Decimal) -> str:
    """MIG 4.1 amount fields must be integer strings (decimal 20,0)."""
    return str(int(d))


def _decimal_str(d: Decimal) -> str:
    """Quantity / unit-price may have decimals."""
    if d == int(d):
        return str(int(d))
    return str(d)


def _rate_str(d: Decimal) -> str:
    """Tax rate as a decimal fraction string (e.g. '0.05')."""
    return str(d.normalize())


def generate_mig41_xml(
    invoice: Invoice,
    *,
    seller_ban: str = _DEFAULT_SELLER_BAN,
    seller_name: str = _DEFAULT_SELLER_NAME,
    invoice_time: time | None = None,
) -> bytes:
    """Build MIG 4.1 A0101 XML from a persisted Invoice.

    Args:
            invoice: Fully loaded Invoice with .lines eagerly loaded.
            seller_ban: Seller business-association number (統一編號).
            seller_name: Seller entity name.
            invoice_time: Optional override; defaults to 00:00:00.

    Returns:
            UTF-8 encoded XML bytes.
    """
    if not invoice.lines:
        raise MIG41Error("Invoice has no line items")

    inv_time = invoice_time or time(0, 0, 0)

    root = ET.Element(f"{{{MIG_NS}}}Invoice")
    root.set("xmlns", MIG_NS)

    main = ET.SubElement(root, f"{{{MIG_NS}}}Main")

    # ── Header ──
    _text(main, "InvoiceNumber", invoice.invoice_number)
    _text(main, "InvoiceDate", invoice.invoice_date.strftime("%Y%m%d"))
    _text(main, "InvoiceTime", inv_time.strftime("%H:%M:%S"))

    # ── Seller ──
    seller = ET.SubElement(main, f"{{{MIG_NS}}}Seller")
    _text(seller, "Identifier", seller_ban)
    _text(seller, "Name", seller_name)
    _text(seller, "RoleRemark", "發票開立")

    # ── Buyer ──
    buyer = ET.SubElement(main, f"{{{MIG_NS}}}Buyer")
    _text(buyer, "Identifier", invoice.buyer_identifier_snapshot)
    # Buyer name would come from the customer record
    _text(buyer, "Name", "")

    # ── Control fields ──
    invoice_type = "08" if _has_special_tax(invoice) else "07"
    _text(main, "RelateNumber", str(invoice.id)[:20])
    _text(main, "InvoiceType", invoice_type)
    _text(main, "GroupMark", "0")
    _text(main, "DonateMark", "0")

    # ── Details ──
    details = ET.SubElement(main, f"{{{MIG_NS}}}Details")
    for line in invoice.lines:
        pi = ET.SubElement(details, f"{{{MIG_NS}}}ProductItem")
        _text(pi, "Description", line.description[:500])
        _text(pi, "Quantity", _decimal_str(line.quantity))
        _text(pi, "UnitPrice", _decimal_str(line.unit_price))
        _text(pi, "Amount", _int_str(line.subtotal_amount))
        _text(pi, "SequenceNumber", str(line.line_number).zfill(4)[:4])
        _text(pi, "TaxType", str(line.tax_type))

    # ── Amounts ──
    amt = ET.SubElement(main, f"{{{MIG_NS}}}Amount")
    _text(amt, "SalesAmount", _int_str(invoice.subtotal_amount))

    summary_tax_type = _summary_tax_type(invoice)
    _text(amt, "TaxType", str(summary_tax_type))

    if invoice.lines:
        _text(amt, "TaxRate", _rate_str(invoice.lines[0].tax_rate))
    _text(amt, "TaxAmount", _int_str(invoice.tax_amount))
    _text(amt, "TotalAmount", _int_str(invoice.total_amount))

    if summary_tax_type == 2:
        reason = _zero_tax_reason(invoice)
        if reason:
            _text(amt, "ZeroTaxRateReason", reason)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _has_special_tax(invoice: Invoice) -> bool:
    return any(line.tax_type == 4 for line in invoice.lines)


def _summary_tax_type(invoice: Invoice) -> int:
    types = {line.tax_type for line in invoice.lines}
    if len(types) == 1:
        return types.pop()
    return 9  # mixed


def _zero_tax_reason(invoice: Invoice) -> str | None:
    for line in invoice.lines:
        if line.zero_tax_rate_reason:
            return line.zero_tax_rate_reason
    return None
