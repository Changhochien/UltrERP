# Invoice Stationery Specification

Status: **approved** — reference asset committed

## Purpose

This file is the canonical print and PDF layout contract for invoice output.
Stories 2.2 and 2.6 must comply with this contract.

## Reference Asset

- **File**: `docs/Image/Invoice image.jpg`
- **Form type**: Triplicate (三聯式) — Copy 1: 收執聯 (Receipt)
- **Company**: Configurable per tenant (reference sample: SQUAREROPE)

## Verified Constraints

- Output must match the approved pre-printed stationery exactly.
- The same renderer must drive print preview, physical print, and PDF export.
- Physical printing uses the platform print dialog from the Tauri/webview shell.
- PDF export uses backend-assisted headless browser rendering from the same HTML/CSS layout.
- Preview render performance is measured on the preview surface only; OS print dialog launch and PDF generation startup are out of scope for the < 1 second target.
- Seller name, address, and contact info are configurable — not hardcoded from the reference sample.

## Page Geometry

| Property | Value |
|----------|-------|
| Paper size | A5 landscape (210 × 148 mm) |
| Orientation | Landscape |
| Margins (top / right / bottom / left) | 8 / 18 / 8 / 8 mm |
| Printable area | 184 × 132 mm |
| Right margin reserved | 18 mm (copy label: 第一聯：收執聯) |
| Field placement tolerance | ±1 mm |

## Field Coordinate Map

All coordinates are (x, y) from top-left of printable area in mm.
Width (w) and height (h) define the bounding box.

### Header Zone (y: 0–25 mm)

| Field | x | y | w | h | Alignment | Notes |
|-------|---|---|---|---|-----------|-------|
| Company logo | 0 | 0 | 30 | 18 | left | Tenant-configurable image |
| Company name | 0 | 18 | 60 | 7 | left | Below logo |
| Company address | 100 | 0 | 84 | 7 | right | 彰化市線東路一段臨670號 |
| Company TEL/FAX | 100 | 7 | 84 | 7 | right | TEL:(04)7613535 FAX:(04)7613030 |

### Date / Document Number Row (y: 25–35 mm)

| Field | x | y | w | h | Alignment | Notes |
|-------|---|---|---|---|-----------|-------|
| Date (年月日) | 30 | 27 | 60 | 7 | center | Format: YYYY 年 MM 月 DD 日 |
| Document number (單據號碼) | 120 | 27 | 64 | 7 | left | = invoice_number |

### Customer Info Block (y: 35–60 mm)

| Field | x | y | w | h | Alignment | Notes |
|-------|---|---|---|---|-----------|-------|
| 客戶名稱 (Customer Name) | 0 | 36 | 100 | 6 | left | label + value |
| 統一編號 (Tax ID / BAN) | 0 | 42 | 100 | 6 | left | buyer_identifier_snapshot |
| 發票地址 (Invoice Address) | 0 | 48 | 100 | 6 | left | billing_address |
| 送貨地址 (Delivery Address) | 0 | 54 | 100 | 6 | left | shipping_address (optional) |
| 聯絡電話 (Contact Phone) | 120 | 36 | 64 | 6 | left | contact_phone |
| 傳真號碼 (Fax Number) | 120 | 42 | 64 | 6 | left | contact_fax (optional) |
| 聯絡人員 (Contact Person) | 120 | 54 | 64 | 6 | left | contact_name |

### Line Items Grid (y: 60–105 mm)

| Column | Label | x | w | Alignment | Data field |
|--------|-------|---|---|-----------|------------|
| 1 | 產品編號 (Product Code) | 0 | 24 | left | product_code_snapshot |
| 2 | 品名規格 (Product Name/Spec) | 24 | 52 | left | description |
| 3 | 數量 (Quantity) | 76 | 18 | right | quantity |
| 4 | 單位 (Unit) | 94 | 12 | center | unit (e.g. 個, 箱) |
| 5 | 單價 (Unit Price) | 106 | 22 | right | unit_price |
| 6 | 實價 (Net Price) | 128 | 22 | right | subtotal_amount (per line) |
| 7 | 金額 (Amount) | 150 | 34 | right | total_amount (per line, tax-inclusive) |

