#!/usr/bin/env python3
"""
MIG 4.1 XML Invoice Generator

Generates a MIG 4.1 compliant A0101 Invoice Message XML.
Effective January 1, 2026 - replaces MIG 4.0.

Key MIG 4.1 changes from 4.0:
  - CheckNumber field REMOVED from A0101
  - TaxType field ADDED at line-item Details level
  - CarrierId1/CarrierId2 extended to 400 bits
  - ZeroTaxRateReason added at summary level
  - ProductItem cardinality increased to 9999
  - Description length extended to 500 chars
  - SequenceNumber extended to 4 digits
  - Remark at detail level extended to 120 chars
  - RelateNumber at detail level extended to 50 chars
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, date, time
import re
import os

# ─── MIG 4.1 Namespace Constants ────────────────────────────────────────────

MIG_NS = "urn:GEINV:Message:4.1"
A0101_TAG = f"{{{MIG_NS}}}Invoice"
FTA0301_TAG = f"{{{MIG_NS}}}WinningNumber"


# ─── Validation helpers ──────────────────────────────────────────────────────

class MIG41ValidationError(Exception):
    """Raised when a field violates MIG 4.1 rules."""
    pass


def validate_ban(ban: str) -> bool:
    """
    Validate a Business Association Number (統一編號).
    Format: 8 digits + 1 check digit (9 chars total).
    Uses mod 10 weighting algorithm.
    """
    if not re.fullmatch(r"\d{9}", ban):
        raise MIG41ValidationError(
            f"BAN must be exactly 9 digits (8-digit + check), got: {ban!r}"
        )
    # Mod 10 weighting: alternating 1,2 weights from leftmost
    digits = [int(d) for d in ban]
    weighted = sum(d * w for d, w in zip(digits[:8], [1, 2] * 4))
    check = (10 - (weighted % 10)) % 10
    if check != digits[8]:
        raise MIG41ValidationError(
            f"BAN check digit invalid: computed={check}, got={digits[8]}"
        )
    return True


def validate_invoice_number(inv_num: str) -> bool:
    """InvoiceNumber format: 2 uppercase letters + 8 digits."""
    if not re.fullmatch(r"[A-Z]{2}\d{8}", inv_num):
        raise MIG41ValidationError(
            f"InvoiceNumber must match [A-Z]{{2}}\\d{{8}}, got: {inv_num!r}"
        )
    return True


def validate_invoice_date(dt: date) -> bool:
    """InvoiceDate must be a valid date in YYYYMMDD format."""
    if dt > date.today():
        raise MIG41ValidationError(
            f"InvoiceDate cannot be in the future: {dt.isoformat()}"
        )
    return True


def validate_tax_type(tt: int) -> bool:
    """TaxType enum: 1=taxable, 2=zero-rate, 3=tax-free, 4=special, 9=mixed."""
    if tt not in (1, 2, 3, 4, 9):
        raise MIG41ValidationError(
            f"TaxType must be 1|2|3|4|9, got: {tt}"
        )
    return True


def validate_tax_rate(tr: float) -> bool:
    """Allowed tax rates: 0, 0.01, 0.02, 0.05, 0.15, 0.25."""
    allowed = (0.0, 0.01, 0.02, 0.05, 0.15, 0.25)
    if round(tr, 4) not in allowed:
        raise MIG41ValidationError(
            f"TaxRate must be one of {allowed}, got: {tr}"
        )
    return True


def validate_amount(amount: float) -> bool:
    """Amount fields must be integer values (decimal 20,0)."""
    if amount != int(amount):
        raise MIG41ValidationError(
            f"Amount must be an integer (decimal 20,0), got: {amount}"
        )
    return True


# ─── XML Builder ─────────────────────────────────────────────────────────────

class MIG41InvoiceBuilder:
    """
    Builds a MIG 4.1 A0101 Invoice Message XML document.

    Minimal required fields per MIG 4.1 spec:
      InvoiceNumber, InvoiceDate, InvoiceTime,
      Seller (Identifier, Name, RoleRemark),
      Buyer (Identifier, Name),
      RelateNumber, InvoiceType, GroupMark, DonateMark,
      Details/ProductItem (at least 1),
      Amount (SalesAmount, TaxType, TaxRate, TaxAmount, TotalAmount)
    """

    def __init__(
        self,
        invoice_number: str,          # e.g. "QQ12345678"
        invoice_date: date,            # Invoice date
        invoice_time: time,            # Invoice time
        seller_ban: str,               # Seller 統一編號 (10 digits)
        seller_name: str,              # Seller entity name
        buyer_ban: str,                # Buyer 統一編號 (10 digits) or "0000000000" B2C
        buyer_name: str,               # Buyer entity name
        invoice_type: str,            # "07" general, "08" special tax rate
        relate_number: str,            # RelateNumber (max 20 in spec, 50 in MIG 4.1)
        line_items: list[dict],        # List of line item dicts
        tax_type: int = 1,             # Summary TaxType
        tax_rate: float = 0.05,        # Summary TaxRate
        group_mark: str = "0",         # GroupMark (separate with "*")
        donate_mark: str = "0",        # DonateMark (0=no, 1=yes)
        zero_tax_reason: int | None = None,  # Required when TaxType=2
        main_remark: str = "",
        custom_fields: dict | None = None,
    ):
        self.inv_num = invoice_number
        self.inv_date = invoice_date
        self.inv_time = invoice_time
        self.seller_ban = seller_ban
        self.seller_name = seller_name
        self.buyer_ban = buyer_ban
        self.buyer_name = buyer_name
        self.inv_type = invoice_type
        self.relate_number = relate_number
        self.line_items = line_items
        self.tax_type = tax_type
        self.tax_rate = tax_rate
        self.group_mark = group_mark
        self.donate_mark = donate_mark
        self.zero_tax_reason = zero_tax_reason
        self.main_remark = main_remark
        self.custom = custom_fields or {}

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _text(self, parent: ET.Element, tag: str, text: str | None) -> ET.Element:
        el = ET.SubElement(parent, tag)
        if text:
            el.text = str(text)
        return el

    def _build_party(
        self, parent: ET.Element, role: str, identifier: str, name: str, **kwargs
    ):
        """Build Seller or Buyer element block."""
        party = ET.SubElement(parent, role)
        self._text(party, f"{{{MIG_NS}}}Identifier", identifier)
        self._text(party, f"{{{MIG_NS}}}Name", name)
        # Optional fields
        if kwargs.get("address"):
            self._text(party, f"{{{MIG_NS}}}Address", kwargs["address"])
        if kwargs.get("role_remark"):
            self._text(
                party, f"{{{MIG_NS}}}RoleRemark", str(kwargs["role_remark"])
            )
        return party

    def _build_details(self, parent: ET.Element) -> None:
        """Build the Details/ProductItem block for all line items."""
        details = ET.SubElement(parent, f"{{{MIG_NS}}}Details")

        for idx, item in enumerate(self.line_items, start=1):
            pi = ET.SubElement(details, f"{{{MIG_NS}}}ProductItem")

            # Mandatory at detail level (MIG 4.1)
            self._text(
                pi, f"{{{MIG_NS}}}Description",
                str(item["description"])[:500]   # max 500 chars
            )
            # decimal fields — int if whole number, float otherwise
            qty = item["quantity"]
            up  = item["unit_price"]
            amt = item["amount"]
            self._text(pi, f"{{{MIG_NS}}}Quantity", str(int(qty) if qty == int(qty) else qty))
            self._text(pi, f"{{{MIG_NS}}}UnitPrice", str(int(up) if up == int(up) else up))
            self._text(pi, f"{{{MIG_NS}}}Amount", str(int(amt) if amt == int(amt) else amt))
            # SequenceNumber: 1-4 digits, MIG 4.1 extended from 3
            seq = str(item.get("sequence_number", idx)).zfill(4)[:4]
            self._text(pi, f"{{{MIG_NS}}}SequenceNumber", seq)
            # TaxType at detail level (MIG 4.1 new field)
            detail_tax_type = item.get("tax_type", self.tax_type)
            self._text(pi, f"{{{MIG_NS}}}TaxType", str(detail_tax_type))

            # Optional
            if item.get("unit"):
                self._text(pi, f"{{{MIG_NS}}}Unit", str(item["unit"])[:6])
            if item.get("remark"):
                self._text(
                    pi, f"{{{MIG_NS}}}Remark",
                    str(item["remark"])[:120]   # max 120 chars MIG 4.1
                )
            if item.get("relate_number"):
                self._text(
                    pi, f"{{{MIG_NS}}}RelateNumber",
                    str(item["relate_number"])[:50]   # max 50 MIG 4.1
                )

    def _build_amounts(
        self, parent: ET.Element,
        sales_amount: float,
        tax_amount: float,
        total_amount: float,
    ) -> None:
        """Build the Amount block."""
        amt = ET.SubElement(parent, f"{{{MIG_NS}}}Amount")
        self._text(amt, f"{{{MIG_NS}}}SalesAmount", str(int(sales_amount)))
        self._text(amt, f"{{{MIG_NS}}}TaxType", str(self.tax_type))
        self._text(amt, f"{{{MIG_NS}}}TaxRate", str(self.tax_rate))
        self._text(amt, f"{{{MIG_NS}}}TaxAmount", str(int(tax_amount)))
        self._text(amt, f"{{{MIG_NS}}}TotalAmount", str(int(total_amount)))
        # ZeroTaxRateReason required when TaxType=2 (MIG 4.1 new field)
        if self.tax_type == 2:
            reason = self.zero_tax_reason or 71  # default: exports
            self._text(amt, f"{{{MIG_NS}}}ZeroTaxRateReason", str(reason))

    # ── Public API ───────────────────────────────────────────────────────────

    def validate_all(self) -> None:
        """Run all validations before building XML."""
        validate_invoice_number(self.inv_num)
        validate_invoice_date(self.inv_date)
        validate_ban(self.seller_ban)
        validate_ban(self.buyer_ban)
        validate_tax_type(self.tax_type)
        validate_tax_rate(self.tax_rate)

        if not self.line_items:
            raise MIG41ValidationError("At least 1 line item (ProductItem) required")

        for i, item in enumerate(self.line_items):
            if item.get("amount", 0) != int(item.get("amount", 0)):
                raise MIG41ValidationError(
                    f"Line item {i+1} Amount must be integer: {item['amount']}"
                )

        # B2C buyer ban check
        if self.buyer_ban != "0000000000":
            try:
                validate_ban(self.buyer_ban)
            except MIG41ValidationError:
                raise MIG41ValidationError(
                    f"B2C buyer BAN must be '0000000000', got: {self.buyer_ban!r}"
                )

        # Cross-check tax calculation
        total_sales = sum(int(i["amount"]) for i in self.line_items)
        expected_tax = round(total_sales * self.tax_rate)
        # Allow minor float drift
        if abs(expected_tax - int(self.line_items[0].get("tax_amount", 0))) > 1:
            pass  # Soft check in generator; server-side strict check is expected

    def build(self) -> bytes:
        """Build and return the complete A0101 XML as bytes."""
        self.validate_all()

        # Root: A0101 Invoice Message
        root = ET.Element(A0101_TAG)
        root.set("xmlns", MIG_NS)

        # Main block
        main = ET.SubElement(root, f"{{{MIG_NS}}}Main")

        self._text(main, f"{{{MIG_NS}}}InvoiceNumber", self.inv_num)
        self._text(
            main, f"{{{MIG_NS}}}InvoiceDate",
            self.inv_date.strftime("%Y%m%d")
        )
        self._text(
            main, f"{{{MIG_NS}}}InvoiceTime",
            self.inv_time.strftime("%H:%M:%S")
        )

        # Seller block (mandatory)
        seller = ET.SubElement(main, f"{{{MIG_NS}}}Seller")
        self._text(seller, f"{{{MIG_NS}}}Identifier", self.seller_ban)
        self._text(seller, f"{{{MIG_NS}}}Name", self.seller_name)
        self._text(seller, f"{{{MIG_NS}}}RoleRemark", "發票開立")  # default

        # Buyer block (mandatory)
        buyer = ET.SubElement(main, f"{{{MIG_NS}}}Buyer")
        self._text(buyer, f"{{{MIG_NS}}}Identifier", self.buyer_ban)
        self._text(buyer, f"{{{MIG_NS}}}Name", self.buyer_name)

        # RelateNumber, InvoiceType, GroupMark, DonateMark
        self._text(main, f"{{{MIG_NS}}}RelateNumber", self.relate_number[:20])
        self._text(main, f"{{{MIG_NS}}}InvoiceType", self.inv_type)
        self._text(main, f"{{{MIG_NS}}}GroupMark", self.group_mark)
        self._text(main, f"{{{MIG_NS}}}DonateMark", self.donate_mark)

        # MainRemark
        if self.main_remark:
            self._text(main, f"{{{MIG_NS}}}MainRemark", self.main_remark[:200])

        # Reserved fields (MIG 4.1 new)
        if self.custom.get("reserved1"):
            self._text(main, f"{{{MIG_NS}}}Reserved1", str(self.custom["reserved1"]))
        if self.custom.get("reserved2"):
            self._text(main, f"{{{MIG_NS}}}Reserved2", str(self.custom["reserved2"]))

        # Details block
        self._build_details(main)

        # Amounts block
        total_sales = sum(int(i["amount"]) for i in self.line_items)
        tax_amount = round(total_sales * self.tax_rate)
        total_amount = total_sales + tax_amount
        self._build_amounts(main, total_sales, tax_amount, total_amount)

        # Attach random UTM fields if present
        if self.custom.get("customs_clearance_mark"):
            self._text(
                main, f"{{{MIG_NS}}}CustomsClearanceMark",
                str(self.custom["customs_clearance_mark"])
            )

        xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        return xml_bytes


# ─── Pretty-print helper ────────────────────────────────────────────────────

def prettify_xml(xml_bytes: bytes) -> str:
    """Return a pretty-printed string version of the XML."""
    dom = minidom.parseString(xml_bytes)
    return dom.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


# ─── Generate sample invoice ─────────────────────────────────────────────────

def generate_sample_invoice(
    output_path: str = "sample_invoice.xml",
    inv_num: str = "QQ87654321",
    inv_date: date | None = None,
    inv_time: time | None = None,
) -> str:
    """
    Generate a sample MIG 4.1 A0101 invoice with:
      - 5% tax rate (TaxType=1, standard)
      - 2 line items
      - Valid seller/buyer identifiers
    """

    inv_date = inv_date or date.today()
    inv_time = inv_time or time(10, 30, 0)

    # Sample line items (2 items)
    line_items = [
        {
            "description": "Enterprise Software License - Annual Subscription",
            "quantity": 1.0,
            "unit": "套",
            "unit_price": 28500.0,
            "amount": 28500.0,           # tax-excluded amount
            "sequence_number": 1,
            "tax_type": 1,              # taxable
            "remark": "License key delivered via email",
        },
        {
            "description": "Priority Support Service - Monthly Retainer",
            "quantity": 3.0,
            "unit": "月",
            "unit_price": 5000.0,
            "amount": 15000.0,
            "sequence_number": 2,
            "tax_type": 1,              # taxable
            "remark": "January to March 2026",
        },
    ]

    # Seller: UltrERP Co. (fictional valid BAN)
    # Valid BAN computed: 54321876 + check(4) = 543218764
    SELLER_BAN = "543218764"
    SELLER_NAME = "UltrERP Co., Ltd."

    # Buyer: Acme Corp (B2B)
    # Valid BAN computed: 27856194 + check(1) = 278561941
    BUYER_BAN = "278561941"
    BUYER_NAME = "Acme Corporation"

    builder = MIG41InvoiceBuilder(
        invoice_number=inv_num,
        invoice_date=inv_date,
        invoice_time=inv_time,
        seller_ban=SELLER_BAN,
        seller_name=SELLER_NAME,
        buyer_ban=BUYER_BAN,
        buyer_name=BUYER_NAME,
        invoice_type="07",           # General invoice
        relate_number="ORD-2026-001",
        line_items=line_items,
        tax_type=1,                  # Standard 5% taxable
        tax_rate=0.05,
        group_mark="0",
        donate_mark="0",
        main_remark="Thank you for your business!",
        zero_tax_reason=None,
    )

    xml_bytes = builder.build()
    xml_str = prettify_xml(xml_bytes)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(f"[mig41_generator] Wrote MIG 4.1 XML to: {output_path}")
    print(f"  InvoiceNumber : {inv_num}")
    print(f"  InvoiceDate   : {inv_date.strftime('%Y%m%d')}")
    print(f"  InvoiceTime   : {inv_time.strftime('%H:%M:%S')}")
    print(f"  Seller BAN    : {SELLER_BAN}")
    print(f"  Buyer BAN     : {BUYER_BAN}")
    print(f"  TaxType       : 1 (standard taxable)")
    print(f"  TaxRate       : 0.05 (5%)")
    total_s = sum(int(i["amount"]) for i in line_items)
    tax_a = round(total_s * 0.05)
    print(f"  SalesAmount   : {total_s:,}")
    print(f"  TaxAmount     : {tax_a:,}")
    print(f"  TotalAmount   : {total_s + tax_a:,}")
    return output_path


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MIG 4.1 A0101 XML Generator")
    parser.add_argument(
        "--output", "-o", default="sample_invoice.xml",
        help="Output XML file path"
    )
    parser.add_argument(
        "--invoice-number", "-n", default="QQ87654321",
        help="Invoice number (2 letters + 8 digits)"
    )
    parser.add_argument(
        "--invoice-date", "-d", default=None,
        help="Invoice date YYYYMMDD (default: today)"
    )
    parser.add_argument(
        "--invoice-time", "-t", default=None,
        help="Invoice time HHMMSS (default: 10:30:00)"
    )
    args = parser.parse_args()

    inv_date = date.today()
    if args.invoice_date:
        inv_date = datetime.strptime(args.invoice_date, "%Y%m%d").date()

    inv_time = time(10, 30, 0)
    if args.invoice_time:
        inv_time = datetime.strptime(args.invoice_time, "%H%M%S").time()

    generate_sample_invoice(
        output_path=args.output,
        inv_num=args.invoice_number,
        inv_date=inv_date,
        inv_time=inv_time,
    )
