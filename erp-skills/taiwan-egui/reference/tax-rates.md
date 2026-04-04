# Taiwan Tax Rates

## Standard VAT
- **Rate:** 5% (營業稅)
- **Applies to:** All domestic B2B and B2C sales unless exempt or zero-rated
- **Calculation:** `tax_amount = subtotal * 0.05`

## Zero-Rated (0%)
- Export sales
- Services provided to foreign entities outside Taiwan
- Goods delivered to bonded warehouses/zones

## Tax-Exempt
- Medical services
- Educational services
- Land transactions
- Financial services (certain categories)
- Agricultural products (certain categories)

## Implementation Notes
- Tax rates are stored per invoice line (`tax_rate` field on `InvoiceLine` model)
- `tax_type` field distinguishes taxable, zero-rated, and exempt
- Standard rate is applied as default; exemptions and zero-rating are explicit overrides