- Grid header row height: 8 mm
- Line row height: 6 mm
- Maximum rows: ~7 visible rows (overflow to second page)
- Alternating row shading: light grey (#f0f0f0) on even rows

### Footer Zone (y: 105–132 mm)

| Field | x | y | w | h | Alignment | Notes |
|-------|---|---|---|---|-----------|-------|
| 折讓 (Discount) label | 0 | 106 | 24 | 6 | left | Row label |
| 折讓 value | 24 | 106 | 52 | 6 | right | discount_amount |
| 實價品 label | 76 | 106 | 30 | 6 | left | "實價品" |
| 合計 (Subtotal) label | 120 | 106 | 30 | 6 | left | |
| 合計 value | 150 | 106 | 34 | 6 | right | subtotal_amount |
| 未收款 (Outstanding) label | 0 | 112 | 24 | 6 | left | Row label |
| 未收款 value | 24 | 112 | 52 | 6 | right | outstanding_amount |
| 三角帶 label | 76 | 112 | 30 | 6 | left | Category subtotal |
| 營業稅 (Tax) label | 120 | 112 | 30 | 6 | left | |
| 營業稅 value | 150 | 112 | 34 | 6 | right | tax_amount |
| | | | | | | |
| 總計 (Grand Total) label | 120 | 118 | 30 | 6 | left | |
| 總計 value | 150 | 118 | 34 | 6 | right | total_amount |
| 備註 (Notes) label | 0 | 124 | 24 | 8 | left | |
| 備註 value | 24 | 124 | 90 | 8 | left | notes_text |
| 客戶簽收 (Customer Sign) | 120 | 124 | 64 | 8 | center | Signature area |

### Right Margin Label (vertical)

| Field | x | y | w | h | Notes |
|-------|---|---|---|---|-------|
| 第一聯：收執聯 | 186 | 60 | 12 | 72 | Vertical text, pre-printed on form |

## Data Source Mapping

All rendered fields are sourced from **persisted invoice data** (Story 2.1 snapshot):

| Rendered Field | Source Model | Source Field |
|----------------|-------------|--------------|
| 單據號碼 | Invoice | invoice_number |
| 年月日 | Invoice | invoice_date |
| 客戶名稱 | Customer | company_name |
| 統一編號 | Invoice | buyer_identifier_snapshot |
| 發票地址 | Customer | billing_address |
| 聯絡電話 | Customer | contact_phone |
| 聯絡人員 | Customer | contact_name |
| 產品編號 | InvoiceLine | product_code_snapshot |
| 品名規格 | InvoiceLine | description |
| 數量 | InvoiceLine | quantity |
| 單價 | InvoiceLine | unit_price |
| 實價 | InvoiceLine | subtotal_amount |
| 金額 | InvoiceLine | total_amount |
| 合計 | Invoice | subtotal_amount |
| 營業稅 | Invoice | tax_amount |
| 總計 | Invoice | total_amount |

## Print CSS Requirements

```css
@page {
  size: A5 landscape;
  margin: 8mm 18mm 8mm 8mm;
}
```

- Font: system sans-serif (Noto Sans TC preferred for CJK)
- Font size: 9pt for body, 8pt for grid rows, 11pt for header fields
- Grid borders: 0.5pt solid #333
- No color output — monochrome compatible
- Hide browser chrome, headers, footers via `@media print`

## Acceptance Contract

- Preview and PDF must consume persisted invoice snapshot data only.
- The layout contract defines field anchors and tolerances (±1 mm) explicitly.
- Manual alignment verification must compare rendered output against `docs/Image/Invoice image.jpg` at 1:1 scale.
- Renderer must be reusable across print preview, physical print, and PDF export (Story 2.6).

## Approval Checklist

- [x] Reference asset committed (`docs/Image/Invoice image.jpg`)
- [x] Form factor identified: A5 landscape, triplicate
- [x] Field coordinates documented
- [x] Tolerance approved: ±1 mm
- [ ] Manual verification checklist approved (deferred to implementation)