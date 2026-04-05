"""PDF export for invoices — reuses the same layout as InvoicePrintSheet.tsx.

The HTML template mirrors the structure and CSS class names from:
  src/components/invoices/print/InvoicePrintSheet.tsx
  src/components/invoices/print/invoice-print.css

This ensures consistent output between browser print and backend PDF export.
Canonical layout specification: docs/invoices/stationery-spec.md
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from html import escape

from domains.invoices.models import Invoice


@dataclass(frozen=True)
class SellerInfo:
    """Seller identity printed on invoice header."""

    name: str
    address: str
    phone: str
    fax: str


DEFAULT_SELLER = SellerInfo(
    name="UltrERP",
    address="",
    phone="",
    fax="",
)


def _format_date(d: date) -> str:
    return f"{d.year} 年 {d.month:02d} 月 {d.day:02d} 日"


def _format_amount(value: Decimal) -> str:
    n = int(value)
    if value == n:
        return f"{n:,}"
    return f"{value:,.2f}"


def _esc(value: str | None) -> str:
    return escape(value or "")


# ──────────────────────────────────────────────────────────────────────
# Embedded CSS — identical rules to invoice-print.css
# ──────────────────────────────────────────────────────────────────────

_CSS = """\
@page {
	size: A5 landscape;
	margin: 8mm 18mm 8mm 8mm;
}
body {
	margin: 0; padding: 0;
	font-family: "Noto Sans TC", "Microsoft JhengHei", system-ui, sans-serif;
	font-size: 9pt; color: #000;
}
.invoice-print-sheet {
	width: 184mm; min-height: 132mm; box-sizing: border-box;
}
.ips-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2mm;
}
.ips-header-left { display: flex; flex-direction: column; gap: 1mm; }
.ips-company-name { font-size: 11pt; font-weight: 700; }
.ips-header-right { text-align: right; font-size: 8pt; line-height: 1.6; }
.ips-doc-row { display: flex; justify-content: space-between; margin-bottom: 2mm; font-size: 10pt; }
.ips-customer {
  display: flex;
  justify-content: space-between;
  border: 0.5pt solid #333;
  padding: 1.5mm 2mm;
  margin-bottom: 2mm;
  font-size: 8pt;
  line-height: 1.8;
}
.ips-customer-left { flex: 1; display: flex; flex-direction: column; }
.ips-customer-right { flex: 0 0 35%; display: flex; flex-direction: column; }
.ips-field-label { font-weight: 600; margin-right: 1mm; }
.ips-grid { width: 100%; border-collapse: collapse; font-size: 8pt; margin-bottom: 2mm; }
.ips-grid th, .ips-grid td { border: 0.5pt solid #333; padding: 1mm 2mm; }
.ips-grid th { font-weight: 600; text-align: center; height: 8mm; }
.ips-grid td { height: 6mm; vertical-align: middle; }
.ips-grid tbody tr:nth-child(even) { background-color: #f0f0f0; }
.ips-col-code { width: 24mm; text-align: left; }
.ips-col-desc { width: 52mm; text-align: left; }
.ips-col-qty { width: 18mm; text-align: right; }
.ips-col-unit { width: 12mm; text-align: center; }
.ips-col-price { width: 22mm; text-align: right; }
.ips-col-net { width: 22mm; text-align: right; }
.ips-col-amount { width: 34mm; text-align: right; }
.ips-footer {
  display: grid;
  grid-template-columns: 76mm 1fr;
  border: 0.5pt solid #333;
  font-size: 8pt;
}
.ips-footer-left { border-right: 0.5pt solid #333; padding: 1.5mm 2mm; }
.ips-footer-right { padding: 1.5mm 2mm; }
.ips-footer-row { display: flex; justify-content: space-between; line-height: 2; }
.ips-footer-notes {
  display: flex;
  justify-content: space-between;
  border-top: 0.5pt solid #333;
  padding: 1.5mm 2mm;
  min-height: 8mm;
}
.ips-footer-notes-left { flex: 1; }
.ips-footer-notes-right { flex: 0 0 35%; text-align: center; }
"""


def render_invoice_html(
    invoice: Invoice,
    seller: SellerInfo = DEFAULT_SELLER,
) -> str:
    """Generate HTML matching InvoicePrintSheet.tsx structure."""
    lines_html = ""
    for line in invoice.lines:
        lines_html += (
            f"<tr>"
            f'<td class="ips-col-code">{_esc(line.product_code_snapshot)}</td>'
            f'<td class="ips-col-desc">{_esc(line.description)}</td>'
            f'<td class="ips-col-qty">{line.quantity}</td>'
            f'<td class="ips-col-unit">個</td>'
            f'<td class="ips-col-price">{_format_amount(line.unit_price)}</td>'
            f'<td class="ips-col-net">{_format_amount(line.subtotal_amount)}</td>'
            f'<td class="ips-col-amount">{_format_amount(line.total_amount)}</td>'
            f"</tr>\n"
        )

    return f"""\
<!DOCTYPE html>
<html lang="zh-TW">
<head><meta charset="utf-8"><style>{_CSS}</style></head>
<body>
<div class="invoice-print-sheet">

<div class="ips-header">
  <div class="ips-header-left">
    <span class="ips-company-name">{_esc(seller.name)}</span>
  </div>
  <div class="ips-header-right">
    <div>{_esc(seller.address)}</div>
    <div>TEL:{_esc(seller.phone)} FAX:{_esc(seller.fax)}</div>
  </div>
</div>

<div class="ips-doc-row">
  <span class="ips-date">{_format_date(invoice.invoice_date)}</span>
  <span class="ips-doc-number">
    <span class="ips-field-label">單據號碼：</span>{_esc(invoice.invoice_number)}
  </span>
</div>

<div class="ips-customer">
  <div class="ips-customer-left">
    <div>
      <span class="ips-field-label">統一編號：</span>
      {_esc(invoice.buyer_identifier_snapshot)}
    </div>
  </div>
</div>

<table class="ips-grid">
  <thead>
    <tr>
      <th class="ips-col-code">產品編號</th>
      <th class="ips-col-desc">品名規格</th>
      <th class="ips-col-qty">數量</th>
      <th class="ips-col-unit">單位</th>
      <th class="ips-col-price">單價</th>
      <th class="ips-col-net">實價</th>
      <th class="ips-col-amount">金額</th>
    </tr>
  </thead>
  <tbody>
{lines_html}  </tbody>
</table>

<div class="ips-footer">
  <div class="ips-footer-left">
    <div class="ips-footer-row"><span class="ips-field-label">折讓</span><span></span></div>
    <div class="ips-footer-row"><span class="ips-field-label">未收款</span><span></span></div>
  </div>
  <div class="ips-footer-right">
    <div class="ips-footer-row">
      <span class="ips-field-label">合　　計</span>
      <span>{_format_amount(invoice.subtotal_amount)}</span>
    </div>
    <div class="ips-footer-row">
      <span class="ips-field-label">營業稅</span>
      <span>{_format_amount(invoice.tax_amount)}</span>
    </div>
    <div class="ips-footer-row">
      <span class="ips-field-label">總　　計</span>
      <span style="font-weight:700">{_format_amount(invoice.total_amount)}</span>
    </div>
  </div>
</div>

<div class="ips-footer-notes">
  <div class="ips-footer-notes-left"><span class="ips-field-label">備註</span></div>
  <div class="ips-footer-notes-right"><span class="ips-field-label">客戶簽收</span></div>
</div>

</div>
</body>
</html>"""


def generate_invoice_pdf(
    invoice: Invoice,
    seller: SellerInfo = DEFAULT_SELLER,
) -> bytes:
    """Render invoice HTML to PDF bytes via WeasyPrint."""
    if invoice.status == "voided":
        raise ValueError("Cannot export a voided invoice to PDF.")
    if not invoice.lines:
        raise ValueError("Invoice has no line items.")

    html_str = render_invoice_html(invoice, seller)
    try:
        from weasyprint import HTML  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "WeasyPrint is required for PDF export. "
            "Install: pip install weasyprint  "
            "(requires system libs: pango, cairo — see https://doc.courtbouillon.org/weasyprint/stable/first_steps.html)"
        ) from exc
    return HTML(string=html_str).write_pdf()


def pdf_filename(invoice: Invoice) -> str:
    """Predictable filename: invoice-{number}.pdf"""
    safe = "".join(c for c in invoice.invoice_number if c.isalnum())
    return f"invoice-{safe}.pdf"
